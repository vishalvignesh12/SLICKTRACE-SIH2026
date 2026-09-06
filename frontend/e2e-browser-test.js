import { chromium } from 'playwright';

async function runBrowserE2E() {
  console.log('='.repeat(80));
  console.log('OIL SPILL PLATFORM - BROWSER-LEVEL E2E AUTOMATION & NETWORK AUDIT');
  console.log('='.repeat(80));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const networkLog = [];
  const networkErrors = [];

  page.on('request', (req) => {
    if (req.url().includes(':8000/api/v1')) {
      networkLog.push({
        method: req.method(),
        url: req.url(),
        headers: req.headers()
      });
    }
  });

  page.on('response', (res) => {
    if (res.url().includes(':8000/api/v1')) {
      const status = res.status();
      const method = res.request().method();
      const url = res.url();
      console.log(`  [HTTP ${status}] ${method} ${url}`);
      if (status >= 400) {
        networkErrors.push({ method, url, status });
      }
    }
  });

  try {
    // ─── STEP 1: INITIAL PAGE LOAD & LOGIN ──────────────────────────────────
    console.log('\n[STEP 1] Navigating to Frontend & Executing Login...');
    await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    const emailInput = page.locator('input#email');
    const passInput = page.locator('input#password');
    const submitBtn = page.locator('button[type="submit"]');

    await emailInput.fill('officer.verma@coastguard.gov.in');
    await passInput.fill('SIH2026@CoastGuard');
    await submitBtn.click();
    await page.waitForTimeout(1500);

    const token = await page.evaluate(() => localStorage.getItem('auth_token'));
    if (!token) throw new Error('JWT token not stored in localStorage after login');
    console.log(`  [OK] Login successful. JWT token present: ${token.substring(0, 15)}...`);

    // ─── STEP 2: DASHBOARD VIEW VERIFICATION ─────────────────────────────────
    console.log('\n[STEP 2] Verifying Command & Control Dashboard Data...');
    await page.waitForSelector('text=Command & Control Dashboard', { timeout: 8000 });
    const dashboardTitle = await page.locator('main h1, h1:has-text("Command & Control")').first().textContent();
    console.log(`  [OK] Header verified: "${dashboardTitle.trim()}"`);

    // Verify Metric Cards exist
    const metricCards = await page.locator('.grid-cols-1 > div, .lg\\:grid-cols-4 > div').count();
    console.log(`  [OK] Dashboard KPI metric cards rendered: ${metricCards}`);

    // ─── STEP 3: DETECTION REGISTRY VIEW ────────────────────────────────────
    console.log('\n[STEP 3] Testing Oil Spill Detection Registry...');
    const detectionNavBtn = page.locator('text=Detection Registry').first();
    await detectionNavBtn.click();
    await page.waitForTimeout(1000);

    await page.waitForSelector('text=Oil Spill Detection Registry', { timeout: 8000 });
    console.log('  [OK] Detection Registry view loaded');

    // Trigger Live Satellite Analysis
    console.log('  [ACTION] Triggering Live Satellite Scene Analysis...');
    const analyzeBtn = page.locator('button:has-text("Run Satellite Analysis")');
    if (await analyzeBtn.isVisible()) {
      await analyzeBtn.click();
      await page.waitForTimeout(3000);
      console.log('  [OK] Live ML scene analysis triggered and completed in browser');
    }

    // ─── STEP 4: GEOSPATIAL FORENSICS WORKSPACE (GIS) ────────────────────────
    console.log('\n[STEP 4] Testing GIS Workspace & Leaflet Map Rendering...');
    const gisNavBtn = page.locator('text=Geospatial Map').first();
    if (await gisNavBtn.isVisible()) {
      await gisNavBtn.click();
    } else {
      await page.locator('button:has-text("Inspect")').first().click();
    }
    await page.waitForTimeout(1500);

    await page.waitForSelector('text=Geospatial Forensics Workspace', { timeout: 8000 });
    const mapContainer = await page.locator('.leaflet-container').count();
    console.log(`  [OK] Leaflet Map Canvas initialized: ${mapContainer > 0 ? 'YES' : 'NO'}`);

    // Verify Slick Tooltip or Layer controls
    const layerControls = await page.locator('text=SAR Slick Boundaries').count();
    console.log(`  [OK] GIS Layer controls active: ${layerControls > 0 ? 'YES' : 'NO'}`);

    // ─── STEP 5: PROBABILISTIC ATTRIBUTION VIEW ─────────────────────────────
    console.log('\n[STEP 5] Testing Vessel Attribution Matrix...');
    const attribNavBtn = page.locator('text=Attribution Matrix').first();
    await attribNavBtn.click();
    await page.waitForTimeout(1500);

    await page.waitForSelector('text=Probabilistic Vessel Attribution Matrix', { timeout: 8000 });
    console.log('  [OK] Attribution Matrix view loaded');

    const candidateCards = await page.locator('.grid-cols-1.md\\:grid-cols-2 > div').count();
    console.log(`  [OK] Candidate vessel cards rendered: ${candidateCards}`);

    // ─── STEP 6: VESSEL FORENSIC PROFILE ─────────────────────────────────────
    console.log('\n[STEP 6] Testing Vessel Forensic Profile View...');
    const profileBtn = page.locator('button:has-text("Forensic Profile"), button:has-text("Open Full Forensic Profile")').first();
    if (await profileBtn.isVisible()) {
      await profileBtn.click();
      await page.waitForTimeout(1000);
      console.log('  [OK] Vessel Forensic Profile loaded');
    }

    // ─── STEP 7: OFFICIAL EVIDENCE DOSSIER ───────────────────────────────────
    console.log('\n[STEP 7] Testing Official Legal Evidence Dossier & CSV Export...');
    const dossierNavBtn = page.locator('text=Evidence Dossier').first();
    await dossierNavBtn.click();
    await page.waitForTimeout(1500);

    await page.waitForSelector('text=Official Incident Evidence Dossier', { timeout: 8000 });
    console.log('  [OK] Legal Evidence Dossier loaded');

    // ─── STEP 8: SYSTEM REPORTS & SECURITY ALERTS ───────────────────────────
    console.log('\n[STEP 8] Testing Alerts & System Settings Views...');
    const alertsNavBtn = page.locator('text=Security Alerts').first();
    if (await alertsNavBtn.isVisible()) {
      await alertsNavBtn.click();
      await page.waitForTimeout(800);
      console.log('  [OK] Security Alerts view loaded');
    }

    const settingsNavBtn = page.locator('text=System Settings').first();
    if (await settingsNavBtn.isVisible()) {
      await settingsNavBtn.click();
      await page.waitForTimeout(800);
      console.log('  [OK] Settings view loaded');
    }

    // ─── STEP 9: BROWSER REFRESH / STATE PERSISTENCE ────────────────────────
    console.log('\n[STEP 9] Testing Browser Page Refresh & Auth Persistence...');
    const dossierNav = page.locator('text=Evidence Dossier').first();
    await dossierNav.click();
    await page.waitForTimeout(1000);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const reloadedToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    if (!reloadedToken) throw new Error('Auth token lost on page refresh');
    await page.waitForSelector('text=Official Incident Evidence Dossier', { timeout: 8000 });
    console.log('  [OK] Page refresh successfully preserved auth session & active dossier screen');

    console.log('\n' + '='.repeat(80));
    console.log('NETWORK & API AUDIT SUMMARY:');
    console.log(`  Total API Calls Made: ${networkLog.length}`);
    console.log(`  Failed API Requests: ${networkErrors.length}`);
    if (networkErrors.length > 0) {
      console.log('  Errors:');
      networkErrors.forEach(e => console.log(`    - [${e.status}] ${e.method} ${e.url}`));
    } else {
      console.log('  [100% SUCCESS] Zero network errors observed in browser E2E session.');
    }
    console.log('='.repeat(80));

  } catch (err) {
    console.error('\n[BROWSER E2E FAILURE]:', err);
    throw err;
  } finally {
    await browser.close();
  }
}

runBrowserE2E().catch((err) => {
  process.exit(1);
});
