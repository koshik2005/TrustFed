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

  test('2. Hospital Staff login and role-scoped navigation', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('hospital@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    // Wait for redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    await expect(page.getByText(/Boston General/i).or(page.getByText(/Hospital Node/i))).toBeVisible({ timeout: 10000 });

    // Verify hospital staff sees clinical prediction tab
    await expect(page.getByRole('link', { name: /predict/i })).toBeVisible();
  });

  test('3. Object-level & Role-based isolation: hospital_staff is blocked from Admin routes', async ({ page }) => {
    // Log in as hospital_staff
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('hospital@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Attempt direct URL navigation to global admin route: /audit
    await page.goto('/audit');
    // Expect 403 Forbidden page or redirection
    await expect(
      page.getByText(/403/i).or(page.getByText(/access forbidden/i)).or(page.getByText(/not authorized/i))
    ).toBeVisible({ timeout: 10000 });

    // Attempt direct URL navigation to regional route: /regional
    await page.goto('/regional');
    await expect(
      page.getByText(/403/i).or(page.getByText(/access forbidden/i)).or(page.getByText(/not authorized/i))
    ).toBeVisible({ timeout: 10000 });
  });

  test('4. Regional Admin login and access to Regional Aggregator page', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('regional@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    // Navigate to regional page
    await page.goto('/regional');
    await expect(page.getByText(/Regional/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('5. Global Admin login and system governance access', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });
    // Global admin can view audit logs and privacy validation
    await page.goto('/audit');
    await expect(page.getByText(/Audit/i).first()).toBeVisible({ timeout: 10000 });

    await page.goto('/privacy');
    await expect(page.getByText(/Privacy/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('6. Logout flow resets authentication and returns to /login', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Click logout
    const logoutBtn = page.getByRole('button', { name: /logout|sign out/i });
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
    } else {
      // Find logout button in profile menu
      const userMenu = page.getByText(/Global Admin/i).first();
      await userMenu.click();
      await page.getByRole('button', { name: /logout|sign out/i }).click();
    }

    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
    // Verify visiting protected dashboard redirects back to login
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

  test('7. Unauthenticated user visiting protected route is redirected to /login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

});
