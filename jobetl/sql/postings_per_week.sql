-- New postings per week by role family: the hiring trend.
SELECT strftime('%Y-W%W', posted_at) AS week,
       role_family,
       COUNT(*) AS new_postings
FROM jobs
WHERE posted_at IS NOT NULL
GROUP BY week, role_family
ORDER BY week, role_family;
