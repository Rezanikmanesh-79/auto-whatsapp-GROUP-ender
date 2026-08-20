import json
from pathlib import Path
from typing import Optional


class GroupDatabase:
    """
    دیتابیس یکپارچهٔ group_categories.json
    ساختار: {"categories": {...}, "groups": {...}}
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._data = {"categories": {}, "groups": {}}
            self.save()
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}

        # Migrate old format: {"Cat": ["group1", ...]} → new format
        if isinstance(raw, dict) and "categories" not in raw and "groups" not in raw:
            self._data = {"categories": {}, "groups": {}}
            for cat, groups in raw.items():
                self._data["categories"][cat] = groups
                for g in groups:
                    if g not in self._data["groups"]:
                        self._data["groups"][g] = {"members": [], "note": ""}
            self.save()
            return

        self._data = raw if isinstance(raw, dict) else {}
        if "categories" not in self._data:
            self._data["categories"] = {}
        if "groups" not in self._data:
            self._data["groups"] = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=4)

    @property
    def categories(self) -> dict[str, list[str]]:
        return self._data.get("categories", {})

    @property
    def groups(self) -> dict[str, dict]:
        return self._data.get("groups", {})

    def get_group(self, name: str) -> Optional[dict]:
        return self.groups.get(name)

    def get_category_groups(self, category: str) -> list[str]:
        return self.categories.get(category, [])

    def category_names(self) -> list[str]:
        return sorted(self.categories.keys(), key=str.casefold)

    def categories_of(self, group_name: str) -> list[str]:
        return [
            cat for cat, names in self._data.get("categories", {}).items()
            if group_name in names
        ]

    # ---- Category CRUD ----

    def add_category(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        cats = self._data.setdefault("categories", {})
        if name in cats:
            return False
        cats[name] = []
        self.save()
        return True

    def rename_category(self, old_name: str, new_name: str) -> bool:
        new_name = new_name.strip()
        cats = self._data.setdefault("categories", {})
        if old_name not in cats or not new_name or new_name in cats:
            return False
        cats[new_name] = cats.pop(old_name)
        self.save()
        return True

    def delete_category(self, name: str) -> bool:
        cats = self._data.setdefault("categories", {})
        if name not in cats:
            return False
        del cats[name]
        self.save()
        return True

    def add_group_to_category(self, group_name: str, category: str) -> bool:
        """Tag an existing group with an additional category (no duplicate group entry)."""
        if group_name not in self.groups:
            return False
        cats = self._data.setdefault("categories", {})
        bucket = cats.setdefault(category, [])
        if group_name in bucket:
            return False
        bucket.append(group_name)
        self.save()
        return True

    def remove_group_from_category(self, group_name: str, category: str) -> bool:
        """Untag a group from one category, without deleting the group itself."""
        cats = self._data.get("categories", {})
        bucket = cats.get(category)
        if not bucket or group_name not in bucket:
            return False
        bucket.remove(group_name)
        self.save()
        return True

    def add_group(self, name: str, category: str = "All Groups") -> bool:
        if name not in self._data.setdefault("groups", {}):
            self._data["groups"][name] = {"members": [], "note": ""}

        cats = self._data.setdefault("categories", {})
        if category not in cats:
            cats[category] = []
        if name not in cats[category]:
            cats[category].append(name)

        self.save()
        return True

    def remove_group(self, name: str) -> bool:
        if name not in self.groups:
            return False

        del self._data["groups"][name]
        for cat_list in self._data.get("categories", {}).values():
            if name in cat_list:
                cat_list.remove(name)

        self.save()
        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.groups or new_name in self.groups:
            return False

        self._data["groups"][new_name] = self._data["groups"].pop(old_name)

        for cat_list in self._data.get("categories", {}).values():
            if old_name in cat_list:
                cat_list[cat_list.index(old_name)] = new_name

        self.save()
        return True

    def add_member(self, group_name: str, member: str) -> bool:
        group = self.groups.get(group_name)
        if not group:
            return False

        members = group.setdefault("members", [])
        if member in members:
            return False

        members.append(member)
        self.save()
        return True

    def remove_member(self, group_name: str, member: str) -> bool:
        group = self.groups.get(group_name)
        if not group:
            return False

        members = group.get("members", [])
        if member not in members:
            return False

        members.remove(member)
        self.save()
        return True

    def set_note(self, group_name: str, note: str) -> bool:
        group = self.groups.get(group_name)
        if not group:
            return False

        group["note"] = note
        self.save()
        return True

    def import_from_scan(self, scanned_groups: list[str], category: str = "All Groups"):
        cats = self._data.setdefault("categories", {})
        if category not in cats:
            cats[category] = []

        grps = self._data.setdefault("groups", {})
        for name in scanned_groups:
            if name not in cats[category]:
                cats[category].append(name)
            if name not in grps:
                grps[name] = {"members": [], "note": ""}

        self.save()

    def get_all_group_names(self) -> list[str]:
        return sorted(self.groups.keys(), key=str.casefold)

    def import_from_categories_file(self, path: Path | str) -> int:
        """
        One-way merge from the flat-format group_categories.json
        ({"Category": ["group1", "group2"]}) into this database.

        This file is *not* the same store as this GroupDatabase — it's
        written separately (by core/categories.py + the scan worker) in
        the old flat format. This reads it and adds anything missing
        here, without touching the other file and without overwriting
        members/notes on groups that already exist here.

        Returns the number of new group entries created.
        """
        path = Path(path)
        if not path.exists():
            return 0

        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return 0

        if not isinstance(raw, dict):
            return 0

        # Tolerate the nested {"categories": {...}} shape too.
        if "categories" in raw and isinstance(raw.get("categories"), dict):
            raw = raw["categories"]

        cats = self._data.setdefault("categories", {})
        grps = self._data.setdefault("groups", {})
        added = 0
        changed = False

        for category, names in raw.items():
            if not isinstance(names, list):
                continue
            bucket = cats.setdefault(category, [])
            for name in names:
                if name not in grps:
                    grps[name] = {"members": [], "note": ""}
                    added += 1
                    changed = True
                if name not in bucket:
                    bucket.append(name)
                    changed = True

        if changed:
            self.save()

        return added