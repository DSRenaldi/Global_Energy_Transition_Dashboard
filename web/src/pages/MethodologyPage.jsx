import { api } from '../lib/api'
import { useApi } from '../hooks/useApi'
import { ErrorState, LoadingState, SectionHeading } from '../components/UI'

export function MethodologyPage() {
  const meta = useApi(api.meta, [])
  if (meta.loading) return <LoadingState />
  if (meta.error) return <ErrorState error={meta.error} />

  return (
    <div className="page page-enter methodology-page">
      <SectionHeading eyebrow="Metodologi & sumber" title="Dua jam data, satu narasi yang jujur." copy="Snapshot aset dan deret waktu listrik menjawab pertanyaan berbeda. Dashboard tidak memaksa keduanya menjadi satu tanggal semu." />
      <div className="method-timeline">
        <article><span>1900—2025</span><h3>Riwayat listrik</h3><p>OWID menyimpan produksi, baur, intensitas karbon, dan data per kapita. Perbandingan utama dikunci ke 2005–2022 karena cakupan endpoint paling konsisten.</p></article>
        <article className="active"><span>2020</span><h3>Potret armada</h3><p>WRI Global Power Plant Database memetakan lokasi, bahan bakar, kapasitas, dan commissioning 34.936 pembangkit.</p></article>
        <article><span>2023—2025</span><h3>Cakupan parsial</h3><p>Tahun terbaru tersedia tetapi belum merata. Ia disimpan di basis data dan dilabeli, tidak dipakai sebagai default peringkat.</p></article>
      </div>
      <section className="method-grid">
        <div><span className="eyebrow">Definisi inti</span><dl><dt>Terbarukan</dt><dd>Hydro, solar, wind, biomass, geothermal, wave & tidal.</dd><dt>Rendah karbon</dt><dd>Seluruh energi terbarukan ditambah nuklir.</dd><dt>Momentum transisi</dt><dd>Perubahan share listrik terbarukan dibagi 17 tahun, dalam poin persentase per tahun.</dd><dt>Aset fosil tua</dt><dd>Kapasitas coal, gas, dan oil dengan umur lebih dari 30 tahun pada tahun referensi 2020.</dd></dl></div>
        <div><span className="eyebrow">Guardrail analisis</span><ul className="guardrails"><li><b>≥1 GW</b> ambang kelayakan ranking share kapasitas.</li><li><b>165 / 167</b> negara memiliki endpoint renewable share 2005 dan 2022.</li><li><b>Cakupan umur</b> selalu menyertai analisis aset berusia tua.</li><li><b>Tidak kausal</b> dashboard menggambarkan struktur dan perubahan, bukan penyebab kebijakan.</li></ul></div>
      </section>
      <section className="source-register"><div className="ledger-head"><span>Register sumber</span><b>Provenance</b></div>{meta.data.sources.map((source, index) => <article key={source.name}><span>0{index + 1}</span><div><h3>{source.name}</h3><p>{source.role}</p></div><b>{source.version}</b></article>)}</section>
      <div className="coverage-strip"><span>CAKUPAN RENEWABLE SHARE / TAHUN</span><div>{meta.data.coverage.filter((row) => row.year >= 2000 && row.year % 5 === 0).map((row) => <i key={row.year} style={{ height: `${Math.max(5, Number(row.entities_with_renewable_share) / 1.8)}%` }} title={`${row.year}: ${row.entities_with_renewable_share} entitas`} />)}</div><small>2000 <b>→</b> 2025</small></div>
    </div>
  )
}
