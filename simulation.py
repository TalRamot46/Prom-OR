import pygame
import random
import time
import math
from typing import Self
from target import Target, Anti_Ship_Missile, Drone, Ballistic_Missile, TIME_CONST, ROCKET_SPEED_METERS_PER_SECOND
import barrage  # Import barrage functions
import json
import numpy as np
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
PIXLES_PER_KM = 20
LASER_WIDTH = 3
ROCKET_WIDTH = 3  # Changed to 3 for the new rocket shape
EXPLOSION_COLOR = (255, 255, 0)
DOME_ATTEMPTS = 3
EXPLOSION_DURATION = 0.5 / TIME_CONST
ROCKET_LAUNCH_DELAY = 3 / TIME_CONST # Add a 5-second delay between rocket launches of the same target
ROCKET_LENGTH = 10  # new rocket length
MAX_ROCKETS_PER_LAUNCH = 3  # Allow launching a pair of rockets
GAME_OVER_REASON_TIME = 0
GAME_OVER_REASON_SHIP_HIT = 1
GAME_OVER_REASON_NO_TARGETS = 2
LONG_LASER_COOLDOWN = 3 / TIME_CONST  # Add a cooldown for the laser
SHORT_LASER_COOLDOWN = 2 / TIME_CONST  # Cooldown time for the laser when not firing


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
            self.z = 0
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
        return target_symbol.get_target().get_time_to_range_limit(ROCKET_SPEED_METERS_PER_SECOND)

    class InterceptorSymbol:
        def __init__(self, start_x, start_y, target_symbol, velocity, double=False):
            self.x = start_x
            self.y = start_y
            self.target_x = target_symbol.x
            self.target_y = target_symbol.y
            self.target_symbol = target_symbol  # Store the target
            self.velocity = PIXLES_PER_KM * velocity / 1000
            self.angle = math.atan2(target_symbol.y - start_y, target_symbol.x - start_x)  # calculate initial angle
            self.double = double

        def get_target_symbol(self):
            return self.target_symbol

        def update_position(self, dt):
            self.x += self.velocity * math.cos(self.angle) * dt
            self.y += self.velocity * math.sin(self.angle) * dt
            math.sin(self.angle) * dt

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
        self.target_symbols = []
        self.explosion_coords = None  # Store explosion coordinates
        self.interceptors: list["Self.InterceptorSymbol"] = []  # List to store active rockets
        self.last_rocket_launch_time = 0  # Store the time of the last rocket launch
        self.target_symbols_launched_interceptors_at = []  # use this list to store rockets to be launched
        self.interceptor_count = 0  # Initialize the rocket counter
        self.laser_cooldown_time = 0
        self.interception_result = None

    def draw_laser_line(self, start_x, start_y, end_x, end_y, width=LASER_WIDTH):
        pygame.draw.line(self.screen, LASER_COLOR, (start_x, start_y), (end_x, end_y), width)


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
        self.target_symbols = [target_symbol for target_symbol in self.target_symbols]

                    # Check for game over condition: Ship hit by target
        for target_symbol in list(self.target_symbols):
            if math.sqrt((self.ship.x - target_symbol.x) ** 2 + (self.ship.y - target_symbol.y) ** 2) < TARGET_SIZE:
                self.game_over = True
                self.game_over_reason = GAME_OVER_REASON_SHIP_HIT
                self.running = False
                break



    def intercept_with_laser_preferred_target(self):
        if not (self.target_symbols and \
            (self.laser_cooldown_time == 0 or (time.time() - self.laser_cooldown_time >= LONG_LASER_COOLDOWN and not self.quick_switch_flag) \
                or (time.time() - self.laser_cooldown_time >= SHORT_LASER_COOLDOWN and self.quick_switch_flag)) and \
            not self.laser_beam_active):
            return
  #x
        best_target_index = self.choose_target([target_symbol.get_target() for target_symbol in self.target_symbols])
                                                                
        if best_target_index is not None:
            target_to_intercept = self.target_symbols[best_target_index]
            if target_to_intercept in self.target_symbols_launched_interceptors_at:
                return self.intercept_with_laser_preferred_target()  # call intercept target
            self.intercept_with_laser(target_to_intercept)  # call intercept target
        else:
            pass



    def launch_dome(self, with_laser=True):            
        # Launch up to MAX_ROCKETS_PER_LAUNCH at a time, if available
        if self.target_symbols:
            ship_x, ship_y = self.ship.get_position()
            # Sort targets by distance, closest first
            sorted_candidates_for_dome_interception: list["Simulation.TargetSymbol"] = []
            for ts in self.target_symbols:
                if with_laser and (ts.get_target().get_laser_attempts() < 1 or ts.get_target().get_dome_attempts(ROCKET_SPEED_METERS_PER_SECOND) < DOME_ATTEMPTS) and \
                    ts.get_target().get_dome_attempts(ROCKET_SPEED_METERS_PER_SECOND) > 0:
                    sorted_candidates_for_dome_interception.append(ts)
                elif not with_laser:
                    sorted_candidates_for_dome_interception.append(ts)
                print(ts.get_target().get_laser_attempts())
                print(ts.get_target().get_dome_attempts(ROCKET_SPEED_METERS_PER_SECOND))
                print("distance", ts.get_target().distance)

            sorted_candidates_for_dome_interception = sorted(sorted_candidates_for_dome_interception, key=self.compare_target_dome_attempts)
                        
            for target_symbol in sorted_candidates_for_dome_interception:
                if target_symbol in self.target_symbols_launched_interceptors_at or \
                        (time.time() - target_symbol.get_target().last_interception_time) < ROCKET_LAUNCH_DELAY:
                    continue
                # shut down laser beam if dome is launched
                if target_symbol is self.intercepted_target_symbol:
                    self.laser_beam_active = False
                    self.quick_switch_flag = True
                    self.laser_cooldown_time = time.time()
                # not to launch an interceptor at a target that already has an interceptor on the way
                already_spawned_interceptor = False
                for interceptor in self.interceptors:
                    if interceptor.get_target_symbol() is target_symbol:
                        already_spawned_interceptor = True
                        break
                if already_spawned_interceptor:
                    continue
                
                self.interceptor_count += 1  # Increment the rocket counter
                new_interceptor = self.InterceptorSymbol(ship_x, ship_y, target_symbol, ROCKET_SPEED_METERS_PER_SECOND, double= \
                                                                target_symbol.get_target().get_dome_attempts(ROCKET_SPEED_METERS_PER_SECOND) < 2)
                if new_interceptor.double:
                    self.interceptor_count += 1
                self.interceptors.append(new_interceptor)
                self.target_symbols_launched_interceptors_at.append(target_symbol)


    def update_interceptor_positions(self, dt):
        # Update rocket positions
        for interceptor in self.interceptors:
            interceptor.update_position(dt)

        if self.target_symbols_launched_interceptors_at and not self.interceptors:
            self.target_symbols_launched_interceptors_at = []

        # Check for rocket collisions
        for interceptor in self.interceptors:  # Iterate over a copy to allow removal
            # sanity check:
            if interceptor.get_target_symbol() not in self.target_symbols:
                if interceptor.get_target_symbol() in self.target_symbols_launched_interceptors_at:
                    self.target_symbols_launched_interceptors_at.remove(interceptor.get_target_symbol())
                self.interceptors.remove(interceptor)
            
            for target_symbol in self.target_symbols_launched_interceptors_at:
                target_symbol.z = 1
                if interceptor.check_collision(target_symbol) and interceptor in self.interceptors:
                    interception_probability = target_symbol.get_target()._interception_max_probabolities["dome"]
                    range_limit = {"drone": 0.5, "anti-ship": 4}[target_symbol.get_target().type]
                    
                    if interceptor.double:
                        interception_probability = 1 - (1-interception_probability) ** 2

                    self.interceptors.remove(interceptor)
                    self.target_symbols_launched_interceptors_at.remove(target_symbol)  # Remove the target from the launched list
                    
                    target_symbol.z = 2
                    if target_symbol.get_target().distance < range_limit:
                        self.target_symbols.remove(target_symbol)  # Remove the hit target
                        target_symbol.z = 3
                    elif random.random() > interception_probability:
                        target_symbol.get_target().last_interception_time = time.time()
                        target_symbol.z = 4
                    else:
                        target_symbol.z = 5
                        self.explosion_time = time.time()
                        self.explosion_coords = (interceptor.x, interceptor.y)  # Use rocket's position
                        self.target_symbols.remove(target_symbol)  # Remove the hit target
                
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

    def choose_target(self, on_air_targets: list[Target]):
        if not on_air_targets:
            return None
                    
        best_ratio = -1
        best_target_index = None

        for i, target in enumerate(on_air_targets):
            # Assuming distance and velocity are updated elsewhere based on current_time
            max_ratio_of_interception_by_time = target.get_optimized_laser_firing_time(choice_oriented=True)
            if max_ratio_of_interception_by_time > best_ratio and target.amount_of_attempts_to_intercept_with_laser < 2 \
                and target.distance > 1 and target not in self.target_symbols_launched_interceptors_at:
                best_ratio = max_ratio_of_interception_by_time
                best_target_index = i

        if best_target_index is not None:
            on_air_targets[best_target_index].amount_of_attempts_to_intercept_with_laser += 1
        return best_target_index

    def run(self, num_targets, with_laser=True):
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
            if with_laser:
                self.intercept_with_laser_preferred_target()
                self.handle_laser_interception()
            self.launch_dome(with_laser)
            self.update_interceptor_positions(dt)
            self.drawing_screen(dt)
            self.check_game_over()

            
        if self.game_over_reason == GAME_OVER_REASON_SHIP_HIT:
            self.interceptor_count = -1
        pygame.quit()
        return self.interceptor_count

