import { test, expect } from '@playwright/test';

/**
 * Phase F: Public Legal and Regulatory Pages E2E Suite
 *
 * Verifies public accessibility without authentication:
 * 1. /terms
 * 2. /privacy-policy
 * 3. /disclaimer
 * 4. /grievance
 * 5. /intended-use
 * 6. Footer links on every screen
 */
test.describe('Phase F: Public Legal & Transparency Pages', () => {
  test.setTimeout(60000);

  test('Public legal pages are accessible without login and contain DRAFT notices', async ({ page }) => {
    // 1. Terms of Use
    await page.goto('/terms');
    await expect(page.getByRole('heading', { name: /Terms of Use/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/DRAFT, pending legal review/i).first()).toBeVisible();

    // 2. Privacy Policy
    await page.goto('/privacy-policy');
    await expect(page.getByRole('heading', { name: /Privacy Policy/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/What Is NOT Collected/i)).toBeVisible();
    await expect(page.getByText(/NOT ACTIVE/i).first()).toBeVisible();

    // 3. Medical Disclaimer
    await page.goto('/disclaimer');
    await expect(page.getByRole('heading', { name: /Medical & Safety Disclaimer/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/112/).first()).toBeVisible();

    // 4. Contact & Grievance
    await page.goto('/grievance');
    await expect(page.getByRole('heading', { name: /Contact & Grievance Redressal/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Adv\. Rajesh V\. Sharma/i)).toBeVisible();

    // 5. Intended Use
    await page.goto('/intended-use');
    await expect(page.getByRole('heading', { name: /Intended Use Specification/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('heading', { name: /Who It Is For/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /What It Is NOT For/i })).toBeVisible();

    // 6. Verify Footer Links
    const footer = page.locator('footer');
    await expect(footer.getByRole('link', { name: /Terms of Use/i })).toBeVisible();
    await expect(footer.getByRole('link', { name: /Privacy Policy/i })).toBeVisible();
    await expect(footer.getByRole('link', { name: /Medical Disclaimer/i })).toBeVisible();
    await expect(footer.getByRole('link', { name: /Contact & Grievance/i })).toBeVisible();
    await expect(footer.getByRole('link', { name: /Intended Use/i })).toBeVisible();
  });
});
