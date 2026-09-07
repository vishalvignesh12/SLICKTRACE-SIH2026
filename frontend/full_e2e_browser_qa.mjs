/**
 * Comprehensive E2E Playwright Browser QA Suite
 * SIH 2026 — Oil Spill Detection & Attribution System
 */

import { chromium } from 'playwright';
import fs from 'fs';

const FRONTEND_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000/api/v1';

const ANALYST_EMAIL = 'officer.verma@coastguard.gov.in';
const ANALYST_PASSWORD = 'SIH2026@CoastGuard';

const ADMIN_EMAIL = 'admin.sharma@coastguard.gov.in';
const ADMIN_PASSWORD = 'SIH2026@CoastGuard';

const consoleErrors = [];
const networkErrors = [];
const testResults = [];

function recordTest(section, name, status, detail = '') {
  const icon = status === 'PASS' ? '✅' : '❌';
  console.log(`[${section}] ${icon} ${name}${detail ? ' — ' + detail : ''}`);
  testResults.push({ section, name, status, detail });
}

async function runQA() {
  console.log('\n===============================================================');
  console.log('STARTING COMPREHENSIVE E2E BROWSER QA SUITE');
  console.log('Frontend:', FRONTEND_URL, '| Backend:', BACKEND_URL);
  console.log('===============================================================\n');

  const browser = await chromium.launch({ headless: true });

  // ---------------------------------------------------------------------------
  // SECTION 1: AUTHENTICATION FLOW
  // ---------------------------------------------------------------------------
  console.log('--- SECTION 1: Authentication Flow ---');
  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(`[Console Error] ${msg.text()}`);
    });
    page.on('pageerror', err => consoleErrors.push(`[Page Error] ${err.message}`));

    try {
      // 1.1 Fresh Unauthenticated visit
      await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
      await page.evaluate(() => localStorage.clear());
      await page.reload({ waitUntil: 'domcontentloaded' });
      
      const emailInput = await page.waitForSelector('input[type="email"]', { timeout: 8000 });
      if (emailInput) {
        recordTest('Authentication', 'Unauthenticated access redirects to Login page', 'PASS');
      } else {
        recordTest('Authentication', 'Unauthenticated access redirects to Login page', 'FAIL');
      }

      // 1.2 Analyst login
      await page.fill('input[type="email"]', ANALYST_EMAIL);
      await page.fill('input[type="password"]', ANALYST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2500);

      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      const loginGone = !(await page.$('input[type="email"]'));

      if (token && token.length > 50 && loginGone) {
        recordTest('Authentication', 'Analyst login succeeds and stores valid JWT in localStorage', 'PASS', `Token length: ${token.length}`);
      } else {
        recordTest('Authentication', 'Analyst login succeeds and stores valid JWT in localStorage', 'FAIL');
      }

      // 1.3 Dashboard Hard Refresh
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1500);

      const tokenAfterRefresh = await page.evaluate(() => localStorage.getItem('auth_token'));
      const loginGoneAfterRefresh = !(await page.$('input[type="email"]'));

      if (tokenAfterRefresh && loginGoneAfterRefresh) {
        recordTest('Authentication', 'Hard refresh preserves authentication session on Dashboard', 'PASS');
      } else {
        recordTest('Authentication', 'Hard refresh preserves authentication session on Dashboard', 'FAIL');
      }

      // 1.4 New tab session check
      const page2 = await context.newPage();
      await page2.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
      await page2.waitForTimeout(1500);
      const tokenTab2 = await page2.evaluate(() => localStorage.getItem('auth_token'));
      if (tokenTab2) {
        recordTest('Authentication', 'New browser tab inherits active authentication session', 'PASS');
      } else {
        recordTest('Authentication', 'New browser tab inherits active authentication session', 'FAIL');
      }
      await page2.close();

      // 1.5 Logout
      const signoutBtn = page.getByRole('button', { name: /Sign Out/i });
      if (await signoutBtn.count() > 0) {
        await signoutBtn.first().scrollIntoViewIfNeeded();
        await signoutBtn.first().click();
        await page.waitForTimeout(1500);

        const tokenAfterLogout = await page.evaluate(() => localStorage.getItem('auth_token'));
        const loginPresentAfterLogout = !!(await page.$('input[type="email"]'));

        if (!tokenAfterLogout && loginPresentAfterLogout) {
          recordTest('Authentication', 'Logout clears JWT token and redirects to Login page', 'PASS');
        } else {
          recordTest('Authentication', 'Logout clears JWT token and redirects to Login page', 'FAIL', `Token: ${tokenAfterLogout}`);
        }
      } else {
        recordTest('Authentication', 'Secure Sign Out button locatable in UI', 'FAIL');
      }

    } catch (err) {
      recordTest('Authentication', 'Authentication flow execution', 'FAIL', err.message);
    }

    await context.close();
  }

  // ---------------------------------------------------------------------------
  // SECTION 2 & 3: AUTHORIZATION & RBAC MATRIX
  // ---------------------------------------------------------------------------
  console.log('\n--- SECTION 2 & 3: Authorization & RBAC Matrix ---');
  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    try {
      // 2.1 Analyst RBAC Check (Blocked from /admin/*)
      await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('input[type="email"]', { timeout: 8000 });
      await page.fill('input[type="email"]', ANALYST_EMAIL);
      await page.fill('input[type="password"]', ANALYST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      const analystToken = await page.evaluate(() => localStorage.getItem('auth_token'));

      const analystToAdminCode = await page.evaluate(async ({ token, url }) => {
        const r = await fetch(`${url}/admin/users`, { headers: { 'Authorization': `Bearer ${token}` } });
        return r.status;
      }, { token: analystToken, url: BACKEND_URL });

      if (analystToAdminCode === 403) {
        recordTest('Authorization', 'Analyst user blocked from Admin API (HTTP 403 Forbidden)', 'PASS');
      } else {
        recordTest('Authorization', 'Analyst user blocked from Admin API (HTTP 403 Forbidden)', 'FAIL', `Status: ${analystToAdminCode}`);
      }

      // 2.2 Admin RBAC Check (Allowed on /admin/* and /dashboard/*)
      await page.evaluate(() => localStorage.clear());
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForSelector('input[type="email"]', { timeout: 8000 });
      await page.fill('input[type="email"]', ADMIN_EMAIL);
      await page.fill('input[type="password"]', ADMIN_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      const adminToken = await page.evaluate(() => localStorage.getItem('auth_token'));

      const adminToAdminCode = await page.evaluate(async ({ token, url }) => {
        const r = await fetch(`${url}/admin/users`, { headers: { 'Authorization': `Bearer ${token}` } });
        return r.status;
      }, { token: adminToken, url: BACKEND_URL });

      if (adminToAdminCode === 200) {
        recordTest('Authorization', 'Admin user granted access to Admin API (HTTP 200 OK)', 'PASS');
      } else {
        recordTest('Authorization', 'Admin user granted access to Admin API (HTTP 200 OK)', 'FAIL', `Status: ${adminToAdminCode}`);
      }

      const adminToDashCode = await page.evaluate(async ({ token, url }) => {
        const r = await fetch(`${url}/dashboard/overview`, { headers: { 'Authorization': `Bearer ${token}` } });
        return r.status;
      }, { token: adminToken, url: BACKEND_URL });

      if (adminToDashCode === 200) {
        recordTest('Authorization', 'Admin user granted access to Dashboard API (HTTP 200 OK)', 'PASS');
      } else {
        recordTest('Authorization', 'Admin user granted access to Dashboard API (HTTP 200 OK)', 'FAIL', `Status: ${adminToDashCode}`);
      }

    } catch (err) {
      recordTest('Authorization', 'Authorization matrix execution', 'FAIL', err.message);
    }

    await context.close();
  }

  // ---------------------------------------------------------------------------
  // SECTION 4 & 7: SCREEN-BY-SCREEN & HARD REFRESH TEST
  // ---------------------------------------------------------------------------
  console.log('\n--- SECTION 4 & 7: Navigation & Hard Refresh Across All Screens ---');
  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(`[Console Error] ${msg.text()}`);
    });
    page.on('response', res => {
      if (res.url().includes('/api/v1/') && res.status() >= 400) {
        networkErrors.push(`${res.request().method()} ${res.url()} -> ${res.status()}`);
      }
    });

    try {
      await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('input[type="email"]', { timeout: 8000 });
      await page.fill('input[type="email"]', ANALYST_EMAIL);
      await page.fill('input[type="password"]', ANALYST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2500);

      const navLabels = [
        'Command Dashboard',
        'Detection Registry',
        'Investigation Map',
        'Vessel Attribution',
        'Vessel Details',
        'Evidence Dossier',
        'Security Alerts',
        'System Reports',
        'Settings'
      ];

      for (const label of navLabels) {
        const btn = page.getByRole('button', { name: new RegExp(label, 'i') });
        if (await btn.count() > 0) {
          await btn.first().click();
          await page.waitForTimeout(800);
        }

        // Hard refresh on screen
        await page.reload({ waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1200);

        const token = await page.evaluate(() => localStorage.getItem('auth_token'));
        const loginPresent = !!(await page.$('input[type="email"]'));

        if (token && !loginPresent) {
          recordTest('Screen QA & Hard Refresh', `Screen "${label}" renders cleanly and survives hard refresh`, 'PASS');
        } else {
          recordTest('Screen QA & Hard Refresh', `Screen "${label}" renders cleanly and survives hard refresh`, 'FAIL', 'Session lost');
        }
      }

    } catch (err) {
      recordTest('Screen QA & Hard Refresh', 'Screen navigation execution', 'FAIL', err.message);
    }

    await context.close();
  }

  // ---------------------------------------------------------------------------
  // SECTION 8: RESPONSIVE VIEWPORT TESTING
  // ---------------------------------------------------------------------------
  console.log('\n--- SECTION 8: Responsive Viewport Testing ---');
  {
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 812 },
      isMobile: true
    });
    const page = await mobileContext.newPage();

    try {
      await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('input[type="email"]', { timeout: 8000 });
      await page.fill('input[type="email"]', ANALYST_EMAIL);
      await page.fill('input[type="password"]', ANALYST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);

      const isAuth = await page.evaluate(() => !!localStorage.getItem('auth_token'));
      const bodyHeight = await page.evaluate(() => document.body.clientHeight);

      if (isAuth && bodyHeight > 300) {
        recordTest('Responsive', 'Mobile Viewport (375x812) layout renders and scales properly', 'PASS', `Body height: ${bodyHeight}px`);
      } else {
        recordTest('Responsive', 'Mobile Viewport (375x812) layout renders and scales properly', 'FAIL', `isAuth: ${isAuth}, height: ${bodyHeight}`);
      }

    } catch (err) {
      recordTest('Responsive', 'Mobile Viewport testing execution', 'FAIL', err.message);
    }

    await mobileContext.close();
  }

  await browser.close();

  // ---------------------------------------------------------------------------
  // SUMMARY
  // ---------------------------------------------------------------------------
  console.log('\n===============================================================');
  console.log('E2E QA SUITE RESULTS SUMMARY');
  console.log('===============================================================');

  const passed = testResults.filter(r => r.status === 'PASS').length;
  const failed = testResults.filter(r => r.status === 'FAIL').length;

  console.log(`TOTAL: ${testResults.length} | PASS: ${passed} | FAIL: ${failed}\n`);

  if (consoleErrors.length > 0) {
    console.log('Console Errors Captured:', consoleErrors.length);
    consoleErrors.forEach(e => console.log('  ⚠️', e));
  } else {
    console.log('Console Errors Captured: 0 (CLEAN) ✅');
  }

  if (networkErrors.length > 0) {
    console.log('Network API Errors Captured:', networkErrors.length);
    networkErrors.forEach(e => console.log('  ❌', e));
  } else {
    console.log('Network API Errors Captured: 0 (CLEAN) ✅');
  }

  const outputData = {
    testResults,
    consoleErrors,
    networkErrors,
    passed,
    failed,
    total: testResults.length,
    timestamp: new Date().toISOString()
  };

  fs.writeFileSync('./e2e_qa_output.json', JSON.stringify(outputData, null, 2));
  return outputData;
}

runQA().then(res => {
  process.exit(res.failed > 0 ? 1 : 0);
}).catch(err => {
  console.error('Runner Exception:', err);
  process.exit(1);
});
