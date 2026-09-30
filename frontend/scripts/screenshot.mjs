import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = fs.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const url = process.argv[2] || 'http://127.0.0.1:5173/companies/terraspark/company';
const outputPath = process.argv[3] || 'screenshot.png';
const width = parseInt(process.argv[4] || '1440', 10);
const height = parseInt(process.argv[5] || '900', 10);

async function run() {
  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height });
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 15000 });
    // Small delay to ensure any animations/fonts settle
    await new Promise((r) => setTimeout(r, 600));
    await page.screenshot({ path: outputPath, fullPage: false });
    console.log(`Saved screenshot: ${outputPath} (${width}x${height})`);
  } catch (err) {
    console.error('Screenshot error:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

run();
