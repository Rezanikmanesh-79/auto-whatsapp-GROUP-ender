from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.database import GroupDatabase
from pathlib import Path


class GroupManagerDialog(QDialog):
    """
    پنجرهٔ مدیریت دسته‌ها، گروه‌ها و اعضا.

    سه ستون:
      - Categories: CRUD کامل روی دسته‌ها (Add/Rename/Delete) + فیلتر کردن
        لیست گروه‌ها بر اساس دستهٔ انتخاب‌شده
      - Groups: CRUD روی گروه‌ها (Add/Rename/Delete) + افزودن/حذف گروه
        انتخاب‌شده به/از دستهٔ فعلی
      - Details: اعضا و یادداشت گروه انتخاب‌شده (بدون تغییر)
    """

    data_changed = pyqtSignal()

    def __init__(self, db_path: Path, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.db = GroupDatabase(db_path)
        self.current_category: Optional[str] = None
        self.current_group: Optional[str] = None

        self.setWindowTitle("Group Manager")
        self.resize(1100, 650)

        self.setup_ui()

        # This dialog's database (GroupDatabase) is a *different* file
        # from group_categories.json (the flat file the scanner/Send
        # tab use). If this database starts out empty, pull the groups
        # in from group_categories.json once so the panel isn't blank.
        if not self.db.groups:
            self._import_from_categories_file(silent=True)

        self.load_categories()
        self.load_groups()

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self._build_categories_panel())
        splitter.addWidget(self._build_groups_panel())
        splitter.addWidget(self._build_details_panel())

        main_layout.addWidget(splitter)

    def _section_font(self) -> QFont:
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        return font

    def _build_categories_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Categories")
        title.setFont(self._section_font())
        layout.addWidget(title)

        self.categories_list = QListWidget()
        self.categories_list.currentItemChanged.connect(self.on_category_selected)
        layout.addWidget(self.categories_list)

        btn_layout = QHBoxLayout()
        self.add_category_btn = QPushButton("Add")
        self.add_category_btn.clicked.connect(self.add_category)
        self.rename_category_btn = QPushButton("Rename")
        self.rename_category_btn.clicked.connect(self.rename_category)
        self.delete_category_btn = QPushButton("Delete")
        self.delete_category_btn.clicked.connect(self.delete_category)
        btn_layout.addWidget(self.add_category_btn)
        btn_layout.addWidget(self.rename_category_btn)
        btn_layout.addWidget(self.delete_category_btn)
        layout.addLayout(btn_layout)

        self.clear_filter_btn = QPushButton("Show All Groups")
        self.clear_filter_btn.clicked.connect(self.clear_category_filter)
        layout.addWidget(self.clear_filter_btn)

        self.import_btn = QPushButton("Import from group_categories.json")
        self.import_btn.clicked.connect(self.import_from_categories_file)
        layout.addWidget(self.import_btn)

        return panel

    def _build_groups_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Groups")
        title.setFont(self._section_font())
        layout.addWidget(title)

        self.groups_list = QListWidget()
        self.groups_list.currentItemChanged.connect(self.on_group_selected)
        layout.addWidget(self.groups_list)

        btn_layout = QHBoxLayout()
        self.add_group_btn = QPushButton("Add")
        self.add_group_btn.clicked.connect(self.add_group)
        self.rename_group_btn = QPushButton("Rename")
        self.rename_group_btn.clicked.connect(self.rename_group)
        self.delete_group_btn = QPushButton("Delete")
        self.delete_group_btn.clicked.connect(self.delete_group)
        btn_layout.addWidget(self.add_group_btn)
        btn_layout.addWidget(self.rename_group_btn)
        btn_layout.addWidget(self.delete_group_btn)
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("Assign selected group to category:"))
        assign_layout = QHBoxLayout()
        self.assign_category_combo = QComboBox()
        self.assign_btn = QPushButton("Add to Category")
        self.assign_btn.clicked.connect(self.assign_group_to_category)
        assign_layout.addWidget(self.assign_category_combo)
        assign_layout.addWidget(self.assign_btn)
        layout.addLayout(assign_layout)

        self.remove_from_category_btn = QPushButton("Remove from Selected Category")
        self.remove_from_category_btn.setEnabled(False)
        self.remove_from_category_btn.clicked.connect(self.remove_group_from_category)
        layout.addWidget(self.remove_from_category_btn)

        return panel

    def _build_details_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Group Details")
        title.setFont(self._section_font())
        layout.addWidget(title)

        self.group_name_label = QLabel("Select a group")
        self.group_name_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.group_name_label)

        self.group_categories_label = QLabel("")
        self.group_categories_label.setWordWrap(True)
        layout.addWidget(self.group_categories_label)

        layout.addWidget(QLabel("Members:"))
        self.members_list = QListWidget()
        layout.addWidget(self.members_list)

        add_member_layout = QHBoxLayout()
        self.member_input = QLineEdit()
        self.member_input.setPlaceholderText("Member name or phone...")
        self.add_member_btn = QPushButton("Add Member")
        self.add_member_btn.clicked.connect(self.add_member)
        add_member_layout.addWidget(self.member_input)
        add_member_layout.addWidget(self.add_member_btn)
        layout.addLayout(add_member_layout)

        self.remove_member_btn = QPushButton("Remove Selected Member")
        self.remove_member_btn.clicked.connect(self.remove_member)
        layout.addWidget(self.remove_member_btn)

        layout.addWidget(QLabel("Note:"))
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(80)
        layout.addWidget(self.note_edit)

        self.save_note_btn = QPushButton("Save Note")
        self.save_note_btn.clicked.connect(self.save_note)
        layout.addWidget(self.save_note_btn)

        return panel

    # =====================================================
    # Categories CRUD
    # =====================================================

    def load_categories(self):
        self.categories_list.clear()
        for name in self.db.category_names():
            self.categories_list.addItem(name)
        self._refresh_assign_combo()

    def _refresh_assign_combo(self):
        self.assign_category_combo.clear()
        self.assign_category_combo.addItems(self.db.category_names())

    def on_category_selected(self):
        item = self.categories_list.currentItem()
        self.current_category = item.text() if item else None
        self.remove_from_category_btn.setEnabled(self.current_category is not None)
        self.load_groups()

    def clear_category_filter(self):
        self.categories_list.clearSelection()
        self.current_category = None
        self.remove_from_category_btn.setEnabled(False)
        self.load_groups()

    def _categories_file_path(self) -> Path:
        # group_categories.json lives alongside this dialog's db file
        # (both under .../Data/) — see whatsapp_worker.py's scan_groups.
        return self.db.path.parent / "group_categories.json"

    def import_from_categories_file(self):
        self._import_from_categories_file(silent=False)

    def _import_from_categories_file(self, silent: bool = False):
        path = self._categories_file_path()
        added = self.db.import_from_categories_file(path)

        self.load_categories()
        self.load_groups()
        if self.current_group:
            self.on_group_selected()
        self.data_changed.emit()

        if not silent:
            if not path.exists():
                QMessageBox.warning(
                    self, "Import", f"File not found:\n{path}"
                )
            elif added:
                QMessageBox.information(
                    self, "Import", f"{added} group(s) imported from group_categories.json."
                )
            else:
                QMessageBox.information(
                    self, "Import", "No new groups found in group_categories.json."
                )

    def add_category(self):
        text, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if not ok or not text.strip():
            return

        if self.db.add_category(text.strip()):
            self.load_categories()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Category already exists.")

    def rename_category(self):
        if self.current_category is None:
            return

        text, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=self.current_category
        )
        if not ok or not text.strip():
            return

        new_name = text.strip()
        if self.db.rename_category(self.current_category, new_name):
            self.current_category = new_name
            self.load_categories()
            self._select_category(new_name)
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Cannot rename category.")

    def delete_category(self):
        if self.current_category is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete category '{self.current_category}'?\n"
            "Groups themselves are kept, only the category tag is removed.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.db.delete_category(self.current_category):
            self.current_category = None
            self.load_categories()
            self.load_groups()
            self.data_changed.emit()

    def _select_category(self, name: str):
        for i in range(self.categories_list.count()):
            if self.categories_list.item(i).text() == name:
                self.categories_list.setCurrentRow(i)
                return

    # =====================================================
    # Groups CRUD (optionally filtered by current_category)
    # =====================================================

    def load_groups(self):
        self.groups_list.clear()

        if self.current_category is not None:
            names = sorted(
                self.db.get_category_groups(self.current_category), key=str.casefold
            )
        else:
            names = sorted(self.db.groups.keys(), key=str.casefold)

        for name in names:
            self.groups_list.addItem(name)

    def on_group_selected(self):
        item = self.groups_list.currentItem()
        if item is None:
            self.current_group = None
            self.group_name_label.setText("Select a group")
            self.group_categories_label.setText("")
            self.members_list.clear()
            return

        name = item.text()
        self.current_group = name
        self.group_name_label.setText(f"Group: {name}")

        cats = self.db.categories_of(name)
        self.group_categories_label.setText(
            "Categories: " + (", ".join(cats) if cats else "(none)")
        )

        group = self.db.get_group(name)
        if group is None:
            return

        self.members_list.clear()
        for member in group.get("members", []):
            self.members_list.addItem(member)

        self.note_edit.setPlainText(group.get("note", ""))

    def add_group(self):
        text, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if not ok or not text.strip():
            return

        name = text.strip()
        category = self.current_category or "All Groups"
        if self.db.add_group(name, category):
            self.load_categories()
            self.load_groups()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Group already exists.")

    def rename_group(self):
        if self.current_group is None:
            return

        text, ok = QInputDialog.getText(
            self, "Rename Group", "New name:", text=self.current_group
        )
        if not ok or not text.strip():
            return

        new_name = text.strip()
        if self.db.rename_group(self.current_group, new_name):
            self.load_groups()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Cannot rename.")

    def delete_group(self):
        if self.current_group is None:
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete group '{self.current_group}'? "
            "This removes it entirely, from every category.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.db.remove_group(self.current_group):
            self.current_group = None
            self.load_groups()
            self.members_list.clear()
            self.group_name_label.setText("Select a group")
            self.group_categories_label.setText("")
            self.data_changed.emit()

    def assign_group_to_category(self):
        if self.current_group is None:
            QMessageBox.warning(self, "Error", "Select a group first.")
            return

        category = self.assign_category_combo.currentText().strip()
        if not category:
            QMessageBox.warning(self, "Error", "No category available. Add one first.")
            return

        if self.db.add_group_to_category(self.current_group, category):
            self.on_group_selected()  # refresh the "Categories:" label
            self.data_changed.emit()
        else:
            QMessageBox.warning(
                self, "Error", "Group already in that category (or invalid)."
            )

    def remove_group_from_category(self):
        if self.current_group is None or self.current_category is None:
            return

        if self.db.remove_group_from_category(self.current_group, self.current_category):
            self.load_groups()
            self.on_group_selected()
            self.data_changed.emit()

    # =====================================================
    # Members / Notes (unchanged)
    # =====================================================

    def add_member(self):
        if self.current_group is None:
            return

        member = self.member_input.text().strip()
        if not member:
            return

        if self.db.add_member(self.current_group, member):
            self.members_list.addItem(member)
            self.member_input.clear()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Member already exists or invalid.")

    def remove_member(self):
        if self.current_group is None:
            return

        item = self.members_list.currentItem()
        if item is None:
            return

        member = item.text()
        if self.db.remove_member(self.current_group, member):
            self.members_list.takeItem(self.members_list.row(item))
            self.data_changed.emit()

    def save_note(self):
        if self.current_group is None:
            return

        note = self.note_edit.toPlainText().strip()
        if self.db.set_note(self.current_group, note):
            self.data_changed.emit()