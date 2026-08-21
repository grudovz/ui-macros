import pyautogui
import keyboard
import time

print("Move your mouse to any target position.")
print("Press ESC to stop.\n")

while not keyboard.is_pressed("esc"):
    x, y = pyautogui.position()
    print(f"Position: x={x}, y={y}", end="\r")
    time.sleep(0.1)

print("\nDone.")
