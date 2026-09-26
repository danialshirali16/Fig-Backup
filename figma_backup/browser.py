"""Figma's native Save local copy flow, automated with Python Playwright."""
from __future__ import annotations

import base64
import ctypes
import json
import platform
import re
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
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
        self.active_channel = None
        self.failed_system_channels: set[str] = set()
        self.installing = False
        self.install_error = ""

    @staticmethod
    def browser_cache_dir() -> Path:
        # Keep browser downloads in a writable per-user cache outside the frozen app.
        if sys.platform == "win32":
            return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "ms-playwright"
        return Path.home() / "Library/Caches/ms-playwright"

    @staticmethod
    def _windows_app_paths(executable: str) -> list[Path]:
        """Find browser installations registered outside the usual directories."""
        try:
            import winreg
        except ImportError:
            return []
        paths = []
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,
                            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
                            0, winreg.KEY_READ | view) as key:
                        value, _ = winreg.QueryValueEx(key, None)
                    if value:
                        paths.append(Path(value.strip('"')))
                except OSError:
                    continue
        return paths

    @staticmethod
    def system_browsers() -> list[tuple[str, Path]]:
        """Installed Chrome/Edge builds that Playwright can drive without a download."""
        if sys.platform == "win32":
            program_files = Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
            program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
            local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
            candidates = [
                ("chrome", program_files / "Google/Chrome/Application/chrome.exe"),
                ("chrome", program_files_x86 / "Google/Chrome/Application/chrome.exe"),
                ("chrome", local / "Google/Chrome/Application/chrome.exe"),
                *(("chrome", path) for path in Browser._windows_app_paths("chrome.exe")),
                ("msedge", program_files_x86 / "Microsoft/Edge/Application/msedge.exe"),
                ("msedge", program_files / "Microsoft/Edge/Application/msedge.exe"),
                ("msedge", local / "Microsoft/Edge/Application/msedge.exe"),
                *(("msedge", path) for path in Browser._windows_app_paths("msedge.exe")),
            ]
        elif sys.platform == "darwin":
            candidates = [
                (channel, applications / app / "Contents/MacOS" / binary)
                for channel, app, binary in (
                    ("chrome", "Google Chrome.app", "Google Chrome"),
                    ("msedge", "Microsoft Edge.app", "Microsoft Edge"),
                )
                for applications in (Path("/Applications"), Path.home() / "Applications")
            ]
        else:
            return []
        found = []
        for channel, path in candidates:
            if path.is_file() and channel not in {item[0] for item in found}:
                found.append((channel, path))
        return found

    @staticmethod
    def _windows_file_version(path: Path) -> str:
        """Read the installed browser version without opening a console window."""
        if sys.platform != "win32":
            return ""
        try:
            version = ctypes.windll.version
            size = version.GetFileVersionInfoSizeW(str(path), None)
            data = ctypes.create_string_buffer(size)
            if not size or not version.GetFileVersionInfoW(str(path), 0, size, data):
                return ""
            value = ctypes.c_void_p()
            length = ctypes.c_uint()
            if not version.VerQueryValueW(data, "\\", ctypes.byref(value), ctypes.byref(length)):
                return ""
            fields = ctypes.cast(value, ctypes.POINTER(ctypes.c_uint32))
            major_minor, build_patch = fields[2], fields[3]
            return f"{major_minor >> 16}.{major_minor & 0xffff}.{build_patch >> 16}.{build_patch & 0xffff}"
        except (AttributeError, OSError, ValueError):
            return ""

    @classmethod
    def _headless_user_agent(cls, binary: Path) -> str:
        version = cls._windows_file_version(binary)
        if not version and sys.platform != "win32":
            try:
                reported = subprocess.run([str(binary), "--version"], capture_output=True,
                                          text=True, timeout=10, creationflags=SUBPROCESS_FLAGS).stdout
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", reported)
                version = match.group(1) if match else ""
            except Exception:
                pass
        if not version and sys.platform == "darwin":
            try:
                info = plistlib.loads((binary.parent.parent / "Info.plist").read_bytes())
                version = str(info.get("CFBundleShortVersionString", ""))
            except (OSError, ValueError):
                pass
        if not version:
            entry = cls._manifest_entry("chromium")
            version = (entry or {}).get("browserVersion", "")
        if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
            raise FigmaError("Could not determine the browser version")
        platform_agent = "Windows NT 10.0; Win64; x64" if sys.platform == "win32" else "Macintosh; Intel Mac OS X 10_15_7"
        return (f"Mozilla/5.0 ({platform_agent}) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{version} Safari/537.36")

    def open(self, headless: bool = True) -> None:
        self.close()
        self.active_channel = None
        self.install_error = ""
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browser_cache_dir())
        if self.playwright is None:
            self.playwright = sync_playwright().start()
        self.support.mkdir(parents=True, exist_ok=True, mode=0o700)
        options = dict(headless=headless, accept_downloads=True,
                       viewport={"width": 1400, "height": 900})
        if headless:
            options["args"] = ["--disable-blink-features=AutomationControlled"]
        if not (headless and self.use_headless_shell):
            skip_once = self.failed_system_channels.copy()
            self.failed_system_channels.clear()
            for channel, binary in self.system_browsers():
                if channel in skip_once:
                    continue
                for attempt in range(2 if channel == "chrome" else 1):
                    try:
                        system_options = {**options, "channel": channel, "executable_path": str(binary)}
                        if headless:
                            system_options["user_agent"] = self._headless_user_agent(binary)
                        self.context = self.playwright.chromium.launch_persistent_context(
                            str(self.support / f"chromium-profile-{channel}"), **system_options,
                        )
                        self.active_channel = channel
                        break
                    except Exception:
                        if attempt == 0 and channel == "chrome":
                            time.sleep(0.3)
                if self.context is not None:
                    break
        if self.context is None:
            browser_binary = Path(self.playwright.chromium.executable_path)
            if not chromium_ready():
                self._install_bundled()
            bundled_options = dict(options)
            if not headless or not self.use_headless_shell:
                bundled_options["channel"] = "chromium"
            if headless:
                bundled_options["user_agent"] = self._headless_user_agent(browser_binary)
            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    str(self.support / "chromium-profile"), **bundled_options,
                )
            except Exception as error:
                if "Executable doesn't exist" not in str(error):
                    raise
                self._install_bundled()
                self.context = self.playwright.chromium.launch_persistent_context(
                    str(self.support / "chromium-profile"), **bundled_options,
                )
            self.active_channel = "chromium"
        if headless:
            self.context.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.headless = headless

    def _install_bundled(self) -> None:
        self.installing = True
        self.install_error = ""
        try:
            self._install_chromium()
        except Exception as error:
            self.install_error = str(error).splitlines()[0]
            raise
        finally:
            self.installing = False

    @classmethod
    def _install_chromium(cls) -> None:
        """Install the pinned browsers, trying every download source in turn."""
        cls._migrate_legacy_shell()
        if chromium_ready():
            cls._reset_progress(0)
            return
        failures = []
        for host, label in cls._ordered_hosts():
            try:
                cls._reset_progress(cls._pending_bytes(host))
                cls._ensure_browser(host, "chromium")
                cls._ensure_browser(host, "chromium-headless-shell")
                return
            except Exception as error:
                failures.append(f"{label}: {error}")
        cls._reset_progress(0)
        error = cls._install_via_cli()
        if error is None and chromium_ready():
            return
        failures.append(error or "playwright-installer: browser files are incomplete")
        raise FigmaError(
            "Automatic Chromium installation failed - tried all sources: "
            + "; ".join(failures)
        )

    # Byte progress for the setup UI. done/total cover the current source
    # attempt; when total is 0 the UI falls back to an indeterminate bar.
    INSTALL_PROGRESS = {"done": 0, "total": 0}
    _progress_lock = threading.Lock()

    @classmethod
    def _reset_progress(cls, total: int) -> None:
        with cls._progress_lock:
            cls.INSTALL_PROGRESS.update(done=0, total=total)

    @classmethod
    def _bump_progress(cls, count: int) -> None:
        with cls._progress_lock:
            cls.INSTALL_PROGRESS["done"] += count

    @classmethod
    def install_progress(cls) -> dict:
        with cls._progress_lock:
            return dict(cls.INSTALL_PROGRESS)

    @classmethod
    def _pending_bytes(cls, host: str) -> int:
        """Total bytes still missing for a fresh install from this host.

        0 on any failure to measure; the UI then stays indeterminate.
        """
        try:
            pending = 0
            for name in ("chromium", "chromium-headless-shell"):
                entry = cls._manifest_entry(name)
                if not entry:
                    continue
                dest = cls._browser_dir(name, entry["revision"])
                if cls._browser_installed(name, dest):
                    continue
                archive, _ = cls._cft_archive(name, entry["browserVersion"])
                pending += cls._content_length(f"{host}/{archive}")
            return pending
        except Exception:
            return 0

    @classmethod
    def _ensure_browser(cls, host: str, name: str) -> None:
        """Fetch one browser build from a download host and unpack it."""
        entry = cls._manifest_entry(name)
        if not entry:
            raise RuntimeError(f"{name} is missing from the bundled browsers.json")
        archive, top = cls._cft_archive(name, entry["browserVersion"])
        dest = cls._browser_dir(name, entry["revision"])
        if cls._browser_installed(name, dest):
            return
        # A previous interrupted extraction can leave a marker or partial tree.
        (dest / "INSTALLATION_COMPLETE").unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix="figbak-pw-") as scratch:
            bundle = Path(scratch) / f"{top}.zip"
            cls._download(f"{host}/{archive}", bundle, cls._bump_progress)
            with zipfile.ZipFile(bundle) as data:
                data.extractall(dest)
        if not cls._browser_binary(name, dest):
            raise RuntimeError(f"unexpected archive layout: {archive}")
        (dest / "INSTALLATION_COMPLETE").write_text("", encoding="utf-8")

    @classmethod
    def _browser_dir(cls, name: str, revision: str) -> Path:
        # Playwright's registry replaces hyphens with underscores in cache names.
        return cls.browser_cache_dir() / f"{name.replace('-', '_')}-{revision}"

    @classmethod
    def _migrate_legacy_shell(cls) -> None:
        """Reuse a complete shell saved under the old, incorrect cache name."""
        name = "chromium-headless-shell"
        entry = cls._manifest_entry(name)
        if not entry:
            return
        legacy = cls.browser_cache_dir() / f"{name}-{entry['revision']}"
        current = cls._browser_dir(name, entry["revision"])
        if not current.exists() and cls._browser_installed(name, legacy):
            try:
                legacy.rename(current)
            except OSError:
                pass  # A normal download can still populate the current cache.

    @classmethod
    def _browser_binary(cls, name: str, directory: Path) -> bool:
        archive = cls._manifest_entry(name)
        if not archive:
            return False
        _, top = cls._cft_archive(name, archive["browserVersion"])
        root = directory / top
        if sys.platform == "win32":
            filename = "chrome-headless-shell.exe" if name.endswith("headless-shell") else "chrome.exe"
            return (root / filename).is_file()
        if sys.platform == "darwin":
            if name.endswith("headless-shell"):
                return (root / "chrome-headless-shell").is_file()
            return any(path.is_file() for path in root.glob("*.app/Contents/MacOS/*"))
        filename = "chrome-headless-shell" if name.endswith("headless-shell") else "chrome"
        return (root / filename).is_file()

    @classmethod
    def _browser_installed(cls, name: str, directory: Path) -> bool:
        return (directory / "INSTALLATION_COMPLETE").is_file() and cls._browser_binary(name, directory)

    @staticmethod
    def _cft_archive(name: str, version: str) -> tuple[str, str]:
        """(archive path under any Chrome-for-Testing host, extracted top folder)."""
        if sys.platform == "win32":
            arch = "win64"
        elif sys.platform == "darwin":
            arch = f"mac-{'arm64' if platform.machine() == 'arm64' else 'x64'}"
        else:
            arch = "linux64"
        flavor = "-headless-shell" if name.endswith("headless-shell") else ""
        stem = f"chrome{flavor}-{arch}"
        return f"builds/cft/{version}/{arch}/{stem}.zip", stem

    @classmethod
    def _download(cls, url: str, dest: Path, on_bytes=None) -> None:
        """Ranged, multi-segment download; one stalled socket never kills it."""
        size = cls._content_length(url)
        parts = cls._download_segments(url, size, dest.parent, dest.name, on_bytes)
        with dest.open("wb") as sink:
            for part in parts:
                with part.open("rb") as piece:
                    shutil.copyfileobj(piece, sink)
        if dest.stat().st_size != size:
            raise RuntimeError(f"size mismatch: got {dest.stat().st_size}, want {size}")
        for part in parts:
            part.unlink(missing_ok=True)

    @staticmethod
    def _content_length(url: str) -> int:
        request = Request(url, method="HEAD", headers={"User-Agent": "Fig-Backup"})
        try:
            with urlopen(request, timeout=30) as response:
                length = response.headers.get("Content-Length")
                if length:
                    return int(length)
        except Exception:
            pass
        request = Request(url, headers={"Range": "bytes=0-0", "User-Agent": "Fig-Backup"})
        with urlopen(request, timeout=30) as response:
            total = response.headers.get("Content-Range", "").rpartition("/")[-1]
        if not total.isdigit():
            raise RuntimeError(f"no length announced for {url}")
        return int(total)

    SEGMENTS = 4

    @classmethod
    def _download_segments(cls, url: str, size: int, work: Path,
                           stem: str, on_bytes=None) -> list[Path]:
        count = max(1, min(cls.SEGMENTS, size // (512 * 1024)))
        span = (size + count - 1) // count
        parts, futures = [], []
        with ThreadPoolExecutor(max_workers=count) as pool:
            for index in range(count):
                start = index * span
                end = min(start + span - 1, size - 1)
                if start > end:
                    break
                part = work / f"{stem}.{index:03d}.part"
                parts.append(part)
                futures.append(pool.submit(cls._fetch_segment, url, start, end, part, on_bytes))
            for future in futures:
                future.result()
        return parts

    @staticmethod
    def _fetch_segment(url: str, start: int, end: int, part: Path,
                       on_bytes=None, attempts: int = 4) -> None:
        """Fetch one byte range, resuming from whatever a previous try saved."""
        want = end - start + 1
        for _ in range(attempts):
            have = part.stat().st_size if part.exists() else 0
            if have == want:
                return
            if have > want:
                part.unlink()
                have = 0
            try:
                request = Request(url, headers={"Range": f"bytes={start + have}-{end}",
                                                "User-Agent": "Fig-Backup"})
                with urlopen(request, timeout=25) as response:
                    if response.status != 206 and (start + have):
                        raise RuntimeError("server ignored the range request")
                    with part.open("ab") as sink:
                        while True:
                            chunk = response.read(256 * 1024)
                            if not chunk:
                                break
                            sink.write(chunk)
                            if on_bytes:
                                on_bytes(len(chunk))
            except Exception:
                continue
            if part.stat().st_size == want:
                return
        raise RuntimeError(f"segment {start}-{end} failed after {attempts} attempts")

    @classmethod
    def _install_via_cli(cls) -> str | None:
        """Last resort: the stock installer, fine on networks that don't stall it.

        chromium + headless-shell is ~325MB; on a throttled mirror that can
        take over an hour, hence the generous ceiling. Returns None on success,
        else a one-line failure summary.
        """
        driver, cli = compute_driver_executable()
        try:
            subprocess.run([str(driver), str(cli), "install", "chromium"],
                           check=True, capture_output=True, text=True,
                           timeout=cls.INSTALL_TIMEOUT,
                           creationflags=SUBPROCESS_FLAGS)
            return None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            detail = (getattr(error, "stderr", None) or getattr(error, "output", None)
                      or "").strip().splitlines()
            return f"playwright-installer: {detail[-1] if detail else 'failed'}"

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
    # chromium + headless-shell is ~325MB; on throttled single-stream mirrors
    # that can take over an hour, so this is a generous ceiling, not a guess.
    # A dead source still fails fast: the installer itself times each request
    # out after 30s and retries a handful of times before exiting.
    INSTALL_TIMEOUT = 7200

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

    @classmethod
    def _manifest_entry(cls, name: str) -> dict | None:
        """One browser entry from the bundled driver's browsers.json."""
        try:
            _, cli = compute_driver_executable()
            manifest = json.loads((Path(cli).parent / "browsers.json").read_text(encoding="utf-8"))
            return next((b for b in manifest["browsers"] if b["name"] == name), None)
        except Exception:
            return None

    @classmethod
    def _chromium_archive_path(cls) -> str | None:
        """Path of the pinned chromium zip under any Playwright download host."""
        entry = cls._manifest_entry("chromium")
        if not entry:
            return None
        version = entry["browserVersion"]
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
        if self.active_channel in ("chrome", "msedge"):
            self.failed_system_channels.add(self.active_channel)
        else:
            self.use_headless_shell = True
        self.stop()

    def _goto(self, url: str, **kwargs):
        """page.goto with readable failures instead of Playwright's raw text.

        TargetClosedError is re-raised untouched: app.py recovers from a browser
        crash by reopening headless, and that path keys off this exception.
        """
        try:
            return self.page.goto(url, **kwargs)
        except TargetClosedError:
            raise
        except PlaywrightTimeout as error:
            raise FigmaError(f"Figma took too long to respond: {url}") from error
        except Exception as error:
            raise FigmaError(f"Could not reach Figma: {str(error).splitlines()[0]}") from error

    def open_sign_in(self) -> None:
        self.open(headless=False)
        try:
            self.page.goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)
        except Exception:
            self.close()
            raise

    def close_sign_in(self) -> None:
        if self.context is not None and not self.headless:
            self.close()

    def verify_sign_in(self) -> bool:
        """Check the saved browser session in the same headless mode as backups."""
        self.close_sign_in()
        if self.context is None:
            self.open(headless=True)
        self.page.goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)
        try:
            self.page.wait_for_function(
                "() => document.querySelector('button[aria-label^=\"Plan:\"]') || document.querySelector('a[href*=\"/team/\"]')",
                timeout=15000,
            )
        except PlaywrightTimeout:
            return False
        return bool(self._collect_teams()) or self.page.get_by_role(
            "button", name=re.compile(r"^Plan:")
        ).first.count() > 0

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
        self._goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)
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

    def download(self, file: dict, index: ArchiveIndex, progress, overwrite: bool = False) -> dict:
        expected_extension = native_extension(file.get("editorType"))
        destination, migrated = index.target(file, overwrite=overwrite)
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
        response = self._goto(
            f"https://www.figma.com/{segment}/{file['key']}",
            wait_until="domcontentloaded", timeout=90000,
        )
        if response and response.status == 403:
            # A 403 on ONE file is not a dead session: it is usually file-level
            # access, or Figma blocking the background browser. Raising the auth
            # error here aborted the whole queue AND reset the user's completed
            # setup, so a single blocked file threw them back into the wizard.
            raise FigmaError(
                "Figma refused to open this file (HTTP 403). You may not have "
                "access to it, or Figma is temporarily blocking the backup browser.",
                403,
            )
        # The genuine session signal is the login *route* — match the first path
        # segment only, so a file or board called "login" is not mistaken for it.
        route = [part for part in urlparse(self.page.url).path.split("/") if part]
        if route and route[0].lower() in ("login", "signin", "signup", "password"):
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
    """Check both pinned browser builds and their executables.

    Fails toward False (missing); Browser.open() remains the authoritative installer.
    """
    root = cache_dir if cache_dir is not None else Browser.browser_cache_dir()
    if not root.is_dir():
        return False
    for name in ("chromium", "chromium-headless-shell"):
        entry = Browser._manifest_entry(name)
        if not entry or not Browser._browser_installed(name, root / f"{name.replace('-', '_')}-{entry['revision']}"):
            return False
    return True
