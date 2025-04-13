import pygame
import random
import time
import threading
import queue
import math
import numpy as np
from target import Target, Anti_Ship_Missile, Drone, Ballistic_Missile
import barrage  # Import barrage functions
from ship import Ship  # Import the Ship class


# --- Constants ---
SCREEN_WIDTH = 800
CENTER_X = SCREEN_WIDTH // 2
SCREEN_HEIGHT = 600
CENTER_Y = SCREEN_HEIGHT // 2
BACKGROUND_COLOR = (0, 0, 30)
SHIP_COLOR = (0, 255, 0)
LASER_COLOR = (255, 0, 0)
ROCKET_COLOR = (0, 255, 255)  # Cyan for rockets
SHIP_SIZE = 30
TARGET_SIZE = 10
FONT_COLOR = (255, 255, 255)
MAX_TARGETS = 10
TARGET_SPAWN_RATE = 0.5
PIXLES_TO_KM = 20
LASER_WIDTH = 3
ROCKET_WIDTH = 3  # Changed to 3 for the new rocket shape
EXPLOSION_COLOR = (255, 255, 0)
EXPLOSION_DURATION = 0.5
ROCKET_SPEED = 200  # Pixels per second, reduced for visual effect
ROCKET_ACCELERATION = 10  # Added rocket acceleration
ROCKET_LAUNCH_DELAY = 5  # Add a 5-second delay between rocket launches
ROCKET_LENGTH = 10  # new rocket length
MAX_ROCKETS_PER_LAUNCH = 2  # Allow launching a pair of rockets
GAME_OVER_REASON_TIME = 0
GAME_OVER_REASON_SHIP_HIT = 1
LASER_COOLDOWN = 0.5  # Add a cooldown for the laser


