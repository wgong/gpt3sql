# Write a powershell script to calculate prime numbers less than 1000.

$prime = @()

for ($i = 2; $i -lt 1000; $i++)

{

$isPrime = $true

for ($j = 2; $j -lt $i; $j++)

{

if ($i % $j -eq 0)

{

$isPrime = $false

break

}

}

if ($isPrime)

{

$prime += $i

}

}

$prime