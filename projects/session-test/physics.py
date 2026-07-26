def calculate_velocity(dist, time): 
    if time == 0:
        raise ValueError("Time cannot be zero")
    return dist / time
