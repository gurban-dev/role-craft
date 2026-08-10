# Import the pyautogui library.
# This library allows Python to control the mouse.
import pyautogui

# Import the time library to pause briefly between clicks.
import time

# Import os to exit the program immediately when requested.
import os

# Import tkinter.
# Tkinter lets us display popup windows.
import tkinter as tk

# Import the messagebox module.
# This module displays Yes/No dialogs.
from tkinter import messagebox

# Import the keyboard module from pynput.
# This module lets us listen for keyboard events.
from pynput import keyboard

# This program automatically clicks the cookie in Cookie Clicker.
# Open the game in your web browser before running this program:
# https://orteil.dashnet.org/cookieclicker/

# Install the required packages before running this program.

# Windows and Linux:
# pip install -r requirements.txt

# macOS:
# pip3 install -r requirements.txt

# Keep track of whether the auto-clicker should continue running.
running = False

# Store the location selected by the user.
click_position = None

# True after the user presses A to capture a location.
position_saved = False

# Create a hidden tkinter window.
root = tk.Tk()

# Hide the main window.
root.withdraw()

# Bring dialogs to the front.
root.attributes("-topmost", True)

# Give the hidden window keyboard focus.
root.focus_force()


# Terminate the program immediately.
def terminate_program():
    print("Program terminated.")
    os._exit(0)


# Escape terminates the program at any time.
def on_escape(key):
    if key == keyboard.Key.esc:
        terminate_program()


# Listen for A to save the current mouse position.
def on_press_select(key):
    global click_position
    global position_saved

    # Escape is handled by the global listener.
    if key == keyboard.Key.esc:
        return False

    # Save the current mouse position when A is pressed.
    try:
        if key.char.lower() == "a":
            click_position = pyautogui.position()
            position_saved = True
            print(f"Position saved: {click_position}\n")

            # Stop listening after A is pressed.
            return False

    # Ignore special keys that do not have a character.
    except AttributeError:
        pass


# Stop the auto-clicker when Escape is pressed.
def on_press_running(key):
    global running

    if key == keyboard.Key.esc:
        running = False
        return False


# Listen for Escape for the entire lifetime of the program.
escape_listener = keyboard.Listener(on_press=on_escape)
escape_listener.start()

while True:

    # Reset selection state for each attempt.
    position_saved = False
    click_position = None

    # Instruct the user to select a location.
    print("Press A on your keyboard at the location you would like to auto-click.\n")

    print("Press Escape at any time to terminate the program.\n")

    # Wait until the user presses A.
    with keyboard.Listener(on_press=on_press_select) as listener:
        listener.join()

    # If Escape ended the selection listener without saving a position.
    if not position_saved:
        terminate_program()

    # Confirm whether this location should be auto-clicked.
    should_click = messagebox.askyesno(
        "Auto Clicker",
        "Do you want this location to be auto-clicked?",
        parent=root
    )

    # Ask the user to choose another location if they select No.
    # Proceed once the user selects Yes.
    if should_click:
        break

# Close the hidden tkinter window.
root.destroy()

# The auto-clicker is now running.
running = True

# Tell PyAutoGUI not to stop when the mouse reaches the corner.
pyautogui.FAILSAFE = False

# Inform the user that auto-clicking has begun.
print("Auto-clicking has started.\n")

print("Press Escape at any time to terminate the program.\n")

# Also listen during the click loop (in addition to the global Escape listener).
listener = keyboard.Listener(on_press=on_press_running)
listener.start()

try:

    # Save the chosen location so we can reuse it during every loop.
    target_position = click_position

    # Continue clicking until Escape is pressed.
    while running:

        # Move back if the mouse has been moved away.
        if pyautogui.position() != target_position:
            pyautogui.moveTo(target_position, duration=0)

        # Click at the saved location.
        pyautogui.click()

        # Pause briefly before the next click.
        time.sleep(0)

finally:

    # Stop listening for keyboard events.
    listener.stop()
    listener.join()
    escape_listener.stop()

# Tell the user the program has ended.
terminate_program()