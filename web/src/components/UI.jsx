import { pct } from '../lib/format'

export function LoadingState({ label = 'Menghubungkan data energi…' }) {
  return <div className="loading-state" role="status"><span className="loader" />{label}</div>
}

export function ErrorState({ error }) {
  return (
    <div className="error-state" role="alert">
      <span>DATA LINK / OFFLINE</span>
      <p>{error?.message ?? 'Data belum dapat dimuat.'}</p>
    </div>
  )
}

export function SectionHeading({ eyebrow, title, copy, aside }) {
  return (
    <header className="section-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {copy && <p>{copy}</p>}
      </div>
      {aside && <div className="section-aside">{aside}</div>}
    </header>
  )
}

export function Stat({ label, value, detail, tone = 'ink' }) {
  return (
    <div className={`stat stat--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  )
}

export function EnergyRibbon({ fossil = 0, renewable = 0, nuclear = 0, other = 0, compact = false }) {
  const segments = [
    ['Fosil', fossil, 'fossil'],
    ['Terbarukan', renewable, 'renewable'],
    ['Nuklir', nuclear, 'nuclear'],
    ['Lainnya', other, 'other'],
  ].filter(([, value]) => Number(value) > 0)

  return (
    <div className={compact ? 'energy-ribbon energy-ribbon--compact' : 'energy-ribbon'}>
      <div className="ribbon-track" aria-label="Komposisi kapasitas pembangkit">
        {segments.map(([label, value, tone]) => (
          <span key={label} className={`ribbon-segment ribbon-segment--${tone}`} style={{ width: `${value}%` }} title={`${label}: ${pct(value)}`} />
        ))}
      </div>
      {!compact && (
        <div className="ribbon-legend">
          {segments.map(([label, value, tone]) => (
            <span key={label}><i className={`dot dot--${tone}`} />{label} <b>{pct(value)}</b></span>
          ))}
        </div>
      )}
    </div>
  )
}
