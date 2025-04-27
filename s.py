import threading
import time

# Shared state
current_number = 1
sleep_event = threading.Event()
lock = threading.Lock()
interrupted = False

def notify_full_display(number):
    print(f"✅ Number {number} was displayed for the full 5 seconds.")

def number_printer():
    global current_number, interrupted
    while True:
        with lock:
            interrupted = False
            local_number = current_number
            print(f"Printed: {local_number}")

        sleep_event.clear()
        sleep_event.wait(timeout=5)

        with lock:
            if not interrupted and local_number == current_number:
                notify_full_display(local_number)

def time_generator():
    """Generates random waiting times and simulates an event."""
    import random
    while True:
        wait_time = random.uniform(1, 8)  # Generate a random wait time between 1 and 8 seconds
        time.sleep(wait_time)
        new_number = random.randint(0, 9) # Simulate receiving a new number
        trigger_listener(new_number)

def trigger_listener(new_number):
    """Simulates the key press event, updating the current number."""
    global current_number, interrupted
    with lock:
        interrupted = True
        current_number = new_number
        print(f"Simulated new input: {current_number}")
    sleep_event.set()  # Interrupt the 5s wait

# Start threads
printer_thread = threading.Thread(target=number_printer, daemon=True)
time_generator_thread = threading.Thread(target=time_generator, daemon=True)

printer_thread.start()
time_generator_thread.start()

# Keep the main thread alive
while True:
    time.sleep(1)