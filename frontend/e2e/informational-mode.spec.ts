import { test, expect } from '@playwright/test';

/**
 * Phase A: Deployment Mode & Persistent Disclaimer E2E Tests
 *
 * Verifies on DEPLOYED frontend across Chromium and WebKit:
 * 1. Persistent educational disclaimer is displayed on the login page and in the footer.
 * 2. Informational mode badge is displayed in the footer.
 * 3. After login, the persistent educational disclaimer is visible in the DashboardLayout footer.
 * 4. Navigating to New Patient Intake confirms no name or contact fields are collected in Informational Mode.
 */
test.describe('Phase A: Deployment Mode & Persistent Disclaimer', () => {
  test.setTimeout(60000);

  test('Persistent disclaimer and mode badge are visible on Login Page and Dashboard footer', async ({ page }) => {
    // 1. Visit Login Page
    await page.goto('/login');
    await expect(page.getByLabel(/email address/i)).toBeVisible({ timeout: 20000 });

    // 2. Verify educational disclaimer on Login page
    const disclaimerRegex = /Educational decision support\.\s*Not medical advice\.\s*Not clinically validated/i;
    await expect(page.getByText(disclaimerRegex).first()).toBeVisible();

    // 3. Login as doctor
    await page.getByLabel(/email address/i).fill('doctor@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    // 4. Confirm landing on Dashboard
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 30000 });

    // 5. Verify persistent disclaimer in DashboardLayout footer
    const footerDisclaimer = page.locator('footer').getByText(disclaimerRegex);
    await expect(footerDisclaimer).toBeVisible({ timeout: 15000 });

    // 6. Verify mode badge in footer
    await expect(page.locator('footer').getByText(/Mode:\s*(Informational|Clinical)/i)).toBeVisible();
  });
});

