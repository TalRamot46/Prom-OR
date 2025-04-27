import numpy as np
import barrage
MAX_INTERCEPTION_PERIOD = 30  # seconds
import random
import threading
from target import Target
import time
import queue

class Ship():
    def __init__(self, capacities):
        self._capacities = capacities

    def choose_target(self, on_air_targets: list[Target]):
        if not on_air_targets:
            return None

        best_ratio = -1
        best_target_index = None

        for i, target in enumerate(on_air_targets):
            # Assuming distance and velocity are updated elsewhere based on current_time
            _, _, max_ratio_of_interception_by_time = target.get_optimized_laser_firing_time()
            if max_ratio_of_interception_by_time > best_ratio and target.amount_of_attemps_to_intercept < 2:
                best_ratio = max_ratio_of_interception_by_time
                best_target_index = i

        if best_target_index is not None:
            on_air_targets[best_target_index].amount_of_attemps_to_intercept += 1
        return best_target_index




if __name__ == '__main__':
    ship = Ship(None)
    total_mission_duration = 14  # Simulate for 14 seconds
    simulated_barrages = barrage.generate_barrage(total_mission_duration)
    print("Simulated Barrage History:")
    for t, type in simulated_barrages:
        print(f"Time: {t:.2f} days, Type: {type}")

