-- Annualised pay midpoints for open postings with pay info (medians are computed in Python,
-- since SQLite has no MEDIAN function). Hourly and monthly pay were annualised during transform.
SELECT COALESCE(city, CASE WHEN remote THEN 'Remote' END, 'Unknown') AS location,
       role_family,
       seniority,
       currency,
       (salary_min + salary_max) / 2.0 AS salary_mid
FROM jobs
WHERE closed_at IS NULL
  AND salary_min IS NOT NULL;
