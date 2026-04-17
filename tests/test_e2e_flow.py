import os
import random
import re
import time

from playwright.sync_api import sync_playwright, expect


def select_random_option(page, selector):
    page.wait_for_selector(selector, timeout=15000)
    page.wait_for_function(
        "selector => Array.from(document.querySelectorAll(`${selector} option`)).some(o => o.value.trim() !== '')",
        arg=selector,
        timeout=15000,
    )

    options = page.locator(f"{selector} option")
    data = options.evaluate_all("""
        opts => opts.map(o => ({
            value: o.value,
            label: o.textContent.trim()
        }))
    """)

    valid = [opt for opt in data if opt["value"].strip() != ""]
    if not valid:
        raise ValueError(f"No selectable options found for {selector}: {data}")

    choice = random.choice(valid)
    page.locator(selector).select_option(choice["value"])
    return choice["label"]


def select_random_year_after(page, selector, min_year):
    page.wait_for_selector(selector, timeout=15000)
    page.wait_for_function(
        "selector => Array.from(document.querySelectorAll(`${selector} option`)).some(o => o.value.trim() !== '')",
        arg=selector,
        timeout=15000,
    )

    options = page.locator(f"{selector} option")
    data = options.evaluate_all("""
        opts => opts.map(o => ({
            value: o.value,
            label: o.textContent.trim()
        }))
    """)

    valid = [
        opt
        for opt in data
        if opt["value"].strip() != "" and int(opt["value"]) >= int(min_year)
    ]
    if not valid:
        raise ValueError(f"No selectable end year found for {selector} >= {min_year}: {data}")

    choice = random.choice(valid)
    page.locator(selector).select_option(choice["value"])
    return choice["label"]


def select_option_by_label(page, selector, label, timeout=15000):
    page.wait_for_selector(selector, timeout=timeout)
    page.wait_for_function(
        "([selector, label]) => Array.from(document.querySelectorAll(`${selector} option`))"
        ".map(o => o.textContent.trim().toLowerCase())"
        ".includes(label.trim().toLowerCase())",
        arg=[selector, label],
        timeout=timeout,
    )

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


def build_bucket_identifier(*parts):
    return "_".join(re.sub(r"[^\w]", "", part) for part in parts if part)


