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
SHIP_SIZE = 30
TARGET_SIZE = 10
FONT_COLOR = (255, 255, 255)
MAX_TARGETS = 10
TARGET_SPAWN_RATE = 0.5
INTERCEPTION_DURATION = 2
PIXLES_TO_KM = 10
LASER_WIDTH = 3
EXPLOSION_COLOR = (255, 255, 0)
EXPLOSION_DURATION = 0.5


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

    def draw_laser(self, start_x, start_y, end_x, end_y, width=LASER_WIDTH):
        pygame.draw.line(self.screen, LASER_COLOR, (start_x, start_y), (end_x, end_y), width)

    def intercept_target(self, target_symbol):
        self.interception_in_progress = True
        self.intercepted_target_symbol = target_symbol
        intercepted_target = target_symbol.get_target()
        threading.Thread(target=self.ship_instance.intercept_with_laser, args=(intercepted_target, self.result_queue)).start()

    def handle_interception_result(self):
        try:
            success = self.result_queue.get_nowait()
            if success:
                self.interception_count += 1
                print("Target Intercepted!")
                self.explosion_time = time.time()
                self.explosion_coords = (self.intercepted_target_symbol.x, self.intercepted_target_symbol.y)  # Store coords
                if self.intercepted_target_symbol in self.target_symbols:
                    self.target_symbols.remove(self.intercepted_target_symbol)
            else:
                print("Interception Failed!")
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
                    break

            # Remove targets that go out of bounds
            self.target_symbols = [target_symbol for target_symbol in self.target_symbols
                                     if not target_symbol.is_out_of_bounds()]

            # Choose and intercept target using ship.py
            if not self.interception_in_progress and self.target_symbols:
                best_target_index = self.ship_instance.choose_target(
                    [target_symbol.get_target() for target_symbol in self.target_symbols])
                if best_target_index is not None:
                    target_to_intercept = self.target_symbols[best_target_index]
                    print(
                        f"Attempting to intercept target {target_to_intercept.get_target().type} in distance {target_to_intercept.get_target().distance}.")
                    self.intercept_target(target_to_intercept)

            # Handle interception results
            self.handle_interception_result()

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

            # Draw explosion
            if self.explosion_time > 0 and self.explosion_coords: #and explosion coords
                if time.time() - self.explosion_time < EXPLOSION_DURATION:
                    self.draw_explosion(self.explosion_coords[0], self.explosion_coords[1])
                else:
                    self.explosion_time = 0
                    self.explosion_coords = None # Reset coords
            elif self.explosion_time > 0 and not self.explosion_coords:
                self.explosion_time = 0

            # Display timer
            timer_text = self.font.render(f"Time: {self.current_mission_time:.2f} s", True, FONT_COLOR)
            self.screen.blit(timer_text, (10, 10))

            # Display interception count
            count_text = self.font.render(f"Interceptions: {self.interception_count}", True, FONT_COLOR)
            self.screen.blit(count_text, (10, 40))

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    simulation = Simulation()
    try:
        simulation.run()
    except pygame.error as e:
        print("Target hit the ship!")
