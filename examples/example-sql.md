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


Chinook SQLite DB

Table invoices, columns=[InvoiceId, CustomerId, InvoiceDate, BillingState, Total]
Table invoice_items, columns=[InvoiceId, TrackId, UnitPrice, Quantity]
Table customers, columns=[CustomerId, FirstName,  LastName, State, Country, Email]
Table albums, columns = [AlbumId, Title, ArtistId]
Table tracks, columns = [TrackId, Name, AlbumId]
Table artists, columns = [ArtistId, Name]
Table media_types, columns = [MediaTypeId, Name]
Table playlists, columns = [PlaylistId, Name]
Table playlist_track, columns = [PlaylistId, TrackId]

Create me a SQLite query for all customers in city of Cupertino from country of USA

Create a SQLite query for total revenue in last year

Create a SQLite query for top 3 customers who purchased the most albums in last year

Create a SQLite query for top 5 albums that were sold the most in last year

SELECT t.AlbumId, a.Title, COUNT(t.TrackId) AS tracks_sold FROM invoice_items AS i INNER JOIN tracks AS t ON i.TrackId = t.TrackId INNER JOIN albums AS a ON t.AlbumId = a.AlbumId INNER JOIN invoices AS n ON i.InvoiceId = n.InvoiceId WHERE n.InvoiceDate >= '2011-01-01' GROUP BY 1

 i.InvoiceDate >= '2011-01-01'


