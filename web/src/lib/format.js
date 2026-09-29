const number = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 })
const compact = new Intl.NumberFormat('id-ID', { notation: 'compact', maximumFractionDigits: 1 })

export const fmt = (value, digits = 1) => {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(Number(value))
}

export const pct = (value, digits = 1) => `${fmt(value, digits)}%`
export const gw = (mw) => `${number.format(Number(mw ?? 0) / 1000)} GW`
export const twh = (value) => `${number.format(Number(value ?? 0))} TWh`
export const compactNumber = (value) => compact.format(Number(value ?? 0))
export const signed = (value, suffix = '') => {
  if (value == null) return '—'
  const numeric = Number(value)
  return `${numeric > 0 ? '+' : ''}${fmt(numeric)}${suffix}`
}

export const fuelColor = (group) => ({
  Fossil: '#d15a36',
  Renewable: '#14a86b',
  Nuclear: '#7157b7',
  'Other / Unknown': '#91a0a1',
}[group] ?? '#1f6f8b')
