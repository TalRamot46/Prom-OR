import pygame
import random
import time
import math
from typing import Self
from target import Target, Anti_Ship_Missile, Drone, Ballistic_Missile, TIME_CONST, ROCKET_SPEED_METERS_PER_SECOND
import barrage  # Import barrage functions
from ship import Ship  # Import the Ship class
import json
import matplotlib.pyplot as plt

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
TARGET_SPAWN_RATE = 0.5 * TIME_CONST
PIXLES_PER_KM = 20
LASER_WIDTH = 3
ROCKET_WIDTH = 3  # Changed to 3 for the new rocket shape
EXPLOSION_COLOR = (255, 255, 0)
EXPLOSION_DURATION = 0.5 / TIME_CONST
ROCKET_SPEED_PIXELS = ROCKET_SPEED_METERS_PER_SECOND / 1000 * 20 * TIME_CONST # Pixels per second, reduced for visual effect
ROCKET_ACCELERATION = 10  # Added rocket acceleration
ROCKET_LAUNCH_DELAY = 1 / TIME_CONST # Add a 5-second delay between rocket launches
ROCKET_LENGTH = 10  # new rocket length
MAX_ROCKETS_PER_LAUNCH = 2  # Allow launching a pair of rockets
GAME_OVER_REASON_TIME = 0
GAME_OVER_REASON_SHIP_HIT = 1
GAME_OVER_REASON_NO_TARGETS = 2
LASER_COOLDOWN = 1 / TIME_CONST  # Add a cooldown for the laser
LASER_COOLDOWN_NO_FIRE = 0.5 / TIME_CONST  # Cooldown time for the laser when not firing


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
            self.x = CENTER_X + distance * math.cos(self.angle) * PIXLES_PER_KM
            self.y = CENTER_Y + distance * math.sin(self.angle) * PIXLES_PER_KM

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

    def compare_target_dome_attempts(self, target_symbol: TargetSymbol):
        return target_symbol.get_target().get_dome_attempts()

    class InterceptorSymbol:
        def __init__(self, start_x, start_y, target_symbol):
            self.x = start_x
            self.y = start_y
            self.target_x = target_symbol.x
            self.target_y = target_symbol.y
            self.target_symbol = target_symbol  # Store the target
            self.speed_x = 0
            self.speed_y = 0
            self.speed = ROCKET_SPEED_PIXELS
            self.angle = math.atan2(target_symbol.y - start_y, target_symbol.x - start_x)  # calculate initial angle
            self.has_collided = False

        def get_target_symbol(self):
            return self.target_symbol

        def update_position(self, dt):
            if self.has_collided:
                return  # Stop updating position after collision
            self.x += self.speed * math.cos(self.angle) * dt
            self.y += self.speed * math.sin(self.angle) * dt

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
        self.game_over = False
        self.quick_switch_flag = False
        self.ship = self.ShipSymbol(CENTER_X, CENTER_Y)
        self.font = pygame.font.Font(None, 30)
        self.running = True
        self.laser_interception_count = 0
        self.start_time = time.time()
        self.intercepted_target_symbol = None
        self.laser_beam_active = False
        self.laser_start_point = (0, 0)
        self.laser_end_point = (0, 0)
        self.laser_end_time = 0
        self.total_mission_duration = 80  # Total mission duration in days
        self.simulated_barrages = barrage.generate_barrage(self.total_mission_duration)
        self.current_mission_time = 0
        self.explosion_time = 0
        self.ship_instance = Ship(1)
        self.target_symbols = []
        self.explosion_coords = None  # Store explosion coordinates
        self.interceptors = []  # List to store active rockets
        self.last_rocket_launch_time = 0  # Store the time of the last rocket launch
        self.target_symbols_launched_interceptors_at = []  # use this list to store rockets to be launched
        self.interceptor_count = 0  # Initialize the rocket counter
        self.laser_cooldown_time = 0
        self.interception_result = None

    def draw_laser_line(self, start_x, start_y, end_x, end_y, width=LASER_WIDTH):
        pygame.draw.line(self.screen, LASER_COLOR, (start_x, start_y), (end_x, end_y), width)

    def draw_rocket(self, start_x, start_y, end_x, end_y, width=ROCKET_WIDTH):
        pygame.draw.line(self.screen, ROCKET_COLOR, (start_x, start_y), (end_x, end_y), width)

    def intercept_with_laser(self, target_to_intercept: TargetSymbol):
        duration, self.interception_result = target_to_intercept.get_target().get_optimized_laser_firing_time()
        self.laser_beam_active = True
        ship_x, ship_y = self.ship.get_position()
        self.laser_start_point = (int(ship_x), int(ship_y))
        self.laser_end_point = (int(target_to_intercept.x), int(target_to_intercept.y))
        self.laser_end_time = time.time() + duration
        self.intercepted_target_symbol = target_to_intercept


    def draw_explosion(self, x, y):
        radius = int((time.time() - self.explosion_time) * 30)
        if radius < 30:
            pygame.draw.circle(self.screen, EXPLOSION_COLOR, (int(x), int(y)), radius)

    def generate_targets(self, num_targets):
        # Spawn new targets based on barrage, using barrage.py
        barrage_index = 0
        if barrage_index < len(self.simulated_barrages):
            barrage_time, barrage_type = self.simulated_barrages[barrage_index]
            if self.current_mission_time >= barrage_time:
                new_targets = barrage.generate_targets_by_barrage(barrage_type, num_targets)
                self.target_symbols.extend([self.TargetSymbol(target) for target in new_targets])
                barrage_index += 1

    def update_targets(self, dt):
        # Update target positions
        for target_symbol in self.target_symbols:
            if not target_symbol.update_distance(dt):
                pygame.quit()
                return

        if not self.target_symbols:
            self.game_over = True
            self.game_over_reason = GAME_OVER_REASON_NO_TARGETS

        # Remove targets that go out of bounds
        self.target_symbols = [target_symbol for target_symbol in self.target_symbols
                                if not target_symbol.is_out_of_bounds()]

    def intercept_with_laser_preferred_target(self):
        best_target_index = self.ship_instance.choose_target([target_symbol.get_target() for target_symbol in self.target_symbols if \
                                                                target_symbol not in self.target_symbols_launched_interceptors_at])
        if best_target_index is not None:
            target_to_intercept = self.target_symbols[best_target_index]
            self.intercept_with_laser(target_to_intercept)  # call intercept target
        else:
            pass

    def launch_dome(self):
        # Launch up to MAX_ROCKETS_PER_LAUNCH at a time, if available
        if self.target_symbols:
            if self.last_rocket_launch_time == 0 or time.time() - self.last_rocket_launch_time >= ROCKET_LAUNCH_DELAY:
                ship_x, ship_y = self.ship.get_position()
                num_rockets_launched = 0
                # Sort targets by distance, closest first

                target_symbols_sorted_by_dome_attempts: list["Simulation.TargetSymbol"] = []
                for ts in self.target_symbols:
                    if ts.get_target().get_laser_attempts() < 1 or ts.get_target().get_dome_attempts() < 2:
                        target_symbols_sorted_by_dome_attempts.append(ts)
                target_symbols_sorted_by_dome_attempts = sorted(target_symbols_sorted_by_dome_attempts, key=self.compare_target_dome_attempts)
                if target_symbols_sorted_by_dome_attempts:
                    for target_symbol in target_symbols_sorted_by_dome_attempts:
                        if num_rockets_launched < MAX_ROCKETS_PER_LAUNCH:
                            self.target_symbols_launched_interceptors_at.append(target_symbol)
                            num_rockets_launched += 1
                    if num_rockets_launched > 0:
                        self.last_rocket_launch_time = time.time()
                        for target_symbol in self.target_symbols_launched_interceptors_at:
                            if target_symbol is self.intercepted_target_symbol:
                                self.laser_beam_active = False
                                self.quick_switch_flag = True
                                self.laser_cooldown_time = time.time()
                            already_spawned_interceptor = False
                            for interceptor in self.interceptors:
                                if interceptor.get_target_symbol() is target_symbol:
                                    already_spawned_interceptor = True
                                    break
                            if already_spawned_interceptor:
                                continue
                            self.interceptors.append(self.InterceptorSymbol(ship_x, ship_y, target_symbol))

    def update_interceptor_positions(self, dt):
        # Update rocket positions
        for interceptor in self.interceptors:
            interceptor.update_position(dt)

        # Check for rocket collisions
        for interceptor in list(self.interceptors):  # Iterate over a copy to allow removal
            if interceptor.has_collided:
                # remove the laser if the rocket has already collided
                self.interceptors.remove(interceptor)
                continue
            elif interceptor.get_target_symbol() not in self.target_symbols:
                self.interceptors.remove(interceptor)
                continue
            for target_symbol in list(self.target_symbols):
                if interceptor.check_collision(target_symbol):
                    self.explosion_time = time.time()
                    self.explosion_coords = (interceptor.x, interceptor.y)  # Use rocket's position
                    interceptor.has_collided = True  # set the flag
                    self.interceptor_count += 1  # Increment the rocket counter
                    self.interceptors.remove(interceptor)
                    self.target_symbols.remove(target_symbol)  # Remove the hit target
                    if target_symbol is self.intercepted_target_symbol:
                        self.laser_beam_active = False
                        self.quick_switch_flag = True
                        self.laser_cooldown_time = time.time()
                    break  # Exit inner loop to avoid modifying the list while iterating
            # Check for game over condition: Ship hit by target
            for target_symbol in list(self.target_symbols):
                if math.sqrt((self.ship.x - target_symbol.x) ** 2 + (self.ship.y - target_symbol.y) ** 2) < TARGET_SIZE:
                    self.game_over = True
                    self.game_over_reason = GAME_OVER_REASON_SHIP_HIT
                    self.running = False
                    break

    def drawing_screen(self, dt):
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

        # Draw rockets
        for interceptor in self.interceptors:
            interceptor.draw(self.screen)

        # Draw explosion
        if self.explosion_time > 0 and self.explosion_coords:
            if time.time() - self.explosion_time < EXPLOSION_DURATION:
                self.draw_explosion(self.explosion_coords[0], self.explosion_coords[1])
            else:
                self.explosion_time = 0
                self.explosion_coords = None  # Reset coords
        elif self.explosion_time > 0 and not self.explosion_coords:
            self.explosion_time = 0

        # Draw laser beam
        if self.laser_beam_active and time.time() < self.laser_end_time and self.intercepted_target_symbol:
            ship_x, ship_y = self.ship.get_position()
            target_x, target_y = self.intercepted_target_symbol.x, self.intercepted_target_symbol.y
            self.draw_laser_line(int(ship_x), int(ship_y), int(target_x), int(target_y))

        # Display timer
        timer_text = self.font.render(f"Time: {self.current_mission_time:.2f} s", True, FONT_COLOR)
        self.screen.blit(timer_text, (10, 10))

        # Display interception count
        count_text = self.font.render(f"Beam interceptions: {self.laser_interception_count}", True, FONT_COLOR)
        self.screen.blit(count_text, (10, 40))

        # Display rocket count
        rocket_count_text = self.font.render(f"Dome interceptions: {self.interceptor_count}", True, FONT_COLOR)
        self.screen.blit(rocket_count_text, (10, 70))  # Display below other text

        pygame.display.flip()

    def check_game_over(self):
        if self.game_over:
            self.screen.fill(BACKGROUND_COLOR)
            if self.game_over_reason == GAME_OVER_REASON_TIME:
                reason_text = self.font.render("Mission Time Elapsed", True, FONT_COLOR)
            elif self.game_over_reason == GAME_OVER_REASON_SHIP_HIT:
                reason_text = self.font.render("Ship Hit by Target", True, FONT_COLOR)
            elif self.game_over_reason == GAME_OVER_REASON_NO_TARGETS:
                reason_text = self.font.render("No Targets Left", True, FONT_COLOR)
            else:
                reason_text = self.font.render("Game Over", True, FONT_COLOR)

            self.screen.blit(reason_text, (CENTER_X - 100, CENTER_Y - 20))
            pygame.display.flip()
            # time.sleep(2)  # Keep the message displayed for 5 seconds

    def handle_laser_interception(self):
        if time.time() > self.laser_end_time and self.laser_beam_active:
            if self.interception_result:
                self.laser_interception_count += 1
                self.explosion_time = time.time()
                self.explosion_coords = (self.intercepted_target_symbol.x, self.intercepted_target_symbol.y)
                self.target_symbols.remove(self.intercepted_target_symbol)
            self.quick_switch_flag = False
            self.laser_cooldown_time = time.time()
            self.laser_beam_active = False

    def run(self, num_targets):
        dt = 0
        self.generate_targets(num_targets)

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

            self.update_targets(dt)

            if self.target_symbols and \
                (self.laser_cooldown_time == 0 or (time.time() - self.laser_cooldown_time >= LASER_COOLDOWN and not self.quick_switch_flag) \
                 or (time.time() - self.laser_cooldown_time >= LASER_COOLDOWN_NO_FIRE and self.quick_switch_flag)) and \
                not self.laser_beam_active:
                self.intercept_with_laser_preferred_target()
            self.handle_laser_interception()

            self.launch_dome()
            self.update_interceptor_positions(dt)
            self.drawing_screen(dt)
            self.check_game_over()

        pygame.quit()
        return self.interceptor_count, self.laser_interception_count


