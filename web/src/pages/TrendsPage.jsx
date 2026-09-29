import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { fmt, pct, signed } from '../lib/format'
import { useApi } from '../hooks/useApi'
import { Chart } from '../components/Chart'
import { ErrorState, LoadingState, SectionHeading } from '../components/UI'

const palette = ['#102a2e', '#14a86b', '#d15a36', '#7157b7', '#1f6f8b']

export function TrendsPage() {
  const meta = useApi(api.meta, [])
  const momentum = useApi(api.momentum, [])
  const [selected, setSelected] = useState(['OWID_WRL', 'CHN', 'USA', 'IDN'])
  const trends = useApi((signal) => api.trends(selected, signal), [selected.join(',')])

  const addEntity = (event) => {
    const code = event.target.value
    if (code && !selected.includes(code) && selected.length < 5) setSelected((current) => [...current, code])
    event.target.value = ''
  }

  const lineOption = useMemo(() => {
    const rows = trends.data?.data ?? []
    const names = [...new Set(rows.map((row) => row.entity_name))]
    return {
      color: palette,
      grid: { left: 48, right: 20, top: 42, bottom: 42 },
      legend: { top: 0, left: 0, icon: 'rect', itemWidth: 16, textStyle: { color: '#243d40' } },
      tooltip: { trigger: 'axis', backgroundColor: '#102a2e', borderWidth: 0, textStyle: { color: '#fff' }, valueFormatter: (value) => pct(value) },
      xAxis: { type: 'category', boundaryGap: false, data: [...new Set(rows.map((row) => row.year))], axisLabel: { color: '#617475' }, axisLine: { lineStyle: { color: '#aebfbe' } } },
      yAxis: { type: 'value', name: '% listrik', min: 0, max: 100, axisLabel: { formatter: '{value}%', color: '#617475' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
      series: names.map((name) => ({ name, type: 'line', symbol: 'none', lineStyle: { width: name === 'World' ? 3 : 1.8 }, data: rows.filter((row) => row.entity_name === name).map((row) => row.renewables_share_pct), connectNulls: true })),
    }
  }, [trends.data])

  const momentumOption = useMemo(() => {
    const rows = (momentum.data?.data ?? []).slice(0, 15).reverse()
    return {
      grid: { left: 110, right: 44, top: 8, bottom: 26 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: '#102a2e', borderWidth: 0, textStyle: { color: '#fff' }, valueFormatter: (value) => `${fmt(value, 2)} pp/tahun` },
      xAxis: { type: 'value', axisLabel: { color: '#617475' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
      yAxis: { type: 'category', data: rows.map((row) => row.country_name), axisLabel: { color: '#243d40' }, axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: 'bar', barWidth: 9, data: rows.map((row) => row.renewable_transition_momentum_pp_per_year), itemStyle: { color: '#14a86b' } }],
    }
  }, [momentum.data])

  if (meta.loading || trends.loading || momentum.loading) return <LoadingState label="Menyusun deret waktu 2005–2022…" />
  if (meta.error || trends.error || momentum.error) return <ErrorState error={meta.error ?? trends.error ?? momentum.error} />
  const entities = meta.data.entities.filter((entity) => entity.entity_code === 'OWID_WRL' || entity.entity_type === 'country')
  const rows = trends.data.data
  const worldRows = rows.filter((row) => row.entity_code === 'OWID_WRL')
  const firstWorld = worldRows[0]
  const lastWorld = worldRows.at(-1)

  return (
    <div className="page page-enter">
      <SectionHeading eyebrow="Jejak transisi / 2005—2022" title="Arah berubah. Kecepatannya tidak seragam." copy="Bandingkan share listrik terbarukan pada periode dengan cakupan negara yang paling konsisten." aside={<span className="data-stamp">165 / 167<br />ENDPOINT LENGKAP</span>} />
      <div className="trend-callout">
        <div><span>Dunia</span><strong>{firstWorld && lastWorld ? signed(lastWorld.renewables_share_pct - firstWorld.renewables_share_pct, ' pp') : '—'}</strong><small>perubahan share terbarukan</small></div>
        <p>Pertumbuhan bersifat struktural, tetapi rata-rata global menyamarkan negara yang bergerak beberapa kali lebih cepat.</p>
      </div>
      <div className="entity-control">
        <span className="control-label">Seri aktif</span>
        <div className="chips">{selected.map((code) => { const entity = entities.find((item) => item.entity_code === code); return <button key={code} onClick={() => selected.length > 1 && setSelected((items) => items.filter((item) => item !== code))} title="Hapus seri">{entity?.entity_name ?? code}<span aria-hidden="true">×</span></button> })}</div>
        <label className="add-series"><span className="sr-only">Tambah negara</span><select defaultValue="" onChange={addEntity} disabled={selected.length >= 5}><option value="" disabled>+ Tambah negara</option>{entities.filter((item) => !selected.includes(item.entity_code)).map((item) => <option key={item.entity_code} value={item.entity_code}>{item.entity_name}</option>)}</select></label>
      </div>
      <Chart option={lineOption} className="trend-chart" ariaLabel="Grafik garis share listrik terbarukan 2005 sampai 2022" />
      <div className="coverage-warning"><b>Kenapa berhenti di 2022?</b><span>Data 2025 baru mencakup {meta.data.coverage.find((row) => row.year === 2025)?.entities_with_renewable_share ?? 90} entitas. Mengunci perbandingan di 2022 mencegah peringkat bias karena ketimpangan pelaporan.</span></div>
      <section className="momentum-section">
        <SectionHeading eyebrow="Momentum" title="Siapa yang bergerak paling cepat?" copy="Perubahan poin persentase per tahun, dihitung dari endpoint 2005 dan 2022—bukan pertumbuhan kapasitas." />
        <Chart option={momentumOption} className="momentum-chart" ariaLabel="Peringkat momentum transisi terbarukan negara" />
      </section>
    </div>
  )
}
