def calculate_velocity(dist, time): 
    if time == 0:
        raise ValueError("Time cannot be zero")
    return dist / time


def calculate_acceleration(v_start, v_end, time):
    """Calculate average acceleration given starting velocity, ending velocity, and time.
    
    Formula: a = (v_end - v_start) / time
    
    Args:
        v_start: Starting velocity.
        v_end: Ending velocity.
        time: Time interval (must not be zero).
        
    Returns:
        Average acceleration.
        
    Raises:
        ValueError: If time is zero.
    """
    if time == 0:
        raise ValueError("Time cannot be zero")
    return (v_end - v_start) / time
def calculate_acceleration(v1, v2, t): return (v2 - v1) / t
