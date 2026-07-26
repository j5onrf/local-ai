def calculate_average(numbers):
    """Calculate average of a list of numbers with empty list check."""
    
    # Check for empty list
    if len(numbers) == 0:
        return None
    
    # Calculate sum and count
    total = 0
    for num in numbers:
        total += num
    
    # Return calculated average
    return total / len(numbers)


if __name__ == '__main__':
    import sys
    input_array = [int(x.strip()) for x in sys.argv[1:] if x]
    result = calculate_average(input_array)
    print(f'Average: {result}')
