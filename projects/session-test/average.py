# TEST_EDIT
import sys


def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers) if numbers else None
