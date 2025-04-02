# sample_code/bad_code.py
# A simple function that could be improved

def processData(input_list):
    # This function sums numbers greater than 5
    total = 0
    for item in input_list:
        if item > 5:
            total = total + item # Non-pythonic addition
    # No type hints, unclear variable names sometimes
    return total

my_list = [1, 6, 3, 8, 5, 10]
result = processData(my_list)
# print("Result:", result) # No clear output indication