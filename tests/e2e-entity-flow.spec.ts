import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { DashboardPage } from '../pages/dashboard.page';
import { EntityPage } from '../pages/entity.page';

test('Complete End-to-End Entity Workflow', async ({ page }) => {

  const loginPage = new LoginPage(page);
  const dashboard = new DashboardPage(page);
  const entityPage = new EntityPage(page);

  // ----------------------------
  // STEP 1: LOGIN
  // ----------------------------
  await loginPage.gotoLogin();

  await loginPage.login(
    'your_username',
    'your_password'
  );

  // Validate login success
  await expect(page).toHaveURL(/dashboard/);

  // ----------------------------
  // STEP 2: SELECT MENU OPTION
  // ----------------------------
  await dashboard.selectMenuOption('Your Specific Option');

  // ----------------------------
  // STEP 3: CREATE ENTITY
  // ----------------------------
  const entityName = `AutoEntity_${Date.now()}`;

  await entityPage.createEntity(entityName);

  // Validate entity created
  await expect(page.locator(`text=${entityName}`)).toBeVisible();

  // ----------------------------
  // STEP 4: OPEN ENTITY
  // ----------------------------
  await entityPage.openEntity(entityName);

  // ----------------------------
  // STEP 5: ACTION INSIDE ENTITY
  // ----------------------------
  await entityPage.performActionInsideEntity();

  // ----------------------------
  // FINAL VALIDATION
  // ----------------------------
  await expect(page.locator('#success-message')).toBeVisible();
});