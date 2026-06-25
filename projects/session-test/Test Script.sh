#!/usr/bin/env bash

# Define the input array of numbers
numbers=(1 2 3 4 5)

# Calculate the sum of the numbers
total=0
for num in "${numbers[@]}"; do
    total=$((total + num))
done

# Output the result
echo "The sum of the numbers is: $total"
