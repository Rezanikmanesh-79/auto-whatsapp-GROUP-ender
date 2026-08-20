from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


class WhatsAppClient:
    """
    Playwright client با lifecycle درست.
    ترتیب بستن: page → context → playwright
    """

    URL = "https://web.whatsapp.com"
    NAV_TIMEOUT = 10_000
    DEF_TIMEOUT = 8_000

    def __init__(
        self,
        session: str | Path,
        proxy: Optional[str] = None,
        headless: bool = False,
    ) -> None:
        self.session = Path(session)
        self.proxy = proxy
        self.headless = headless

        self._pw: Optional[Playwright] = None
        self._ctx: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._closed = True

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def is_running(self) -> bool:
        if self._page is None:
            return False
        try:
            return not self._page.is_closed()
        except Exception:
            return False

    def start(self) -> Page:
        if self.is_running:
            return self._page  # type: ignore[return-value]

        self.session.mkdir(parents=True, exist_ok=True)

        self._pw = sync_playwright().start()

        opts: dict = {
            "user_data_dir": str(self.session),
            "headless": self.headless,
        }
        if self.proxy:
            opts["proxy"] = {"server": self.proxy}

        self._ctx = self._pw.firefox.launch_persistent_context(**opts)
        self._ctx.set_default_timeout(self.DEF_TIMEOUT)
        self._ctx.set_default_navigation_timeout(self.NAV_TIMEOUT)

        self._page = (
            self._ctx.pages[0]
            if self._ctx.pages
            else self._ctx.new_page()
        )
        self._page.set_default_timeout(self.DEF_TIMEOUT)
        self._page.set_default_navigation_timeout(self.NAV_TIMEOUT)

        self._closed = False
        return self._page

    def open(self) -> Page:
        page = self.start()
        if "web.whatsapp.com" not in page.url:
            page.goto(
                self.URL,
                wait_until="domcontentloaded",
                timeout=self.NAV_TIMEOUT,
            )
        return page

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        if self._page is not None:
            try:
                if not self._page.is_closed():
                    self._page.close()
            except Exception:
                pass
            self._page = None

        if self._ctx is not None:
            try:
                self._ctx.close()
            except Exception:
                pass
            self._ctx = None

        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def __enter__(self) -> WhatsAppClient:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.close()