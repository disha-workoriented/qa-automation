import { Page } from '@playwright/test';

export class EntityPage {
  constructor(private page: Page) {}

  async createEntity(name: string) {
    await this.page.fill('#entity-name-input', name);
    await this.page.click('#create-entity-button');
  }

  async openEntity(name: string) {
    await this.page.click(`text=${name}`);
  }

  async performActionInsideEntity() {
    await this.page.click('#entity-action-button');
  }
}