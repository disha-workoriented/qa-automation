import { test, expect } from '@playwright/test';

test('Login + Navigate via div click', async ({ page }) => {

  // ----------------------------
  // STEP 1: LOGIN
  // ----------------------------
  await page.goto('https://staging-insight-docx-mgnt-webapp.unicourt.net:9879/accounts/login/');

  await page.getByLabel('Username').fill('interndishak@unicourt.com');
  await page.getByLabel('Password').fill('docx@user');

  await Promise.all([
    page.waitForNavigation(),
    page.getByRole('button', { name: /login Sign in/i }).click()
  ]);

  // Validate login
  await expect(page.getByRole('heading', { name: 'Document Extraction Manager' })).toBeVisible();

  // ----------------------------
  // STEP 2: CLICK DIV + NAVIGATE
  // ----------------------------

  await Promise.all([
    page.waitForNavigation(), // wait for new page load
    page.locator('#ground-truth-card').click() // 🔴 replace this
  ]);

  // ----------------------------
  // STEP 3: VALIDATE NEW PAGE
  // ----------------------------

  // Option 1: URL validation
  await expect(page).toHaveURL(/bronze_maker/);

  // Option 2: UI validation (better)
  await expect(
    page.getByRole('heading', { name: 'Document Extraction Manager' })
  ).toBeVisible();

  await Promise.all([
    page.getByRole('button', { name: /add Add new/i }).click()
  ]);

  await expect(
  page.getByRole('heading', { name: 'Add New Bucket' })
).toBeVisible();

// Select Project
await page.locator('#project_id').selectOption({ label: 'Judgment' });

await page.locator('#state').selectOption({ label: 'NY' });

await page.locator('#start_year').selectOption({ label: '2024' });

await page.locator('#end_year').selectOption({ label: '2025' });

await page.locator('#case_class').selectOption({ label: 'Civil' });

await page.locator('#area_of_law').selectOption({ label: 'Banking' });

await page.locator('#case_type_group').selectOption({ label: 'Banking' });

await page.locator('#case_type').selectOption({ label: 'Business Governance' });

await page.locator('#court_source').selectOption({ label: 'New York(NY) Court of Appeals' });

page.getByRole('button', { name: /save Submit/i }).click();

/*await Promise.all([
    page.locator('#ground-truth-card').click() // 🔴 replace this
  ]);*/
  await expect(
    page.getByRole('heading', { name: 'Document Extraction Manager' })
  ).toBeVisible();

await page.screenshot({ path: 'screenshot.png', fullPage: true });
});