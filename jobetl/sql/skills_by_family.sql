-- Top 5 skills for each role family, using a window function to rank within each family.
WITH counts AS (
    SELECT j.role_family, s.skill, COUNT(*) AS postings
    FROM job_skills s
    JOIN jobs j ON j.id = s.job_id
    WHERE j.closed_at IS NULL
    GROUP BY j.role_family, s.skill
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY role_family ORDER BY postings DESC, skill) AS rnk
    FROM counts
)
SELECT role_family, skill, postings
FROM ranked
WHERE rnk <= 5
ORDER BY role_family, rnk;
