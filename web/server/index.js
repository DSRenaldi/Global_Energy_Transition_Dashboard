import process from 'node:process'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import express from 'express'
import pg from 'pg'

const __dirname = dirname(fileURLToPath(import.meta.url))
const webRoot = resolve(__dirname, '..')
const projectRoot = resolve(webRoot, '..')

try {
  process.loadEnvFile(resolve(projectRoot, '.env'))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}

pg.types.setTypeParser(20, Number)
pg.types.setTypeParser(1700, Number)

const pool = new pg.Pool({
  host: process.env.PGHOST ?? 'localhost',
  port: Number(process.env.PGPORT ?? 5432),
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  database: process.env.PGDATABASE ?? 'energy_transition',
  max: 8,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
})

const app = express()
const port = Number(process.env.PORT ?? 3000)
const isProduction = process.env.NODE_ENV === 'production'

app.disable('x-powered-by')
app.use((request, response, next) => {
  response.setHeader('X-Content-Type-Options', 'nosniff')
  response.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
  next()
})

const asyncRoute = (handler) => (request, response, next) => {
  Promise.resolve(handler(request, response, next)).catch(next)
}

const clampInteger = (value, fallback, minimum, maximum) => {
  const parsed = Number.parseInt(value, 10)
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(maximum, Math.max(minimum, parsed))
}

const parseEntityCodes = (value) => {
  const codes = String(value ?? 'OWID_WRL')
    .split(',')
    .map((code) => code.trim().toUpperCase())
    .filter(Boolean)
  const uniqueCodes = [...new Set(codes)].slice(0, 5)
  if (!uniqueCodes.length || uniqueCodes.some((code) => !/^(?:[A-Z]{3}|OWID_WRL)$/.test(code))) {
    const error = new Error('Kode entitas tidak valid.')
    error.status = 400
    throw error
  }
  return uniqueCodes
}

app.get(
  '/api/health',
  asyncRoute(async (_request, response) => {
    const result = await pool.query('SELECT current_database() AS database, NOW() AS checked_at')
    response.json({ status: 'ok', ...result.rows[0] })
  }),
)

app.get(
  '/api/overview',
  asyncRoute(async (_request, response) => {
    const [snapshot, worldTrend, coverage] = await Promise.all([
      pool.query('SELECT * FROM energy_analytics.v_global_kpi'),
      pool.query(`
        SELECT year, electricity_generation_twh, renewables_share_pct,
               fossil_share_pct, nuclear_share_pct, low_carbon_share_pct,
               carbon_intensity_gco2_per_kwh
        FROM energy_analytics.v_energy_trend
        WHERE entity_code = 'OWID_WRL' AND year IN (2005, 2022)
        ORDER BY year
      `),
      pool.query(`
        SELECT year, entities_with_renewable_share
        FROM energy_analytics.v_energy_year_coverage
        WHERE year IN (2022, 2023, 2024, 2025)
        ORDER BY year
      `),
    ])
    response.json({
      snapshot: snapshot.rows[0],
      worldTrend: worldTrend.rows,
      coverage: coverage.rows,
      methodology: {
        assetReferenceYear: 2020,
        trendStartYear: 2005,
        trendEndYear: 2022,
      },
    })
  }),
)

app.get(
  '/api/countries',
  asyncRoute(async (request, response) => {
    const limit = clampInteger(request.query.limit, 200, 1, 250)
    const result = await pool.query(
      `
      WITH coordinates AS (
        SELECT country_iso3,
               AVG(longitude) AS centroid_longitude,
               AVG(latitude) AS centroid_latitude
        FROM energy_core.fact_power_plant
        GROUP BY country_iso3
      )
      SELECT c.*, coordinates.centroid_longitude, coordinates.centroid_latitude
      FROM energy_analytics.v_country_ranking AS c
      LEFT JOIN coordinates USING (country_iso3)
      ORDER BY c.total_capacity_mw DESC
      LIMIT $1
      `,
      [limit],
    )
    response.json({ data: result.rows })
  }),
)

