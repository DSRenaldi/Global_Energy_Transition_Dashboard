import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { fmt, pct } from '../lib/format'
import { useApi } from '../hooks/useApi'
import { Chart } from '../components/Chart'
import { EnergyRibbon, ErrorState, LoadingState, SectionHeading } from '../components/UI'

const metrics = {
  total_capacity_gw: { label: 'Kapasitas total', unit: 'GW', color: '#1f6f8b' },
  renewable_share_pct: { label: 'Share terbarukan', unit: '%', color: '#14a86b' },
  fossil_share_pct: { label: 'Share fosil', unit: '%', color: '#d15a36' },
  low_carbon_share_pct: { label: 'Share rendah karbon', unit: '%', color: '#7157b7' },
}

export function ComparisonPage() {
  const countries = useApi(api.countries, [])
  const [metric, setMetric] = useState('total_capacity_gw')
  const [region, setRegion] = useState('Semua region')

  const filtered = useMemo(() => {
    const rows = countries.data?.data ?? []
    return rows.filter((row) => region === 'Semua region' || row.region_name === region)
      .sort((a, b) => Number(b[metric] ?? 0) - Number(a[metric] ?? 0)).slice(0, 18)
  }, [countries.data, metric, region])

  const option = useMemo(() => ({
    grid: { left: 112, right: 52, top: 10, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: '#102a2e', borderWidth: 0, textStyle: { color: '#fff' }, valueFormatter: (value) => `${fmt(value)} ${metrics[metric].unit}` },
    xAxis: { type: 'value', axisLabel: { color: '#617475' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
    yAxis: { type: 'category', inverse: true, data: filtered.map((row) => row.country_name), axisLabel: { color: '#243d40', width: 100, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', barWidth: 10, data: filtered.map((row, index) => ({ value: row[metric], itemStyle: { color: index === 0 ? metrics[metric].color : '#799193' } })) }],
  }), [filtered, metric])

  if (countries.loading) return <LoadingState />
  if (countries.error) return <ErrorState error={countries.error} />
  const regions = [...new Set(countries.data.data.map((row) => row.region_name).filter(Boolean))].sort()

  return (
    <div className="page page-enter">
      <SectionHeading eyebrow="Perbandingan negara" title="Bandingkan skala, lalu baca struktur." copy="Peringkat share hanya bermakna jika skala sistem ikut terlihat. Pilih metrik dan wilayah untuk mengubah lensa." aside={<span className="data-stamp">AMBANG SHARE<br />≥ 1 GW</span>} />
      <div className="control-row">
        <label>Metrik<select value={metric} onChange={(event) => setMetric(event.target.value)}>{Object.entries(metrics).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></label>
        <label>Region<select value={region} onChange={(event) => setRegion(event.target.value)}><option>Semua region</option>{regions.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <div className="comparison-layout">
        <Chart option={option} className="ranking-chart" ariaLabel={`Peringkat negara berdasarkan ${metrics[metric].label}`} />
        <div className="country-ledger">
          <div className="ledger-head"><span>Negara teratas</span><b>{metrics[metric].label}</b></div>
          {filtered.slice(0, 6).map((row, index) => (
            <article key={row.country_iso3}>
              <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
              <div><h3>{row.country_name}</h3><p>{fmt(row.total_capacity_gw)} GW · {row.dominant_primary_fuel} dominan</p></div>
              <strong>{fmt(row[metric])}{metrics[metric].unit === '%' ? '%' : ' GW'}</strong>
              <EnergyRibbon compact fossil={row.fossil_share_pct} renewable={row.renewable_share_pct} nuclear={row.nuclear_share_pct} other={row.other_share_pct} />
            </article>
          ))}
        </div>
      </div>
      <p className="method-note"><b>Catatan:</b> database aset adalah potret 2020. Untuk metrik share, negara di bawah 1 GW harus dibaca secara hati-hati karena satu pembangkit dapat mendominasi sistem kecil. Porsi terbarukan global pada aset: {pct(27.2)}.</p>
    </div>
  )
}
