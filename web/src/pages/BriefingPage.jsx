import { api } from '../lib/api'
import { fmt, gw, pct, signed } from '../lib/format'
import { useApi } from '../hooks/useApi'
import { ErrorState, LoadingState, SectionHeading } from '../components/UI'

function SignalList({ rows, metric, formatter }) {
  const maximum = Math.max(...rows.map((row) => Math.abs(Number(row[metric] ?? 0))), 1)
  return (
    <div className="signal-list">
      {rows.map((row, index) => (
        <div className="signal-row" key={row.country_iso3 ?? row.entity_code}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <b>{row.country_name}</b>
          <i style={{ '--signal-width': `${Math.max(3, Math.abs(Number(row[metric])) / maximum * 100)}%` }} />
          <em>{formatter(row[metric])}</em>
        </div>
      ))}
    </div>
  )
}

export function BriefingPage() {
  const briefing = useApi(api.briefing, [])
  if (briefing.loading) return <LoadingState label="Menyusun briefing keputusan…" />
  if (briefing.error) return <ErrorState error={briefing.error} />

  const data = briefing.data
  const [start, end] = data.worldTrend
  const renewableChange = end.renewables_share_pct - start.renewables_share_pct
  const fossilChange = end.fossil_share_pct - start.fossil_share_pct
  const validation = data.validation

  const decisions = [
    { code: 'RETIRE', label: 'Verifikasi retirement', tone: 'orange', value: gw(data.retirement[0].fossil_capacity_over_30_years_mw), country: data.retirement[0].country_name, copy: `aset fosil >30 tahun · coverage ${pct(data.retirement[0].fossil_age_coverage_by_capacity_pct)}` },
    { code: 'LOCK-IN', label: 'Cegah lock-in', tone: 'ember', value: gw(data.lockIn[0].coal_capacity_under_15_years_mw), country: data.lockIn[0].country_name, copy: `batu bara <15 tahun · ${pct(data.lockIn[0].coal_capacity_under_15_years_share_pct)} dari batu bara` },
    { code: 'SCALE', label: 'Pelajari skala', tone: 'green', value: signed(data.leaders[0].renewables_share_pct_change, ' pp'), country: data.leaders[0].country_name, copy: `kenaikan share terbarukan · sistem ${fmt(data.leaders[0].total_capacity_gw)} GW` },
    { code: 'DIAGNOSE', label: 'Investigasi hambatan', tone: 'ink', value: signed(data.laggers[0].renewables_share_pct_change, ' pp'), country: data.laggers[0].country_name, copy: `perubahan share terbarukan · sistem ${fmt(data.laggers[0].total_capacity_gw)} GW` },
  ]

  return (
    <div className="page page-enter briefing-page">
      <SectionHeading
        eyebrow="Executive briefing / Fase 4"
        title="Transisi bergerak. Asetnya belum."
        copy="Sinyal produksi listrik membaik, tetapi struktur armada masih menyimpan risiko pensiun dan lock-in dalam skala besar. Briefing ini mengubah temuan menjadi empat jalur keputusan."
        aside={<div className="validation-seal"><span>VALIDATION GATE</span><b>{validation?.status ?? 'NOT RUN'}</b><small>{validation ? `${validation.passCount} pass · ${validation.warningCount} warning · ${validation.failCount} fail` : 'Jalankan Fase 4'}</small></div>}
      />

      <section className="briefing-thesis" aria-label="Tesis transisi global">
        <div><span>Kapasitas fosil / aset 2020</span><strong>{pct(data.snapshot.fossil_share_pct)}</strong><small>dari {fmt(data.snapshot.total_capacity_gw / 1000, 2)} TW terpasang</small></div>
        <div className="thesis-connector"><i /><span>struktur bergerak lebih lambat</span><i /></div>
        <div><span>Share listrik terbarukan / 2005—2022</span><strong>{signed(renewableChange, ' pp')}</strong><small>fosil berubah {signed(fossilChange, ' pp')}</small></div>
      </section>

      <section className="decision-board">
        <div className="decision-board__label"><span>Jalur keputusan</span><small>Bukan skor komposit. Setiap jalur menjawab risiko yang berbeda.</small></div>
        <div className="decision-grid">
          {decisions.map((decision) => (
            <article className={`decision-card decision-card--${decision.tone}`} key={decision.code}>
              <span>{decision.code}</span>
              <h3>{decision.label}</h3>
              <strong>{decision.value}</strong>
              <b>{decision.country}</b>
              <p>{decision.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="briefing-evidence">
        <div>
          <SectionHeading eyebrow="Evidence / armada" title="Dua ujung risiko fosil." copy="Armada tua membuka jendela retirement. Armada muda memperbesar risiko lock-in." />
          <div className="evidence-split">
            <div><h3>Fosil &gt;30 tahun</h3><SignalList rows={data.retirement} metric="fossil_capacity_over_30_years_mw" formatter={gw} /></div>
            <div><h3>Batu bara &lt;15 tahun</h3><SignalList rows={data.lockIn} metric="coal_capacity_under_15_years_mw" formatter={gw} /></div>
          </div>
        </div>
        <aside className="briefing-note"><span>INTERPRETATION LIMIT</span><p>Umur aset hanya berlaku pada kapasitas dengan commissioning year. Status operasi terkini tidak tersedia pada snapshot.</p><b>{pct(data.snapshot.age_coverage_by_capacity_pct)}</b><small>coverage umur global berdasarkan kapasitas</small></aside>
      </section>

      <section className="briefing-evidence briefing-evidence--trend">
        <div>
          <SectionHeading eyebrow="Evidence / sistem ≥50 GW" title="Bandingkan yang sebanding." copy="Peer group berskala besar mengurangi distorsi ranking yang didominasi sistem kecil." />
          <div className="evidence-split">
            <div><h3>Momentum tercepat</h3><SignalList rows={data.leaders} metric="renewables_share_pct_change" formatter={(value) => signed(value, ' pp')} /></div>
            <div><h3>Momentum terendah</h3><SignalList rows={data.laggers} metric="renewables_share_pct_change" formatter={(value) => signed(value, ' pp')} /></div>
          </div>
        </div>
        <aside className="recommendation-stack">
          <span>REKOMENDASI</span>
          <ol>
            <li>Verifikasi status operasi sebelum menetapkan retirement.</li>
            <li>Pisahkan strategi aset tua dan batu bara muda.</li>
            <li>Gunakan peer group region dan skala yang serupa.</li>
            <li>Jangan campurkan kapasitas dengan produksi listrik.</li>
            <li>Publikasikan coverage bersama setiap ranking.</li>
          </ol>
        </aside>
      </section>

      <p className="method-note"><b>Batas keputusan:</b> temuan bersifat deskriptif, bukan estimasi dampak kausal, profitabilitas aset, atau kepastian stranded asset. Periode utama sengaja berhenti pada 2022 untuk menjaga perbandingan lintas negara.</p>
    </div>
  )
}
