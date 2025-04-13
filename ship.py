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
            if max_ratio_of_interception_by_time > best_ratio:
                best_ratio = max_ratio_of_interception_by_time
                best_target_index = i

        return best_target_index

    def intercept_with_laser(self, target_to_intercept: Target, result_queue: queue.Queue):
        optimized_firing_time, probability_of_interception, _ = target_to_intercept.get_optimized_laser_firing_time()
        time.sleep(optimized_firing_time)  # Simulate interception time
        was_intercepted = random.random() < probability_of_interception
        result_queue.put([was_intercepted, optimized_firing_time, target_to_intercept])
 

    def process_barrages_intercept(self, barrage_history, total_mission_time: float, dt=1):
        current_mission_time_in_seconds = 0
        targets_on_air: list[Target] = []
        barrage_index = 0
        count_laser_interception = 0
        interception_result_queue = queue.Queue()
        intercepting_threads = []

        while current_mission_time_in_seconds < total_mission_time:
            # Check for new barrages
            if barrage_index < len(barrage_history):
                barrage_time_in_days, barrage_type = barrage_history[barrage_index]
                barrage_time_in_seconds = barrage_time_in_days
                if current_mission_time_in_seconds >= barrage_time_in_seconds:
                    print(f"Barrage of type {barrage_type} detected at mission time: {barrage_time_in_days:.2f} days.")
                    new_targets = barrage.generate_targets_by_barrage(barrage_type)
                    targets_on_air.extend(new_targets)
                    print(f"Number of targets on air: {len(targets_on_air)}")
                    barrage_index += 1

            # Try to intercept if there are targets and the ship isn't already intercepting
            if targets_on_air and not intercepting_threads:
                best_target_index = self.choose_target(targets_on_air)
                if best_target_index is not None:
                    target_to_intercept: Target = targets_on_air[best_target_index]
                    print(f"Attempting to intercept target {target_to_intercept.type} in distance {target_to_intercept.distance}.")

                    laser_thread = threading.Thread(target=self.intercept_with_laser, args=(target_to_intercept, interception_result_queue))
                    laser_thread.start()
                    intercepting_threads.append(laser_thread)

            # Process interception results from the queue
            while not interception_result_queue.empty():
                was_intercepted, intercept_time, intercepted_target = interception_result_queue.get()
                print(f"Interception attempt for {intercepted_target.type} took {intercept_time:.2f} seconds.")
                current_mission_time_in_seconds += intercept_time
                if was_intercepted:
                    print("Interception successful!")
                    if intercepted_target in targets_on_air:
                        targets_on_air.remove(intercepted_target)
                        count_laser_interception += 1
                else:
                    print("Interception failed.")
                intercepting_threads.pop(0) # Remove the finished thread

            # Update target distances
            for target in targets_on_air:
                target.update_distance(dt)
                if target.distance <= 0:
                    print(f"Target {target.type} has reached the ship. Mission failed.")
                    return

            current_mission_time_in_seconds += dt
            time.sleep(dt)  # Simulate the passage of time

            if targets_on_air:
                print(f"Number of targets still on air at mission time {current_mission_time_in_seconds:.2f}: {len(targets_on_air)}")

        print("\nMission ended.")
        current_mission_time_in_seconds = 0
        targets_on_air: list[Target] = []
        barrage_index = 0
        count_laser_interception = 0
        interception_result_queue = queue.Queue()
        intercepting_threads = []

        while current_mission_time_in_seconds < total_mission_time:
            # Check for new barrages
            if barrage_index < len(barrage_history):
                barrage_time_in_days, barrage_type = barrage_history[barrage_index]
                barrage_time_in_seconds = barrage_time_in_days * 24 * 60 * 60
                if current_mission_time_in_seconds >= barrage_time_in_seconds:
                    print(f"Barrage of type {barrage_type} detected at mission time: {barrage_time_in_days:.2f} days.")
                    new_targets = barrage.generate_targets_by_barrage(barrage_type)
                    targets_on_air.extend(new_targets)
                    print(f"Number of targets on air: {len(targets_on_air)}")
                    barrage_index += 1

            # Try to intercept if there are targets and the ship isn't already intercepting
            if targets_on_air and not intercepting_threads:
                best_target_index = self.choose_target(targets_on_air)
                if best_target_index is not None:
                    target_to_intercept: Target = targets_on_air[best_target_index]
                    print(f"Attempting to intercept target {target_to_intercept.type} in distance {target_to_intercept.distance}.")

                    laser_thread = threading.Thread(target=self.intercept_with_laser, args=(target_to_intercept, interception_result_queue))
                    laser_thread.start()
                    intercepting_threads.append(laser_thread)

            # Process interception results from the queue
            while not interception_result_queue.empty():
                was_intercepted, intercept_time, intercepted_target = interception_result_queue.get()
                print(f"Interception attempt for {intercepted_target.type} took {intercept_time:.2f} seconds.")
                current_mission_time_in_seconds += intercept_time
                if was_intercepted:
                    print("Interception successful!")
                    if intercepted_target in targets_on_air:
                        targets_on_air.remove(intercepted_target)
                        count_laser_interception += 1
                else:
                    print("Interception failed.")
                intercepting_threads.pop(0) # Remove the finished thread

            # Update target distances
            for target in targets_on_air:
                target.update_distance(dt)

            current_mission_time_in_seconds += dt
            time.sleep(dt)  # Simulate the passage of time

            if targets_on_air:
                print(f"Number of targets still on air at mission time {current_mission_time_in_seconds / (24 * 60 * 60):.2f}: {len(targets_on_air)}")

        print("\nMission ended.")

if __name__ == '__main__':
    ship = Ship(None)
    total_mission_duration = 14  # Simulate for 14 seconds
    simulated_barrages = barrage.generate_barrage(total_mission_duration)
    print("Simulated Barrage History:")
    for t, type in simulated_barrages:
        print(f"Time: {t:.2f} days, Type: {type}")

    print("\nInitiating Interception Simulation:")
    ship.process_barrages_intercept(simulated_barrages, total_mission_duration * 14)