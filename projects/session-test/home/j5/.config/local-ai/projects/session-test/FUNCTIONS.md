# Math & Physics Functions Reference

A summary of all math and physics functions in the workspace.

---

## Python Functions

### `calculate_velocity(dist, time)`

**File:** `physics.py`  
**Formula:** `v = dist / time`

| Parameter | Type    | Description        |
|-----------|---------|--------------------|
| `dist`    | float   | Distance traveled  |
| `time`    | float   | Time elapsed       |

**Returns:** Velocity (`float`)  
**Raises:** `ValueError` if `time == 0`

```python
>>> calculate_velocity(100, 5)
20.0
```

---

### `calculate_acceleration(v_start, v_end, time)`

**File:** `physics.py`  
**Formula:** `a = (v_end - v_start) / time`

| Parameter  | Type    | Description             |
|------------|---------|-------------------------|
| `v_start`  | float   | Starting velocity       |
| `v_end`    | float   | Ending velocity         |
| `time`     | float   | Time interval           |

**Returns:** Average acceleration (`float`)  
**Raises:** `ValueError` if `time == 0`

```python
>>> calculate_acceleration(0, 100, 5)
20.0
```

---

### `calculate_sum(a, b)`

**File:** `broken_syntax.py`  
**Formula:** `sum = a + b`

| Parameter | Type | Description |
|-----------|------|-------------|
| `a`       | int/float | First operand |
| `b`       | int/float | Second operand |

**Returns:** Sum of two numbers (`int` or `float`)  
**Raises:** None

```python
>>> calculate_sum(3, 7)
10
```

---

## Shell Script Calculation

### Array Sum (Iterative Loop)

**File:** `Test Script.sh`  
**Algorithm:** Iterates over an array `[1, 2, 3, 4, 5]`, accumulating the total via a bash loop.

**Result:** Outputs `"The sum of the numbers is: 15"`

This is not a formal function but demonstrates the same summation logic as `calculate_sum(a, b)` extended to an arbitrary-length array using shell arithmetic.

---

## Summary Table

| Function | File | Domain | Formula |
|----------|------|--------|---------|
| `calculate_velocity(dist, time)` | `physics.py` | Physics (kinematics) | `v = d / t` |
| `calculate_acceleration(v_start, v_end, time)` | `physics.py` | Physics (kinematics) | `a = Δv / t` |
| `calculate_sum(a, b)` | `broken_syntax.py` | Math (arithmetic) | `a + b` |
| Array Sum loop | `Test Script.sh` | Shell arithmetic | Iterative summation |