app.get(
  '/api/fuels',
  asyncRoute(async (_request, response) => {
    const result = await pool.query(`
      SELECT * FROM energy_analytics.v_global_fuel
      ORDER BY capacity_mw DESC
    `)
    response.json({ data: result.rows })
  }),
)

app.get(
  '/api/trends',
  asyncRoute(async (request, response) => {
    const entityCodes = parseEntityCodes(request.query.entities)
    const startYear = clampInteger(request.query.start, 2005, 1900, 2025)
    const endYear = clampInteger(request.query.end, 2022, startYear, 2025)
    const result = await pool.query(
      `
      SELECT entity_code, entity_name, entity_type, region_name, year,
             electricity_generation_twh, renewables_electricity_twh,
             fossil_electricity_twh, nuclear_electricity_twh,
             renewables_share_pct, fossil_share_pct, nuclear_share_pct,
             low_carbon_share_pct, carbon_intensity_gco2_per_kwh,
             electricity_generation_per_capita_kwh
      FROM energy_analytics.v_energy_trend
      WHERE entity_code = ANY($1::text[]) AND year BETWEEN $2 AND $3
      ORDER BY entity_name, year
      `,
      [entityCodes, startYear, endYear],
    )
    response.json({
      data: result.rows,
      selection: { entityCodes, startYear, endYear },
    })
  }),
)

app.get(
  '/api/momentum',
  asyncRoute(async (request, response) => {
    const limit = clampInteger(request.query.limit, 20, 1, 100)
    const result = await pool.query(
      `
      SELECT * FROM energy_analytics.v_transition_momentum_2005_2022
      WHERE has_comparable_endpoints
      ORDER BY renewable_transition_momentum_pp_per_year DESC
      LIMIT $1
      `,
      [limit],
    )
    response.json({ data: result.rows, period: { startYear: 2005, endYear: 2022 } })
  }),
)

app.get(
  '/api/risk',
  asyncRoute(async (request, response) => {
    const limit = clampInteger(request.query.limit, 80, 1, 200)
    const result = await pool.query(
      `
      SELECT * FROM energy_analytics.v_fossil_asset_risk
      WHERE fossil_capacity_mw > 0
      ORDER BY fossil_capacity_mw DESC
      LIMIT $1
      `,
      [limit],
    )
    response.json({ data: result.rows })
  }),
)

app.get(
  '/api/age-bands',
  asyncRoute(async (request, response) => {
    const countryCode = request.query.country
      ? String(request.query.country).trim().toUpperCase()
      : null
    if (countryCode && !/^[A-Z]{3}$/.test(countryCode)) {
      const error = new Error('Kode negara tidak valid.')
      error.status = 400
      throw error
    }
    const result = await pool.query(
      `
      SELECT * FROM energy_analytics.v_country_age_band
      WHERE ($1::text IS NULL OR country_iso3 = $1)
      ORDER BY country_name, age_band_sort, fuel_group
      `,
      [countryCode],
    )
    response.json({ data: result.rows })
  }),
)

app.get(
  '/api/meta',
  asyncRoute(async (_request, response) => {
    const [entities, coverage, unmatched] = await Promise.all([
      pool.query(`
        SELECT entity_code, entity_name, entity_type, region_name
        FROM energy_core.dim_energy_entity
        ORDER BY entity_type DESC, entity_name
      `),
      pool.query('SELECT * FROM energy_analytics.v_energy_year_coverage ORDER BY year'),
      pool.query(`
        SELECT country_iso3, country_name
        FROM energy_core.dim_country
        WHERE world_bank_match_status = 'unmatched'
        ORDER BY country_iso3
      `),
    ])
    response.json({
      entities: entities.rows,
      coverage: coverage.rows,
      unmatchedWorldBank: unmatched.rows,
      sources: [
        { name: 'WRI Global Power Plant Database', version: '1.3.0', role: 'Aset dan kapasitas' },
        { name: 'Our World in Data Energy Data', version: 'Pinned snapshot', role: 'Tren listrik country-year' },
        { name: 'World Bank Open Data', version: 'Population 2020', role: 'Region dan normalisasi' },
      ],
    })
  }),
)

