-- Which companies have the most open internship, co-op and new-grad roles.
SELECT company,
       SUM(seniority = 'intern')   AS internships_and_coops,
       SUM(seniority = 'new grad') AS new_grad,
       COUNT(*)                    AS all_open_roles
FROM jobs
WHERE closed_at IS NULL
GROUP BY company
HAVING SUM(seniority IN ('intern', 'new grad')) > 0
ORDER BY internships_and_coops + new_grad DESC, company
LIMIT 15;
