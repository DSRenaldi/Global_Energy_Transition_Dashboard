import { expect, test } from '@playwright/test'

test('dashboard memuat data nyata dan semua tampilan utama', async ({ page }, testInfo) => {
  const errors = []
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon.ico')) errors.push(message.text())
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: /TW terpasang/i })).toBeVisible()
  await expect(page.getByText('34,9 rb unit pembangkit')).toBeVisible()
  await expect(page.locator('canvas')).toHaveCount(2)

  if (testInfo.project.name === 'desktop') {
    await page.screenshot({ path: 'test-results/gridshift-overview.png', fullPage: true })
  }

  const destinations = [
    ['Briefing', /Transisi bergerak/i],
    ['Negara', /Bandingkan skala/i],
    ['Jejak transisi', /Arah berubah/i],
    ['Risiko aset', /Umur aset/i],
    ['Metodologi', /Dua jam data/i],
  ]

  for (const [label, heading] of destinations) {
    await page.getByRole('button', { name: label, exact: true }).click()
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
    if (label === 'Briefing' && testInfo.project.name === 'desktop') {
      await page.screenshot({ path: 'test-results/gridshift-briefing.png', fullPage: true })
    }
  }

  expect(errors).toEqual([])
})

test('API sehat dan layout tidak meluap horizontal', async ({ page }) => {
  const response = await page.request.get('/api/health')
  expect(response.ok()).toBeTruthy()
  expect((await response.json()).status).toBe('ok')

  await page.goto('/#overview')
  await expect(page.getByRole('heading', { name: /TW terpasang/i })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})
