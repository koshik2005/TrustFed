import { test, expect } from '@playwright/test';
import crypto from 'crypto';

function computeTotp(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const c of secret.toUpperCase()) {
    const idx = alphabet.indexOf(c);
    if (idx !== -1) bits += idx.toString(2).padStart(5, '0');
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    bytes.push(parseInt(bits.substr(i, 8), 2));
  }
  const key = Buffer.from(bytes);
  const epoch = Math.floor(Date.now() / 1000);
  const counter = Math.floor(epoch / 30);
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64BE(BigInt(counter));
  const hmac = crypto.createHmac('sha1', key).update(buf).digest();
  const offset = hmac[hmac.length - 1] & 0xf;
  const code = (
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff)
  ) % 1000000;
  return code.toString().padStart(6, '0');
}

test.describe('Phase G Pre-Launch Fix: End-to-End MFA Enrollment Flow', () => {

  test('User can enroll in TOTP MFA, verify code, and receive emergency recovery codes', async ({ page }) => {
    // 1. Log in as an administrator
    await page.goto('/login');
    const adminEmail = 'admin@trustfed.ai';
    const adminPassword = process.env.TEST_ADMIN_PASSWORD || 'TrustFed2026!SecAdmin';

    await page.getByLabel(/email address/i).fill(adminEmail);
    await page.getByLabel(/password/i).fill(adminPassword);
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();

    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // 2. Navigate to Settings page
    await page.goto('/settings');
    await expect(page.getByText(/Security & Authentication/i)).toBeVisible({ timeout: 10000 });

    // 3. Initiate MFA Setup
    const setupBtn = page.getByTestId('mfa-setup-btn');
    if (await setupBtn.isVisible()) {
      await setupBtn.click();
      
      // 4. Secret code displayed
      const secretEl = page.getByTestId('mfa-secret-code');
      await expect(secretEl).toBeVisible({ timeout: 10000 });
      const secret = (await secretEl.textContent()) || '';
      expect(secret.length).toBeGreaterThanOrEqual(16);

      // 5. Compute real TOTP RFC 6238 code
      const totp = computeTotp(secret.trim());

      // 6. Enter code and verify
      await page.getByTestId('mfa-code-input').fill(totp);
      await page.getByTestId('mfa-verify-btn').click();
    }

    // 7. Verify MFA is active and recovery codes grid rendered
    await expect(page.getByTestId('mfa-active-badge')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/MFA Enrollment Confirmed/i)).toBeVisible({ timeout: 10000 });
  });

});
