import json
import time

from playwright.sync_api import sync_playwright


# =========================================================
# Configuration
# =========================================================

PROXY = "http://192.168.100.10:8080"
SESSION = "./whatsapp_session"

CATEGORIES_FILE = "group_categories.json"

WHATSAPP_URL = "https://web.whatsapp.com"

SEND_DELAY = 2

WHATSAPP_WAIT = 10


# =========================================================
# Load categories
# =========================================================

def load_categories():

    try:

        with open(
            CATEGORIES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except FileNotFoundError:

        print(
            f"❌ File not found: {CATEGORIES_FILE}"
        )

        return None

    except json.JSONDecodeError as e:

        print(
            f"❌ Invalid JSON: {e}"
        )

        return None

    return data


# =========================================================
# Select category
# =========================================================

def select_category(categories):

    print()
    print("=" * 60)
    print("AVAILABLE CATEGORIES")
    print("=" * 60)

    category_names = list(
        categories.keys()
    )

    for i, category in enumerate(
        category_names,
        start=1
    ):

        groups = categories[category]

        print(
            f"{i}. {category} "
            f"({len(groups)} groups)"
        )

    print("=" * 60)

    while True:

        value = input(
            "\nCategory name or number: "
        ).strip()

        # شماره
        if value.isdigit():

            index = int(value) - 1

            if 0 <= index < len(category_names):

                return category_names[index]

            print(
                "❌ Invalid category number."
            )

            continue

        # اسم
        if value in categories:

            return value

        print(
            "❌ Category not found."
        )


# =========================================================
# Find group in current group list
# =========================================================

def find_group(page, group_name):

    chat_selector = (
        '[data-testid="cell-frame-title"] span[title]'
    )

    print(
        f"Looking for group: {group_name}"
    )

    stable_rounds = 0
    previous_count = 0

    while stable_rounds < 5:

        chats = page.locator(
            chat_selector
        )

        count = chats.count()

        # -----------------------------------------------
        # Search currently visible DOM items
        # -----------------------------------------------

        for i in range(count):

            try:

                chat = chats.nth(i)

                if not chat.is_visible():

                    continue

                title = chat.get_attribute(
                    "title"
                )

                if not title:

                    continue

                title = title.strip()

                if title == group_name:

                    print(
                        f"✅ Found: {group_name}"
                    )

                    try:

                        chat.scroll_into_view_if_needed()

                        page.wait_for_timeout(
                            300
                        )

                        chat.click()

                    except Exception:

                        # fallback
                        chat.locator(
                            "xpath=ancestor::*["
                            "@data-testid='cell-frame-container'"
                            "]"
                        ).first.click()

                    page.wait_for_timeout(
                        1000
                    )

                    return True

            except Exception:

                continue


        # -----------------------------------------------
        # Scroll آخرین گروه
        # -----------------------------------------------

        if count > 0:

            try:

                chats.nth(
                    count - 1
                ).scroll_into_view_if_needed()

            except Exception:

                pass


        # -----------------------------------------------
        # Detect stable DOM
        # -----------------------------------------------

        if count == previous_count:

            stable_rounds += 1

        else:

            stable_rounds = 0

        previous_count = count

        page.wait_for_timeout(
            700
        )


    print(
        f"❌ Group not found: {group_name}"
    )

    return False


# =========================================================
# Find message box
# =========================================================

def find_message_box(page):

    selectors = [

        # WhatsApp current
        '[data-testid="conversation-compose-box-input"]',

        # Generic composer
        'footer div[contenteditable="true"]',

        # Generic textbox
        'div[contenteditable="true"][role="textbox"]',

    ]

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            )

            count = elements.count()

            for i in range(count):

                element = elements.nth(i)

                if element.is_visible():

                    return element

        except Exception:

            continue

    return None


# =========================================================
# Send message
# =========================================================

def send_message(page, message):

    message_box = find_message_box(
        page
    )

    if message_box is None:

        print(
            "❌ Message box not found."
        )

        return False


    try:

        message_box.click()

        page.wait_for_timeout(
            200
        )

        # -----------------------------------------------
        # fill
        # -----------------------------------------------

        try:

            message_box.fill(
                message
            )

        except Exception:

            # fallback for contenteditable
            message_box.press(
                "Control+A"
            )

            message_box.type(
                message
            )


        # -----------------------------------------------
        # Send
        # -----------------------------------------------

        message_box.press(
            "Enter"
        )

        page.wait_for_timeout(
            1000
        )

        return True


    except Exception as e:

        print(
            f"❌ Send error: {e}"
        )

        return False


# =========================================================
# Verify current chat
# =========================================================

def verify_chat(page, group_name):

    """
    بررسی می‌کند آیا conversation باز شده
    یا نه.
    """

    selectors = [

        '[data-testid="conversation-header"]',

        'header',

    ]

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            )

            count = elements.count()

            for i in range(count):

                element = elements.nth(i)

                if not element.is_visible():

                    continue

                text = element.inner_text().strip()

                if group_name in text:

                    return True

        except Exception:

            continue

    return True


