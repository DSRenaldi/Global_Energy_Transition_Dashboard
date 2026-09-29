import { useMemo } from 'react'
import { feature } from 'topojson-client'
import world from 'world-atlas/countries-110m.json'
import { api } from '../lib/api'
import { compactNumber, fmt, gw, pct, signed } from '../lib/format'
import { useApi } from '../hooks/useApi'
import { Chart, echarts } from '../components/Chart'
import { EnergyRibbon, ErrorState, LoadingState, SectionHeading, Stat } from '../components/UI'

const worldGeoJson = feature(world, world.objects.countries)
if (!echarts.getMap('gridshift-world')) echarts.registerMap('gridshift-world', worldGeoJson)

const tooltip = {
  backgroundColor: '#102a2e',
  borderWidth: 0,
  padding: [10, 12],
  textStyle: { color: '#f4f7f4', fontFamily: 'Manrope', fontSize: 12 },
}

export function OverviewPage({ onOpen }) {
  const overview = useApi(api.overview, [])
  const countries = useApi(api.countries, [])
  const fuels = useApi(api.fuels, [])

  const mapOption = useMemo(() => {
    const points = (countries.data?.data ?? [])
      .filter((item) => item.centroid_longitude != null && item.centroid_latitude != null)
      .map((item) => ({
        name: item.country_name,
        value: [item.centroid_longitude, item.centroid_latitude, item.total_capacity_gw],
        country: item,
      }))
    return {
      backgroundColor: 'transparent',
      tooltip: {
        ...tooltip,
        formatter: ({ data }) => data ? `<b>${data.name}</b><br/>${fmt(data.value[2])} GW kapasitas<br/>${pct(data.country.renewable_share_pct)} terbarukan` : '',
      },
      geo: {
        map: 'gridshift-world',
        roam: true,
        silent: true,
        itemStyle: { areaColor: '#dce6e4', borderColor: '#aebfbe', borderWidth: 0.6 },
        emphasis: { disabled: true },
      },
      series: [{
        type: 'scatter',
        coordinateSystem: 'geo',
        data: points,
        symbolSize: (value) => Math.max(4, Math.min(26, Math.sqrt(value[2]) * 0.9)),
        itemStyle: { color: '#d15a36', opacity: 0.72, borderColor: '#fff', borderWidth: 0.7 },
      }],
    }
  }, [countries.data])

  const fuelOption = useMemo(() => {
    const rows = (fuels.data?.data ?? []).slice(0, 9).reverse()
    return {
      grid: { left: 88, right: 28, top: 8, bottom: 30 },
      tooltip: { ...tooltip, trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (value) => `${fmt(value)} GW` },
      xAxis: { type: 'value', axisLabel: { color: '#617475', formatter: '{value} GW' }, splitLine: { lineStyle: { color: '#d7e1e0' } } },
      yAxis: { type: 'category', data: rows.map((row) => row.primary_fuel), axisLabel: { color: '#243d40', fontFamily: 'Manrope' }, axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: 'bar', data: rows.map((row) => ({ value: row.capacity_mw / 1000, itemStyle: { color: row.fuel_group === 'Fossil' ? '#d15a36' : row.fuel_group === 'Renewable' ? '#14a86b' : row.fuel_group === 'Nuclear' ? '#7157b7' : '#91a0a1' } })), barWidth: 12 }],
    }
  }, [fuels.data])

  if (overview.loading || countries.loading || fuels.loading) return <LoadingState />
  if (overview.error || countries.error || fuels.error) return <ErrorState error={overview.error ?? countries.error ?? fuels.error} />

  const kpi = overview.data.snapshot
  const [start, end] = overview.data.worldTrend

  return (
    <div className="page page-enter">
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">Sistem kelistrikan dunia / aset 2020</span>
          <h1><em>{fmt(kpi.total_capacity_gw / 1000, 1)} TW</em> terpasang.<br />Dunia masih dibangun di atas fosil.</h1>
          <p>Potret 34.936 pembangkit bertemu dengan dua dekade data produksi listrik—untuk membaca bukan hanya posisi hari ini, tetapi arah perubahannya.</p>
          <button className="text-action" onClick={() => onOpen('trends')}>Ikuti jejak transisi <span aria-hidden="true">↗</span></button>
        </div>
        <div className="hero-index" aria-label="Ringkasan indeks global">
          <span>GRIDSHIFT / 001</span>
          <b>167</b>
          <small>negara & wilayah<br />dalam peta aset</small>
        </div>
      </section>

      <section className="ribbon-panel">
        <div className="ribbon-lead"><span>Baur kapasitas global</span><b>2020</b></div>
        <EnergyRibbon fossil={kpi.fossil_share_pct} renewable={kpi.renewable_share_pct} nuclear={kpi.nuclear_share_pct} other={kpi.other_share_pct} />
      </section>

      <section className="stat-grid">
        <Stat label="Kapasitas terpasang" value={`${fmt(kpi.total_capacity_gw / 1000, 2)} TW`} detail={`${compactNumber(kpi.total_plants)} unit pembangkit`} />
        <Stat label="Kapasitas rendah karbon" value={pct(kpi.low_carbon_share_pct)} detail="Terbarukan + nuklir" tone="green" />
        <Stat label="Porsi listrik terbarukan" value={pct(end.renewables_share_pct)} detail={`Naik ${signed(end.renewables_share_pct - start.renewables_share_pct, ' pp')} sejak 2005`} tone="green" />
        <Stat label="Fosil berusia >30 tahun" value={gw(kpi.fossil_capacity_over_30_years_mw)} detail={`${pct(kpi.fossil_capacity_over_30_years_share_pct)} dari fosil berumur diketahui`} tone="orange" />
      </section>

      <section className="map-section">
        <SectionHeading eyebrow="01 / Geografi aset" title="Kapasitas tidak tersebar merata." copy="Ukuran titik mewakili kapasitas pembangkit yang terpetakan. Geser dan perbesar peta untuk membaca konsentrasi sistem." aside={<span className="data-stamp">WRI GPPD<br />REF. 2020</span>} />
        <Chart option={mapOption} className="map-chart" ariaLabel="Peta dunia dengan titik kapasitas pembangkit per negara" />
      </section>

      <section className="split-analysis">
        <div>
          <SectionHeading eyebrow="02 / Bahan bakar" title="Fosil tetap menjadi massa terbesar." />
          <Chart option={fuelOption} className="fuel-chart" ariaLabel="Diagram batang kapasitas global menurut bahan bakar" />
        </div>
        <aside className="field-note">
          <span>CATATAN LAPANGAN</span>
          <blockquote>Transisi produksi listrik bergerak lebih cepat daripada pergantian armada pembangkit.</blockquote>
          <p>Share terbarukan global naik dari {pct(start.renewables_share_pct)} pada 2005 menjadi {pct(end.renewables_share_pct)} pada 2022. Namun {pct(kpi.fossil_share_pct)} kapasitas aset 2020 masih berbasis fosil.</p>
          <button className="text-action" onClick={() => onOpen('risk')}>Lihat risiko aset <span aria-hidden="true">→</span></button>
        </aside>
      </section>
    </div>
  )
}
