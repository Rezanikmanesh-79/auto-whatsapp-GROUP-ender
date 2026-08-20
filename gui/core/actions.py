import re
from typing import Callable, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

SELECTORS = {
    "chat_title": '[data-testid="cell-frame-title"] span[title]',
    "chat_container": 'xpath=ancestor::*[@data-testid="cell-frame-container"]',
    "message_box": '[data-testid="conversation-compose-box-input"]',
    "message_box_alt": 'footer div[contenteditable="true"]',
    "message_box_alt2": 'div[contenteditable="true"][role="textbox"]',
}

ShouldStop = Callable[[], bool]
ProcessEvents = Callable[[], None]


def _default_stop() -> bool:
    return False


def _default_events() -> None:
    pass


_UNREAD_SUFFIX = re.compile(r"\s+\d+$")


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def _remove_unread(value: str) -> str:
    return re.sub(_UNREAD_SUFFIX, "", _normalize(value)).strip()


def _first_line(value: str) -> str:
    lines = [_normalize(line) for line in value.splitlines()]
    lines = [line for line in lines if line]
    return lines[0] if lines else ""


def _get_labels(element) -> list[str]:
    values: list[str] = []
    for attr in ("inner_text", "aria-label", "title"):
        try:
            if attr == "inner_text":
                text = _normalize(element.inner_text())
            else:
                text = _normalize(element.get_attribute(attr))
            if text:
                values.append(text)
        except Exception:
            pass
    return values


def _is_groups_element(element) -> bool:
    try:
        if not element.is_visible():
            return False
        for label in _get_labels(element):
            normalized = _remove_unread(label)
            if re.fullmatch(r"Groups", normalized, re.IGNORECASE):
                return True
        return False
    except Exception:
        return False


def _is_selected(element) -> bool:
    try:
        if element.get_attribute("aria-selected") == "true":
            return True
    except Exception:
        pass
    try:
        if element.get_attribute("data-active") == "true":
            return True
    except Exception:
        pass
    return False