if __name__ == "__main__":
    NEW_FILE = True
    data_file = ""
    result_file = ""


    if not NEW_FILE:
        with open(data_file, 'r') as json_file:
            result = json.load(json_file)
    else:
        result = {}

    simulation = Simulation()

    # Step 1: Run simulations and collect raw data
    
    for num_targets in range(10, 9, -1):
        if not NEW_FILE:
            lst_of_pairs = result[str(num_targets)]
        else:
            lst_of_pairs = []
            result[str(num_targets)] = lst_of_pairs

        for repetitions in range(30):
            pair = [999,999]
            lst_of_pairs.append(pair)
            simulation = Simulation()
            interceptors_with_laser = simulation.run(num_targets, with_laser=True)
            pair[0] = interceptors_with_laser
            print(interceptors_with_laser)

            # Save raw results
            with open(data_file, 'w') as json_file:
                json.dump(result, json_file, indent=4)

        for repetitions in range(10):
            simulation = Simulation()
            interceptors_without_laser = simulation.run(num_targets, with_laser=False)
            lst_of_pairs[repetitions][1] = interceptors_without_laser
            print(interceptors_without_laser)
            
            # Save raw results
            with open(data_file, 'w') as json_file:
                json.dump(result, json_file, indent=4)

    # Step 2: Calculate averages
    averages = {}

    for num_targets, successes in result.items():
        filtered_with = [item[0] for item in successes if item[0] != -1]
        sum_interceptors_with = sum(filtered_with)
        avg_interceptors_with = sum_interceptors_with / len(filtered_with)
        avg_hit_with = len([item[0] for item in successes if item[0] == -1]) / len(successes)

        filtered_without = [item[1] for item in successes if item[1] != -1]
        sum_interceptors_without = sum(filtered_without)
        avg_interceptors_without = sum_interceptors_without / len(filtered_without)
        avg_hit_without = len([item[1] for item in successes if item[1] == -1]) / len(successes)
        
        averages[int(num_targets)] = {'avg_interceptors_with': avg_interceptors_with, 'avg_interceptors_without': avg_interceptors_without,
                                      'avg_hit_with': avg_hit_with, 'avg_hit_without': avg_hit_without}

    # Save averages
    with open(result_file, 'w') as file:
        json.dump(averages, file, indent=4)

    # Step 3: Plot the graph
    sorted_targets = sorted(averages.keys(), key=lambda x: int(x))
    avg_interceptors_with = [averages[k]['avg_interceptors_with'] for k in sorted_targets]
    avg_interceptors_without = [averages[k]['avg_interceptors_without'] for k in sorted_targets]
    avg_hit_with = [averages[k]['avg_hit_with'] for k in sorted_targets]
    avg_hit_without = [averages[k]['avg_hit_without'] for k in sorted_targets]  
    
    plt.figure(figsize=(12, 7))
    plt.plot(sorted_targets, avg_interceptors_with, marker='o', label='avg_interceptors_with')
    plt.plot(sorted_targets, avg_interceptors_without, marker='x', label='avg_interceptors_without')
    plt.plot(sorted_targets, avg_hit_with, marker='P', label='avg_hit_with')
    plt.plot(sorted_targets, avg_hit_without, marker='v', label='avg_hit_without')
    plt.title('Beam Effectiveness vs Number of Initial Targets (Big Barrage)')
    plt.xlabel('Number of Initial Targets')
    plt.ylabel('Average Interceptions')
    plt.grid(True)
    plt.gca().invert_xaxis()  # Optional: Higher target counts on the left
    plt.legend()
    plt.show()
    

    
