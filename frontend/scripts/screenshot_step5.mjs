import puppeteer from 'puppeteer-core';
import fs from 'fs';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const targets = [
  { url: 'http://127.0.0.1:5173/companies/terraspark/actions', name: 'terraspark_actions' },
  { url: 'http://127.0.0.1:5173/companies/mysa/actions', name: 'mysa_actions' },
  { url: 'http://127.0.0.1:5173/companies/terraspark/sources', name: 'terraspark_sources' },
  { url: 'http://127.0.0.1:5173/companies/mysa/sources', name: 'mysa_sources' },
  { url: 'http://127.0.0.1:5173/companies/terraspark/team', name: 'terraspark_team_strip' },
  { url: 'http://127.0.0.1:5173/companies/mysa/funding', name: 'mysa_funding_strip' },
];

const viewports = [
  { w: 1440, h: 900, label: '1440' },
  { w: 1024, h: 768, label: '1024' },
  { w: 390, h: 844, label: '390' },
];

fs.mkdirSync('../screenshots/step5', { recursive: true });

async function capture() {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
  for (const t of targets) {
    for (const v of viewports) {
      const page = await browser.newPage();
      await page.setViewport({ width: v.w, height: v.h });
      await page.goto(t.url, { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise(r => setTimeout(r, 600));
      const file = `../screenshots/step5/${t.name}_${v.label}.png`;
      await page.screenshot({ path: file });
      console.log('Saved', file);
      await page.close();
    }
  }
  await browser.close();
}

capture().catch(err => { console.error(err); process.exit(1); });
