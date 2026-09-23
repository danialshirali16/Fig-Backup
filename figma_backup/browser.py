"""Figma's native Save local copy flow, automated with Python Playwright."""
from __future__ import annotations

import re
import os
import subprocess
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
from playwright._impl._driver import compute_driver_executable

from .core import ArchiveIndex, FigmaError, SUPPORT, merge_teams, verify_fig


class Browser:
    def __init__(self, support: Path = SUPPORT):
        self.support = support
        self.playwright = None
        self.context = None
        self.page = None
        self.headless = True

    def open(self, headless: bool = True) -> None:
        self.close()
        # Playwright's PyInstaller hook otherwise points to a read-only .app/.local-browsers.
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path.home() / "Library/Caches/ms-playwright")
        if self.playwright is None:
            self.playwright = sync_playwright().start()
        self.support.mkdir(parents=True, exist_ok=True, mode=0o700)
        options = dict(channel="chromium", headless=headless, accept_downloads=True,
                       viewport={"width": 1400, "height": 900})
        if headless:
            browser_binary = Path(self.playwright.chromium.executable_path)
            if not browser_binary.exists():
                self._install_chromium()
            version = subprocess.run([str(browser_binary), "--version"],
                                     check=True, capture_output=True, text=True).stdout
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", version)
            if not match:
                raise FigmaError("Could not determine the Chromium version")
            options["user_agent"] = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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
        try:
            subprocess.run([str(driver), str(cli), "install", "chromium"],
                           check=True, capture_output=True, text=True, timeout=900)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise FigmaError(f"Automatic Chromium installation failed: {error}") from error

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

    def open_sign_in(self) -> None:
        self.open(headless=False)
        self.page.goto("https://www.figma.com/files", wait_until="domcontentloaded", timeout=90000)

    def _collect_teams(self) -> list[dict]:
        return self.page.evaluate("""() => {
          const found = new Map();
          const current = location.pathname.match(/\\/team\\/(\\d+)/);
          if (current) {
            const label = document.querySelector('button[aria-label^="Plan:"]')?.getAttribute('aria-label');
            found.set(current[1], {id: current[1], name: label?.replace(/^Plan:\\s*/, '').trim() || current[1]});
          }
          for (const a of document.querySelectorAll('a[href*="/team/"]')) {
            const match = a.href.match(/\\/team\\/(\\d+)/);
            if (match) found.set(match[1], {id: match[1], name: (a.innerText || a.getAttribute('aria-label') || a.title || match[1]).trim()});
          }
          return [...found.values()];
        }""")

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
            entries = self.page.locator('[role="menuitemradio"]').evaluate_all("""els => els.map(el => {
              const lines = el.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
              return {name: lines.length > 1 ? lines.at(-2) : lines[0], selected: el.getAttribute('aria-checked') === 'true'};
            }).filter(x => x.name)""")
            self.page.keyboard.press("Escape")
        except Exception:
            return {"teams": merge_teams(saved, teams), "auth_required": False}
        initial = re.search(r"/team/(\d+)", original_url)
        initial_id = initial.group(1) if initial else None
        all_teams = teams[:]
        for index, entry in enumerate(entries):
            saved_id = next((x["id"] for x in saved if x["name"] == entry["name"]), None)
            if entry["selected"] and (initial_id or saved_id):
                all_teams.append({"id": initial_id or saved_id, "name": entry["name"]})
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
                    all_teams.append({"id": match.group(1), "name": entry["name"]})
            except Exception:
                self.page.keyboard.press("Escape")
        try:
            self.page.goto(original_url, wait_until="domcontentloaded", timeout=90000)
        except Exception:
            pass
        return {"teams": merge_teams(saved, all_teams), "auth_required": False}

    def _save_local_copy(self) -> None:
        page = self.page
        try:
            page.keyboard.press("ControlOrMeta+/", timeout=3500)
            page.wait_for_function("() => ['INPUT','TEXTAREA'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable", timeout=3500)
            page.keyboard.type("save local copy", delay=50)
            page.get_by_text(re.compile("save local copy", re.I)).first.wait_for(state="visible", timeout=5000)
            page.keyboard.press("Enter")
            return
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
            except Exception:
                continue
        else:
            raise FigmaError("The Figma main menu was not found")
        file_menu = page.get_by_role("menuitem", name=re.compile(r"^File\b", re.I)).first
        try:
            file_menu.hover(timeout=6000)
        except Exception:
            page.get_by_text("File", exact=True).last.hover(timeout=6000)
        save = page.get_by_role("menuitem", name=re.compile("Save local copy", re.I)).last
        try:
            save.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeout:
            try:
                file_menu.click(timeout=6000)
            except Exception:
                pass
            save = page.get_by_text("Save local copy", exact=True).last
        save.click(timeout=10000)

    def download(self, file: dict, index: ArchiveIndex, progress) -> dict:
        destination, migrated = index.target(file)
        if destination.exists():
            verify_fig(destination)
            return {"status": "renamed" if migrated else "exists", "path": str(destination)}
        if self.context is None or not self.headless:
            self.open(headless=True)
        progress("opening", "Opening the file in Figma…")
        response = self.page.goto(
            f"https://www.figma.com/design/{file['key']}",
            wait_until="domcontentloaded", timeout=90000,
        )
        if response and response.status == 403:
            raise FigmaError("Figma blocked the background editor (HTTP 403). No browser window was opened.")
        if re.search(r"/login|/signin", self.page.url):
            raise FigmaError("Browser sign-in is required. Use the Sign in button, then retry.")
        try:
            self.page.locator("canvas").first.wait_for(state="attached", timeout=120000)
        except PlaywrightTimeout as error:
            raise FigmaError("The Figma editor did not load in the background browser.") from error
        progress("preparing", "Preparing a local copy…")
        try:
            with self.page.expect_download(timeout=480000) as download_info:
                self._save_local_copy()
            download = download_info.value
        except Exception as error:
            screenshot = self.support / f"download-error-{file['key']}.png"
            try:
                self.page.screenshot(path=str(screenshot))
            except Exception:
                pass
            raise FigmaError(f"The local-copy download did not start: {str(error).splitlines()[0]}") from error
        if not download.suggested_filename.lower().endswith(".fig"):
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
