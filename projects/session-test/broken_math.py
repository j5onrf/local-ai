try:
    result = 10 / 0
except ZeroDivisionError as e:
    print("ZeroDivisionError captured:", e)