import { Page } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  async selectMenuOption(optionName: string) {
    // one of the 3 dashboard options
    await this.page.click(`text=${optionName}`);
  }
}