class Simulation:
    class ShipSymbol:
        def __init__(self, x=None, y=None):
            self.x = x
            self.y = y
            self.angle = 0  # facing upwards
            self.size = SHIP_SIZE

        def draw(self, screen):
            # A simple triangle shape for the ship
            points = [
                (self.x, self.y - self.size),  # Top point
                (self.x + self.size * 0.5, self.y + self.size * 0.5),  # Bottom-right
                (self.x - self.size * 0.5, self.y + self.size * 0.5)  # Bottom-left
            ]
            pygame.draw.polygon(screen, SHIP_COLOR, points)

        def get_position(self):
            return self.x, self.y

    class TargetSymbol:
        def __init__(self, target: Target):
            self.target = target
            self.set_xy(target.distance)
            self.size = TARGET_SIZE

        def draw(self, screen, color):
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size)

        def set_xy(self, distance):
            if not hasattr(self, 'angle'):
                self.angle = random.uniform(0, 2 * math.pi)
            self.x = CENTER_X + distance * math.cos(self.angle) * PIXLES_TO_KM
            self.y = CENTER_Y + distance * math.sin(self.angle) * PIXLES_TO_KM

        def update_distance(self, dt):
            try:
                self.target.update_distance(dt)
            except ValueError:
                return False
            self.set_xy(self.target.distance)
            return True

        def is_out_of_bounds(self):
            return self.target.distance <= 0

        def get_target(self):
            return self.target

    def compare_target_distance(self, target_symbol):
        return target_symbol.get_target().distance

    def compare_target_laser_constants(self, target_symbol):
        return target_symbol.get_target().get_laser_constant()

    class RocketSymbol:
        def __init__(self, start_x, start_y, target_symbol):
            self.x = start_x
            self.y = start_y
            self.target_x = target_symbol.x
            self.target_y = target_symbol.y
            self.target_symbol = target_symbol  # Store the target
            self.speed_x = 0
            self.speed_y = 0
            self.acceleration = ROCKET_ACCELERATION
            self.speed = ROCKET_SPEED
            self.traveled_distance = 0
            self.angle = math.atan2(target_symbol.y - start_y, target_symbol.x - start_x)  # calculate initial angle
            self.has_collided = False

        def update_velocity(self, dt):
            if self.has_collided:
                return  # Stop updating velocity after collision

            # Calculate the direction vector towards the target
            direction_x = self.target_x - self.x
            direction_y = self.target_y - self.y
            # Calculate the distance to the target
            distance_to_target = math.sqrt(direction_x ** 2 + direction_y ** 2)

            if distance_to_target > 0:
                # Normalize the direction vector
                direction_x /= distance_to_target
                direction_y /= distance_to_target

                # Update speed using acceleration
                self.speed_x += direction_x * self.acceleration * dt
                self.speed_y += direction_y * self.acceleration * dt
                # Cap the speed
                self.speed = math.sqrt(self.speed_x ** 2 + self.speed_y ** 2)
                if self.speed > ROCKET_SPEED:
                    self.speed_x = self.speed_x / self.speed * ROCKET_SPEED
                    self.speed_y = self.speed_y / self.speed * ROCKET_SPEED
            self.angle = math.atan2(self.speed_y, self.speed_x)

        def update_position(self, dt):
            if self.has_collided:
                return  # Stop updating position after collision
            self.update_velocity(dt)
            self.x += self.speed_x * dt
            self.y += self.speed_y * dt
            self.traveled_distance += self.speed * dt

        def draw(self, screen):
            # Draw a small triangle for the rocket
            tip_x = self.x + ROCKET_LENGTH * math.cos(self.angle)
            tip_y = self.y + ROCKET_LENGTH * math.sin(self.angle)
            points = [
                (int(tip_x), int(tip_y)),  # Tip of the rocket
                (int(self.x + ROCKET_WIDTH * math.cos(self.angle + math.pi / 2)),
                 int(self.y + ROCKET_WIDTH * math.sin(self.angle + math.pi / 2))),
                (int(self.x), int(self.y)),
                (int(self.x + ROCKET_WIDTH * math.cos(self.angle - math.pi / 2)),
                 int(self.y + ROCKET_WIDTH * math.sin(self.angle - math.pi / 2))),
            ]
            pygame.draw.polygon(screen, ROCKET_COLOR, points)

        def check_collision(self, target_symbol):
            if self.has_collided:
                return False
            distance = math.sqrt((self.x - target_symbol.x) ** 2 + (self.y - target_symbol.y) ** 2)
            return distance <= target_symbol.size

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Ship Interception Simulation")
        self.clock = pygame.time.Clock()
        self.ship = self.ShipSymbol(CENTER_X, CENTER_Y)
        self.font = pygame.font.Font(None, 30)
        self.running = True
        self.interception_count = 0
        self.start_time = time.time()
        self.interception_in_progress = False
        self.intercepted_target_symbol = None
        self.result_queue = queue.Queue()
        self.total_mission_duration = 200  # Total mission duration in days
        self.simulated_barrages = barrage.generate_barrage(self.total_mission_duration)
        self.barrage_index = 0
        self.current_mission_time = 0
        self.explosion_time = 0
        self.ship_instance = Ship(1)
        self.target_symbols = []
        self.interception_count = 0
        self.explosion_coords = None  # Store explosion coordinates
        self.rockets = []  # List to store active rockets
        self.last_rocket_launch_time = 0  # Store the time of the last rocket launch
        self.rockets_to_launch = []  # use this list to store rockets to be launched
        self.rocket_count = 0  # Initialize the rocket counter
        self.laser_start_time = 0
        self.laser_duration_extension = 0.2  # Extend laser duration by 200ms
        self.game_over = False
        self.game_over_reason = -1  # -1 for not over, 0 for time, 1 for ship hit
        self.laser_cooldown_time = 0
        self.interception_end_time = None
        self.interception_result = None

    def draw_laser(self, start_x, start_y, end_x, end_y, width=LASER_WIDTH):
        pygame.draw.line(self.screen, LASER_COLOR, (start_x, start_y), (end_x, end_y), width)

    def draw_rocket(self, start_x, start_y, end_x, end_y, width=ROCKET_WIDTH):
        pygame.draw.line(self.screen, ROCKET_COLOR, (start_x, start_y), (end_x, end_y), width)

    def intercept_target(self, target_symbol):
        self.interception_in_progress = True
        self.intercepted_target_symbol = target_symbol
        intercepted_target = target_symbol.get_target()
        self.laser_start_time = time.time()  # Store the start time of the laser
        threading.Thread(target=self.ship_instance.intercept_with_laser,
                         args=(intercepted_target, self.result_queue)).start()
        self.interception_end_time = None  # Store the end time here
        self.interception_result = None  # Store the result here

    def handle_interception_result(self):
        try:
            result_list = self.result_queue.get_nowait()
            self.interception_result = result_list[0]
            interception_duration = result_list[1]
            self.interception_end_time = time.time() + interception_duration  # Calculate end time
            self.interception_in_progress = False
            self.intercepted_target_symbol = None
        except queue.Empty:
            pass

    def draw_explosion(self, x, y):
        radius = int((time.time() - self.explosion_time) * 30)
        if radius < 30:
            pygame.draw.circle(self.screen, EXPLOSION_COLOR, (int(x), int(y)), radius)

    def run(self):
        last_target_spawn_time = self.start_time
        dt = 0

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.current_mission_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            if self.current_mission_time >= self.total_mission_duration:
                self.game_over = True
                self.game_over_reason = GAME_OVER_REASON_TIME

            if self.game_over:
                self.running = False
                continue

            # Spawn new targets based on barrage, using barrage.py
            if self.barrage_index < len(self.simulated_barrages):
                barrage_time_in_days, barrage_type = self.simulated_barrages[self.barrage_index]
                barrage_time_in_seconds = barrage_time_in_days
                if self.current_mission_time >= barrage_time_in_seconds:
                    new_targets = barrage.generate_targets_by_barrage(barrage_type)
                    self.target_symbols.extend([self.TargetSymbol(target) for target in new_targets])
                    print(
                        f"Barrage of type {barrage_type} detected at mission time: {barrage_time_in_days:.2f} days.  {len(new_targets)} new targets spawned.")
                    self.barrage_index += 1

            # Update target positions
            for target_symbol in self.target_symbols:
                if not target_symbol.update_distance(dt):
                    pygame.quit()
                    return

            # Remove targets that go out of bounds
            self.target_symbols = [target_symbol for target_symbol in self.target_symbols
                                    if not target_symbol.is_out_of_bounds()]

            # Choose and intercept target using ship.py
            if not self.interception_in_progress and self.target_symbols:
                best_target_index = self.ship_instance.choose_target(
                    [target_symbol.get_target() for target_symbol in self.target_symbols])
                if best_target_index is not None:
                    target_to_intercept = self.target_symbols[best_target_index]
                    # Check if the laser is off cooldown
                    if time.time() - self.laser_cooldown_time >= LASER_COOLDOWN:
                        self.intercept_target(target_to_intercept)  # call intercept target
                        print(
                            f"Attempting to intercept target {target_to_intercept.get_target().type} in distance {target_to_intercept.get_target().distance}.")
                    else:
                        print("Laser on cooldown")

            # Launch up to MAX_ROCKETS_PER_LAUNCH at a time, if available
            if self.target_symbols:
                current_time = time.time()
                if self.last_rocket_launch_time == 0 or current_time - self.last_rocket_launch_time >= ROCKET_LAUNCH_DELAY:
                    ship_x, ship_y = self.ship.get_position()
                    num_rockets_launched = 0
                    # Sort targets by distance, closest first
                    sorted_target_symbols = filter(lambda ts: ts.get_target().get_laser_constant() < 2 and \
                                                   ts is not self.intercepted_target_symbol,
                                                    self.target_symbols)
                    sorted_target_symbols = sorted(self.target_symbols, key=self.compare_target_laser_constants)
                    if sorted_target_symbols:
                        for target_symbol in sorted_target_symbols:
                            if num_rockets_launched < MAX_ROCKETS_PER_LAUNCH:
                                self.rockets_to_launch.append(target_symbol)
                                num_rockets_launched += 1
                        if num_rockets_launched > 0:
                            self.last_rocket_launch_time = current_time
                            for target_symbol in self.rockets_to_launch:
                                self.rockets.append(self.RocketSymbol(ship_x, ship_y, target_symbol))
                                self.rocket_count += 1  # Increment the rocket counter
                                print(f"Rocket launched at target {target_symbol.get_target().type}!")
                            self.rockets_to_launch = []  # Clear the list after launching
                    else:
                        print("No targets available for launch")
            # Handle interception results
            self.handle_interception_result()

            # Check for interception completion and process result
            if self.interception_end_time and time.time() >= self.interception_end_time:
                if self.interception_result:
                    self.interception_count += 1
                    print("Target Intercepted!")
                    self.explosion_time = time.time()
                    self.explosion_coords = (
                        self.intercepted_target_symbol.x, self.intercepted_target_symbol.y)
                    if self.intercepted_target_symbol in self.target_symbols:
                        self.target_symbols.remove(self.intercepted_target_symbol)
                    self.laser_cooldown_time = time.time()  # Start cooldown
                else:
                    print("Interception Failed!")
                    self.laser_cooldown_time = time.time()
                self.interception_end_time = None  # Reset
                self.interception_result = None

            # Update rocket positions
            for rocket in self.rockets:
                rocket.update_position(dt)

            # Check for rocket collisions
            for rocket in list(self.rockets):  # Iterate over a copy to allow removal
                if rocket.has_collided:
                    # remove the laser if the rocket has already collided
                    self.rockets.remove(rocket)
                    continue
                for target_symbol in list(self.target_symbols):
                    if rocket.check_collision(target_symbol):
                        print("Rocket hit target!")
                        self.explosion_time = time.time()
                        self.explosion_coords = (rocket.x, rocket.y)  # Use rocket's position
                        rocket.has_collided = True  # set the flag
                        self.rockets.remove(rocket)
                        self.target_symbols.remove(target_symbol)  # Remove the hit target
                        break  # Exit inner loop to avoid modifying the list while iterating
                # Check for game over condition: Ship hit by target
                for target_symbol in list(self.target_symbols):
                    if math.sqrt((self.ship.x - target_symbol.x) ** 2 + (self.ship.y - target_symbol.y) ** 2) < TARGET_SIZE:
                        self.game_over = True
                        self.game_over_reason = GAME_OVER_REASON_SHIP_HIT
                        self.running = False
                        break
                if self.game_over:
                    break

                if rocket.traveled_distance > 2000:
                    self.rockets.remove(rocket)

            # Draw everything
            self.screen.fill(BACKGROUND_COLOR)

            self.ship.draw(self.screen)

            for target_symbol in self.target_symbols:
                # Get target color based on type
                if isinstance(target_symbol.get_target(), Anti_Ship_Missile):
                    target_color = (255, 0, 0)
                elif isinstance(target_symbol.get_target(), Drone):
                    target_color = (0, 255, 0)
                elif isinstance(target_symbol.get_target(), Ballistic_Missile):
                    target_color = (0, 0, 255)
                else:
                    target_color = (255, 255, 255)
                target_symbol.draw(self.screen, target_color)

            # Draw laser during interception
            if self.interception_in_progress and self.intercepted_target_symbol:
                ship_x, ship_y = self.ship.get_position()
                target_x, target_y = self.intercepted_target_symbol.x, self.intercepted_target_symbol.y
                self.draw_laser(ship_x, ship_y, int(target_x), int(target_y))

            # Draw rockets
            for rocket in self.rockets:
                rocket.draw(self.screen)

            # Draw explosion
            if self.explosion_time > 0 and self.explosion_coords:  # and explosion coords
                if time.time() - self.explosion_time < EXPLOSION_DURATION:
                    self.draw_explosion(self.explosion_coords[0], self.explosion_coords[1])
                else:
                    self.explosion_time = 0
                    self.explosion_coords = None  # Reset coords
            elif self.explosion_time > 0 and not self.explosion_coords:
                self.explosion_time = 0

            # Display timer
            timer_text = self.font.render(f"Time: {self.current_mission_time:.2f} s", True, FONT_COLOR)
            self.screen.blit(timer_text, (10, 10))

            # Display interception count
            count_text = self.font.render(f"Interceptions: {self.interception_count}", True, FONT_COLOR)
            self.screen.blit(count_text, (10, 40))

            # Display rocket count
            rocket_count_text = self.font.render(f"Rockets: {self.rocket_count}", True, FONT_COLOR)
            self.screen.blit(rocket_count_text, (10, 70))  # Display below other text

            pygame.display.flip()

        if self.game_over:
            self.screen.fill(BACKGROUND_COLOR)
            if self.game_over_reason == GAME_OVER_REASON_TIME:
                reason_text = self.font.render("Mission Time Elapsed", True, FONT_COLOR)
            elif self.game_over_reason == GAME_OVER_REASON_SHIP_HIT:
                reason_text = self.font.render("Ship Hit by Target", True, FONT_COLOR)
            else:
                reason_text = self.font.render("Game Over", True, FONT_COLOR)

            self.screen.blit(reason_text, (CENTER_X - 100, CENTER_Y - 20))
            pygame.display.flip()
            time.sleep(5)  # Keep the message displayed for 5 seconds

        pygame.quit()



if __name__ == "__main__":
    simulation = Simulation()
    try:
        simulation.run()
    except pygame.error as e:
        print("Target hit the ship!")
