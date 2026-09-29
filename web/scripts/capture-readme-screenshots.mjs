import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const scriptDirectory = fileURLToPath(new URL('.', import.meta.url))
const webRoot = resolve(scriptDirectory, '..')
const outputDirectory = resolve(webRoot, '..', 'docs', 'assets')
const baseUrl = process.env.CAPTURE_BASE_URL ?? 'http://127.0.0.1:3000'

await mkdir(outputDirectory, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  colorScheme: 'light',
  reducedMotion: 'reduce',
})
const page = await context.newPage()
const consoleErrors = []
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('favicon.ico')) {
    consoleErrors.push(message.text())
  }
})

async function capture(hash, heading, filename) {
  await page.goto(`${baseUrl}/${hash}`, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: heading }).waitFor()
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({
    path: resolve(outputDirectory, filename),
    type: 'jpeg',
    quality: 90,
    fullPage: false,
  })
}

try {
  await capture('', /TW terpasang/i, 'gridshift-overview.jpg')
  await capture('#briefing', /Transisi bergerak/i, 'gridshift-briefing.jpg')
  if (consoleErrors.length) {
    throw new Error(`Console errors saat capture:\n${consoleErrors.join('\n')}`)
  }
  console.log(`Screenshot README disimpan di ${outputDirectory}`)
} finally {
  await browser.close()
}
