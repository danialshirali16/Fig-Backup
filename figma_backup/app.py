"""Desktop bridge. Browser work is confined to one worker thread."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import webview
from playwright._impl._errors import TargetClosedError

from .browser import Browser, chromium_ready
from .core import APP_SUPPORT, BrowserAuthError, DOWNLOADS, SUPPORT, ArchiveIndex, EditorTypeCache, FigmaClient, FigmaError, PreferencesStore, TokenStore, TreeArchiveIndex, merge_teams, read_json, team_id_from_input, write_json

# Editor types this app can export via the web editor's "Save local copy".
SUPPORTED_EDITOR_TYPES = ("figma", "figjam", "slides")


def _reveal_in_explorer(path: Path) -> None:
    """Open a file's parent in Explorer and select it, including Unicode names."""
    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulong,
                                           ctypes.POINTER(ctypes.c_ulong)]
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                                   ctypes.c_void_p, ctypes.c_ulong]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    initialized = ole32.CoInitialize(None)
    changed_mode = ctypes.c_long(0x80010106).value
    if initialized < 0 and initialized != changed_mode:
        raise FigmaError(f"Windows could not initialize Explorer (0x{initialized & 0xffffffff:08X})")
    pidl = ctypes.c_void_p()
    try:
        result = shell32.SHParseDisplayName(str(path), None, ctypes.byref(pidl), 0, None)
        if result < 0:
            raise FigmaError(f"Windows could not locate the downloaded file (0x{result & 0xffffffff:08X})")
        result = shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
        if result < 0:
            raise FigmaError(f"Windows could not reveal the downloaded file (0x{result & 0xffffffff:08X})")
    finally:
        if pidl.value:
            ole32.CoTaskMemFree(pidl)
        if initialized >= 0:
            ole32.CoUninitialize()