app.get(
  '/api/briefing',
  asyncRoute(async (_request, response) => {
    const [snapshot, worldTrend, retirement, lockIn, leaders, laggers] = await Promise.all([
      pool.query('SELECT * FROM energy_analytics.v_global_kpi'),
      pool.query(`
        SELECT year, renewables_share_pct, fossil_share_pct
        FROM energy_analytics.v_energy_trend
        WHERE entity_code = 'OWID_WRL' AND year IN (2005, 2022)
        ORDER BY year
      `),
      pool.query(`
        SELECT country_iso3, country_name, fossil_capacity_over_30_years_mw,
               fossil_age_coverage_by_capacity_pct
        FROM energy_analytics.v_fossil_asset_risk
        ORDER BY fossil_capacity_over_30_years_mw DESC
        LIMIT 5
      `),
      pool.query(`
        SELECT country_iso3, country_name, coal_capacity_under_15_years_mw,
               coal_capacity_under_15_years_share_pct,
               fossil_age_coverage_by_capacity_pct
        FROM energy_analytics.v_fossil_asset_risk
        ORDER BY coal_capacity_under_15_years_mw DESC
        LIMIT 5
      `),
      pool.query(`
        SELECT m.entity_code, m.country_name, c.total_capacity_gw,
               m.renewables_share_pct_change,
               m.renewable_transition_momentum_pp_per_year
        FROM energy_analytics.v_transition_momentum_2005_2022 AS m
        JOIN energy_analytics.v_country_kpi AS c ON c.country_iso3 = m.entity_code
        WHERE m.has_comparable_endpoints AND c.total_capacity_gw >= 50
        ORDER BY m.renewable_transition_momentum_pp_per_year DESC
        LIMIT 5
      `),
      pool.query(`
        SELECT m.entity_code, m.country_name, c.total_capacity_gw,
               m.renewables_share_pct_change,
               m.renewable_transition_momentum_pp_per_year
        FROM energy_analytics.v_transition_momentum_2005_2022 AS m
        JOIN energy_analytics.v_country_kpi AS c ON c.country_iso3 = m.entity_code
        WHERE m.has_comparable_endpoints AND c.total_capacity_gw >= 50
        ORDER BY m.renewable_transition_momentum_pp_per_year ASC
        LIMIT 5
      `),
    ])
    let validation = null
    try {
      validation = JSON.parse(
        await readFile(resolve(projectRoot, 'reports', 'phase4', 'validation_summary.json'), 'utf8'),
      )
    } catch (error) {
      if (error.code !== 'ENOENT') throw error
    }
    response.json({
      snapshot: snapshot.rows[0],
      worldTrend: worldTrend.rows,
      retirement: retirement.rows,
      lockIn: lockIn.rows,
      leaders: leaders.rows,
      laggers: laggers.rows,
      validation: validation && {
        status: validation.overall_status,
        generatedAt: validation.generated_at_utc,
        passCount: validation.pass_count,
        warningCount: validation.warning_count,
        failCount: validation.fail_count,
      },
    })
  }),
)

if (isProduction) {
  app.use(express.static(resolve(webRoot, 'dist'), { maxAge: '1h', etag: true }))
  app.use((_request, response) => response.sendFile(resolve(webRoot, 'dist', 'index.html')))
} else {
  const { createServer: createViteServer } = await import('vite')
  const vite = await createViteServer({
    root: webRoot,
    server: { middlewareMode: true },
    appType: 'spa',
  })
  app.use(vite.middlewares)
}

app.use((error, _request, response, _next) => {
  const status = error.status ?? 500
  if (status >= 500) console.error(error)
  response.status(status).json({
    error: status >= 500 ? 'Data tidak dapat dimuat dari PostgreSQL.' : error.message,
  })
})

const server = app.listen(port, '127.0.0.1', () => {
  console.log(`Gridshift dashboard: http://127.0.0.1:${port}`)
})

const shutdown = async () => {
  server.close()
  await pool.end()
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