if __name__ == "__main__":
    results = {}
    simulation = Simulation()
    simulation.run(20)
    """
    # Step 1: Run simulations and collect raw data
    for num_targets in range(20, 0, -1):
        lst = []
        for repetitions in range(10):
            simulation = Simulation()
            lst.append(simulation.run(num_targets))
        results[num_targets] = lst

    # Save raw results
    with open('result.json', 'w') as json_file:
        json.dump(results, json_file, indent=4)

    # Step 2: Calculate averages
    averages = {}

    for num_targets, successes in results.items():
        total_rockets = sum([item[0] for item in successes])
        avg_rockets = total_rockets / len(successes) if successes else 0

        total_lasers = sum([item[1] for item in successes])
        avg_lasers = total_lasers / len(successes) if successes else 0

        averages[int(num_targets)] = {'avg_rockets': avg_rockets, 'avg_lasers': avg_lasers}

    # Save averages
    with open('averages.json', 'w') as file:
        json.dump(averages, file, indent=4)

    # Step 3: Plot the graph
    sorted_targets = sorted(averages.keys(), key=lambda x: int(x))
    avg_rocket_successes = [averages[k]['avg_rockets'] for k in sorted_targets]
    avg_laser_successes = [averages[k]['avg_lasers'] for k in sorted_targets]

    plt.figure(figsize=(12, 7))
    plt.plot(sorted_targets, avg_rocket_successes, marker='o', label='Average Dome Interceptions')
    plt.plot(sorted_targets, avg_laser_successes, marker='x', label='Average Beam Interceptions')
    plt.title('Interception Success vs Number of Initial Targets')
    plt.xlabel('Number of Initial Targets')
    plt.ylabel('Average Interceptions')
    plt.grid(True)
    plt.gca().invert_xaxis()  # Optional: Higher target counts on the left
    plt.legend()
    plt.show()
    """