import { test, expect } from '@playwright/test';

test('official evidence, full context, exports, and scope invalidation', async ({ page }) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Consumer protection', exact: true }).click();
  await page.getByRole('button', { name: 'Find evidence', exact: true }).click();
  await expect(page.getByRole('heading', { name: '5 passages to explore' })).toBeVisible();
  await expect(page.locator('.evidence-card').first()).toContainText('Consumer Protection Act');
  await page.getByRole('button', { name: 'Read full context' }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Source provenance');
  await expect(dialog.getByRole('link', { name: 'Department section' })).toBeVisible();
  await expect(dialog.getByText('Retrieved passage', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape'); await expect(dialog).not.toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Markdown', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('vidhaan_research.md');
  await page.getByLabel('Research collection', { exact: true }).selectOption('reviewed');
  await expect(page.locator('.evidence-card')).toHaveCount(0);
  await page.getByRole('button', { name: 'Find evidence', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A closer look is needed' })).toBeVisible();
  await expect(page.locator('.answer-text')).toContainText('No eligible supporting passages');
  expect(errors).toEqual([]);
});

test('source search, document reader, provenance and original download', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Source library', exact: true }).click();
  await expect(page.locator('.source-row')).toHaveCount(21);
  await page.getByLabel('Search sources', { exact: true }).fill('Hindu Marriage');
  await expect(page.locator('.source-row')).toHaveCount(1);
  await page.locator('.source-row').click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Hindu Marriage Act');
  await dialog.getByLabel('Search document sections').fill('conditions');
  await expect(dialog.locator('.section-passage')).not.toHaveCount(0);
  await dialog.locator('.section-passage summary').first().click();
  await expect(dialog.locator('.legal-text').first()).toBeVisible();
  await dialog.getByRole('button', { name: 'Provenance', exact: true }).click();
  await expect(dialog).toContainText('SHA-256');
  const download = page.waitForEvent('download');
  await dialog.getByRole('link', { name: 'Download original' }).click();
  expect((await download).suggestedFilename()).toMatch(/\.txt$/);
  await page.getByRole('button', { name: 'Close reader' }).click();
});

test('private upload, private search, isolation and explicit clear', async ({ page, browser }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Source library', exact: true }).click();
  await page.getByRole('button', { name: 'Add private document' }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'university-clause.txt', mimeType: 'text/plain', buffer: Buffer.from('Section 1. Assignment requires written consent. This invented clause is only a software test.') });
  await page.getByRole('button', { name: 'Import private document', exact: true }).click();
  await expect(page.getByText('Document imported', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Private documents', exact: true }).click();
  await expect(page.locator('.source-row')).toHaveCount(1);
  const other = await browser.newContext(); const otherPage = await other.newPage();
  await otherPage.goto('/');
  await otherPage.getByRole('button', { name: 'Source library', exact: true }).click();
  await otherPage.getByRole('button', { name: 'Private documents', exact: true }).click();
  await expect(otherPage.getByRole('heading', { name: 'This collection is empty' })).toBeVisible();
  await other.close();
  await page.getByRole('button', { name: 'Research workspace', exact: true }).click();
  await page.getByLabel('Research collection', { exact: true }).selectOption('private');
  await page.getByLabel('What would you like to research?', { exact: true }).fill('written consent');
  await page.getByRole('button', { name: 'Find evidence', exact: true }).click();
  await expect(page.locator('.evidence-card')).toHaveCount(1);
  await expect(page.locator('.source-kicker')).toContainText('PRIVATE DOCUMENT');
  await page.getByRole('button', { name: 'Workspace settings', exact: true }).click();
  await page.getByRole('button', { name: 'Clear this session’s private files' }).click();
  await page.getByRole('button', { name: 'Delete private files', exact: true }).click();
  await expect(page.locator('.private-settings .badge')).toHaveText('0 files');
});

test('all pages are usable on mobile and reduced motion respects the preference', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Explore a legal domain' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.page-enter').evaluate(e => getComputedStyle(e).animationName)).toBe('none');
  for (const name of ['Source library', 'Corpus coverage', 'Evaluation', 'Workspace settings', 'Research workspace']) {
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await page.getByRole('button', { name, exact: true }).click();
    await expect(page.locator('.breadcrumb strong')).toHaveText(name === 'Research workspace' ? 'Legal research' : name);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.getByRole('button', { name: 'About this workspace' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Tab');
  expect(await page.getByRole('dialog').evaluate(e => e.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('eight real domain counts and the matching measured benchmark', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.domain-card')).toHaveCount(8);
  await page.getByRole('button', { name: 'Corpus coverage', exact: true }).click();
  await expect(page.locator('.coverage-card')).toHaveCount(8);
  await expect(page.locator('.stat-card').first()).toContainText('21');
  await page.getByRole('button', { name: 'Evaluation', exact: true }).click();
  await expect(page.getByText('Matches local corpus', { exact: true })).toBeVisible();
  await expect(page.locator('.evaluation-table tbody tr')).toHaveCount(117);
});

test('PDF evidence retains genuine physical pagination in the full reader', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('What would you like to research?', { exact: true }).fill('What passage covers wholesome drinking water in plantations?');
  await page.getByRole('button', { name: 'Find evidence', exact: true }).click();
  await expect(page.locator('.evidence-card').first()).toContainText('Physical PDF');
  await page.getByRole('button', { name: 'Read full context' }).first().click();
  await expect(page.getByRole('dialog').locator('.reader-location')).toContainText('Physical PDF pages');
  await expect(page.getByRole('dialog').locator('.reader-location')).toContainText('Printed pagination unknown');
  await expect(page.getByRole('dialog').getByText('Physical PDF pages', { exact: true })).toBeVisible();
});
