-- Current-state marts. These encode the semantic-layer definitions
-- (latest_inspection, score_change, neighborhood) so "current" is unambiguous.

CREATE OR REPLACE VIEW restaurant_scored_history AS
SELECT
    camis,
    inspection_id,
    inspection_date,
    program,
    inspection_kind,
    score,
    grade,
    is_graded,
    was_closed,
    total_violations,
    critical_violations,
    source_record_ids,
    row_number() OVER w                       AS n_recent,   -- 1 = most recent
    count(*)     OVER (PARTITION BY camis)    AS scored_count
FROM inspections
WHERE is_scored AND inspection_date > DATE '1901-01-01'
WINDOW w AS (PARTITION BY camis ORDER BY inspection_date DESC, is_graded DESC, score ASC);


CREATE OR REPLACE VIEW restaurant_latest_inspection AS
SELECT camis, inspection_id, inspection_date, program, inspection_kind,
       score, grade, is_graded, was_closed,
       total_violations, critical_violations, source_record_ids
FROM restaurant_scored_history
WHERE n_recent = 1;


CREATE OR REPLACE VIEW restaurant_latest_graded_inspection AS
SELECT camis, inspection_id, inspection_date, grade, score
FROM (
    SELECT camis, inspection_id, inspection_date, grade, score,
           row_number() OVER (PARTITION BY camis ORDER BY inspection_date DESC) AS rn
    FROM inspections
    WHERE grade IN ('A', 'B', 'C')
)
WHERE rn = 1;


-- score_change: latest vs previous scored inspection. Negative = improved
-- (lower score is better).
CREATE OR REPLACE VIEW restaurant_score_change AS
SELECT
    cur.camis,
    cur.inspection_date        AS latest_date,
    cur.score                  AS latest_score,
    prv.inspection_date        AS prev_date,
    prv.score                  AS prev_score,
    cur.score - prv.score      AS score_change,
    CASE
        WHEN cur.score - prv.score < 0 THEN 'improved'
        WHEN cur.score - prv.score > 0 THEN 'deteriorated'
        ELSE 'unchanged'
    END                        AS direction
FROM restaurant_scored_history cur
JOIN restaurant_scored_history prv
  ON cur.camis = prv.camis AND cur.n_recent = 1 AND prv.n_recent = 2;


CREATE OR REPLACE VIEW restaurant_violation_history AS
SELECT i.camis, i.inspection_date, i.inspection_id,
       v.violation_code, v.violation_description, v.is_critical, v.source_record_id
FROM violations v
JOIN inspections i USING (inspection_id);


CREATE OR REPLACE VIEW neighborhood_inspection_summary AS
SELECT
    coalesce(r.nta, r.boro, 'Unknown')                          AS neighborhood,
    count(DISTINCT r.camis)                                     AS restaurants,
    count(DISTINCT li.camis)                                    AS restaurants_with_score,
    round(avg(li.score), 2)                                     AS avg_latest_score,
    round(100.0 * count(*) FILTER (WHERE lg.grade = 'A')
          / nullif(count(lg.grade), 0), 1)                      AS pct_grade_a
FROM restaurants r
LEFT JOIN restaurant_latest_inspection li ON li.camis = r.camis
LEFT JOIN restaurant_latest_graded_inspection lg ON lg.camis = r.camis
GROUP BY 1;
