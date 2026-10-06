import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect


ORIGIN = "https://iisauh.ethdigitalcampus.com"


def log(message):
    print(message, flush=True)


def main():
    username = os.environ.get("IIS_USERNAME")
    password = os.environ.get("IIS_PASSWORD")

    if not username or not password:
        raise RuntimeError("Missing IIS login secrets.")

    stage = "starting browser"
    closing_started = False
    closing_confirmed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            stage = "opening login page"
            log(stage)
            page.goto(
                f"{ORIGIN}/IISAUH/",
                wait_until="domcontentloaded",
            )

            stage = "logging in"
            page.locator('input[name="loginid"]').fill(username)
            page.locator('input[name="password"]').fill(password)
            page.get_by_role(
                "button", name="Sign In", exact=True
            ).click()

            page.wait_for_url(
                "**/jsp_dashboard/UserDashboard.jsp*",
                timeout=60000,
            )
            expect(
                page.get_by_text(
                    "International Indian School", exact=True
                )
            ).to_be_visible()
            log("Login verified.")

            stage = "finding Day Closing link"
            link = page.locator(
                'a[href*="DayClosingForFeeParam.jsp"]'
            ).first

            # Reading the link works even when its menu is collapsed.
            link.wait_for(state="attached")
            href = link.get_attribute("href")

            if not href:
                raise RuntimeError("Day Closing link has no address.")

            closing_url = urljoin(page.url, href)
            if (
                urlparse(closing_url).scheme != "https"
                or urlparse(closing_url).netloc
                != urlparse(ORIGIN).netloc
            ):
                raise RuntimeError("Unexpected Day Closing destination.")

            stage = "performing Day Closing"
            log("Day Closing link found. Starting closing.")
            closing_started = True

            page.goto(
                closing_url,
                wait_until="domcontentloaded",
                timeout=120000,
            )

            stage = "verifying Day Closing result"
            expect(
                page.get_by_text(
                    "Day Closing Done Successfully", exact=True
                )
            ).to_be_visible(timeout=120000)

            closing_confirmed = True
            completed_at = datetime.now(
                ZoneInfo("Asia/Dubai")
            ).strftime("%d-%m-%Y %H:%M:%S")

            log(
                f"SUCCESS: Day closing confirmed at "
                f"{completed_at} UAE."
            )

            stage = "returning to Financial Accounting"
            accounting = page.get_by_text(
                "Financial Accounting", exact=True
            ).and_(page.locator(":visible"))

            accounting.first.click()
            expect(
                page.get_by_role(
                    "heading",
                    name="Financial Accounting",
                    exact=True,
                )
            ).to_be_visible()

            log("Returned to Financial Accounting.")

        except Exception as error:
            log(
                f"ERROR: Stage '{stage}' failed "
                f"({type(error).__name__})."
            )

            if closing_confirmed:
                log(
                    "Day closing SUCCEEDED, but returning to "
                    "Financial Accounting failed."
                )
            elif closing_started:
                log(
                    "Closing was requested, but success is UNKNOWN. "
                    "Check IIS before repeating."
                )
            else:
                log("Day closing was NOT requested.")

            raise

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
