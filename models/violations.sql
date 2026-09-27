-- Canonical detail: one row per (inspection, violation_code).
-- Collapses the 172 exact-duplicate violation rows in the source.

CREATE OR REPLACE TABLE violations AS
SELECT
    md5(camis || '|' || cast(inspection_date AS DATE)::VARCHAR || '|' || coalesce(inspection_type, '')) AS inspection_id,
    violation_code,
    any_value(violation_description)          AS violation_description,
    any_value(critical_flag) = 'Critical'     AS is_critical,
    min(source_record_id)                     AS source_record_id
FROM raw
WHERE inspection_date > '1901-01-01'
  AND violation_code IS NOT NULL
GROUP BY 1, 2;
