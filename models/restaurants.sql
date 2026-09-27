-- Canonical entity: one row per restaurant establishment (grain = camis).
-- CAMIS is the source-provided stable id; we never merge across it.
-- Attributes are taken from the establishment's most recent record.

CREATE OR REPLACE TABLE restaurants AS
WITH ranked AS (
    SELECT
        camis,
        dba,
        cuisine_description,
        building,
        street,
        zipcode,
        nullif(boro, '0')                         AS boro,
        nta,
        try_cast(latitude AS DOUBLE)              AS latitude,
        try_cast(longitude AS DOUBLE)             AS longitude,
        row_number() OVER (
            PARTITION BY camis
            ORDER BY inspection_date DESC, record_date DESC
        )                                          AS rn
    FROM raw
),
spans AS (
    SELECT
        camis,
        cast(min(inspection_date) FILTER (WHERE inspection_date > '1901-01-01') AS DATE) AS first_inspection_date,
        cast(max(inspection_date) FILTER (WHERE inspection_date > '1901-01-01') AS DATE) AS last_inspection_date,
        count(*) FILTER (WHERE inspection_date > '1901-01-01') = 0                        AS never_inspected
    FROM raw
    GROUP BY camis
)
SELECT
    r.camis,
    r.dba                                          AS dba_raw,
    -- deterministic name normalization (no LLM): strip accents, uppercase,
    -- punctuation -> space, collapse whitespace. Merges DUNKIN / DUNKIN' /
    -- curly-quote variants; deliberately keeps store-number noise distinct.
    nullif(trim(regexp_replace(
        regexp_replace(upper(strip_accents(r.dba)), '[^A-Z0-9 ]', ' ', 'g'),
        ' +', ' ', 'g')), '')                      AS name_normalized,
    r.cuisine_description,
    r.building,
    r.street,
    r.zipcode,
    r.boro,
    r.nta,
    r.latitude,
    r.longitude,
    s.first_inspection_date,
    s.last_inspection_date,
    s.never_inspected
FROM ranked r
JOIN spans s USING (camis)
WHERE r.rn = 1;
