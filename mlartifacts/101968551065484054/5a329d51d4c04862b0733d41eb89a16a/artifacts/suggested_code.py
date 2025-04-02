def process_data(input_list: list[int]) -> int:
    """Sum numbers greater than 5 from the input list."""
    return sum(item for item in input_list if item > 5)

my_list = [1, 6, 3, 8, 5, 10]
result = process_data(my_list)
print(f"Result: {result}")