class Bridge:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="figma-browser")
        self.browser = Browser()
        self.browser_verified = False
        self.token_verified = False
        self.token_store = TokenStore()
        self.preferences_store = PreferencesStore()
        self.token = os.environ.get("FIGMA_PAT") or self.token_store.load()
        self.client = self._make_client(self.token) if self.token else None
        self.lock = threading.Lock()
        self.state = {"running": False, "phase": "idle", "items": [], "current": 0, "total": 0,
                      "saved": 0, "existing": 0, "skipped": 0, "failed": 0,
                      "message": "", "warning": "", "finished": False}
        # Kept outside self.state: start_download replaces that dict wholesale.
        system = self.browser.system_browsers()
        self.browser_state = {"phase": "ready" if system or chromium_ready() else "missing",
                              "message": "", "source": system[0][0] if system else "chromium"}
        self.maximized = False
        self.stop_requested = False

    @staticmethod
    def _make_client(token: str) -> FigmaClient:
        return FigmaClient(token, type_cache=EditorTypeCache(APP_SUPPORT / "editor-types.json"))

    def minimize_window(self) -> dict:
        webview.windows[0].minimize()
        return {"ok": True}

    def toggle_maximize_window(self) -> dict:
        window = webview.windows[0]
        if self.maximized:
            window.restore()
        else:
            window.maximize()
        return {"ok": True}

    def close_window(self) -> dict:
        webview.windows[0].destroy()
        return {"ok": True}

    def begin_resize(self, edge: int) -> dict:
        """Hand the mouse to the native sizing loop (frameless edge strips, Windows)."""
        edge = int(edge)
        if sys.platform != "win32" or self.maximized or not 10 <= edge <= 17:
            return {"ok": False}
        window = webview.windows[0]
        WM_NCLBUTTONDOWN = 0xA1
        ctypes.windll.user32.ReleaseCapture()
        ctypes.windll.user32.SendMessageW(int(window.native.Handle), WM_NCLBUTTONDOWN, edge, 0)
        return {"ok": True}

    def open_external(self, url: str) -> dict:
        """Open an allowlisted https URL in the user's default browser."""
        parsed = urlparse(url or "")
        if parsed.scheme != "https" or parsed.hostname not in ("figma.com", "www.figma.com"):
            raise FigmaError("Only figma.com links can be opened externally")
        if sys.platform == "win32":
            os.startfile(url)  # noqa: S606 - shell-open of an allowlisted https URL
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        return {"ok": True}

    def _browser_status(self) -> dict:
        browser = dict(self.browser_state)
        if getattr(self.browser, "installing", False):
            browser = {"phase": "setting_up", "message": "", "source": "chromium"}
        elif browser.get("phase") == "ready" and getattr(self.browser, "install_error", ""):
            browser = {"phase": "failed", "message": self.browser.install_error, "source": "chromium"}
        channel = getattr(self.browser, "active_channel", None)
        if channel and not getattr(self.browser, "installing", False):
            browser = {"phase": "ready", "message": "", "source": channel}
        if browser.get("phase") == "setting_up":
            browser.update(self.browser.install_progress())
        return browser

    def _required(self) -> FigmaClient:
        if not self.client:
            raise FigmaError("Add a Personal Access Token first")
        return self.client

    def bootstrap(self) -> dict:
        SUPPORT.mkdir(parents=True, exist_ok=True, mode=0o700)
        APP_SUPPORT.mkdir(parents=True, exist_ok=True, mode=0o700)
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        if self.browser_state["phase"] == "missing":
            self.install_browser()
        return {"has_token": bool(self.token), "downloads": str(DOWNLOADS),
                "teams": read_json(SUPPORT / "teams.json", []),
                "preferences": self.preferences_store.load(),
                "browser": self._browser_status(), "version": "0.3.0"}

    def install_browser(self) -> dict:
        with self.lock:
            if self.browser_state["phase"] == "setting_up":
                return {"started": False}
            self.browser_state = {"phase": "setting_up", "message": ""}
        self.executor.submit(self._run_install)
        return {"started": True}

    def _run_install(self) -> None:
        try:
            self.browser._install_chromium()
            if not chromium_ready():
                raise FigmaError("Chromium installation finished, but the required browser files are missing")
            self.browser.install_error = ""
            with self.lock:
                self.browser_state = {"phase": "ready", "message": "", "source": "chromium"}
        except Exception as error:
            with self.lock:
                self.browser_state = {"phase": "failed", "message": str(error).splitlines()[0]}

    def save_preferences(self, changes: dict) -> dict:
        if not isinstance(changes, dict) or "onboarding_complete" in changes or "setup_version" in changes:
            raise FigmaError("Setup completion must be verified")
        return self.preferences_store.save(changes)

    def begin_setup(self) -> dict:
        self.browser_verified = False
        self.token_verified = False
        return {"preferences": self.preferences_store.save({"onboarding_complete": False, "setup_version": 0})}

    def verify_browser(self) -> dict:
        self.browser_verified = False
        try:
            self.executor.submit(self.browser.open, True).result()
            channel = self.browser.active_channel
            self.executor.submit(self.browser.close).result()
            with self.lock:
                self.browser_state = {"phase": "ready", "message": "", "source": channel}
            self.browser_verified = True
            return {"ready": True, "source": channel}
        except Exception as error:
            with self.lock:
                self.browser_state = {"phase": "failed", "message": str(error).splitlines()[0]}
            raise

    def save_token(self, token: str) -> dict:
        token = token.strip()
        if not token:
            raise FigmaError("Token cannot be empty")
        candidate = self._make_client(token)
        user = candidate.me()
        setup_required = self.token != token and self.preferences_store.load()["setup_version"] == 2
        self.token_store.save(token)
        previous, self.token, self.client = self.client, token, candidate
        if previous is not None and previous is not candidate:
            previous.close()
        if setup_required:
            self.begin_setup()
        else:
            self.token_verified = True
        return {"name": user.get("handle") or user.get("email") or "Figma",
                "setup_required": setup_required}

    def verify_token(self) -> dict:
        self.token_verified = False
        user = self._required().me()
        self.token_verified = True
        return {"name": user.get("handle") or user.get("email") or "Figma"}

    def open_sign_in(self) -> dict:
        self.executor.submit(self.browser.open_sign_in).result()
        with self.lock:
            self.browser_state = {"phase": "ready", "message": "",
                                  "source": self.browser.active_channel}
        return {"opened": True}

    def close_sign_in(self) -> dict:
        self.executor.submit(self.browser.close_sign_in).result()
        return {"closed": True}

    def complete_setup(self) -> dict:
        if not self.browser_verified or not self.token_verified:
            raise FigmaError("Verify the browser and access token before completing setup")
        signed_in = self.executor.submit(self.browser.verify_sign_in).result()
        if not signed_in:
            return {"completed": False}
        preferences = self.preferences_store.save({"onboarding_complete": True, "setup_version": 2})
        return {"completed": True, "preferences": preferences}

    def discover_teams(self) -> dict:
        self._required()
        saved = read_json(SUPPORT / "teams.json", [])
        if not isinstance(saved, list):
            saved = []
        result = self.executor.submit(self.browser.discover_teams, saved).result()
        teams = merge_teams(saved, result["teams"])
        write_json(SUPPORT / "teams.json", teams)
        return {"teams": teams, "auth_required": result["auth_required"]}

    def add_team(self, text: str, name: str = "") -> dict:
        self._required()
        team_id = team_id_from_input(text)
        if not team_id:
            raise FigmaError("Enter a valid team link or ID")
        teams = merge_teams(read_json(SUPPORT / "teams.json", []), [{"id": team_id, "name": name or team_id}])
        write_json(SUPPORT / "teams.json", teams)
        return {"teams": teams, "team": next(team for team in teams if team["id"] == team_id)}

    def folders(self, team_id: str) -> dict:
        client = self._required()
        folders = client.top_folders(team_id)
        return {"folders": folders, "legacy": client.folder_api == "v1"}

    def subfolders(self, folder_id: str) -> dict:
        client = self._required()
        folders = client.subfolders(folder_id)
        return {"folders": folders, "unavailable": str(folder_id) in client.unavailable_subfolders}

    def files(self, folder_id: str) -> dict:
        """The folder listing, with every type already known applied.

        The listing itself never carries an editor type, and resolving a type
        costs one API call per file — so this returns the names immediately and
        leaves the icons to file_types() once the rows are already on screen.
        """
        client = self._required()
        files = client.files(folder_id)
        client.apply_cached_types(files)
        return {"files": files, "unavailable": str(folder_id) in client.unavailable_subfolders}

    def file_types(self, keys: list) -> dict:
        """Resolve the file-type icons for a listing that is already displayed.

        Returns a map covering every requested key, with null where the type
        could not be read, so the UI can tell "still loading" from "unknown".
        """
        client = self._required()
        wanted: list[str] = []
        for key in keys if isinstance(keys, list) else []:
            key = str(key or "")
            if key and key not in wanted:
                wanted.append(key)
        if not wanted:
            return {}
        result: dict[str, str | None] = {}
        pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="figma-meta")
        try:
            futures = [(pool.submit(client.editor_type, {"key": key}), key) for key in wanted]
            for future, key in futures:
                try:
                    result[key] = future.result() or None
                except FigmaError as error:
                    # A confirmed rate limit drops the rest: icons fall back to the
                    # Design glyph and the download path resolves types itself.
                    if error.status == 429:
                        break
                    result[key] = None
                except Exception:
                    result[key] = None
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        for key in wanted:
            result.setdefault(key, None)
        client.flush_types()
        return result

    def start_download(self, selection: dict) -> dict:
        self._required()
        preferences = self.preferences_store.load()
        if not preferences["onboarding_complete"] or preferences["setup_version"] != 2:
            raise FigmaError("Complete all three setup steps before downloading")
        if not isinstance(selection, dict) or selection.get("scope") not in ("team", "folder", "file"):
            raise FigmaError("Choose a team, folder, or file to download")
        team = selection.get("team")
        if not isinstance(team, dict) or not str(team.get("id", "")).isdigit():
            raise FigmaError("Choose a valid team")
        if selection["scope"] != "team":
            folder = selection.get("folder")
            if not isinstance(folder, dict) or not str(folder.get("id", "")).isdigit():
                raise FigmaError("Choose a valid folder")
        if selection["scope"] == "file" and not selection.get("file_key"):
            raise FigmaError("Choose a file")
        with self.lock:
            if self.state["running"]:
                raise FigmaError("Another download is already running")
            self.state = {"running": True, "phase": "scanning", "items": [], "current": 0, "total": 0,
                          "saved": 0, "existing": 0, "skipped": 0, "failed": 0,
                          "message": "Collecting files…", "warning": "", "finished": False}
            self.stop_requested = False
        self.executor.submit(self._run_download, selection)
        return {"started": True}

    def stop_download(self) -> dict:
        with self.lock:
            self.stop_requested = True
            self.state["message"] = "Stopping after the current file…"
        return {"stopping": True}

    def status(self) -> dict:
        with self.lock:
            return {**self.state, "items": [item.copy() for item in self.state["items"]],
                    "browser": self._browser_status()}

    def _set(self, **changes) -> None:
        with self.lock:
            self.state.update(changes)

    def _run_download(self, selection: dict) -> None:
        client = self._required()
        try:
            client.unavailable_subfolders.clear()
            scope = selection["scope"]
            team = selection["team"]
            if scope == "file":
                files = [item for item in client.files(selection["folder"]["id"])
                         if item.get("key") == selection["file_key"]]
                if not files:
                    raise FigmaError("The selected file was not found in this folder")
                index = ArchiveIndex()
                destination = str(DOWNLOADS)
            else:
                roots = client.top_folders(team["id"]) if scope == "team" else [selection["folder"]]
                files, folder_paths = client.walk_tree(roots)
                index = TreeArchiveIndex(team)
                index.prepare_folders(folder_paths)
                destination = str(index.folder_path([selection["folder"]])) if scope == "folder" else str(index.root)
            items = [{"key": file["key"], "name": file.get("name") or "Untitled", "status": "queued", "detail": ""}
                     for file in files if file.get("key")]
            self._set(items=items, total=len(items), phase="downloading",
                      destination=destination, message="Download queue is ready" if items else "No supported files were found")
            for position, file in enumerate(files):
                if not file.get("key"):
                    continue
                with self.lock:
                    if self.stop_requested:
                        self.state["phase"] = "stopped"
                        break
                    self.state["current"] = position + 1
                    item = next(x for x in self.state["items"] if x["key"] == file["key"])
                    item["status"] = "checking"
                    self.state["message"] = file.get("name") or "Untitled"
                try:
                    kind = client.editor_type(file)
                    if kind not in SUPPORTED_EDITOR_TYPES:
                        with self.lock:
                            item["status"] = "skipped"
                            item["detail"] = f"File type: {kind or 'unknown'}"
                            self.state["skipped"] += 1
                        continue
                    file = {**file, "editorType": kind or ""}
                    def progress(status: str, detail: str) -> None:
                        with self.lock:
                            item["status"] = status
                            item["detail"] = detail
                    try:
                        result = self.browser.download(file, index, progress)
                    except TargetClosedError:
                        progress("retrying", "Chromium crashed; retrying with the headless browser…")
                        self.browser.recover_from_crash()
                        result = self.browser.download(file, index, progress)
                    with self.lock:
                        item["status"] = result["status"]
                        item["detail"] = result["path"]
                        item["size"] = int(result.get("size") or 0)
                        self.state["saved" if result["status"] == "saved" else "existing"] += 1
                except BrowserAuthError as error:
                    with self.lock:
                        item["status"] = "failed"
                        item["detail"] = str(error).splitlines()[0]
                        self.state["failed"] += 1
                    self._set(phase="attention", message=str(error).splitlines()[0])
                    break
                except Exception as error:
                    with self.lock:
                        item["status"] = "failed"
                        item["detail"] = str(error).splitlines()[0]
                        self.state["failed"] += 1
            with self.lock:
                if self.state["phase"] == "downloading":
                    # A stop requested during scanning (or under the last file)
                    # must not report the run as completed.
                    self.state["phase"] = "stopped" if self.stop_requested else "done"
                self.state["warning"] = (
                    f"Figma did not expose subfolders for {len(client.unavailable_subfolders)} folder(s); this backup may be incomplete."
                    if client.unavailable_subfolders else ""
                )
                self.state["running"] = False
                self.state["finished"] = True
            client.flush_types()
        except Exception as error:
            self._set(running=False, finished=True, phase="error", message=str(error).splitlines()[0])

    def open_downloads(self) -> dict:
        if sys.platform == "win32":
            os.startfile(str(DOWNLOADS))
        else:
            subprocess.Popen(["open", str(DOWNLOADS)])
        return {"opened": True}

    def open_destination(self) -> dict:
        with self.lock:
            destination = self.state.get("destination") or str(DOWNLOADS)
        path = Path(destination).resolve()
        if not path.is_relative_to(DOWNLOADS.resolve()):
            raise FigmaError("The backup destination is outside Downloads")
        target = path if path.exists() else DOWNLOADS
        if sys.platform == "win32":
            os.startfile(str(target))
        else:
            subprocess.Popen(["open", str(target)])
        return {"opened": True}

    def open_path(self, path: str) -> dict:
        """Reveal one downloaded file in Finder/Explorer, or open its folder."""
        target = Path(path).expanduser().resolve()
        if not target.is_relative_to(DOWNLOADS.resolve()):
            raise FigmaError("The backup destination is outside Downloads")
        if not target.exists():
            raise FigmaError("That file no longer exists on disk")
        if sys.platform == "win32":
            if target.is_dir():
                os.startfile(str(target))
            else:
                _reveal_in_explorer(target)
        elif target.is_dir():
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["open", "-R", str(target)])
        return {"opened": True}

    def shutdown(self, grace_seconds: float = 3.0, exit_now=os._exit) -> None:
        """Quit within a bounded time even when a download keeps the worker busy.

        Playwright's sync API is thread-bound, so an in-flight download cannot be
        interrupted from this thread. Downloads and indexes are written atomically
        (temp file + rename), so after a grace period the process is hard-exited.
        """
        with self.lock:
            self.stop_requested = True
        try:
            self.executor.submit(self.browser.stop).result(timeout=grace_seconds)
        except Exception:
            pass
        self.executor.shutdown(wait=False)
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline:
            with self.lock:
                if not self.state["running"]:
                    break
            time.sleep(0.05)
        exit_now(0)


