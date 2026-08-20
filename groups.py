import json
import re

from playwright.sync_api import sync_playwright


# =========================================================
# Configuration
# =========================================================

PROXY = "http://192.168.100.10:8080"
SESSION = "./whatsapp_session"
OUTPUT = "group_categories.json"


# =========================================================
# Categories
# =========================================================

CATEGORIES = {
    "دانیال": r"دانیال",
}


# =========================================================
# Category matcher
# =========================================================

def match_category(group_name, pattern):

    return re.search(
        pattern,
        group_name,
        re.IGNORECASE
    ) is not None


# =========================================================
# Find Groups button
# =========================================================
def find_groups_button(page):

    print("\nSearching for Groups button...")
    print("-" * 60)

    # =========================================================
    # STEP 1 - متن‌های مختلف
    # =========================================================

    labels = [
        "گروه‌ها",
        "گروه ها",
        "گروه",
        "Groups",
        "Group",
    ]

    for label in labels:

        try:

            locator = page.get_by_text(
                label,
                exact=True
            )

            count = locator.count()

            print(
                f"Text '{label}': {count}"
            )

            if count == 0:
                continue

            for i in range(count):

                element = locator.nth(i)

                if not element.is_visible():
                    continue

                print("\nFOUND BY TEXT")

                print(
                    "TEXT:",
                    element.inner_text()
                )

                print(
                    "TAG:",
                    element.evaluate(
                        "(e) => e.tagName"
                    )
                )

                print(
                    "HTML:",
                    element.evaluate(
                        "(e) => e.outerHTML"
                    )
                )

                # نزدیک‌ترین clickable
                clickable = element.locator(
                    "xpath=ancestor-or-self::*["
                    "@role='button' or "
                    "@role='tab' or "
                    "self::button"
                    "]"
                ).first

                if clickable.count():

                    print("\nCLICKABLE:")

                    print(
                        clickable.evaluate(
                            "(e) => e.outerHTML"
                        )
                    )

                    return clickable

        except Exception as e:

            print(
                f"Text search error: {e}"
            )

    # =========================================================
    # STEP 2 - aria-label
    # =========================================================

    print("\nSearching aria-label...")
    print("-" * 60)

    try:

        elements = page.locator(
            "[aria-label]"
        )

        count = elements.count()

        print(
            f"Total aria-label elements: {count}"
        )

        for i in range(
            min(count, 300)
        ):

            try:

                element = elements.nth(i)

                if not element.is_visible():
                    continue

                aria = element.get_attribute(
                    "aria-label"
                )

                if not aria:
                    continue

                # موارد مرتبط احتمالی
                if re.search(
                    r"group|groups|گروه",
                    aria,
                    re.IGNORECASE
                ):

                    print(
                        "\nPOSSIBLE GROUP ELEMENT:"
                    )

                    print(
                        "ARIA:",
                        aria
                    )

                    print(
                        "TAG:",
                        element.evaluate(
                            "(e) => e.tagName"
                        )
                    )

                    print(
                        "ROLE:",
                        element.get_attribute(
                            "role"
                        )
                    )

                    print(
                        "TITLE:",
                        element.get_attribute(
                            "title"
                        )
                    )

                    print(
                        "HTML:",
                        element.evaluate(
                            "(e) => e.outerHTML"
                        )
                    )

            except Exception:
                continue

    except Exception as e:

        print(
            "ARIA scan error:",
            e
        )

    # =========================================================
    # STEP 3 - title
    # =========================================================

    print("\nSearching title attributes...")
    print("-" * 60)

    try:

        elements = page.locator(
            "[title]"
        )

        count = elements.count()

        print(
            f"Total title elements: {count}"
        )

        for i in range(
            min(count, 300)
        ):

            try:

                element = elements.nth(i)

                if not element.is_visible():
                    continue

                title = element.get_attribute(
                    "title"
                )

                if not title:
                    continue

                if re.search(
                    r"group|groups|گروه",
                    title,
                    re.IGNORECASE
                ):

                    print(
                        "\nPOSSIBLE GROUP TITLE:"
                    )

                    print(
                        "TITLE:",
                        title
                    )

                    print(
                        "TAG:",
                        element.evaluate(
                            "(e) => e.tagName"
                        )
                    )

                    print(
                        "ROLE:",
                        element.get_attribute(
                            "role"
                        )
                    )

                    print(
                        "HTML:",
                        element.evaluate(
                            "(e) => e.outerHTML"
                        )
                    )

            except Exception:
                continue

    except Exception as e:

        print(
            "Title scan error:",
            e
        )

    # =========================================================
    # STEP 4 - role=tab
    # =========================================================

    print("\nScanning tabs...")
    print("-" * 60)

    try:

        tabs = page.locator(
            "[role='tab']"
        )

        count = tabs.count()

        print(
            f"Tabs: {count}"
        )

        for i in range(count):

            try:

                tab = tabs.nth(i)

                if not tab.is_visible():
                    continue

                print(
                    f"\nTAB #{i}"
                )

                print(
                    "TEXT:",
                    tab.inner_text().strip()
                )

                print(
                    "ARIA:",
                    tab.get_attribute(
                        "aria-label"
                    )
                )

                print(
                    "TITLE:",
                    tab.get_attribute(
                        "title"
                    )
                )

                print(
                    "HTML:",
                    tab.evaluate(
                        "(e) => e.outerHTML"
                    )
                )

            except Exception:
                continue

    except Exception as e:

        print(
            "Tab scan error:",
            e
        )

    # =========================================================
    # STEP 5 - buttons
    # =========================================================

    print("\nScanning buttons...")
    print("-" * 60)

    try:

        buttons = page.locator(
            "button"
        )

        count = buttons.count()

        print(
            f"Buttons: {count}"
        )

        for i in range(
            min(count, 100)
        ):

            try:

                button = buttons.nth(i)

                if not button.is_visible():
                    continue

                print(
                    f"\nBUTTON #{i}"
                )

                print(
                    "TEXT:",
                    button.inner_text().strip()
                )

                print(
                    "ARIA:",
                    button.get_attribute(
                        "aria-label"
                    )
                )

                print(
                    "TITLE:",
                    button.get_attribute(
                        "title"
                    )
                )

                print(
                    "HTML:",
                    button.evaluate(
                        "(e) => e.outerHTML"
                    )
                )

            except Exception:
                continue

    except Exception as e:

        print(
            "Button scan error:",
            e
        )

    # =========================================================
    # Nothing found
    # =========================================================

    print()
    print("=" * 60)
    print("❌ Groups button was NOT found")
    print("=" * 60)

    return None