# =========================================================
# Send category
# =========================================================

def send_to_category(
    page,
    category,
    groups,
    message
):

    print()
    print("=" * 60)
    print(
        f"CATEGORY: {category}"
    )
    print("=" * 60)

    success = 0
    failed = 0


    for index, group_name in enumerate(
        groups,
        start=1
    ):

        print()
        print(
            f"[{index}/{len(groups)}] "
            f"{group_name}"
        )


        # -----------------------------------------------
        # Find + open group
        # -----------------------------------------------

        opened = find_group(
            page,
            group_name
        )

        if not opened:

            failed += 1

            continue


        # -----------------------------------------------
        # Verify
        # -----------------------------------------------

        if not verify_chat(
            page,
            group_name
        ):

            print(
                "❌ Conversation verification failed."
            )

            failed += 1

            continue


        # -----------------------------------------------
        # Send
        # -----------------------------------------------

        print(
            "Sending message..."
        )

        sent = send_message(
            page,
            message
        )

        if sent:

            print(
                f"✅ Sent to: {group_name}"
            )

            success += 1

        else:

            print(
                f"❌ Failed: {group_name}"
            )

            failed += 1


        # -----------------------------------------------
        # Delay
        # -----------------------------------------------

        if index < len(groups):

            print(
                f"Waiting {SEND_DELAY} seconds..."
            )

            time.sleep(
                SEND_DELAY
            )


    # =====================================================
    # Result
    # =====================================================

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        f"Category : {category}"
    )

    print(
        f"Success  : {success}"
    )

    print(
        f"Failed   : {failed}"
    )

    print(
        f"Total    : {len(groups)}"
    )

    print("=" * 60)


# =========================================================
# Main
# =========================================================

def main():

    print()
    print("=" * 60)
    print("WHATSAPP CATEGORY SENDER")
    print("=" * 60)


    # =====================================================
    # Load JSON
    # =====================================================

    categories = load_categories()

    if categories is None:

        return


    if not categories:

        print(
            "❌ No categories found."
        )

        return


    # =====================================================
    # Select category
    # =====================================================

    category = select_category(
        categories
    )

    groups = categories[
        category
    ]


    if not isinstance(
        groups,
        list
    ):

        print(
            "❌ Category must contain a list."
        )

        return


    if not groups:

        print(
            f"❌ Category '{category}' "
            f"has no groups."
        )

        return


    # =====================================================
    # Message
    # =====================================================

    print()
    print(
        f"Selected category: {category}"
    )

    print()
    print("Groups:")

    for i, group in enumerate(
        groups,
        start=1
    ):

        print(
            f"  {i}. {group}"
        )


    print()

    message = input(
        "Message: "
    )


    if not message.strip():

        print(
            "❌ Message cannot be empty."
        )

        return


    # =====================================================
    # Confirmation
    # =====================================================

    print()
    print("=" * 60)

    print(
        f"Category : {category}"
    )

    print(
        f"Groups   : {len(groups)}"
    )

    print(
        f"Message  : {message}"
    )

    print("=" * 60)


    confirm = input(
        "\nSend to all groups? [y/N]: "
    ).strip().lower()


    if confirm != "y":

        print(
            "Cancelled."
        )

        return


    # =====================================================
    # Playwright
    # =====================================================

    with sync_playwright() as p:

        context = p.firefox.launch_persistent_context(

            user_data_dir=SESSION,

            headless=False,

            proxy={
                "server": PROXY
            }

        )


        # =================================================
        # Page
        # =================================================

        page = (

            context.pages[0]

            if context.pages

            else context.new_page()

        )


        # =================================================
        # Open WhatsApp
        # =================================================

        page.goto(
            WHATSAPP_URL,
            wait_until="domcontentloaded"
        )


        # =================================================
        # 10 SECOND WAIT
        # =================================================

        print()
        print("=" * 60)
        print("Waiting for WhatsApp Web...")
        print("=" * 60)


        for i in range(
            WHATSAPP_WAIT,
            0,
            -1
        ):

            print(
                f"\rStarting in {i} seconds...",
                end="",
                flush=True
            )

            page.wait_for_timeout(
                1000
            )


        print()
        print(
            "✅ WhatsApp wait completed."
        )


        # =================================================
        # Send
        # =================================================

        try:

            send_to_category(

                page,

                category,

                groups,

                message

            )

        except KeyboardInterrupt:

            print(
                "\n\nStopped by user."
            )


        except Exception as e:

            print()
            print(
                "❌ Unexpected error:"
            )

            print(
                e
            )


        # =================================================
        # Keep browser open
        # =================================================

        input(
            "\nPress Enter to close..."
        )


        context.close()


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":

    main()