import os
import re
import time
from playwright.sync_api import sync_playwright, expect

def select_option_by_label(page, selector, label, timeout=15000):
    page.wait_for_selector(selector, timeout=timeout)
    option_value = page.locator(f"{selector} option").evaluate_all(
        """
        (options, label) => {
            const normalized = label.trim().toLowerCase();
            const match = options.find(o => o.textContent.trim().toLowerCase() === normalized);
            return match ? match.value : null;
        }
        """,
        label,
    )
    if option_value is None:
        raise ValueError(f"Could not find option with label '{label}' for selector '{selector}'")
    page.locator(selector).select_option(option_value)
    return label

def select_random_option(page, selector):
    page.wait_for_selector(selector, timeout=15000)
    options = page.locator(f"{selector} option")
    data = options.evaluate_all("""
        opts => opts.map(o => ({
            value: o.value,
            label: o.textContent.trim()
        }))
    """)
    valid = [opt for opt in data if opt["value"].strip() != ""]
    choice = valid[0]  # pick first for consistency
    page.locator(selector).select_option(choice["value"])
    return choice["label"]

def take_screenshot(page, name):
    timestamp = int(time.time())
    page.screenshot(path=f"screenshots/{name}_{timestamp}.png", full_page=True)

def fill_and_submit_form(page, start_year, end_year, scenario_name, expect_error=False, minimal=False):
    # Open form
    page.get_by_role("button", name=re.compile(r"add new", re.I)).click()
    expect(page.get_by_role("heading", name="Add New Bucket")).to_be_visible()

    # Always choose project and state
    project_name = select_random_option(page, "#project_id")
    state_name = select_option_by_label(page, "#state", "NY")

    # Set years
    page.locator("#start_year").select_option(str(start_year))
    page.locator("#end_year").select_option(str(end_year))

    if not minimal:
        # Fill rest of the fields only if required
        case_class = select_option_by_label(page, "#case_class", "Civil")
        area_of_law = select_option_by_label(page, "#area_of_law", "Personal Injury and Torts")
        case_type_group = select_random_option(page, "#case_type_group")
        case_type = select_random_option(page, "#case_type")
        court_source = select_random_option(page, "#court_source")

    print(f"[{scenario_name}] Filled form with start={start_year}, end={end_year}")

    # Submit form
    page.get_by_role("button", name=re.compile(r"save|submit", re.I)).click()

    if expect_error:
        # Wait for popup alert
        dialog = page.wait_for_event("dialog", timeout=10000)
        print(f"[{scenario_name}] Error popup text:", dialog.message)
        take_screenshot(page, f"{scenario_name}_error_popup")
        dialog.accept()  # click OK
    else:
        # Normal success path
        page.wait_for_load_state("networkidle")
        take_screenshot(page, scenario_name)

def test_full_flow():
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Login
        page.goto("https://staging-insight-docx-mgnt-webapp.unicourt.net:9879/accounts/login/")
        page.get_by_label("Username").fill("interndishak@unicourt.com")
        page.get_by_label("Password").fill("docx@user")
        page.get_by_role("button", name=re.compile(r"sign in", re.I)).click()
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name="Document Extraction Manager")).to_be_visible()
        take_screenshot(page, "login")

        # Navigate
        page.locator("#ground-truth-card").click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(r"bronze_maker"))
        take_screenshot(page, "navigation")

        # Scenario 1: Start < End
        fill_and_submit_form(page, 2015, 2020, "scenario1_start_lower")

        # Scenario 2: Start = End
        fill_and_submit_form(page, 2020, 2020, "scenario2_start_equal")

        # Scenario 3: Start > End (only project + state + years, expect error popup)
        fill_and_submit_form(page, 2025, 2020, "scenario3_start_higher", expect_error=True, minimal=True)

        browser.close()

if __name__ == "__main__":
    test_full_flow()
