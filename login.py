from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.firefox.launch_persistent_context(
        user_data_dir="./whatsapp_session",
        headless=False,
        proxy={
        "server": "http://192.168.100.10:8080"        }
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto("https://web.whatsapp.com")

    input("بعد از اینکه QR را اسکن کردی، Enter بزن...")

    context.close()