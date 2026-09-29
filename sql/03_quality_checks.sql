\pset pager off
\echo 'Phase 2 PostgreSQL quality checks'

SELECT 'fact_row_count' AS check_name, COUNT(*)::TEXT AS actual, '34936' AS expected
FROM energy_core.fact_power_plant;

SELECT 'fact_total_capacity_mw' AS check_name,
       ROUND(SUM(capacity_mw), 6)::TEXT AS actual,
       '5706975.447257' AS expected
FROM energy_core.fact_power_plant;

SELECT 'duplicate_plant_id' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM (
    SELECT plant_id FROM energy_core.fact_power_plant GROUP BY plant_id HAVING COUNT(*) > 1
) AS duplicate_ids;

SELECT 'orphan_country' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_core.fact_power_plant AS p
LEFT JOIN energy_core.dim_country AS c USING (country_iso3)
WHERE c.country_iso3 IS NULL;

SELECT 'orphan_fuel' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_core.fact_power_plant AS p
LEFT JOIN energy_core.dim_fuel AS f USING (fuel_key)
WHERE f.fuel_key IS NULL;

SELECT 'negative_age' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_core.fact_power_plant
WHERE plant_age_years < 0;

SELECT 'invalid_country_share' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM energy_analytics.v_country_kpi
WHERE fossil_share_pct NOT BETWEEN 0 AND 100
   OR renewable_share_pct NOT BETWEEN 0 AND 100
   OR nuclear_share_pct NOT BETWEEN 0 AND 100
   OR low_carbon_share_pct NOT BETWEEN 0 AND 100;

SELECT 'country_mix_not_100_pct' AS check_name, COUNT(*)::TEXT AS violations, '0' AS expected
FROM (
    SELECT country_iso3, SUM(country_capacity_share_pct) AS mix_total
    FROM energy_analytics.v_country_fuel_mix
    GROUP BY country_iso3
    HAVING ABS(SUM(country_capacity_share_pct) - 100) > 0.000001
) AS invalid_mix;

SELECT 'world_bank_unmatched' AS check_name,
       COUNT(*)::TEXT AS actual,
       'informational' AS expected
FROM energy_core.dim_country
WHERE world_bank_match_status = 'unmatched';

