import math
import numpy as np

class Target:
    """
    Represents a target being shot at by a warship.
    """
    def __init__(self, distance, velocity, target_type):
        """
        Initializes a Target object.

        Args:
            distance (float): The initial distance from the ship to the target.
            velocity (float): The constant velocity of the target.
            target_type (str): The type of the target (e.g., missile, drone, aircraft).
        """
        self.distance = distance
        self.velocity = velocity
        self.type = target_type
        self._interception_pdfs = {
            "missile": {"mean": 5, "std": 2, "max_interception_rate": 0.8},
            "drone": {"mean": 10, "std": 3, "max_interception_rate": 0.9},
            "aircraft": {"mean": 15, "std": 4, "max_interception_rate": 0.95},
        }
        
    def update_distance(self, dt):
        """
        Updates the distance of the target based on its velocity and the time elapsed.

        Args:
            dt (float): The time elapsed since the last update.
        """
        self.distance -= self.velocity * dt

    def get_arrival_time(self):
        """
        Calculates the estimated time of arrival of the target to the ship.

        Returns:
            float: The estimated time of arrival. Returns infinity if velocity is zero.
        """
        if self.velocity == 0:
            return float('inf')
        return self.distance / self.velocity

    def _gaussian_pdf(self, x, mean, std):
        """
        Calculates the probability density function of a Gaussian distribution.

        Args:
            x (float): The value at which to evaluate the PDF.
            mean (float): The mean of the Gaussian distribution.
            std (float): The standard deviation of the Gaussian distribution.

        Returns:
            float: The probability density at the given value.
        """
        exponent = -((x - mean) ** 2) / (2 * std ** 2)
        return (1 / (std * math.sqrt(2 * math.pi))) * math.exp(exponent)


    def get_best_laser_interception(self, a=None):
        """
        Calculates the optimal time to continuously laser the target for maximum
        probability of interception per unit time.

        Args:
            a (float, optional): The maximum rate of successful interception.
                                 Defaults to the class's max_interception_rate.

        Returns:
            tuple: A tuple containing the optimal time to laser and the
                   corresponding CDF(time) / time value. Returns (None, 0) if
                   the target type is not recognized.
        """
        pdf_params = self._interception_pdfs[self.type]
        mean = pdf_params["mean"]
        std = pdf_params["std"]
        max_rate = a if a is not None else self.max_interception_rate

        times = np.linspace(0.01, 30, 300)  # Avoid division by zero
        cdf_values = np.clip([self._gaussian_cdf(t, mean, std) for t in times], 0, max_rate)
        ratios = cdf_values / times

        if not ratios.any():  # Handle the case where all ratios are zero
            return None, 0

        best_index = np.argmax(ratios)
        best_time = times[best_index]
        best_ratio = ratios[best_index]
        best_probability = cdf_values[best_index]

        return best_time, best_probability, best_ratio
