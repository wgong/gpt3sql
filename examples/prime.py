# write a function to calculate prime

def calculate_prime(max_number):
    prime_list = []
    for num in range(2, max_number):
        if num > 1:
            for i in range(2, num):
                if (num % i) == 0:
                    break
            else:
                prime_list.append(num)
    return prime_list

# call the function

calculate_prime(100)


