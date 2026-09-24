"""Figma API and local archive state. No UI or browser dependency here."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import requests


if sys.platform == "win32":
    _local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    SUPPORT = _local_app_data / "Figma Fig Downloader"
    APP_SUPPORT = _local_app_data / "Fig Backup"
else:
    SUPPORT = Path.home() / "Library/Application Support/Figma Fig Downloader"
    APP_SUPPORT = Path.home() / "Library/Application Support/Fig Backup"
DOWNLOADS = Path.home() / "Downloads"


class FigmaError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class BrowserAuthError(FigmaError):
    """Browser-session failures that must stop the whole queue until the user signs in."""


def clean_name(value: str | None) -> str:
    name = unicodedata.normalize("NFC", str(value or "Untitled"))
    name = re.sub(r'[\x00-\x1f\x7f/\\:*?"<>|]', "_", name)
    return name.strip(". ")[:90] or "Untitled"


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class TokenStore:
    """A private app-data file, deliberately independent of macOS Keychain."""

    def __init__(self, support: Path = APP_SUPPORT):
        self.path = support / "token.json"

    def load(self) -> str | None:
        body = read_json(self.path, {})
        token = body.get("token") if isinstance(body, dict) else None
        return token if isinstance(token, str) and token else None

    def save(self, token: str) -> None:
        if not token.strip():
            raise FigmaError("Token cannot be empty")
        write_json(self.path, {"version": 1, "token": token.strip()})

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class PreferencesStore:
    """Local presentation preferences; a missing file means onboarding is pending."""

    LANGUAGES = {"en", "fa", "ja", "fr", "de", "es", "es-419", "ko", "pt-BR"}
    THEMES = {"system", "light", "dark"}

    def __init__(self, support: Path = APP_SUPPORT):
        self.path = support / "preferences.json"

    def load(self) -> dict:
        body = read_json(self.path, {})
        if not isinstance(body, dict):
            body = {}
        return {
            "language": body.get("language") if body.get("language") in self.LANGUAGES else "en",
            "theme": body.get("theme") if body.get("theme") in self.THEMES else "system",
            "onboarding_complete": body.get("onboarding_complete") is True,
        }

    def save(self, changes: dict) -> dict:
        if not isinstance(changes, dict) or set(changes) - {"language", "theme", "onboarding_complete"}:
            raise FigmaError("Invalid preferences")
        result = {**self.load(), **changes}
        if result["language"] not in self.LANGUAGES or result["theme"] not in self.THEMES:
            raise FigmaError("Choose a supported language and theme")
        if not isinstance(result["onboarding_complete"], bool):
            raise FigmaError("Invalid onboarding state")
        write_json(self.path, result)
        return result


def merge_teams(*groups: list[dict]) -> list[dict]:
    found: dict[str, dict] = {}
    for group in groups:
        for team in group:
            team_id = str(team.get("id", ""))
            if not team_id.isdigit():
                continue
            old = found.get(team_id, {})
            name = str(team.get("name") or "").strip()
            merged = {"id": team_id, "name": name if name and name != team_id else old.get("name", team_id)}
            avatar = team.get("avatar") or old.get("avatar")
            if isinstance(avatar, str) and avatar.strip():
                merged["avatar"] = avatar.strip()
            found[team_id] = merged
    return sorted(found.values(), key=lambda team: team["name"].casefold())


def team_id_from_input(value: str) -> str | None:
    match = re.search(r"(?:^|/team/)(\d+)(?:\b|/|\?|$)", value.strip())
    return match.group(1) if match else None


# Native container each editor's "Save local copy" produces.
EDITOR_EXTENSIONS = {"figma": ".fig", "figjam": ".jam", "slides": ".deck"}
NATIVE_EXTENSIONS = tuple(EDITOR_EXTENSIONS.values())


def native_extension(editor_type: str | None) -> str:
    return EDITOR_EXTENSIONS.get(str(editor_type or "").lower(), ".fig")


def verify_fig(path: Path) -> int:
    size = path.stat().st_size
    if size <= 1024:
        raise FigmaError(f"Downloaded file is too small: {path.name} ({size} bytes)")
    with path.open("rb") as stream:
        head = stream.read(8)
    if head.startswith((b"<", b"{")):
        raise FigmaError(f"Downloaded file appears to be an HTML/JSON error response: {path.name}")
    return size


class ArchiveIndex:
    def __init__(self, support: Path = SUPPORT, downloads: Path = DOWNLOADS):
        self.path = support / "downloads.json"
        self.downloads = downloads
        body = read_json(self.path, {})
        self.names = {
            key: value for key, value in body.get("files", {}).items()
            if isinstance(value, str) and Path(value).name == value and value.lower().endswith(NATIVE_EXTENSIONS)
        } if isinstance(body, dict) and isinstance(body.get("files"), dict) else {}

    def target(self, file: dict) -> tuple[Path, bool]:
        key = str(file["key"])
        extension = native_extension(file.get("editorType"))
        if key in self.names:
            return self.downloads / self.names[key], False
        base = clean_name(file.get("name"))
        reserved = {value.casefold() for value in self.names.values()}
        number = 0
        while True:
            suffix = f"({number})" if number else ""
            filename = f"{base}{suffix}{extension}"
            if filename.casefold() not in reserved and not (self.downloads / filename).exists():
                break
            number += 1
        destination = self.downloads / filename
        migrated = False
        if re.fullmatch(r"[A-Za-z0-9_-]+", key):
            legacy = self.downloads / f"{base}--{key}.fig"
            if legacy.exists():
                verify_fig(legacy)
                legacy.rename(destination)
                migrated = True
        self.names[key] = filename
        write_json(self.path, {"version": 1, "files": self.names})
        return destination, migrated


class TreeArchiveIndex:
    """Stable, collision-safe team/folder/file paths inside Downloads/Fig Backup."""

    def __init__(self, team: dict, support: Path = APP_SUPPORT, downloads: Path = DOWNLOADS):
        self.team_id = str(team["id"])
        if not self.team_id.isdigit():
            raise FigmaError("Invalid team ID")
        self.base = downloads / "Fig Backup"
        roots_path = support / "archive-roots.json"
        roots = read_json(roots_path, {})
        if not isinstance(roots, dict):
            roots = {}
        root_name = roots.get(self.team_id)
        if not isinstance(root_name, str) or root_name != clean_name(root_name):
            reserved = {str(value).casefold() for value in roots.values()}
            root_name = self._available_name(clean_name(team.get("name")), reserved, self.base)
            roots[self.team_id] = root_name
            write_json(roots_path, roots)
        self.root = self.base / root_name
        self.path = support / "archives" / self.team_id / "paths.json"
        body = read_json(self.path, {})
        if not isinstance(body, dict):
            body = {}
        self.folders = self._safe_paths(body.get("folders"), is_file=False)
        self.files = self._safe_paths(body.get("files"), is_file=True)

    @staticmethod
    def _safe_paths(value: Any, is_file: bool) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        result = {}
        for key, relative in value.items():
            if not isinstance(key, str) or not isinstance(relative, str):
                continue
            path = Path(relative)
            if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
                continue
            if is_file and not path.name.lower().endswith(NATIVE_EXTENSIONS):
                continue
            result[key] = relative
        return result

    @staticmethod
    def _available_name(base: str, reserved: set[str], directory: Path, extension: str = "") -> str:
        number = 0
        while True:
            name = f"{base}{f'({number})' if number else ''}{extension}"
            if name.casefold() not in reserved and not (directory / name).exists():
                return name
            number += 1

    def _save(self) -> None:
        write_json(self.path, {"version": 1, "folders": self.folders, "files": self.files})

    def folder_path(self, ancestors: list[dict]) -> Path:
        relative = Path()
        for folder in ancestors:
            folder_id = str(folder["id"])
            if not folder_id.isdigit():
                raise FigmaError("Invalid folder ID")
            saved = self.folders.get(folder_id)
            if saved:
                relative = Path(saved)
                continue
            parent = relative
            reserved = {Path(value).name.casefold() for value in self.folders.values()
                        if Path(value).parent == parent}
            name = self._available_name(clean_name(folder.get("name")), reserved, self.root / parent)
            relative = parent / name
            self.folders[folder_id] = relative.as_posix()
            self._save()
        return self.root / relative

    def prepare_folders(self, folders: list[list[dict]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for ancestors in folders:
            self.folder_path(ancestors).mkdir(parents=True, exist_ok=True)

    def target(self, file: dict) -> tuple[Path, bool]:
        key = str(file["key"])
        if key in self.files:
            destination = self.root / self.files[key]
            destination.parent.mkdir(parents=True, exist_ok=True)
            return destination, False
        directory = self.folder_path(file["_folder_path"])
        directory.mkdir(parents=True, exist_ok=True)
        relative = directory.relative_to(self.root)
        reserved = {Path(value).name.casefold() for value in self.files.values()
                    if Path(value).parent == relative}
        name = self._available_name(clean_name(file.get("name")), reserved, directory, native_extension(file.get("editorType")))
        destination = directory / name
        self.files[key] = (relative / name).as_posix()
        self._save()
        return destination, False


class FigmaClient:
    def __init__(self, token: str, request_get: Callable | None = None):
        self.token = token
        self.request_get = request_get or requests.get
        self.folder_api = "v2"
        self.unavailable_subfolders: set[str] = set()
        self._editor_type_cache: dict[str, str] = {}

    def get(self, endpoint: str) -> dict:
        for attempt in range(6):
            response = self.request_get(
                "https://api.figma.com" + endpoint,
                headers={"X-Figma-Token": self.token}, timeout=30,
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 5:
                    raise FigmaError(f"Figma API HTTP {response.status_code}: {endpoint}", response.status_code)
                retry_after = response.headers.get("retry-after")
                try:
                    delay = min(max(float(retry_after), 1), 60)
                except (ValueError, TypeError):
                    delay = min(2 ** attempt, 30)
                time.sleep(delay)
                continue
            if not response.ok:
                try:
                    body = response.json()
                    detail = body.get("message") or body.get("err") or ""
                except (ValueError, AttributeError):
                    detail = ""
                raise FigmaError(f"Figma API HTTP {response.status_code}: {endpoint}{': ' + str(detail) if detail else ''}", response.status_code)
            try:
                body = response.json()
            except ValueError as error:
                raise FigmaError(f"Figma API returned a non-JSON response: {endpoint}", response.status_code) from error
            if not isinstance(body, dict):
                raise FigmaError(f"Unexpected Figma API response: {endpoint}")
            return body
        raise AssertionError("unreachable")

    @staticmethod
    def _items(body: dict, key: str) -> list[dict]:
        items = body.get(key)
        if not isinstance(items, list):
            raise FigmaError(f"The Figma response has no {key} list")
        return items

    def me(self) -> dict:
        return self.get("/v1/me")

    def top_folders(self, team_id: str) -> list[dict]:
        team_id = quote(str(team_id), safe="")
        try:
            self.folder_api = "v2"
            return self._items(self.get(f"/v2/teams/{team_id}/folders"), "folders")
        except FigmaError as new_error:
            if new_error.status not in (403, 404):
                raise
            try:
                projects = self._items(self.get(f"/v1/teams/{team_id}/projects"), "projects")
                self.folder_api = "v1"
                return projects
            except FigmaError as old_error:
                raise FigmaError(f"Team folders are unavailable. Folders API: {new_error}. Projects API: {old_error}") from old_error

    def subfolders(self, folder_id: str) -> list[dict]:
        if self.folder_api == "v1" or str(folder_id) in self.unavailable_subfolders:
            return []
        try:
            return self._items(self.get(f"/v2/folders/{quote(str(folder_id), safe='')}/folders"), "folders")
        except FigmaError as error:
            if error.status != 451:
                raise
            self.unavailable_subfolders.add(str(folder_id))
            return []

    def files(self, folder_id: str) -> list[dict]:
        folder_id = quote(str(folder_id), safe="")
        endpoint = f"/v1/projects/{folder_id}/files" if self.folder_api == "v1" else f"/v2/folders/{folder_id}/files"
        return self._items(self.get(endpoint), "files")

    def all_files(self, folder: dict) -> list[dict]:
        pending = [folder]
        seen = set()
        result = {}
        while pending:
            current = pending.pop()
            folder_id = str(current["id"])
            if folder_id in seen:
                continue
            seen.add(folder_id)
            for file in self.files(folder_id):
                if file.get("key"):
                    result[file["key"]] = file
            pending.extend(self.subfolders(folder_id))
        return list(result.values())

    def walk_tree(self, roots: list[dict]) -> tuple[list[dict], list[list[dict]]]:
        """Return deduplicated files and every visited folder path, including empty folders."""
        pending = [(folder, [folder]) for folder in reversed(roots)]
        seen_folders: set[str] = set()
        seen_files: set[str] = set()
        files: list[dict] = []
        folders: list[list[dict]] = []
        while pending:
            folder, ancestors = pending.pop()
            folder_id = str(folder["id"])
            if folder_id in seen_folders:
                continue
            seen_folders.add(folder_id)
            folders.append(ancestors)
            for file in self.files(folder_id):
                key = str(file.get("key") or "")
                if key and key not in seen_files:
                    seen_files.add(key)
                    files.append({**file, "_folder_path": ancestors})
            children = sorted(self.subfolders(folder_id), key=lambda item: str(item.get("name", "")).casefold())
            pending.extend((child, [*ancestors, child]) for child in reversed(children))
        return files, folders

    def editor_type(self, file: dict) -> str | None:
        if file.get("editorType") or file.get("editor_type"):
            return file.get("editorType") or file.get("editor_type")
        key_str = str(file["key"])
        cached = self._editor_type_cache.get(key_str)
        if cached:
            return cached
        key = quote(key_str, safe="")
        try:
            body = self.get(f"/v1/files/{key}/meta")
            data = body.get("file") or {}
            kind = data.get("editorType") or data.get("editor_type")
        except FigmaError as error:
            if error.status != 403:
                raise
            kind = self.get(f"/v1/files/{key}?depth=1").get("editorType")
        if kind:
            self._editor_type_cache[key_str] = kind
        return kind
