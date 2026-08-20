from playwright.sync_api import sync_playwright


PROXY = "http://192.168.100.10:8080"
SESSION = "./whatsapp_session"


with sync_playwright() as p:

    context = p.firefox.launch_persistent_context(
        user_data_dir=SESSION,
        headless=False,
        proxy={
            "server": PROXY
        }
    )

    page = (
        context.pages[0]
        if context.pages
        else context.new_page()
    )

    page.goto("https://web.whatsapp.com")

    print("Waiting for WhatsApp...")

    page.wait_for_timeout(5000)

    # ==========================================
    # پیدا کردن متن Groups
    # ==========================================

    groups_text = page.get_by_text(
        "Groups",
        exact=True
    )

    print(
        f"Groups text elements: {groups_text.count()}"
    )

    if groups_text.count() == 0:
        print("❌ Groups not found")
        input("Enter...")
        context.close()
        raise SystemExit

    # ==========================================
    # پیدا کردن نزدیک‌ترین عنصر قابل کلیک
    # ==========================================

    result = groups_text.first.evaluate("""
    element => {

        let current = element;

        while (current) {

            const role = current.getAttribute("role");

            const tag = current.tagName;

            if (
                role === "button" ||
                tag === "BUTTON"
            ) {

                return {
                    tag: current.tagName,
                    role: current.getAttribute("role"),
                    className: current.className,
                    ariaLabel: current.getAttribute("aria-label"),
                    title: current.getAttribute("title"),
                    text: current.innerText,
                    outerHTML: current.outerHTML
                };

            }

            current = current.parentElement;
        }

        return null;
    }
    """)

    # ==========================================
    # Result
    # ==========================================

    if not result:

        print("❌ Clickable Groups element not found")

    else:

        print()
        print("=" * 70)
        print("GROUP BUTTON")
        print("=" * 70)

        print(
            "TAG:",
            result["tag"]
        )

        print(
            "ROLE:",
            result["role"]
        )

        print(
            "CLASS:",
            result["className"]
        )

        print(
            "ARIA:",
            result["ariaLabel"]
        )

        print(
            "TITLE:",
            result["title"]
        )

        print(
            "TEXT:",
            result["text"]
        )

        print()
        print("OUTER HTML:")
        print("-" * 70)
        print(result["outerHTML"])
        print("-" * 70)

    input("\nEnter بزن...")

    context.close()