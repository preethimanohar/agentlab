-- Canonical event: one row per inspection (grain = camis + date + inspection_type).
-- Raw is one row per violation; score and grade are invariant within an inspection
-- (verified: 0 inspections with >1 distinct score), so any_value() is safe.
-- Year-1900 placeholder rows (never inspected) are excluded here.

CREATE OR REPLACE TABLE inspections AS
WITH base AS (
    SELECT
        camis,
        cast(inspection_date AS DATE)                       AS inspection_date,
        inspection_type                                     AS inspection_type_raw,
        trim(split_part(inspection_type, ' / ', 1))         AS program,
        nullif(trim(split_part(inspection_type, ' / ', 2)), '') AS inspection_kind,
        try_cast(score AS INTEGER)                          AS score,
        grade,
        try_cast(nullif(grade_date, '') AS DATE)            AS grade_date,
        action                                             AS action_raw,
        action ILIKE '%Closed by DOHMH%'                    AS was_closed,
        critical_flag,
        violation_code,
        source_record_id
    FROM raw
    WHERE inspection_date > '1901-01-01'
)
SELECT
    md5(camis || '|' || inspection_date::VARCHAR || '|' || coalesce(inspection_type_raw, '')) AS inspection_id,
    camis,
    inspection_date,
    program,
    inspection_kind,
    inspection_type_raw,
    any_value(score)                                        AS score,
    any_value(score) IS NOT NULL                            AS is_scored,
    any_value(grade)                                        AS grade,
    any_value(grade) IN ('A', 'B', 'C')                     AS is_graded,
    any_value(grade_date)                                   AS grade_date,
    any_value(action_raw)                                   AS action_raw,
    bool_or(was_closed)                                     AS was_closed,
    count(*) FILTER (WHERE violation_code IS NOT NULL)      AS total_violations,
    count(*) FILTER (WHERE critical_flag = 'Critical')      AS critical_violations,
    list(DISTINCT source_record_id)                         AS source_record_ids
FROM base
GROUP BY 1, 2, 3, 4, 5, 6;
