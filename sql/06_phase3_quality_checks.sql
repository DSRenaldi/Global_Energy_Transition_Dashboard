\pset pager off
\echo 'Phase 3 PostgreSQL quality checks'

SELECT 'energy_fact_rows' AS check_name, COUNT(*)::TEXT AS actual, '14843' AS expected
FROM energy_core.fact_country_energy_year;

SELECT 'energy_entity_rows' AS check_name, COUNT(*)::TEXT AS actual, '168' AS expected
FROM energy_core.dim_energy_entity;

SELECT 'duplicate_entity_year' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM (
    SELECT entity_code, year
    FROM energy_core.fact_country_energy_year
    GROUP BY entity_code, year
    HAVING COUNT(*) > 1
) AS duplicate_keys;

SELECT 'invalid_share_range' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_core.fact_country_energy_year
WHERE renewables_share_pct NOT BETWEEN 0 AND 100
   OR fossil_share_pct NOT BETWEEN 0 AND 100
   OR nuclear_share_pct NOT BETWEEN 0 AND 100
   OR low_carbon_share_pct NOT BETWEEN 0 AND 100;

SELECT 'low_carbon_formula' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_core.fact_country_energy_year
WHERE low_carbon_share_pct IS NOT NULL
  AND renewables_share_pct IS NOT NULL
  AND nuclear_share_pct IS NOT NULL
  AND ABS(low_carbon_share_pct - renewables_share_pct - nuclear_share_pct) > 0.01;

SELECT 'comparable_2005_2022' AS check_name,
       COUNT(*) FILTER (WHERE has_comparable_endpoints)::TEXT AS actual,
       '165' AS expected
FROM energy_analytics.v_transition_momentum_2005_2022;

SELECT 'phase3_view_count' AS check_name, COUNT(*)::TEXT AS actual, '4' AS expected
FROM pg_views
WHERE schemaname = 'energy_analytics'
  AND viewname IN (
      'v_energy_trend',
      'v_energy_year_coverage',
      'v_transition_momentum_2005_2022',
      'v_transition_latest'
  );

