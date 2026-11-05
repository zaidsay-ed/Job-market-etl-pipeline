-- Most requested skills across open postings, optionally for one seniority level.
-- :seniority = NULL for all postings, or e.g. 'intern'
SELECT s.skill,
       s.category,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs
                                 WHERE closed_at IS NULL
                                   AND (:seniority IS NULL OR seniority = :seniority)), 1) AS pct_of_postings
FROM job_skills s
JOIN jobs j ON j.id = s.job_id
WHERE j.closed_at IS NULL
  AND (:seniority IS NULL OR j.seniority = :seniority)
GROUP BY s.skill, s.category
ORDER BY postings DESC, s.skill
LIMIT 15;
