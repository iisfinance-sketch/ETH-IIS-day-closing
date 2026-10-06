import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect


def main():
    username = os.environ.get("IIS_USERNAME")
    password = os.environ.get("IIS_PASSWORD")

    if not username or not password:
        raise RuntimeError("Missing IIS_USERNAME or IIS_PASSWORD secret.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            print("Opening IIS login...")
            page.goto(
                "https://iisauh.ethdigitalcampus.com/IISAUH/",
                wait_until="domcontentloaded",
            )

            page.locator('input[name="loginid"]').fill(username)
            page.locator('input[name="password"]').fill(password)
            page.get_by_role(
                "button", name="Sign In", exact=True
            ).click()

            expect(
                page.get_by_text("International Indian School", exact=True)
            ).to_be_visible()

            print("Login verified. Opening Day Closing for Fee...")

            # The dashboard contains several copies of this link.
            closing_link = page.get_by_role(
                "link", name="Day Closing for Fee", exact=True
            )
            closing_link.first.wait_for(state="attached")
            closing_link.locator("visible=true").first.click()

            expect(
                page.get_by_text(
                    "Day Closing Done Successfully", exact=True
                )
            ).to_be_visible(timeout=120000)

            completed_at = datetime.now(
                ZoneInfo("Asia/Dubai")
            ).strftime("%d-%m-%Y %H:%M:%S")

            print(f"SUCCESS: Day closing confirmed at {completed_at} UAE.")

            page.get_by_text(
                "Financial Accounting", exact=True
            ).click()

            expect(
                page.get_by_role(
                    "heading", name="Financial Accounting", exact=True
                )
            ).to_be_visible()

            print("Returned to Financial Accounting.")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "FAILED: The workflow did not finish successfully. "
            "Do not assume closing completed or rerun without checking IIS.",
            file=sys.stderr,
        )
        sys.exit(1)
