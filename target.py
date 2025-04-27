import math
ROCKET_SPEED_METERS_PER_SECOND = 750  # Speed of the rocket in meters per second
import numpy as np
import matplotlib.pyplot as plt
TIME_CONST = 1
class Target:
    def __init__(self, distance, velocity, target_type, interception_max_probabilities, laser_interception_timing_data=None):
        self.distance = distance
        self.velocity = velocity * TIME_CONST
        self.type = target_type
        self._interception_max_probabolities = interception_max_probabilities
        self._laser_interception_timing_data = laser_interception_timing_data
        self.amount_of_attemps_to_intercept = 0
        
    def get_interception_probability(self, interceptor):
        return self._interception_probabolities[interceptor]
    
    def update_distance(self, dt):
        self.distance -= self.velocity * dt / 3600
        if self.distance < 0:
            raise ValueError("Distance cannot be negative.")

    def get_arrival_time(self):
        if self.velocity == 0:
            return float('inf')
        return self.distance / self.velocity * 3600

    @staticmethod
    def linear_interpolate(key, data_dict):
        if len(data_dict) < 2:
            return None

        sorted_keys = sorted(data_dict.keys())
        values = [data_dict[k] for k in sorted_keys]

        if key <= sorted_keys[0]:
            # Linear extrapolation below the lowest key
            x1, y1 = sorted_keys[0], values[0]
            x2, y2 = sorted_keys[1], values[1]
            slope = (y2 - y1) / (x2 - x1)
            return y1 + slope * (key - x1)
        elif key >= sorted_keys[-1]:
            # Linear extrapolation above the highest key
            x1, y1 = sorted_keys[-2], values[-2]
            x2, y2 = sorted_keys[-1], values[-1]
            slope = (y2 - y1) / (x2 - x1)
            return y2 + slope * (key - x2)
        else:
            # Linear interpolation within the key range
            lower_key = None
            upper_key = None
            for i in range(len(sorted_keys) - 1):
                if sorted_keys[i] <= key <= sorted_keys[i + 1]:
                    lower_key = sorted_keys[i]
                    upper_key = sorted_keys[i + 1]
                    break

            if lower_key is not None and upper_key is not None:
                lower_value = data_dict[lower_key]
                upper_value = data_dict[upper_key]
                return lower_value + (key - lower_key) * (upper_value - lower_value) / (upper_key - lower_key)
            else:
                # This should ideally not be reached given the previous checks
                return None

    def get_dome_interception(self): 
        interception_timing_data = {5 : 7, 10 : 12}
        linear_interploated_time = self.linear_interpolate(self.distance, interception_timing_data)
        return linear_interploated_time / TIME_CONST
    
    def get_balistic_interception(self):
        interception_timing_data = {10 : 15, 20 : 25} # to be checked with Shaked
        linear_interploated_time = self.linear_interpolate(self.distance, interception_timing_data)
        return linear_interploated_time / TIME_CONST
    
    def get_max_fire_time(self):
        return Target.linear_interpolate(self.distance, self._laser_interception_timing_data) / TIME_CONST if self.distance > 2 else 2

    def get_optimized_laser_firing_time(self, plot=False):
        if self._laser_interception_timing_data is None:
            return None
        
        # If the firing time is not in the dictionary, use linear interpolation
        max_firing_time = self.get_max_fire_time()
        a = self._interception_max_probabolities["beam"]
        p = 0.95 # fraction of a achieved at max firing time
        d = max_firing_time
        times = np.linspace(0.01, 1.5 * d, 300)
        
        probability_of_interception_by_time = a / (1 + np.exp((1 / d) * np.log(1 / p - 1) * (2 * times - d))) - a * (1 - p)

        # Calculate the best interception time - by the ratio of probability to time
        ratio_of_interception_by_time = probability_of_interception_by_time / times
        optimized_index = np.argmax(ratio_of_interception_by_time)
        optimized_firing_time = times[optimized_index]
        max_ratio_of_interception_by_time = ratio_of_interception_by_time[optimized_index]
        probability_of_interception = probability_of_interception_by_time[optimized_index]

        if self.amount_of_attemps_to_intercept == 1:
            a / (1 + np.exp((1 / d) * np.log(1 / p - 1) * (2 * (times - optimized_firing_time) - d))) - a * (1 - p)
            optimized_firing_time = times[optimized_index]
            max_ratio_of_interception_by_time = ratio_of_interception_by_time[optimized_index]
            probability_of_interception = probability_of_interception_by_time[optimized_index]

        # Plotting the results
        if plot:
            plt.figure(figsize=(10, 6))
            plt.plot(times, probability_of_interception_by_time, label=self.type)
            plt.plot(times, probability_of_interception_by_time / times, label=self.type + " ratio")
            plt.title(f"Distance = {self.distance:.2f} | Velcocity = {self.velocity:.2f}")
            plt.show()

        return optimized_firing_time / TIME_CONST, probability_of_interception, max_ratio_of_interception_by_time
    
    def get_dome_attempts(self): 
        """calculates the amount of attempts to intercept the target with beam"""
        if self.type == "drone":
            if self.distance < 0.5:
                return 0
            arrival_time_to_range_limit = (self.distance - 0.5) / self.velocity * 3600
        if self.type == "anti-ship":
            if self.distance < 4:
                return 0
            arrival_time_to_range_limit = (self.distance - 4) / self.velocity * 3600       
        if arrival_time_to_range_limit is None:
            print(self.type)
        return arrival_time_to_range_limit / self.get_beam_interception_time()            
        
    def get_laser_attempts(self):
        return self.get_arrival_time() / self.get_max_fire_time()

    def get_beam_interception_time(self):
        if self.type == "drone":
            if self.distance < 0.5:
                return 0
            arrival_time_of_target_to_range_limit = (self.distance - 0.5) / self.velocity * 3600
        if self.type == "anti-ship":
            if self.distance < 4:
                return 0
            arrival_time_of_target_to_range_limit = (self.distance - 4) / self.velocity * 3600
        arrival_time_of_interceptor_to_range_limit = (self.distance - 0.5) / ROCKET_SPEED_METERS_PER_SECOND / 1000 
        return arrival_time_of_target_to_range_limit/arrival_time_of_interceptor_to_range_limit
        
