from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from workers.whatsapp_worker import WhatsAppWorker
from core.categories import load_categories
from core.database import GroupDatabase
from pathlib import Path


class MainWindow(QMainWindow):

    WINDOW_TITLE = "WhatsApp Group Sender"
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 750

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "Data"
    SESSION = BASE_DIR / "Session" / "whatsapp_session"
    DB_PATH = BASE_DIR / "Data" / "groups_db.json"
    PROXY = "http://192.168.100.10:8080"

    login_requested = pyqtSignal()
    scan_requested = pyqtSignal()
    close_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    send_requested = pyqtSignal(list, str, int)
    create_group_requested = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()

        self.worker: Optional[WhatsAppWorker] = None
        self.groups: list[str] = []
        self.db = GroupDatabase(self.DB_PATH)

        # groups_db.json (self.db) is a different file from
        # group_categories.json — if it's empty, pull the groups in
        # once so the "Group Manager" tab isn't blank.
        if not self.db.groups:
            self.db.import_from_categories_file(self.DATA_DIR / "group_categories.json")

        self.setup_ui()
        self.setup_worker()
        self.load_saved_groups()

    def setup_ui(self):
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        main_layout.addWidget(self.create_header())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_sender_tab(), "Send Message")
        self.tabs.addTab(self.create_group_manager_tab(), "Group Manager")
        main_layout.addWidget(self.tabs)

        # Bottom
        main_layout.addWidget(self.create_bottom_panel())

    # =====================================================
    # Tab 1: Send Message
    # =====================================================

    def create_sender_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self.create_control_panel(), 1)
        layout.addWidget(self.create_log_panel(), 1)

        return tab

    # =====================================================
    # Tab 2: Group Manager
    # =====================================================

    def create_group_manager_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Groups list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Groups Database")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        left_layout.addWidget(title)

        self.db_groups_list = QListWidget()
        self.db_groups_list.currentItemChanged.connect(self.on_db_group_selected)
        left_layout.addWidget(self.db_groups_list)

        btn_layout = QHBoxLayout()
        self.db_add_group_btn = QPushButton("Add")
        self.db_add_group_btn.clicked.connect(self.db_add_group)
        self.db_rename_group_btn = QPushButton("Rename")
        self.db_rename_group_btn.clicked.connect(self.db_rename_group)
        self.db_delete_group_btn = QPushButton("Delete")
        self.db_delete_group_btn.clicked.connect(self.db_delete_group)
        btn_layout.addWidget(self.db_add_group_btn)
        btn_layout.addWidget(self.db_rename_group_btn)
        btn_layout.addWidget(self.db_delete_group_btn)
        left_layout.addLayout(btn_layout)

        self.db_refresh_btn = QPushButton("Refresh from DB")
        self.db_refresh_btn.clicked.connect(self.refresh_db_groups)
        left_layout.addWidget(self.db_refresh_btn)

        self.db_import_btn = QPushButton("Import from group_categories.json")
        self.db_import_btn.clicked.connect(self.import_from_categories_file)
        left_layout.addWidget(self.db_import_btn)

        splitter.addWidget(left)

        # Right: Details + Create
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create new group
        create_title = QLabel("Create New Group")
        create_title.setFont(font)
        right_layout.addWidget(create_title)

        self.tab_group_name = QLineEdit()
        self.tab_group_name.setPlaceholderText("Group name...")
        right_layout.addWidget(self.tab_group_name)

        self.tab_members = QLineEdit()
        self.tab_members.setPlaceholderText("Members (comma separated)...")
        right_layout.addWidget(self.tab_members)

        self.tab_create_btn = QPushButton("Create Group on WhatsApp")
        self.tab_create_btn.clicked.connect(self.tab_create_group_clicked)
        right_layout.addWidget(self.tab_create_btn)

        right_layout.addSpacing(20)

        # Selected group details
        details_title = QLabel("Selected Group Details")
        details_title.setFont(font)
        right_layout.addWidget(details_title)

        self.db_group_name_label = QLabel("No group selected")
        right_layout.addWidget(self.db_group_name_label)

        right_layout.addWidget(QLabel("Members:"))
        self.db_members_list = QListWidget()
        right_layout.addWidget(self.db_members_list)

        add_mem_layout = QHBoxLayout()
        self.db_new_member = QLineEdit()
        self.db_new_member.setPlaceholderText("New member...")
        self.db_add_mem_btn = QPushButton("Add")
        self.db_add_mem_btn.clicked.connect(self.db_add_member)
        add_mem_layout.addWidget(self.db_new_member)
        add_mem_layout.addWidget(self.db_add_mem_btn)
        right_layout.addLayout(add_mem_layout)

        self.db_remove_mem_btn = QPushButton("Remove Selected Member")
        self.db_remove_mem_btn.clicked.connect(self.db_remove_member)
        right_layout.addWidget(self.db_remove_mem_btn)

        right_layout.addWidget(QLabel("Note:"))
        self.db_note = QTextEdit()
        self.db_note.setMaximumHeight(80)
        right_layout.addWidget(self.db_note)

        self.db_save_note_btn = QPushButton("Save Note")
        self.db_save_note_btn.clicked.connect(self.db_save_note)
        right_layout.addWidget(self.db_save_note_btn)

        right_layout.addStretch()
        splitter.addWidget(right)

        layout.addWidget(splitter)

        self.refresh_db_groups()
        return tab

    # -------------------------------------------------
    # Group Manager DB Methods
    # -------------------------------------------------

    def refresh_db_groups(self):
        self.db_groups_list.clear()
        for name in sorted(self.db.groups.keys(), key=str.casefold):
            self.db_groups_list.addItem(name)

    def import_from_categories_file(self):
        path = self.DATA_DIR / "group_categories.json"
        added = self.db.import_from_categories_file(path)
        self.refresh_db_groups()

        if not path.exists():
            QMessageBox.warning(self, "Import", f"File not found:\n{path}")
        elif added:
            QMessageBox.information(
                self, "Import", f"{added} group(s) imported from group_categories.json."
            )
        else:
            QMessageBox.information(
                self, "Import", "No new groups found in group_categories.json."
            )

    def on_db_group_selected(self):
        item = self.db_groups_list.currentItem()
        if item is None:
            self.db_group_name_label.setText("No group selected")
            self.db_members_list.clear()
            return

        name = item.text()
        self.db_group_name_label.setText(f"Group: {name}")
        group = self.db.get_group(name)
        if group is None:
            return

        self.db_members_list.clear()
        for m in group.get("members", []):
            self.db_members_list.addItem(m)
        self.db_note.setPlainText(group.get("note", ""))

    def db_add_group(self):
        text, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if ok and text.strip():
            if self.db.add_group(text.strip()):
                self.refresh_db_groups()
            else:
                QMessageBox.warning(self, "Error", "Group already exists.")

    def db_rename_group(self):
        item = self.db_groups_list.currentItem()
        if item is None:
            return
        old = item.text()
        text, ok = QInputDialog.getText(self, "Rename", "New name:", text=old)
        if ok and text.strip():
            if self.db.rename_group(old, text.strip()):
                self.refresh_db_groups()
            else:
                QMessageBox.warning(self, "Error", "Cannot rename.")

    def db_delete_group(self):
        item = self.db_groups_list.currentItem()
        if item is None:
            return
        name = item.text()
        reply = QMessageBox.question(self, "Confirm", f"Delete '{name}'?")
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.remove_group(name):
                self.refresh_db_groups()
                self.db_members_list.clear()

    def db_add_member(self):
        item = self.db_groups_list.currentItem()
        if item is None:
            return
        name = item.text()
        mem = self.db_new_member.text().strip()
        if mem and self.db.add_member(name, mem):
            self.db_members_list.addItem(mem)
            self.db_new_member.clear()

    def db_remove_member(self):
        item = self.db_groups_list.currentItem()
        mem_item = self.db_members_list.currentItem()
        if item is None or mem_item is None:
            return
        if self.db.remove_member(item.text(), mem_item.text()):
            self.db_members_list.takeItem(self.db_members_list.row(mem_item))

    def db_save_note(self):
        item = self.db_groups_list.currentItem()
        if item is None:
            return
        group = self.db.get_group(item.text())
        if group:
            group["note"] = self.db_note.toPlainText().strip()
            self.db.save()

    def tab_create_group_clicked(self):
        name = self.tab_group_name.text().strip()
        members_raw = self.tab_members.text().strip()

        if not name:
            QMessageBox.warning(self, "Group Name", "Group name cannot be empty.")
            return

        members = [m.strip() for m in members_raw.split(",") if m.strip()]
        if not members:
            QMessageBox.warning(self, "Members", "At least one member required.")
            return

        self.tab_create_btn.setEnabled(False)
        self.create_group_requested.emit(name, members)

    # =====================================================
    # Worker
    # =====================================================

    def setup_worker(self):
        self.worker = WhatsAppWorker(
            session=self.SESSION,
            proxy=self.PROXY,
        )

        self.login_requested.connect(self.worker.login)
        self.scan_requested.connect(self.worker.scan_groups)
        self.send_requested.connect(self.worker.send_message)
        self.close_requested.connect(self.worker.close)
        self.stop_requested.connect(self.worker.request_stop)
        self.create_group_requested.connect(self.worker.create_group)

        self.worker.log.connect(self.on_worker_log)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.login_finished.connect(self.on_login_finished)
        self.worker.groups_finished.connect(self.on_groups_finished)
        self.worker.send_finished.connect(self.on_send_finished)
        self.worker.error.connect(self.on_worker_error)
        self.worker.create_group_finished.connect(self.on_create_group_finished)

        self.log("Worker initialized.")

    def load_saved_groups(self):
        path = self.DATA_DIR / "group_categories.json"
        if not path.exists():
            return

        try:
            data = load_categories(path)
            all_groups = []
            for cat_groups in data.values():
                all_groups.extend(cat_groups)
            all_groups = sorted(set(all_groups), key=str.casefold)

            if not all_groups:
                return

            self.groups = all_groups
            self.groups_label.setText(f"{len(all_groups)} groups loaded (saved)")
            self.category_combo.clear()
            self.category_combo.addItems(list(data.keys()))
            self.category_combo.setEnabled(True)
            self.send_button.setEnabled(True)
            self.log(f"Loaded {len(all_groups)} groups from save.")

        except Exception as exc:
            self.log(f"Load save warning: {exc}")

    # =====================================================
    # Header
    # =====================================================

    def create_header(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(self.WINDOW_TITLE)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)

        self.status_label = QLabel("● Disconnected")
        status_font = QFont()
        status_font.setPointSize(11)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.status_label)

        return frame

    # =====================================================
    # Control Panel (Tab 1)
    # =====================================================

    def create_control_panel(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        session_title = QLabel("Session")
        session_title.setFont(self.section_font())
        layout.addWidget(session_title)

        session_layout = QHBoxLayout()
        self.login_button = QPushButton("Login / Open WhatsApp")
        self.login_button.clicked.connect(self.login_clicked)
        self.scan_button = QPushButton("Scan Groups")
        self.scan_button.clicked.connect(self.scan_groups_clicked)
        self.scan_button.setEnabled(False)
        session_layout.addWidget(self.login_button)
        session_layout.addWidget(self.scan_button)
        layout.addLayout(session_layout)

        category_title = QLabel("Category")
        category_title.setFont(self.section_font())
        layout.addWidget(category_title)

        self.category_combo = QComboBox()
        self.category_combo.setPlaceholderText("Select category...")
        self.category_combo.setEnabled(False)
        self.category_combo.currentIndexChanged.connect(self.category_changed)
        layout.addWidget(self.category_combo)

        groups_title = QLabel("Groups")
        groups_title.setFont(self.section_font())
        layout.addWidget(groups_title)

        self.groups_label = QLabel("No groups loaded")
        layout.addWidget(self.groups_label)

        message_title = QLabel("Message")
        message_title.setFont(self.section_font())
        layout.addWidget(message_title)

        self.message_input = QPlainTextEdit()
        self.message_input.setPlaceholderText("Write your message...")
        self.message_input.setMaximumHeight(150)
        layout.addWidget(self.message_input)

        delay_title = QLabel("Send delay (seconds)")
        delay_title.setFont(self.section_font())
        layout.addWidget(delay_title)

        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 3600)
        self.delay_spinbox.setValue(2)
        layout.addWidget(self.delay_spinbox)

        self.send_button = QPushButton("Send Message")
        self.send_button.setMinimumHeight(42)
        self.send_button.clicked.connect(self.send_clicked)
        self.send_button.setEnabled(False)
        layout.addWidget(self.send_button)

        layout.addStretch()
        return frame

    def create_log_panel(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Activity Log")
        title.setFont(self.section_font())
        layout.addWidget(title)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Application logs will appear here...")
        layout.addWidget(self.log_output)

        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_button)

        return frame

    def create_bottom_panel(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        return frame

    @staticmethod
    def section_font():
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        return font

    # =====================================================
    # Actions
    # =====================================================

    def login_clicked(self):
        if self.worker is None:
            return
        self.log("Opening WhatsApp...")
        self.login_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.set_status("Connecting")
        self.login_requested.emit()

    def on_login_finished(self, success: bool):
        self.login_button.setEnabled(True)
        if success:
            self.scan_button.setEnabled(True)
            self.set_status("Connected")
            self.log("WhatsApp connected.")
        else:
            self.set_status("Disconnected")
            self.log("WhatsApp connection failed.")

    def scan_groups_clicked(self):
        self.log("Starting group scan...")
        self.scan_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Scanning groups...")
        self.scan_requested.emit()

    def on_groups_finished(self, groups: list):
        self.groups = groups
        count = len(groups)
        self.groups_label.setText(f"{count} groups loaded")
        self.category_combo.clear()
        self.category_combo.addItem("All Groups")
        self.category_combo.setEnabled(count > 0)
        self.send_button.setEnabled(count > 0)
        self.scan_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"{count} groups loaded")
        self.log(f"Loaded {count} groups.")

    def category_changed(self, index: int):
        if index < 0:
            return
        category = self.category_combo.currentText().strip()
        if category:
            self.log(f"Selected category: {category}")

    def send_clicked(self):
        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Message", "Message cannot be empty.")
            return
        if not self.groups:
            QMessageBox.warning(self, "Groups", "No groups loaded.")
            return

        delay = self.delay_spinbox.value()
        confirm = QMessageBox.question(
            self, "Confirm", f"Send message to {len(self.groups)} groups?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.send_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Sending...")
        self.send_requested.emit(self.groups, message, delay)

    def on_send_finished(self, success: int, failed: int):
        self.send_button.setEnabled(bool(self.groups))
        self.scan_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText(
            f"Finished | Success: {success} | Failed: {failed}"
        )
        self.log(f"Send finished. Success: {success}, Failed: {failed}")

    def on_create_group_finished(self, success: bool):
        self.tab_create_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", "Group created successfully!")
            self.tab_group_name.clear()
            self.tab_members.clear()
            # Also add to DB
            name = self.tab_group_name.text().strip()
            if name:
                self.db.add_group(name)
                self.refresh_db_groups()
        else:
            QMessageBox.critical(self, "Error", "Failed to create group.")

    def on_worker_log(self, message: str):
        self.log(message)

    def on_status_changed(self, status: str):
        self.set_status(status)

    def on_progress_changed(self, value: int, text: str):
        self.set_progress(value, text)

    def on_worker_error(self, message: str):
        self.log(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)

    def log(self, message: str):
        self.log_output.appendPlainText(message)

    def clear_log(self):
        self.log_output.clear()

    def set_status(self, text: str):
        self.status_label.setText(f"● {text}")

    def set_progress(self, value: int, text: str = ""):
        self.progress_bar.setValue(value)
        if text:
            self.progress_label.setText(text)

    def closeEvent(self, event):
        self.log("Shutting down...")
        self.stop_requested.emit()
        self.close_requested.emit()
        event.accept()


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()