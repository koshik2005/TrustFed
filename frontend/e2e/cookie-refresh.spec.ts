import { test, expect } from '@playwright/test';

/**
 * First-Party Refresh Cookie & Hard Reload Session Restoration
 *
 * Verifies on DEPLOYED Vercel URL across Chromium and WebKit:
 * 1. Clinical sign-in sets httpOnly tf_refresh_token cookie.
 * 2. Hard page reload (F5) silently restores the session via the refresh cookie
 *    and double-submit CSRF token without redirecting the user to /login.
 * 3. In-browser /api/auth/refresh rotation call returns 200 and a new rotating token.
 */
test.describe('First-Party Refresh Cookie & Session Restoration', () => {

  test.setTimeout(90000);

  test('Login on deployed URL, hard page reload, and confirm session restoration via refresh cookie', async ({ page, context }) => {
    // ── 1. Navigate to login page ───────────────────────────────────────────
    await page.goto('/login');
    await expect(page.getByLabel(/email address/i)).toBeVisible({ timeout: 25000 });

    // ── 2. Perform clinical authentication ──────────────────────────────────
    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    // ── 3. Confirm authenticated landing on Dashboard ───────────────────────
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 30000 });
    await expect(
      page.getByText(/admin@trustfed\.ai|Dr\.\s*Marcus Vance|Global Admin/i).first()
    ).toBeVisible({ timeout: 15000 });

    // ── 4. Verify HTTP-only cookie exists in browser context ─────────────────
    const cookies = await context.cookies();
    const refreshCookie = cookies.find((c) => c.name === 'tf_refresh_token');
    expect(refreshCookie, 'tf_refresh_token cookie must be set on client').toBeDefined();
    expect(refreshCookie?.httpOnly, 'tf_refresh_token must be httpOnly').toBe(true);

    // ── 5. Perform hard page reload ──────────────────────────────────────────
    await page.reload({ waitUntil: 'networkidle' });

    // ── 6. Confirm session survived hard reload without kick-out to /login ───
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 25000 });
    await expect(
      page.getByText(/admin@trustfed\.ai|Dr\.\s*Marcus Vance|Global Admin/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('Direct in-browser /api/auth/refresh rotation call succeeds', async ({ page }) => {
    let capturedCsrfToken: string | null = null;

    await page.route('**/auth/login', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      if (body?.csrf_token) {
        capturedCsrfToken = body.csrf_token;
      }
      await route.fulfill({ response, json: body });
    });

    await page.goto('/login');
    await expect(page.getByLabel(/email address/i)).toBeVisible({ timeout: 25000 });

    await page.getByLabel(/email address/i).fill('admin@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 30000 });
    expect(capturedCsrfToken).not.toBeNull();

    // Direct in-browser fetch against the proxy rewrite endpoint
    const refreshResult = await page.evaluate(async (csrf: string) => {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
      });
      let data: Record<string, unknown> = {};
      try { data = await res.json(); } catch { /* ignore */ }
      return {
        status: res.status,
        ok: res.ok,
        hasToken: typeof data['token'] === 'string' && (data['token'] as string).length > 10,
        hasNewCsrf: typeof data['csrf_token'] === 'string',
      };
    }, capturedCsrfToken!);

    expect(refreshResult.status).toBe(200);
    expect(refreshResult.ok).toBe(true);
    expect(refreshResult.hasToken).toBe(true);
    expect(refreshResult.hasNewCsrf).toBe(true);
  });

});