class Anti_Ship_Missile(Target):
    def __init__(self, distance=None, velocity=None):
        interception_max_probabolities = {"dome": 0.85, "beam" : 0.8, "LRAD": 0.8}
        laser_interception_timing_data = {12 : 12, 14 : 14} # distance [km] : time [s], the first one
                                                            # should be checked with Shaked
        if distance is None:
            distance = np.random.normal(15, 1)
        if velocity is None:
            if np.random.random() < 0.5:
                velocity = np.random.normal(2000, 50)  
            else:
                velocity = np.random.normal(800, 30) 
        super().__init__(distance, velocity, "anti-ship", interception_max_probabolities, laser_interception_timing_data)

class Drone(Target):
    def __init__(self, distance=None, velocity=None):
        interception_max_probabolities = {"dome": 0.8, "beam" : 0.9, "LRAD": 0}
        laser_interception_timing_data = {3 : 4, 6 : 6, 14 : 9} # distance [km] : time [s]
        if distance is None:
            distance = np.random.normal(10, 2)
        if velocity is None:
            velocity = np.random.normal(180, 5)
        super().__init__(distance, velocity, "drone", interception_max_probabolities, laser_interception_timing_data)

class Ballistic_Missile(Target):
    def __init__(self, distance=None, velocity=None):
        interception_max_probabolities = {"dome": 0.9, "beam" : 0, "LRAD": 0}
        laser_interception_timing_data = None
        if distance is None:
            distance = np.random.normal(20, 3) # to be checked with Shaked
        if velocity is None:
            velocity = np.random.normal(3000, 100) # to be checked with Shaked
        super().__init__(distance, velocity, "balistic", interception_max_probabolities, laser_interception_timing_data)
        