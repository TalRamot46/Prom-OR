import math
import numpy as np

def simulate_barrages_uniform(total_time):
    """
    Simulates barrages occurring according to Poisson processes and records
    the time and type of each barrage, using a uniform distribution for type selection.

    Args:
        total_time (float): The total simulation time in days.

    Returns:
        list: A list of tuples, where each tuple contains the cumulative time
              of a barrage and the type of the barrage ("small" or "big").
    """
    cumulative_time = 0.0
    barrage_log = []

    rate_small = 1.0  # Average rate of small barrage (1 per day)
    rate_big = 1.0 / 3.0  # Average rate of big barrage (1 per 3 days)

    while cumulative_time < total_time:
        # Generate waiting time for the next event (either small or big barrage)
        waiting_time = np.random.exponential(1 / (rate_small + rate_big))
        cumulative_time += waiting_time

        if cumulative_time >= total_time:
            break  # Stop if total time is reached

        # Determine the type of barrage using a uniform distribution
        prob_small = rate_small / (rate_small + rate_big)
        random_value = np.random.uniform(0, 1)

        if random_value < prob_small:
            barrage_type = "small"
        else:
            barrage_type = "big"

        barrage_log.append((cumulative_time, barrage_type))

    return barrage_log

if __name__ == '__main__':
    simulation_duration = 14  # Simulate for 14 days
    barrage_history = simulate_barrages_uniform(simulation_duration)

    print(f"Barrage history over {simulation_duration:.2f} days:")
    for time, type in barrage_history:
        print(f"Time: {time * 24 * 60 * 60:.0f} seconds, Barrage Type: {type}")

    # Example of how to interpret the barrage log:
    small_barrage_count = sum(1 for _, type in barrage_history if type == "small")
    big_barrage_count = sum(1 for _, type in barrage_history if type == "big")
    print(f"\nNumber of small barrages: {small_barrage_count}")
    print(f"Number of big barrages: {big_barrage_count}")