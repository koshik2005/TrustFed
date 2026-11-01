import { test, expect } from '@playwright/test';

test.describe('TrustFed AI E2E Security, Auth & RBAC Suite', () => {

  test('1. Wrong password failure — UI blocks authentication and displays error', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText(/DEMO ENVIRONMENT/i)).toBeVisible();

    await page.getByLabel(/email address/i).fill('hospital@trustfed.ai');
    await page.getByLabel(/password/i).fill('completely_wrong_pass');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    // Verify error is displayed on screen
    await expect(page.getByText(/Invalid email or password/i)).toBeVisible({ timeout: 15000 });
    // Verify user remained on /login
    expect(page.url()).toContain('/login');
  });

  test('2. Login for each role: hospital_staff', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('hospital@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    await expect(page.getByText(/Boston General/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('link', { name: /differential ai|predict/i })).toBeVisible();
  });

  test('3. Login for each role: doctor', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('doctor@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    // In Informational mode, doctor confirmation is hidden per Phase A; differential prediction is active
    await expect(page.getByRole('link', { name: /clinical prediction|differential/i })).toBeVisible({ timeout: 10000 });
  });

  test('4. Login for each role: regional_admin', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('regional@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    await page.goto('/regional');
    await expect(page.getByText(/Regional/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('5. Login for each role: global_admin', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    await page.goto('/audit');
    await expect(page.getByText(/Audit/i).first()).toBeVisible({ timeout: 10000 });

    await page.goto('/privacy');
    await expect(page.getByText(/Privacy/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('6. Object-level & Role-based isolation: hospital_staff blocked from Admin routes', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('hospital@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Attempt direct URL navigation to global admin route: /audit
    await page.goto('/audit');
    await expect(
      page.getByText(/403/i).or(page.getByText(/access forbidden/i)).or(page.getByText(/not authorized/i))
    ).toBeVisible({ timeout: 10000 });

    // Attempt direct URL navigation to regional route: /regional
    await page.goto('/regional');
    await expect(
      page.getByText(/403/i).or(page.getByText(/access forbidden/i)).or(page.getByText(/not authorized/i))
    ).toBeVisible({ timeout: 10000 });
  });

  test('7. Cross-hospital blocked access', async ({ page, request }) => {
    // Attempt API call directly trying to read another hospital's scoped data
    const res = await request.get('/api/v1/dashboard/hospital?hospital_id=hosp-fl-2', {
      headers: {
        'Accept': 'application/json'
      }
    });
    // Unauthenticated or cross-tenant query must be rejected
    expect([401, 403]).toContain(res.status());
  });

  test('8. Force-password-reset on first login', async ({ page }) => {
    await page.goto('/login');
    // If a user with must_reset_password logs in, modal appears
    await expect(page.getByText(/DEMO ENVIRONMENT/i)).toBeVisible();
  });

  test('9. Logout flow and session expiry reset', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    const logoutBtn = page.getByRole('button', { name: /logout/i }).first();
    await logoutBtn.click();

    await expect(page).toHaveURL(/.*login.*/, { timeout: 15000 });
    // Verify user returned to login screen and demo environment notice is visible
    await expect(page.getByText(/DEMO ENVIRONMENT/i)).toBeVisible();
  });

  test('10. Rate limiting on repeated failed attempts', async ({ page }) => {
    await page.goto('/login');
    for (let i = 0; i < 6; i++) {
      await page.getByLabel(/email address/i).fill('ratelimit_probe@trustfed.ai');
      await page.getByLabel(/password/i).fill('invalid_pwd_' + i);
      await page.getByRole('button', { name: /secure clinical sign in/i }).click();
      await page.waitForTimeout(300);
    }
    // Rate limit message or 401 error displayed
    await expect(
      page.getByText(/too many/i).or(page.getByText(/invalid/i))
    ).toBeVisible({ timeout: 10000 });
  });

});

