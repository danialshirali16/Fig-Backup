"""Figma's native Save local copy flow, automated with Python Playwright."""
from __future__ import annotations

import base64
import json
import platform
import re
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
from playwright._impl._driver import compute_driver_executable
from playwright._impl._errors import TargetClosedError

from .core import ArchiveIndex, BrowserAuthError, FigmaError, SUPPORT, merge_teams, native_extension, verify_fig

# Children of a windowed exe must not allocate a console (the Playwright
# installer and its node.exe driver are console-subsystem programs).
# CREATE_NO_WINDOW only exists on Windows.
if sys.platform == "win32":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


class Browser:
    def __init__(self, support: Path = SUPPORT):
        self.support = support
        self.playwright = None
        self.context = None
        self.page = None
        self.headless = True
        self.use_headless_shell = False

    @staticmethod
    def browser_cache_dir() -> Path:
        # Keep browser downloads in a writable per-user cache outside the frozen app.
        if sys.platform == "win32":
            return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "ms-playwright"
        return Path.home() / "Library/Caches/ms-playwright"

    def open(self, headless: bool = True) -> None:
        self.close()
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browser_cache_dir())
        if self.playwright is None:
            self.playwright = sync_playwright().start()
        self.support.mkdir(parents=True, exist_ok=True, mode=0o700)
        browser_binary = Path(self.playwright.chromium.executable_path)
        if not browser_binary.exists():
            self._install_chromium()
        options = dict(headless=headless, accept_downloads=True,
                       viewport={"width": 1400, "height": 900})
        if not headless or not self.use_headless_shell:
            options["channel"] = "chromium"
        if headless:
            version = subprocess.run([str(browser_binary), "--version"],
                                     check=True, capture_output=True, text=True,
                                     creationflags=SUBPROCESS_FLAGS).stdout
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", version)
            if not match:
                raise FigmaError("Could not determine the Chromium version")
            platform_agent = "Windows NT 10.0; Win64; x64" if sys.platform == "win32" else "Macintosh; Intel Mac OS X 10_15_7"
            options["user_agent"] = (
                f"Mozilla/5.0 ({platform_agent}) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{match.group(1)} Safari/537.36"
            )
            options["args"] = ["--disable-blink-features=AutomationControlled"]
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                str(self.support / "chromium-profile"), **options,
            )
        except Exception as error:
            if "Executable doesn't exist" not in str(error):
                raise
            self._install_chromium()
            self.context = self.playwright.chromium.launch_persistent_context(
                str(self.support / "chromium-profile"), **options,
            )
        if headless:
            self.context.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.headless = headless

    @staticmethod
    def _install_chromium() -> None:
        driver, cli = compute_driver_executable()
        failures = []
        for host, label in Browser._ordered_hosts():
            env = {**os.environ, "PLAYWRIGHT_DOWNLOAD_HOST": host}
            try:
                subprocess.run([str(driver), str(cli), "install", "chromium"],
                               check=True, capture_output=True, text=True,
                               timeout=Browser.INSTALL_TIMEOUT,
                               creationflags=SUBPROCESS_FLAGS, env=env)
                return
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                detail = (getattr(error, "stderr", None) or getattr(error, "output", None) or "").strip().splitlines()
                failures.append(f"{label}: {detail[-1] if detail else 'failed'}")
        raise FigmaError(
            "Automatic Chromium installation failed - tried all sources: " + "; ".join(failures)
        )

    # The official CDN is unreachable from some networks (regional blocks and
    # firewalls); these mirrors serve the same builds/ tree byte-for-byte.
    DOWNLOAD_HOSTS = (
        "https://cdn.playwright.dev",
        "https://registry.npmmirror.com/-/binary/playwright",
        "https://cdn.npmmirror.com/binaries/playwright",
    )
    _HOST_LABELS = {
        "https://cdn.playwright.dev": "playwright.dev",
        "https://registry.npmmirror.com/-/binary/playwright": "npmmirror",
        "https://cdn.npmmirror.com/binaries/playwright": "npmmirror-cdn",
    }
    # A slow single-stream mirror can legitimately need tens of minutes for
    # chromium + headless-shell, so this is a generous ceiling, not a guess.
    INSTALL_TIMEOUT = 2400

    @classmethod
    def _ordered_hosts(cls) -> tuple[tuple[str, str], ...]:
        pairs = [(host, cls._HOST_LABELS[host]) for host in cls.DOWNLOAD_HOSTS]
        archive = cls._chromium_archive_path()
        if archive is None:
            return tuple(pairs)
        with ThreadPoolExecutor(max_workers=len(pairs)) as pool:
            live = {host for host, _ in pairs
                    if pool.submit(cls._probe_host, host, archive).result()}
        if not live:
            # The probe can be wrong (proxies, odd TLS stacks); install anyway
            # in the default order rather than refusing.
            return tuple(pairs)
        return tuple([(host, label) for host, label in pairs if host in live]
                     + [(host, label) for host, label in pairs if host not in live])

    @staticmethod
    def _probe_host(host: str, archive_path: str) -> bool:
        request = Request(f"{host}/{archive_path}",
                          headers={"Range": "bytes=0-65535", "User-Agent": "Fig-Backup"})
        try:
            with urlopen(request, timeout=10) as response:
                if response.status not in (200, 206):
                    return False
                response.read(65536)
                return True
        except Exception:
            return False

    @staticmethod
    def _chromium_archive_path() -> str | None:
        """Path of the pinned chromium zip under any Playwright download host."""
        try:
            _, cli = compute_driver_executable()
            manifest = (Path(cli).parent / "browsers.json").read_text(encoding="utf-8")
            entry = next(b for b in json.loads(manifest)["browsers"] if b["name"] == "chromium")
            version = entry["browserVersion"]
        except Exception:
            return None
        if sys.platform == "win32":
            return f"builds/cft/{version}/win64/chrome-win64.zip"
        if sys.platform == "darwin":
            arch = "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
            return f"builds/cft/{version}/{arch}/chrome-{arch}.zip"
        return f"builds/cft/{version}/linux64/chrome-linux64.zip"

    def close(self) -> None:
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
            self.page = None

    def stop(self) -> None:
        self.close()
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None

    def recover_from_crash(self) -> None:
        self.stop()
        self.use_headless_shell = True

    def open_sign_in(self) -> None:
        self.open(headless=False)
        self.page.goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)

    def _collect_teams(self) -> list[dict]:
        return self.page.evaluate(r"""() => {
          const avatarFor = element => {
            if (!element) return '';
            const image = element.querySelector('img[src], img[srcset]');
            if (image) return image.currentSrc || image.src || '';
            const svgImage = element.querySelector('svg image');
            if (svgImage) return svgImage.href?.baseVal || svgImage.getAttribute('href') || '';
            for (const node of [element, ...element.querySelectorAll('*')]) {
              const box = node.getBoundingClientRect();
              if (box.width < 12 || box.width > 80 || box.height < 12 || box.height > 80) continue;
              const background = getComputedStyle(node).backgroundImage;
              const match = background.match(/url\(["']?(.*?)["']?\)/);
              if (match) return match[1];
            }
            return '';
          };
          const found = new Map();
          const current = location.pathname.match(/\/team\/(\d+)/);
          if (current) {
            const button = document.querySelector('button[aria-label^="Plan:"]');
            const label = button?.getAttribute('aria-label');
            found.set(current[1], {id: current[1], name: label?.replace(/^Plan:\s*/, '').trim() || current[1], avatar: avatarFor(button)});
          }
          for (const a of document.querySelectorAll('a[href*="/team/"]')) {
            const match = a.href.match(/\/team\/(\d+)/);
            if (match) {
              const previous = found.get(match[1]);
              found.set(match[1], {id: match[1], name: (a.innerText || a.getAttribute('aria-label') || a.title || match[1]).trim(), avatar: avatarFor(a) || previous?.avatar || ''});
            }
          }
          return [...found.values()];
        }""")

    def _embed_avatar(self, value: str) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        supported = ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml")
        if value.startswith("data:"):
            return value if len(value) <= 350_000 and any(value.startswith(f"data:{mime};base64,") for mime in supported) else None
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == "figma.com" or host.endswith(".figma.com") or host == "figmausercontent.com" or host.endswith(".figmausercontent.com")):
            return None
        try:
            response = self.context.request.get(value, timeout=8000)
            if not response.ok:
                return None
            mime = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if mime not in supported or int(response.headers.get("content-length", "0")) > 256_000:
                return None
            body = response.body()
            if not body or len(body) > 256_000:
                return None
            return f"data:{mime};base64,{base64.b64encode(body).decode('ascii')}"
        except Exception:
            return None

    def _hydrate_avatars(self, teams: list[dict], saved: list[dict]) -> list[dict]:
        previous = {str(team.get("id")): team.get("avatar") for team in saved}
        for team in teams:
            avatar = self._embed_avatar(team.get("avatar"))
            if not avatar:
                avatar = self._embed_avatar(previous.get(team["id"]))
            if avatar:
                team["avatar"] = avatar
            else:
                team.pop("avatar", None)
        return teams

    def discover_teams(self, saved: list[dict]) -> dict:
        if self.context is not None and not self.headless:
            self.close()
        if self.context is None:
            self.open(headless=True)
        self.page.goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)
        try:
            self.page.wait_for_function("() => document.querySelector('button[aria-label^=\"Plan:\"]') || document.querySelector('a[href*=\"/team/\"]')", timeout=15000)
        except PlaywrightTimeout:
            pass
        teams = self._collect_teams()
        plan = self.page.get_by_role("button", name=re.compile(r"^Plan:")).first
        if not teams and plan.count() == 0:
            return {"teams": saved, "auth_required": True}
        original_url = self.page.url
        try:
            plan.click(timeout=10000)
            entries = self.page.locator('[role="menuitemradio"]').evaluate_all(r"""els => els.map(el => {
              const lines = el.innerText.split('\n').map(s => s.trim()).filter(Boolean);
              const image = el.querySelector('img[src], img[srcset]');
              const svgImage = el.querySelector('svg image');
              let avatar = image?.currentSrc || image?.src || svgImage?.href?.baseVal || '';
              if (!avatar) {
                for (const node of el.querySelectorAll('*')) {
                  const box = node.getBoundingClientRect();
                  if (box.width < 12 || box.width > 80 || box.height < 12 || box.height > 80) continue;
                  const match = getComputedStyle(node).backgroundImage.match(/url\(["']?(.*?)["']?\)/);
                  if (match) { avatar = match[1]; break; }
                }
              }
              return {name: lines.length > 1 ? lines.at(-2) : lines[0], selected: el.getAttribute('aria-checked') === 'true', avatar};
            }).filter(x => x.name)""")
            self.page.keyboard.press("Escape")
        except Exception:
            return {"teams": self._hydrate_avatars(merge_teams(saved, teams), saved), "auth_required": False}
        initial = re.search(r"/team/(\d+)", original_url)
        initial_id = initial.group(1) if initial else None
        all_teams = teams[:]
        for index, entry in enumerate(entries):
            saved_id = next((x["id"] for x in saved if x["name"] == entry["name"]), None)
            if entry["selected"] and (initial_id or saved_id):
                all_teams.append({"id": initial_id or saved_id, "name": entry["name"], "avatar": entry.get("avatar")})
                continue
            try:
                previous = re.search(r"/team/(\d+)", self.page.url)
                previous_id = previous.group(1) if previous else ""
                self.page.get_by_role("button", name=re.compile(r"^Plan:")).first.click(timeout=15000)
                self.page.locator('[role="menuitemradio"]').nth(index).click(timeout=15000)
                self.page.wait_for_function(
                    "oldId => { const next = location.pathname.match(/\\/team\\/(\\d+)/)?.[1]; return next && next !== oldId; }",
                    arg=previous_id, timeout=30000,
                )
                match = re.search(r"/team/(\d+)", self.page.url)
                if match:
                    all_teams.append({"id": match.group(1), "name": entry["name"], "avatar": entry.get("avatar")})
            except Exception:
                self.page.keyboard.press("Escape")
        try:
            self.page.goto(original_url, wait_until="domcontentloaded", timeout=90000)
        except Exception:
            pass
        return {"teams": self._hydrate_avatars(merge_teams(saved, all_teams), saved), "auth_required": False}

    def _save_local_copy(self) -> None:
        page = self.page
        try:
            page.keyboard.press("ControlOrMeta+/")
            page.wait_for_function("() => ['INPUT','TEXTAREA'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable", timeout=3500)
            page.keyboard.type("save local copy", delay=50)
            page.get_by_text(re.compile("save local copy", re.I)).first.wait_for(state="visible", timeout=5000)
            page.keyboard.press("Enter")
            return
        except TargetClosedError:
            raise
        except Exception:
            page.keyboard.press("Escape")
        for control in (
            page.get_by_role("button", name=re.compile("main menu|figma menu", re.I)).first,
            page.locator('[aria-label="Main menu"]').first,
            page.locator('[data-testid*="main-menu"]').first,
        ):
            try:
                control.click(timeout=3500)
                break
            except TargetClosedError:
                raise
            except Exception:
                continue
        else:
            raise FigmaError("The Figma main menu was not found")
        file_menu = page.get_by_role("menuitem", name=re.compile(r"^File\b", re.I)).first
        try:
            file_menu.hover(timeout=6000)
        except TargetClosedError:
            raise
        except Exception:
            page.get_by_text("File", exact=True).last.hover(timeout=6000)
        save = page.get_by_role("menuitem", name=re.compile("Save local copy", re.I)).last
        try:
            save.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeout:
            try:
                file_menu.click(timeout=6000)
            except TargetClosedError:
                raise
            except Exception:
                pass
            save = page.get_by_text("Save local copy", exact=True).last
        save.click(timeout=10000)

    def download(self, file: dict, index: ArchiveIndex, progress) -> dict:
        expected_extension = native_extension(file.get("editorType"))
        destination, migrated = index.target(file)
        if destination.suffix.lower() != expected_extension:
            raise FigmaError(f"The backup path has an unexpected file type: {destination.name}")
        if destination.exists():
            verify_fig(destination)
            return {"status": "renamed" if migrated else "exists", "path": str(destination)}
        if self.context is None or not self.headless:
            self.open(headless=True)
        progress("opening", "Opening the file in Figma…")
        # Editor routes: design uses /design/, slides /slides/, FigJam boards live
        # under /board/ (reached via the /file/ redirect — /figjam/ now 404s).
        segment = {"figma": "design", "figjam": "file", "slides": "slides"}.get(
            str(file.get("editorType") or "").lower(), "design")
        response = self.page.goto(
            f"https://www.figma.com/{segment}/{file['key']}",
            wait_until="domcontentloaded", timeout=90000,
        )
        if response and response.status == 403:
            raise BrowserAuthError("Figma blocked the background editor (HTTP 403). No browser window was opened.")
        if re.search(r"/login|/signin", self.page.url):
            raise BrowserAuthError("Browser sign-in is required. Use the Sign in button, then retry.")
        try:
            self.page.locator("canvas").first.wait_for(state="attached", timeout=120000)
        except PlaywrightTimeout as error:
            raise FigmaError("The Figma editor did not load in the background browser.") from error
        progress("preparing", "Preparing a local copy…")
        try:
            with self.page.expect_download(timeout=480000) as download_info:
                self._save_local_copy()
            download = download_info.value
        except TargetClosedError:
            raise
        except Exception as error:
            screenshot = self.support / f"download-error-{file['key']}.png"
            try:
                self.page.screenshot(path=str(screenshot))
            except Exception:
                pass
            raise FigmaError(f"The local-copy download did not start: {str(error).splitlines()[0]}") from error
        if Path(download.suggested_filename).suffix.lower() != expected_extension:
            raise FigmaError(f"Figma returned an unexpected file: {download.suggested_filename}")
        temporary = destination.with_name(destination.name + ".partial")
        try:
            progress("saving", "Saving to Downloads…")
            download.save_as(str(temporary))
            size = verify_fig(temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return {"status": "saved", "path": str(destination), "size": size}


def chromium_ready(cache_dir: Path | None = None) -> bool:
    """Advisory check for the UI: a chromium build with Playwright's completion marker.

    Fails toward False (missing); Browser.open() remains the authoritative installer.
    """
    root = cache_dir if cache_dir is not None else Browser.browser_cache_dir()
    if not root.is_dir():
        return False
    for directory in root.glob("chromium-*"):
        if not (directory / "INSTALLATION_COMPLETE").exists():
            continue
        if sys.platform == "win32":
            if any(directory.glob("chrome-win*/*.exe")):
                return True
        elif sys.platform == "darwin":
            if any(directory.glob("chrome-mac*/*.app")):
                return True
        else:
            return True
    return False