class WhatsAppActions:
    def __init__(
        self,
        page: Page,
        should_stop: ShouldStop = _default_stop,
        process_events: ProcessEvents = _default_events,
    ) -> None:
        self.page = page
        self.should_stop = should_stop
        self.process_events = process_events

    def _check_stop(self) -> bool:
        self.process_events()
        return self.should_stop()

    def _breath(self, ms: int = 10) -> None:
        self.process_events()
        if ms > 0:
            try:
                self.page.wait_for_timeout(ms)
            except Exception:
                pass

    def _scroll_last(self, locator, count: int) -> None:
        if count <= 0:
            return
        try:
            locator.nth(count - 1).scroll_into_view_if_needed(timeout=2000)
        except Exception:
            pass

    def open_groups_filter(self) -> bool:
        tab = self._find_groups_tab()
        if tab is None:
            return False

        if _is_selected(tab):
            return True

        try:
            tab.scroll_into_view_if_needed(timeout=3000)
            self._breath(100)
            tab.click(timeout=5000)
            self._breath(300)
            return True
        except Exception:
            pass

        try:
            tab.evaluate("(el) => el.click()")
            self._breath(300)
            return True
        except Exception:
            return False

    def _find_groups_tab(self):
        try:
            filters = self.page.locator('[data-testid="filter-button"]')
            count = min(filters.count(), 20)
            for i in range(count):
                self._breath(0)
                el = filters.nth(i)
                if _is_groups_element(el):
                    return el
        except Exception:
            pass

        try:
            tabs = self.page.locator('[role="tab"]')
            count = min(tabs.count(), 10)
            for i in range(count):
                self._breath(0)
                tab = tabs.nth(i)
                if _is_groups_element(tab):
                    return tab
        except Exception:
            pass

        try:
            candidates = self.page.get_by_text(
                re.compile(r"^\s*Groups(?:\s*\d+)?\s*$", re.IGNORECASE)
            )
            count = min(candidates.count(), 5)
            for i in range(count):
                self._breath(0)
                el = candidates.nth(i)
                if not el.is_visible():
                    continue
                clickable = el.locator(
                    "xpath=ancestor-or-self::*[@role='tab' or @role='button' or self::button]"
                ).first
                if clickable.count() and _is_groups_element(clickable):
                    return clickable
        except Exception:
            pass

        return None

    def find_group(self, group_name: str, max_rounds: int = 25) -> bool:
        locator = self.page.locator(SELECTORS["chat_title"])
        stable = 0
        prev_count = 0

        for _ in range(max_rounds):
            if self._check_stop():
                return False

            count = locator.count()

            for i in range(count):
                if self._check_stop():
                    return False

                try:
                    chat = locator.nth(i)
                    if not chat.is_visible():
                        continue

                    title = chat.get_attribute("title")
                    if title and title.strip() == group_name:
                        chat.scroll_into_view_if_needed(timeout=2000)
                        self._breath(100)

                        try:
                            chat.click(timeout=1500)
                        except Exception:
                            chat.locator(
                                SELECTORS["chat_container"]
                            ).first.click(timeout=1500)

                        self._breath(200)
                        return True

                except Exception:
                    continue

            self._scroll_last(locator, count)

            if count == prev_count:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
                prev_count = count

            self._breath(300)

        return False

    def send_message(self, message: str) -> bool:
        if not message.strip():
            return False

        box = self._find_message_box()
        if box is None:
            return False

        try:
            box.click(timeout=1500)

            try:
                box.fill(message, timeout=1500)
            except Exception:
                box.press("Control+A")
                box.type(message)

            box.press("Enter")
            self._breath(200)
            return True

        except Exception:
            return False

    def _find_message_box(self):
        for sel in (
            SELECTORS["message_box"],
            SELECTORS["message_box_alt"],
            SELECTORS["message_box_alt2"],
        ):
            try:
                els = self.page.locator(sel)
                for i in range(els.count()):
                    self._breath(0)
                    el = els.nth(i)
                    if el.is_visible():
                        return el
            except Exception:
                continue
        return None

    def scan_groups(self, max_rounds: int = 25, use_filter: bool = True) -> list[str]:
        if use_filter:
            self.open_groups_filter()

        names: set[str] = set()
        prev_count = -1
        stable = 0

        locator = self.page.locator(SELECTORS["chat_title"])

        for _ in range(max_rounds):
            if self._check_stop():
                break

            count = locator.count()

            for i in range(count):
                if self._check_stop():
                    break

                try:
                    el = locator.nth(i)
                    if not el.is_visible():
                        continue

                    name = self._extract_chat_name(el)
                    if name:
                        names.add(name)

                except Exception:
                    continue

            current = len(names)

            if current == prev_count:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
                prev_count = current

            self._scroll_last(locator, count)
            self._breath(300)

        return sorted(names, key=str.casefold)

    def _extract_chat_name(self, element) -> Optional[str]:
        try:
            title = element.get_attribute("title")
            if title:
                title = _normalize(title)
                if title:
                    return title
        except Exception:
            pass

        try:
            nested = element.locator("[title]")
            for i in range(nested.count()):
                self._breath(0)
                title = nested.nth(i).get_attribute("title")
                if title:
                    title = _normalize(title)
                    if title:
                        return title
        except Exception:
            pass

        try:
            text = _normalize(element.inner_text())
            name = _first_line(text)
            name = _remove_unread(name)
            return name or None
        except Exception:
            return None

    def create_group(self, group_name: str, members: list[str]) -> bool:
        if not group_name.strip() or not members:
            return False

        try:
            try:
                menu = self.page.locator('[data-testid="menu"]').first
                if menu.is_visible():
                    menu.click(timeout=3000)
                else:
                    self.page.locator('[data-testid="chat-list-search"]').first.click(timeout=3000)
            except Exception:
                self.page.get_by_text("New chat").first.click(timeout=3000)

            self._breath(400)

            try:
                self.page.get_by_text("New group").first.click(timeout=3000)
            except Exception:
                self.page.locator('[data-testid="new-group"]').first.click(timeout=3000)

            self._breath(600)

            for member in members:
                if self._check_stop():
                    return False

                search = self.page.locator(
                    'input[placeholder*="Search"], [data-testid="contact-search-input"]'
                ).first
                search.fill(member)
                self._breath(600)

                try:
                    result = self.page.locator('[data-testid="cell-frame-title"]').first
                    result.click(timeout=3000)
                except Exception:
                    self.page.locator('[role="checkbox"]').first.click(timeout=3000)

                self._breath(300)

            try:
                self.page.get_by_text("Next").first.click(timeout=3000)
            except Exception:
                self.page.locator('[data-testid="next"]').first.click(timeout=3000)

            self._breath(500)

            try:
                subject = self.page.locator('[data-testid="group-subject-input"]').first
                subject.fill(group_name)
            except Exception:
                inputs = self.page.locator('input')
                for i in range(inputs.count()):
                    inp = inputs.nth(i)
                    if inp.is_visible():
                        inp.fill(group_name)
                        break

            self._breath(300)

            try:
                self.page.get_by_text("Create").first.click(timeout=5000)
            except Exception:
                self.page.locator('[data-testid="create-group"]').first.click(timeout=5000)

            self._breath(1000)
            return True

        except Exception:
            return False

    def interruptible_wait(self, seconds: int) -> None:
        for _ in range(seconds * 10):
            if self._check_stop():
                return
            self._breath(100)