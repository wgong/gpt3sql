Explain SQL:

SELECT DISTINCT department.name
FROM department
JOIN employee ON department.id = employee.department_id
JOIN salary_payments ON employee.id = salary_payments.employee_id
WHERE salary_payments.date BETWEEN '2020-06-01' AND '2020-06-30'
GROUP BY department.name
HAVING COUNT(employee.id) > 10;
-- Explanation of the above query in human readable format
--

Output:

-- For each department,
--  1. Join the department and employee tables together, so we can get the department name for each employee.
--  2. Join the employee and salary_payments tables together, so we can get the employee ID for each salary payment.
--  3. Get all salary payments made in June 2020.
--  4. Group all records by department name.
--  5. Only return departments where there were more than 10 distinct employees who received salary payments in June 2020.


# Table department, columns = [Id, Name]
# Table employee, columns = [Id, department_id]
# Table salary_payments, columns = [Id, employee_id, date]

# Create a query to find out the name of departments where more than 10 employees were paid their salary in the month of June 2020.

Output:

select d.name as 'Department Name'
from department as d
join employee as e on d.id = e.department_id
join salary_payments as s on s.employee_id = e.id
where s.date like 'June 2020'
group by d.name
having count(*) > 10

