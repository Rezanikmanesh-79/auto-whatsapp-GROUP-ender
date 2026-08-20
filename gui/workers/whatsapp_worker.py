from __future__ import annotations

from pathlib import Path
from typing import Optional, Generator

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import QApplication

from core.whatsapp_client import WhatsAppClient
from core.actions import WhatsAppActions
from core.categories import save_categories
from core.database import GroupDatabase

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"


class WhatsAppWorker(QObject):
    """
    Worker بدون QThread — همه چیز توی Main Thread.
    send با QTimer + generator اجرا می‌شه تا GUI freeze نشه.
    """

    log = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, str)

    login_finished = pyqtSignal(bool)
    groups_finished = pyqtSignal(list)
    send_finished = pyqtSignal(int, int)
    create_group_finished = pyqtSignal(bool)

    error = pyqtSignal(str)

    def __init__(
        self,
        session: str,
        proxy: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.session = session
        self.proxy = proxy

        self.client: Optional[WhatsAppClient] = None
        self._stop_requested = False
        self._send_timer: Optional[QTimer] = None
        self._send_gen: Optional[Generator] = None

    def _should_stop(self) -> bool:
        return self._stop_requested

    def _log(self, msg: str) -> None:
        self.log.emit(msg)

    def _status(self, status: str) -> None:
        self.status_changed.emit(status)

    def _error(self, msg: str) -> None:
        self._status("Error")
        self._log(f"ERROR: {msg}")
        self.error.emit(msg)

    def _get_page(self):
        if self.client is None:
            self._error("Client not running.")
            return None

        page = self.client.page
        if page is None:
            self._error("Page not available.")
            return None

        try:
            if page.is_closed():
                self._error("Page is closed.")
                return None
        except Exception:
            pass

        return page

    @staticmethod
    def _process_events() -> None:
        QApplication.processEvents()

    @pyqtSlot()
    def request_stop(self) -> None:
        self._stop_requested = True
        self._log("Stop requested.")

    @pyqtSlot()
    def login(self) -> None:
        self._stop_requested = False

        try:
            self._status("Connecting")
            self._log("Starting WhatsApp...")

            self.client = WhatsAppClient(
                session=self.session,
                proxy=self.proxy,
            )
            page = self.client.open()

            if self._should_stop():
                self.client.close()
                self.login_finished.emit(False)
                return

            ready = False
            for _ in range(150):
                if self._should_stop():
                    self.client.close()
                    self.login_finished.emit(False)
                    return

                try:
                    if page.locator("body").is_visible():
                        ready = True
                        break
                except Exception:
                    pass

                try:
                    page.wait_for_timeout(100)
                except Exception:
                    break

                self._process_events()

            if not ready:
                self._error("WhatsApp did not become ready.")
                self.client.close()
                self.login_finished.emit(False)
                return

            self._status("Connected")
            self._log("WhatsApp Web opened successfully.")
            self.login_finished.emit(True)

        except Exception as exc:
            self._error(f"Login error: {exc}")
            if self.client:
                self.client.close()
            self.login_finished.emit(False)

    @pyqtSlot()
    def scan_groups(self) -> None:
        page = self._get_page()
        if page is None:
            return

        self._stop_requested = False

        try:
            self._status("Scanning groups")
            self._log("Scanning groups...")

            actions = WhatsAppActions(
                page,
                self._should_stop,
                self._process_events,
            )
            groups = actions.scan_groups(use_filter=True)

            if self._should_stop():
                self._log("Group scan stopped.")
                return

            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                save_categories(
                    {"All Groups": groups},
                    DATA_DIR / "group_categories.json",
                )
                self._log("Saved to Data/group_categories.json")
            except Exception as exc:
                self._log(f"Save warning: {exc}")

            try:
                db = GroupDatabase(DATA_DIR / "groups_db.json")
                db.import_from_scan(groups)
                self._log("Imported to groups_db.json")
            except Exception as exc:
                self._log(f"DB import warning: {exc}")

            self._log(f"Found {len(groups)} groups.")
            self._status("Groups loaded")
            self.groups_finished.emit(groups)

        except Exception as exc:
            self._error(f"Group scan error: {exc}")

    @pyqtSlot(list, str, int)
    def send_message(self, groups: list, message: str, delay: int = 2) -> None:
        page = self._get_page()
        if page is None:
            return

        if not groups:
            self._error("No groups selected.")
            return

        message = message.strip()
        if not message:
            self._error("Message cannot be empty.")
            return

        self._stop_requested = False
        self._status("Sending")
        self._log(f"Starting send to {len(groups)} groups.")

        actions = WhatsAppActions(
            page,
            self._should_stop,
            self._process_events,
        )

        self._send_gen = self._send_generator(groups, message, delay, actions)
        self._send_timer = QTimer(self)
        self._send_timer.timeout.connect(self._run_send_step)
        self._send_timer.start(50)

    def _send_generator(
        self,
        groups: list,
        message: str,
        delay: int,
        actions: WhatsAppActions,
    ):
        success = 0
        failed = 0
        total = len(groups)

        for current, group_name in enumerate(groups, 1):
            if self._should_stop():
                yield "stopped", success, failed
                return

            self._log(f"[{current}/{total}] {group_name}")

            if not actions.find_group(group_name):
                failed += 1
                self._log(f"Failed to open: {group_name}")
            else:
                if actions.send_message(message):
                    success += 1
                    self._log(f"Sent: {group_name}")
                else:
                    failed += 1
                    self._log(f"Failed: {group_name}")

            pct = int(current * 100 / total)
            self.progress_changed.emit(
                pct,
                f"{current}/{total} | Success: {success} | Failed: {failed}",
            )

            if current < total and delay > 0 and not self._should_stop():
                self._log(f"Waiting {delay}s...")
                for _ in range(delay * 10):
                    if self._should_stop():
                        break
                    actions.interruptible_wait(0)
                    yield "waiting", success, failed

            yield "continue", success, failed

        yield "done", success, failed

    def _run_send_step(self):
        try:
            status, success, failed = next(self._send_gen)

            if status in ("stopped", "done"):
                self._send_timer.stop()
                self._send_timer.deleteLater()
                self._send_timer = None
                self._status("Stopped" if status == "stopped" else "Ready")
                self.send_finished.emit(success, failed)

        except StopIteration:
            if self._send_timer is not None:
                self._send_timer.stop()
                self._send_timer.deleteLater()
                self._send_timer = None

        except Exception as exc:
            if self._send_timer is not None:
                self._send_timer.stop()
                self._send_timer.deleteLater()
                self._send_timer = None
            self._error(f"Send error: {exc}")

    @pyqtSlot(str, list)
    def create_group(self, group_name: str, members: list[str]) -> None:
        page = self._get_page()
        if page is None:
            self.create_group_finished.emit(False)
            return

        self._stop_requested = False
        self._status("Creating group")
        self._log(f"Creating group: {group_name}")

        try:
            actions = WhatsAppActions(
                page,
                self._should_stop,
                self._process_events,
            )
            result = actions.create_group(group_name, members)

            if result:
                self._log(f"Group '{group_name}' created.")
                self._status("Ready")
            else:
                self._log("Failed to create group.")
                self._status("Error")

            self.create_group_finished.emit(result)

        except Exception as exc:
            self._error(f"Create group error: {exc}")
            self.create_group_finished.emit(False)

    @pyqtSlot()
    def close(self) -> None:
        try:
            if self._send_timer is not None:
                self._send_timer.stop()
                self._send_timer.deleteLater()
                self._send_timer = None

            if self.client is not None:
                self._log("Closing WhatsApp...")
                self.client.close()
                self.client = None

            self._status("Disconnected")
            self._log("WhatsApp client closed.")

        except Exception as exc:
            self._log(f"Close error: {exc}")