def test_full_flow() -> None:
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # ----------------------------
        # STEP 1: LOGIN
        # ----------------------------
        page.goto("https://staging-insight-docx-mgnt-webapp.unicourt.net:9879/accounts/login/")

        page.get_by_label("Username").fill("interndishak@unicourt.com")
        page.get_by_label("Password").fill("docx@user")

        with page.expect_navigation():
            page.get_by_role("button", name=re.compile(r"sign in", re.I)).click()

        expect(page.get_by_role("heading", name="Document Extraction Manager")).to_be_visible()

        # ----------------------------
        # STEP 2: CLICK DIV + NAVIGATE
        # ----------------------------
        with page.expect_navigation():
            page.locator("#ground-truth-card").click()

        expect(page).to_have_url(re.compile(r"bronze_maker"))

        max_attempts = 5
        attempt = 0
        success = False
        bucket_name = None
        bucket_identifier = None

        while attempt < max_attempts and not success:
            attempt += 1
            print(f"Attempt: {attempt}")

            # ----------------------------
            # STEP 3: OPEN FORM (Add New Bucket)
            # ----------------------------
            page.wait_for_selector("div.overflow-x-auto.table-container table", state="visible", timeout=60000)
            page.get_by_role("button", name=re.compile(r"add new", re.I)).click()
            expect(page.get_by_role("heading", name="Add New Bucket")).to_be_visible()

            # ----------------------------
            # STEP 4: FILL FORM (DYNAMIC)
            # ----------------------------
            project_name = select_random_option(page, "#project_id")

            # Fixed field values
            state_name = select_option_by_label(page, "#state", "NY")
            case_class = select_option_by_label(page, "#case_class", "Civil")
            area_of_law = select_option_by_label(page, "#area_of_law", "Personal Injury and Torts")

            # Random values for the remaining fields
            start_year = select_random_option(page, "#start_year")
            end_year = select_random_year_after(page, "#end_year", start_year)
            case_type_group = select_random_option(page, "#case_type_group")
            case_type = select_random_option(page, "#case_type")
            court_source = select_random_option(page, "#court_source")

            selected_data = {
                "project": project_name,
                "state": state_name,
                "start_year": start_year,
                "end_year": end_year,
                "case_class": case_class,
                "area_of_law": area_of_law,
                "case_type_group": case_type_group,
                "case_type": case_type,
                "court_source": court_source,
            }

            print("Selected Data:", selected_data)

            bucket_identifier = build_bucket_identifier(
                state_name,
                start_year,
                end_year,
                case_type_group,
                area_of_law,
                court_source,
            )
            print("Generated Bucket Identifier:", bucket_identifier)

            # Use project name for validation reference (can adjust later)
            bucket_name = project_name

            # ----------------------------
            # STEP 5: SUBMIT FORM
            # ----------------------------
            with page.expect_response(
                lambda response: response.request.method == "POST" and response.status in (200, 201)
            ) as save_response_info:
                page.get_by_role("button", name=re.compile(r"save|submit", re.I)).click()

            save_response = save_response_info.value
            assert save_response.ok, (
                f"Bucket save request failed: {save_response.status} {save_response.url}"
            )

            # Refresh once after the bucket is created so the list reloads cleanly.
            page.reload(wait_until="networkidle")

            # ----------------------------
            # STEP 6: WAIT FOR LIST TO LOAD
            # ----------------------------
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_selector("text=Add New Bucket", state="hidden", timeout=60000)
            page.wait_for_selector("div.overflow-x-auto.table-container table", state="visible", timeout=60000)
            bucket_table = page.locator("div.overflow-x-auto.table-container table").first
            expect(bucket_table).to_be_visible(timeout=60000)

            bucket_rows = bucket_table.locator("tbody tr")
            candidate_match = None
            primary_expected = bucket_identifier
            fallback_expected_values = [project_name, state_name, start_year, end_year]
            end_time = time.time() + 60

            while time.time() < end_time:
                row_count = bucket_rows.count()
                for index in range(row_count):
                    row = bucket_rows.nth(index)
                    row_text = row.inner_text()
                    if primary_expected in row_text:
                        candidate_match = row
                        break
                    if all(value in row_text for value in fallback_expected_values):
                        candidate_match = row
                        break
                if candidate_match:
                    break
                time.sleep(1)

            if not candidate_match:
                if row_count == 0:
                    raise AssertionError(
                        "No bucket rows found after saving and waiting for the table to refresh."
                    )

                all_rows_text = [bucket_rows.nth(i).inner_text() for i in range(row_count)]
                raise AssertionError(
                    "Could not find newly created bucket row in the table within 60 seconds.\n"
                    f"Primary expected identifier: {primary_expected}\n"
                    f"Fallback expected values: {fallback_expected_values}\n"
                    f"Row texts:\n{os.linesep.join(all_rows_text)}"
                )

            selected_row_text = candidate_match.inner_text()
            print("Found bucket row text:", selected_row_text)

            assert project_name in selected_row_text, f"Expected project='{project_name}' in selected bucket row"
            assert start_year in selected_row_text, f"Expected start_year='{start_year}' in selected bucket row"
            assert end_year in selected_row_text, f"Expected end_year='{end_year}' in selected bucket row"

            # ----------------------------
            # STEP: OPEN BUCKET DETAILS
            # ----------------------------
            with page.expect_navigation(timeout=60000):
                candidate_match.locator("text=Bucket Details").click()

            # Wait for new page
            page.wait_for_load_state("networkidle")
            expect(page).to_have_url(re.compile(r"bucket"))

            # ----------------------------
            # STEP: CHECK IF EMPTY
            # ----------------------------
            no_data = page.get_by_text("No documents found for this bucket.")
            if no_data.is_visible(timeout=5000):
                print("❌ Empty bucket → retrying...")
                page.go_back()
                page.wait_for_load_state("networkidle")
                page.wait_for_selector("div.overflow-x-auto.table-container table", state="visible", timeout=60000)
                continue

            # ----------------------------
            # SUCCESS CASE
            # ----------------------------
            print("✅ Bucket has data!")
            success = True

        if not success:
            raise Exception("Failed: All buckets created were empty")

        # Wait for new page
        page.wait_for_load_state("networkidle")

        # Validate navigation
        expect(page).to_have_url(re.compile(r"bucket"))

        # ----------------------------
        # STEP: CLICK ADD CANDIDATES
        # ----------------------------
        page.get_by_role("button", name=re.compile(r"add candidates", re.I)).click()

        page.wait_for_timeout(1000)

        expect(
            page.get_by_text(re.compile(r"add candidates", re.I))
        ).to_be_visible(timeout=10000)

        # ----------------------------
        # STEP: SELECT RANDOM CANDIDATES
        # ----------------------------
        expect(page.get_by_text(re.compile(r"name", re.I))).to_be_visible(timeout=10000)

        select_buttons = page.get_by_role("button", name=re.compile(r"select", re.I))
        count = select_buttons.count()

        if count < 2:
            raise Exception("Not enough candidates to select")

        indices = random.sample(range(count), 2)
        for i in indices:
            select_buttons.nth(i).click()

        page.get_by_role(
            "button",
            name=re.compile(r"add more candidate docs", re.I)
        ).click()

        table = page.locator("table")
        select_buttons = table.get_by_role("button", name=re.compile("select", re.I))

        # ----------------------------
        # STEP 9: VALIDATE DETAILS PAGE
        # ----------------------------
        expect(page.get_by_text(bucket_name)).to_be_visible()

        # ----------------------------
        # STEP 9: SCREENSHOT
        # ----------------------------
        timestamp = int(time.time())
        page.screenshot(path=f"screenshots/final_{timestamp}.png", full_page=True)

        # ----------------------------
    

        browser.close()


if __name__ == "__main__":
    test_full_flow()