def configure_titlebar(window) -> None:
    """Let the web header fill the titlebar while keeping native window controls."""
    import AppKit

    native = window.native
    native.setStyleMask_(native.styleMask() | AppKit.NSWindowStyleMaskFullSizeContentView)
    native.setTitlebarAppearsTransparent_(True)
    native.setTitleVisibility_(AppKit.NSWindowTitleHidden)
    native.setMovableByWindowBackground_(True)
    # pywebview paints its titlebar view with the system window color. Clear it
    # so the web header is visible behind the native traffic-light buttons.
    native.contentView().superview().subviews().lastObject().setBackgroundColor_(
        AppKit.NSColor.clearColor()
    )

def position_titlebar_buttons(window) -> None:
    """Position traffic lights after AppKit has completed the window layout."""
    from PyObjCTools import AppHelper

    AppHelper.callAfter(_position_titlebar_buttons, window)


def refresh_titlebar_buttons(window, *_size) -> None:
    if getattr(window, "_titlebar_button_insets", None) is not None:
        position_titlebar_buttons(window)


def _position_titlebar_buttons(window) -> None:
    import AppKit

    native = window.native
    kinds = (
        AppKit.NSWindowCloseButton,
        AppKit.NSWindowMiniaturizeButton,
        AppKit.NSWindowZoomButton,
    )
    insets = getattr(window, "_titlebar_button_insets", None)
    if insets is None:
        insets = {}
        for kind in kinds:
            button = native.standardWindowButton_(kind)
            frame = button.frame()
            parent = button.superview()
            bounds = parent.bounds()
            top = (
                frame.origin.y - bounds.origin.y
                if parent.isFlipped()
                else bounds.origin.y + bounds.size.height - frame.origin.y - frame.size.height
            )
            # Preserve AppKit's spacing between buttons, with a larger inset
            # to match the taller web header.
            insets[kind] = (frame.origin.x - bounds.origin.x + 6, top + 8)
        window._titlebar_button_insets = insets

    for kind in kinds:
        button = native.standardWindowButton_(kind)
        frame = button.frame()
        parent = button.superview()
        bounds = parent.bounds()
        left, top = insets[kind]
        y = (
            bounds.origin.y + top
            if parent.isFlipped()
            else bounds.origin.y + bounds.size.height - top - frame.size.height
        )
        button.setFrameOrigin_(
            AppKit.NSMakePoint(bounds.origin.x + left, y)
        )


def main() -> None:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    html = root / "dist/index.html"
    if not html.exists():
        raise SystemExit("The interface has not been built yet. Run Fig Backup.command.")
    bridge = Bridge()
    webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = True
    window = webview.create_window("Fig Backup", str(html), js_api=bridge,
                                   width=960, height=700, min_size=(640, 520),
                                   frameless=sys.platform == "win32",
                                   background_color="#f5f5f5")
    if sys.platform == "darwin":
        window.events.before_show += configure_titlebar
        window.events.shown += position_titlebar_buttons
        window.events.resized += refresh_titlebar_buttons
        window.events.restored += refresh_titlebar_buttons
    if sys.platform == "win32":
        def on_maximized():
            bridge.maximized = True
            window.evaluate_js("window.dispatchEvent(new Event('figbak-window-maximized'))")

        def on_restored():
            bridge.maximized = False
            window.evaluate_js("window.dispatchEvent(new Event('figbak-window-restored'))")

        window.events.maximized += on_maximized
        window.events.restored += on_restored
    window.events.closed += bridge.shutdown
    webview.start(gui="edgechromium" if sys.platform == "win32" else "cocoa",
                  debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
