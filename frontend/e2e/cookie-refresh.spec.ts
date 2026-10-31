import { test, expect } from '@playwright/test';

test.describe('First-Party Refresh Cookie & Session Restoration', () => {

  test('Login sets first-party HTTP-only cookie and /api/auth/refresh succeeds', async ({ page, context }) => {
    // Navigate to login
    await page.goto('/login');
    await expect(page.getByLabel(/email address/i)).toBeVisible({ timeout: 15000 });

    // Perform clinical login
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    // Verify successful login
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Inspect cookies in browser context
    const cookies = await context.cookies();
    const refreshCookie = cookies.find(c => c.name === 'tf_refresh_token');
    expect(refreshCookie).toBeDefined();
    expect(refreshCookie?.httpOnly).toBe(true);
    expect(refreshCookie?.sameSite).toBe('Lax');

    // Test direct first-party API refresh via browser fetch
    const refreshResult = await page.evaluate(async () => {
      const csrf = sessionStorage.getItem('csrf_token') || localStorage.getItem('csrf_token') || '';
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
      });
      const data = await res.json();
      return { status: res.status, ok: res.ok, hasToken: !!data.token };
    });

    expect(refreshResult.status).toBe(200);
    expect(refreshResult.ok).toBe(true);
    expect(refreshResult.hasToken).toBe(true);

    // Verify session survives hard page reload without re-prompting login
    await page.reload();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 15000 });
    await expect(page.getByText(/admin@trustfed.ai|Dr\. Marcus Vance|Global Admin/i).first()).toBeVisible({ timeout: 10000 });
  });
});

