import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { fmt, gw, pct } from '../lib/format'
import { useApi } from '../hooks/useApi'
import { Chart } from '../components/Chart'
import { ErrorState, LoadingState, SectionHeading, Stat } from '../components/UI'

export function RiskPage() {
  const risk = useApi(api.risk, [])
  const [minimum, setMinimum] = useState(10)

  const rows = useMemo(() => (risk.data?.data ?? []).filter((row) => row.fossil_capacity_mw >= minimum * 1000), [risk.data, minimum])
  const option = useMemo(() => ({
    grid: { left: 54, right: 30, top: 22, bottom: 50 },
    tooltip: { trigger: 'item', backgroundColor: '#102a2e', borderWidth: 0, textStyle: { color: '#fff' }, formatter: ({ data }) => `<b>${data.name}</b><br/>${fmt(data.value[0])} GW fosil<br/>${pct(data.value[1])} berusia >30 tahun<br/>Cakupan umur: ${pct(data.coverage)}` },
    xAxis: { type: 'log', name: 'Kapasitas fosil (GW)', nameLocation: 'middle', nameGap: 32, axisLabel: { color: '#617475' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
    yAxis: { type: 'value', name: 'Porsi >30 tahun', axisLabel: { formatter: '{value}%', color: '#617475' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
    series: [{ type: 'scatter', symbolSize: (value) => Math.max(7, Math.min(32, Math.sqrt(value[0]) * 3)), data: rows.map((row) => ({ name: row.country_name, value: [row.fossil_capacity_mw / 1000, row.fossil_capacity_over_30_years_share_pct ?? 0], coverage: row.fossil_age_coverage_by_capacity_pct, itemStyle: { color: Number(row.fossil_age_coverage_by_capacity_pct) >= 75 ? '#d15a36' : '#91a0a1', opacity: 0.75 } })) }],
  }), [rows])

  if (risk.loading) return <LoadingState />
  if (risk.error) return <ErrorState error={risk.error} />
  const totalOld = rows.reduce((sum, row) => sum + Number(row.fossil_capacity_over_30_years_mw ?? 0), 0)
  const youngCoal = [...rows].sort((a, b) => Number(b.coal_capacity_under_15_years_mw ?? 0) - Number(a.coal_capacity_under_15_years_mw ?? 0))[0]

  return (
    <div className="page page-enter">
      <SectionHeading eyebrow="Risiko aset fosil / snapshot 2020" title="Umur aset menentukan sulitnya jalan keluar." copy="Armada tua dapat mendekati masa pensiun; armada batu bara muda justru menciptakan risiko lock-in puluhan tahun." aside={<span className="data-stamp">UMUR TERTIMBANG<br />OLEH KAPASITAS</span>} />
      <div className="stat-grid stat-grid--three">
        <Stat label={`Aset fosil tua, sistem ≥${minimum} GW`} value={gw(totalOld)} detail="Kapasitas fosil >30 tahun, umur diketahui" tone="orange" />
        <Stat label="Lock-in batu bara terbesar" value={youngCoal?.country_name ?? '—'} detail={youngCoal ? `${gw(youngCoal.coal_capacity_under_15_years_mw)} berusia <15 tahun` : 'Tidak tersedia'} />
        <Stat label="Negara dalam lensa" value={rows.length} detail="Disaring menurut kapasitas fosil" tone="green" />
      </div>
      <div className="risk-toolbar"><label>Kapasitas fosil minimum <output>{minimum} GW</output><input type="range" min="1" max="100" step="1" value={minimum} onChange={(event) => setMinimum(Number(event.target.value))} /></label><span><i /> warna oranye = cakupan data umur ≥75%</span></div>
      <Chart option={option} className="risk-chart" ariaLabel="Diagram sebar kapasitas fosil dan porsi aset berusia lebih dari 30 tahun" />
      <div className="risk-ledger">
        <div className="ledger-head"><span>Sinyal lock-in</span><b>Batu bara &lt;15 tahun</b></div>
        {[...rows].sort((a, b) => Number(b.coal_capacity_under_15_years_mw ?? 0) - Number(a.coal_capacity_under_15_years_mw ?? 0)).slice(0, 8).map((row, index) => (
          <div className="risk-row" key={row.country_iso3}><span>{String(index + 1).padStart(2, '0')}</span><b>{row.country_name}</b><em>{gw(row.coal_capacity_under_15_years_mw)}</em><small>{pct(row.coal_capacity_under_15_years_share_pct)} dari batu bara</small></div>
        ))}
      </div>
      <p className="method-note"><b>Batas interpretasi:</b> metrik umur hanya menggunakan pembangkit dengan tahun commissioning. Cakupan berbeda antarnegara dan selalu ditampilkan pada tooltip; ketiadaan tanggal bukan berarti aset muda.</p>
    </div>
  )
}
