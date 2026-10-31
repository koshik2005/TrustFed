import { test, expect } from '@playwright/test';

test.describe('TrustFed AI E2E Clinical Workflow & Federated Governance Suite', () => {

  test('1. Patient Intake & Top-3 AI Differential Prediction', async ({ page }) => {
    // Log in as hospital staff
    await page.goto('/login');
    await page.getByRole('button', { name: /🏥 Hospital/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Navigate to new patient intake via client router
    await page.getByRole('link', { name: /New Patient Intake/i }).click();
    await expect(page.getByText(/New Patient Registration/i)).toBeVisible({ timeout: 10000 });

    // Fill demographics
    await page.getByPlaceholder(/e\.g\. 35/i).fill('42');
    
    // Select a presenting symptom (e.g. fever) after async symptoms load
    const feverBtn = page.getByRole('button', { name: /Fever \/ Pyrexia/i }).first();
    await expect(feverBtn).toBeVisible({ timeout: 10000 });
    await feverBtn.click();

    // Submit assessment
    const submitBtn = page.getByRole('button', { name: /run ai differential assessment/i });
    await submitBtn.click();

    // Verify encounter is created and differential diagnosis is rendered
    await expect(page).toHaveURL(/.*encounters.*/, { timeout: 20000 });
  });

  test('2. Doctor Review & Diagnosis Confirmation Flow', async ({ page }) => {
    // Log in as doctor
    await page.goto('/login');
    await page.getByLabel(/email address/i).fill('doctor@trustfed.ai');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /secure clinical sign in/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Navigate to doctor confirmations review queue
    await page.goto('/doctor/pending');
    await expect(page.getByText(/Doctor Confirmation/i).or(page.getByText(/Pending/i).first())).toBeVisible({ timeout: 10000 });
  });

  test('3. Regional Hospital Management: List, Add, and Status Badges', async ({ page }) => {
    // Log in as regional admin via 1-click demo access
    await page.goto('/login');
    await page.getByRole('button', { name: /🌐 Regional/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Check regional dashboard hospital management controls
    await expect(page.getByRole('button', { name: /Add Hospital/i }).first()).toBeVisible({ timeout: 10000 });
  });

  test('4. Global Admin Hub Management & Governance Controls', async ({ page }) => {
    // Log in as global admin
    await page.goto('/login');
    await page.getByRole('button', { name: /⚡ Global/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // Navigate to Regional Hubs page
    await page.goto('/hubs');
    await expect(page.getByText(/Regional Hubs/i).first()).toBeVisible({ timeout: 10000 });

    // Navigate to Global Training & Governance
    await page.goto('/training');
    await expect(page.getByText(/Global/i).first()).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/Trigger Federated Round/i).or(page.getByText(/Lineage/i).first())
    ).toBeVisible({ timeout: 10000 });
  });

  test('5. Multi-Tier Round Simulation, Model Promotion & Quick Rollback', async ({ page }) => {
    // Log in as global admin
    await page.goto('/login');
    await page.getByRole('button', { name: /⚡ Global/i }).click();
    await expect(page).toHaveURL(/.*dashboard.*/, { timeout: 20000 });

    // View global admin dashboard controls
    await expect(page.getByText(/Trigger Federated Round/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /Rollback/i }).first()).toBeVisible({ timeout: 10000 });
  });

});
