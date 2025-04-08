import numpy as np
import threats
MAX_INTERCEPTION_PERIOD = 30  # seconds
import random

def choose_target(on_air_targets, current_time):
    """
    Chooses the best target to intercept based on the maximum best_ratio.

    Args:
        on_air_targets (list): A list of Target objects currently on air.
        current_time (float): The current simulation time.

    Returns:
        int or None: The index of the chosen target in the list, or None if no targets are on air.
    """
    if not on_air_targets:
        return None

    best_ratio = -1
    best_target_index = None

    for i, target in enumerate(on_air_targets):
        # Assuming distance and velocity are updated elsewhere based on current_time
        _, _, ratio = target.get_best_laser_interception()
        if ratio > best_ratio:
            best_ratio = ratio
            best_target_index = i

    return best_target_index

def intercept(target_to_intercept, current_time, dt_intercept=0.01):
    """
    Attempts to intercept a target by simulating the lasering process.

    Args:
        target_to_intercept (Target): The Target object to intercept.
        current_time (float): The current simulation time.
        dt_intercept (float, optional): The small time step for interception simulation. Defaults to 0.01.

    Returns:
        bool: True if the target is successfully intercepted, False otherwise.
    """
    if target_to_intercept.type not in target_to_intercept._interception_pdfs:
        return False

    pdf_params = target_to_intercept._interception_pdfs[target_to_intercept.type]
    mean = pdf_params["mean"]
    std = pdf_params["std"]
    t = 0.0  # Time spent lasering

    t_intercept = random.normalvariate(mean, std)
    p_success = np.norm.pdf(t_intercept, mean, std)
    
    if random.random() < p_success:
        return True, t_intercept
    return False, t_intercept

    

def process_barrages_intercept(barrage_history, total_mission_time):
    """
    Processes barrages, detects targets, chooses the best target to intercept,
    and simulates the interception attempt.

    Args:
        barrage_history (list): A list of tuples, where each tuple contains the
                                 cumulative time of a barrage and its type
                                 ("small" or "big").
        total_mission_time (float): The total duration of the mission in days.
    """
    current_mission_time = 0.0
    targets_on_air = []
    barrage_index = 0
    count_laser_interception = 0
    while current_mission_time < total_mission_time:
        
        # Check if a new barrage has occurred
        if barrage_index < len(barrage_history) and current_mission_time >= barrage_history[barrage_index][0]:
            barrage_time, barrage_type = barrage_history[barrage_index]
            print(f"\nBarrage of type '{barrage_type}' detected at mission time: {current_mission_time:.2f} days.")
            new_targets = threats.generate_targets_by_barrage(barrage_type, current_mission_time)
            targets_on_air.extend(new_targets)
            print(f"Number of targets on air: {len(targets_on_air)}")
            barrage_index += 1

        # Try to intercept if there are targets on air
        if targets_on_air:
            best_target_index = choose_target(targets_on_air, current_mission_time)
            if best_target_index is not None:
                target_to_intercept = targets_on_air[best_target_index]
                print(f"Attempting to intercept target {target_to_intercept.id} of type '{target_to_intercept.type}'.")
                interception_results = intercept(target_to_intercept, current_mission_time)
                current_mission_time += intercept_time 
                was_intercepted, intercept_time = interception_results
                if was_intercepted:
                    print("interception")
                    # Remove the intercepted target
                    del targets_on_air[best_target_index]
                    count_laser_interception += 1
                else:
                    print("missed interception")
                print(f"Remaining targets on air: {len(targets_on_air)}")

        # Remove targets that have arrived (distance <= 0)
        targets_on_air = [target for target in targets_on_air if target.distance > 0]
         # Update distance of targets on air
        for target in targets_on_air:
            target.update_distance(target.velocity * intercept_time) # Convert days to seconds

        if targets_on_air:
            print(f"Number of targets still on air at mission time {current_mission_time:.2f}: {len(targets_on_air)}")

    print("\nMission ended.")

if __name__ == '__main__':
    total_mission_duration = 5  # Simulate for 5 days
    simulated_barrages = threats.generate_barrage(total_mission_duration)
    print("Simulated Barrage History:")
    for time, type in simulated_barrages:
        print(f"Time: {time:.2f} days, Type: {type}")

    print("\nInitiating Interception Simulation:")
    process_barrages_intercept(simulated_barrages, total_mission_duration)