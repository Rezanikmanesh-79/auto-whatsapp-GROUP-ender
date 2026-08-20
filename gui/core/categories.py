"""
CRUD layer for Data/group_categories.json

File format (flat):
    {
        "Category A": ["Group 1", "Group 2"],
        "Category B": ["Group 3"]
    }

This module is what `ui/main_window.py` (`load_categories`) and
`workers/whatsapp_worker.py` (`save_categories`) import — those two
functions were referenced but never defined, which broke both files
on import. They're implemented here now, alongside a full CRUD
wrapper class for everything else (categories + groups-in-categories).
"""

import json
import re
from pathlib import Path
from typing import Optional

CategoriesData = dict[str, list[str]]


# =====================================================
# Read / Write (module-level functions)
# =====================================================

def load_categories(path: Path | str) -> CategoriesData:
    """Read group_categories.json. Returns {} if missing/invalid."""
    path = Path(path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}

    if not isinstance(raw, dict):
        return {}

    # Tolerate the nested {"categories": {...}, "groups": {...}} shape
    # in case an older/other tool wrote the file that way.
    if "categories" in raw and isinstance(raw.get("categories"), dict):
        raw = raw["categories"]

    return {
        str(cat): [str(g) for g in groups]
        for cat, groups in raw.items()
        if isinstance(groups, list)
    }


def save_categories(data: CategoriesData, path: Path | str) -> None:
    """Write group_categories.json (flat format)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# =====================================================
# Full CRUD wrapper
# =====================================================

class GroupCategoriesDB:
    """
    Loads group_categories.json once and gives Create/Read/Update/Delete
    on both categories and the groups inside them. Every mutating call
    persists to disk immediately (matches the pattern already used by
    GroupDatabase in core/database.py).
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._data: CategoriesData = {}
        self.load()

    # ---- persistence ----

    def load(self) -> None:
        self._data = load_categories(self.path)

    def save(self) -> None:
        save_categories(self._data, self.path)

    @property
    def data(self) -> CategoriesData:
        return self._data

    # ---- Read ----

    def category_names(self) -> list[str]:
        return sorted(self._data.keys(), key=str.casefold)

    def get_category(self, category: str) -> list[str]:
        return list(self._data.get(category, []))

    def all_group_names(self) -> list[str]:
        names: set[str] = set()
        for groups in self._data.values():
            names.update(groups)
        return sorted(names, key=str.casefold)

    def categories_of(self, group: str) -> list[str]:
        """Every category a given group currently belongs to."""
        return [cat for cat, groups in self._data.items() if group in groups]

    def group_exists(self, group: str) -> bool:
        return any(group in groups for groups in self._data.values())

    # ---- Category CRUD ----

    def add_category(self, category: str) -> bool:
        category = category.strip()
        if not category or category in self._data:
            return False
        self._data[category] = []
        self.save()
        return True

    def rename_category(self, old: str, new: str) -> bool:
        new = new.strip()
        if old not in self._data or not new or new in self._data:
            return False
        self._data[new] = self._data.pop(old)
        self.save()
        return True

    def delete_category(self, category: str) -> bool:
        if category not in self._data:
            return False
        del self._data[category]
        self.save()
        return True

    # ---- Group CRUD (within a category) ----

    def add_group(self, category: str, group: str) -> bool:
        group = group.strip()
        if not group:
            return False
        bucket = self._data.setdefault(category, [])
        if group in bucket:
            return False
        bucket.append(group)
        self.save()
        return True

    def remove_group(self, category: str, group: str) -> bool:
        bucket = self._data.get(category)
        if not bucket or group not in bucket:
            return False
        bucket.remove(group)
        self.save()
        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        """Rename a group everywhere it appears, across all categories."""
        old_name, new_name = old_name.strip(), new_name.strip()
        if not new_name:
            return False

        found = False
        for groups in self._data.values():
            if old_name in groups:
                idx = groups.index(old_name)
                if new_name in groups:
                    groups.pop(idx)  # avoid duplicate in same category
                else:
                    groups[idx] = new_name
                found = True

        if found:
            self.save()
        return found

    def delete_group(self, group: str) -> bool:
        """Remove a group from every category it's in."""
        found = False
        for groups in self._data.values():
            if group in groups:
                groups.remove(group)
                found = True

        if found:
            self.save()
        return found

    def move_group(self, group: str, from_category: str, to_category: str) -> bool:
        if not self.remove_group(from_category, group):
            return False
        self.add_group(to_category, group)
        return True

    # ---- Bulk import (used by scan_groups) ----

    def import_from_scan(self, scanned: list[str], category: str = "All Groups") -> None:
        bucket = self._data.setdefault(category, [])
        for name in scanned:
            if name not in bucket:
                bucket.append(name)
        self.save()


# =====================================================
# Legacy pattern-matching helpers (kept for compatibility)
# =====================================================

DEFAULT_CATEGORIES = {
    "دانیال": r"دانیال",
}


def match_category(group_name: str, pattern: str) -> bool:
    try:
        return re.search(pattern, group_name, re.IGNORECASE) is not None
    except re.error as exc:
        raise ValueError(f"Invalid category regex: {pattern!r}") from exc


def categorize_groups(
    group_names: list[str],
    categories: Optional[dict[str, str]] = None,
) -> CategoriesData:
    categories = categories if categories is not None else DEFAULT_CATEGORIES
    result: CategoriesData = {cat: [] for cat in categories}

    for group_name in group_names:
        for category, pattern in categories.items():
            if match_category(group_name, pattern):
                if group_name not in result[category]:
                    result[category].append(group_name)

    return result