# =========================================================
# Click Groups
# =========================================================

def open_groups(page):

    groups_button = find_groups_button(page)

    if groups_button is None:

        print(
            "\n❌ Groups button not found"
        )

        return False

    try:

        print(
            "\nClicking Groups..."
        )

        groups_button.scroll_into_view_if_needed()

        page.wait_for_timeout(500)

        groups_button.click(
            timeout=5000
        )

        page.wait_for_timeout(1500)

        print(
            "✅ Groups selected"
        )

        return True

    except Exception as e:

        print(
            f"❌ Cannot click Groups: {e}"
        )

        # =================================================
        # Fallback: JavaScript click
        # =================================================

        try:

            print(
                "\nTrying JavaScript click..."
            )

            groups_button.evaluate(
                "(e) => e.click()"
            )

            page.wait_for_timeout(1500)

            print(
                "✅ Groups selected using JS"
            )

            return True

        except Exception as js_error:

            print(
                f"❌ JavaScript click failed: {js_error}"
            )

            return False


# =========================================================
# Collect group names
# =========================================================

def collect_group_names(page):

    names = set()

    print(
        "\nCollecting GROUP chats..."
    )

    print(
        "-" * 60
    )

    # =====================================================
    # WhatsApp chat title
    # =====================================================

    chat_selector = (
        '[data-testid="cell-frame-title"] span[title]'
    )

    stable_rounds = 0
    previous_count = 0

    while stable_rounds < 5:

        chats = page.locator(
            chat_selector
        )

        current_count = chats.count()

        for i in range(current_count):

            try:

                title = chats.nth(i).get_attribute(
                    "title"
                )

                if title:

                    title = title.strip()

                    if title:

                        names.add(title)

            except Exception:

                continue

        new_count = len(names)

        print(
            f"Groups found: {new_count} | "
            f"DOM items: {current_count}"
        )

        if new_count == previous_count:

            stable_rounds += 1

        else:

            stable_rounds = 0

        previous_count = new_count

        # =================================================
        # Scroll آخرین آیتم
        # =================================================

        if current_count > 0:

            try:

                chats.nth(
                    current_count - 1
                ).scroll_into_view_if_needed()

            except Exception:

                pass

        page.wait_for_timeout(
            700
        )

    print(
        "-" * 60
    )

    print(
        f"Total groups collected: {len(names)}"
    )

    return list(names)


# =========================================================
# Main
# =========================================================

with sync_playwright() as p:

    # =====================================================
    # Launch browser
    # =====================================================

    context = p.firefox.launch_persistent_context(
        user_data_dir=SESSION,
        headless=False,
        proxy={
            "server": PROXY
        }
    )

    # =====================================================
    # Page
    # =====================================================

    page = (
        context.pages[0]
        if context.pages
        else context.new_page()
    )

    # =====================================================
    # Open WhatsApp
    # =====================================================

    page.goto(
        "https://web.whatsapp.com",
        wait_until="domcontentloaded"
    )

    print(
        "Waiting for WhatsApp..."
    )

    page.wait_for_timeout(
        5000
    )

    # =====================================================
    # STEP 1
    # انتخاب Groups
    # =====================================================

    if not open_groups(page):

        input(
            "\nEnter..."
        )

        context.close()

        raise SystemExit


    # =====================================================
    # STEP 2
    # فقط گروه‌ها
    # =====================================================

    group_names = collect_group_names(
        page
    )


    # =====================================================
    # Print groups
    # =====================================================

    print()

    print(
        "=" * 60
    )

    print(
        f"GROUPS ONLY: {len(group_names)}"
    )

    print(
        "=" * 60
    )

    for i, name in enumerate(
        group_names,
        start=1
    ):

        print(
            f"{i}. {name}"
        )


    # =====================================================
    # STEP 3
    # Category
    # =====================================================

    categorized_groups = {
        category: []
        for category in CATEGORIES
    }


    for name in group_names:

        for category, pattern in CATEGORIES.items():

            if match_category(
                name,
                pattern
            ):

                if name not in categorized_groups[
                    category
                ]:

                    categorized_groups[
                        category
                    ].append(name)


    # =====================================================
    # STEP 4
    # Save JSON
    # =====================================================

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            categorized_groups,
            file,
            ensure_ascii=False,
            indent=4
        )


    # =====================================================
    # Result
    # =====================================================

    print()

    print(
        "=" * 60
    )

    print(
        "Categorization finished"
    )

    print(
        "=" * 60
    )

    for category, groups in categorized_groups.items():

        print()

        print(
            f"[{category}] "
            f"Total: {len(groups)}"
        )

        for group in groups:

            print(
                f"  - {group}"
            )

    print()

    print(
        f"Saved to: {OUTPUT}"
    )

    input(
        "\nEnter بزن..."
    )

    context.close()