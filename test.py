import os
import time
import threading
import msvcrt

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# Initialize ball and paddle settings
ball = 'O'
paddle = '|'
ball_x = 20
ball_y = 0
paddle_y = 10
direction = 1

# Function to read user input
def read_input():
    global paddle_y
    while True:
        char = msvcrt.getch().decode('utf-8')
        if char == 'w':
            paddle_y = max(0, paddle_y - 1)
        elif char == 's':
            paddle_y = min(20, paddle_y + 1)

# Start a thread to read user input
threading.Thread(target=read_input, daemon=True).start()

# Run the game
while True:
    # Clear the terminal
    clear()

    # Draw the ball and paddle
    for i in range(20):
        if i == paddle_y:
            print(paddle + ' ' * (ball_x - 1) + ball)
        elif i == ball_y:
            print(' ' * ball_x + ball)
        else:
            print('')

    # Update ball position and direction
    ball_y += direction
    if ball_y == 20 and abs(paddle_y - ball_y) <= 2:
        direction *= -1
    elif ball_y == 0:
        direction *= -1

    # Pause
    time.sleep(0.1)
ws