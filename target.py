import math
import numpy as np
import matplotlib.pyplot as plt

class Target:
    def __init__(self, distance, velocity, target_type, interception_max_probabilities, laser_interception_timing_data=None):
        self.distance = distance
        self.velocity = velocity
        self.type = target_type
        self._interception_max_probabolities = interception_max_probabilities
        self._laser_interception_timing_data = laser_interception_timing_data

    def get_interception_probability(self, interceptor):
        return self._interception_probabolities[interceptor]
    
    def update_distance(self, dt):
        self.distance -= self.velocity / 3600 * dt
        if self.distance < 0:
            raise ValueError("Distance cannot be negative.")

    def get_arrival_time(self):
        if self.velocity == 0:
            return float('inf')
        return self.distance / self.velocity

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
        return linear_interploated_time
    
    def get_balistic_interception(self):
        interception_timing_data = {10 : 15, 20 : 25} # to be checked with Shaked
        linear_interploated_time = self.linear_interpolate(self.distance, interception_timing_data)
        return linear_interploated_time
    
    def get_max_fire_time(self):
        return Target.linear_interpolate(self.distance, self._laser_interception_timing_data) if self.distance > 2 else 2

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

        # Plotting the results
        if plot:
            plt.figure(figsize=(10, 6))
            plt.plot(times, probability_of_interception_by_time, label=self.type)
            plt.plot(times, probability_of_interception_by_time / times, label=self.type + " ratio")
            plt.title(f"Distance = {self.distance:.2f} | Velcocity = {self.velocity:.2f}")
            plt.show()

        return optimized_firing_time, probability_of_interception, max_ratio_of_interception_by_time
    
    def get_laser_constant(self): 
        return self.get_max_fire_time() / self.get_arrival_time()
    
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

