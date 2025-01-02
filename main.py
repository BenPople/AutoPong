from machine import Pin, SPI
from ili9341 import Display, color565
from framebuf import FrameBuffer, RGB565
from time import sleep_ms
from random import randint
import memory
import gc

# Screen dimensions
WIDTH = 240
HEIGHT = 320

# Ball
BALL_RADIUS = 10
BALL_COLOR = color565(0, 0, 255)   # Blue
BG_COLOR = color565(0, 0, 0)       # Black

# Anims
ANIMS = False
ANIM_COLOR = color565(255, 0, 0)   # Blue (BGR for MPython framebuf)

# Initial position & velocity
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
dx = 1
dy = 1

# Frame timing
FRAME_TIME = 0  # ~120 FPS

# Gravity/Physics
GRAVITY = 0.025

# Turn on display backlight
backlight = Pin(21, Pin.OUT)
backlight.on()

# Set up SPI + Display
spi = SPI(1, baudrate=40_000_000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15), rotation=270, bgr=False)

def update_ball_position(x, y, vx, vy):
    """Return new ball coordinates & velocities with gravity pulling right."""
    global display

    # Apply gravity to horizontal velocity (rightward)
    vx += GRAVITY

    # Update positions
    nx, ny = int(x + vx), int(y + vy)  # Ensure integers

    bounce = None

    # Top/Bottom wall collision (vertical edges of rotated screen)
    if ny - BALL_RADIUS < 0:
        ny, vy = BALL_RADIUS, -vy
        bounce = "top"
    elif ny + BALL_RADIUS >= HEIGHT:
        ny, vy = HEIGHT - BALL_RADIUS - 1, int(-vy * 0.9)  # Add energy loss
        bounce = "bottom"

    # Left/Right wall collision (horizontal edges of rotated screen)
    if nx - BALL_RADIUS < 0:
        nx, vx = BALL_RADIUS, -vx
        bounce = "left"
    elif nx + BALL_RADIUS >= WIDTH:
        nx, vx = WIDTH - BALL_RADIUS - 1, int(-vx * 0.9)  # Add energy loss
        bounce = "right"

    # Add random deflection on bounce
    if bounce:
        deflection = randint(-2, 2)
        if bounce in ["top", "bottom"]:
            vx += deflection  # Change horizontal velocity slightly
            vy = max(1, abs(vy)) * (-1 if bounce == "bottom" else 1)  # Ensure meaningful rebound
        elif bounce in ["left", "right"]:
            vy += deflection  # Change vertical velocity slightly
            vx = max(1, abs(vx)) * (-1 if bounce == "right" else 1)  # Ensure meaningful rebound

        # Ensure velocities remain integers
        vx, vy = int(vx), int(vy)

        # Draw side animation & GC
        if ANIMS: draw_side_animation(bounce)
        else: gc.collect()

    return nx, ny, vx, vy

def draw_side_animation(side):
    """Animation when the ball bounces on a side, focused around the ball."""
    gc.collect()
    effect_size = 50  # Number of pixels around the ball for the animation

    if side == "left":
        x = 0
        y = max(0, ball_y - effect_size // 2)
        height = min(effect_size, HEIGHT - y)
        display.fill_rectangle(x, y, 5, height, ANIM_COLOR)
        sleep_ms(50)
        display.fill_rectangle(x, y, 5, height, BG_COLOR)
    elif side == "right":
        x = WIDTH - 5
        y = max(0, ball_y - effect_size // 2)
        height = min(effect_size, HEIGHT - y)
        display.fill_rectangle(x, y, 5, height, ANIM_COLOR)
        sleep_ms(50)
        display.fill_rectangle(x, y, 5, height, BG_COLOR)
    elif side == "top":
        y = 0
        x = max(0, ball_x - effect_size // 2)
        width = min(effect_size, WIDTH - x)
        display.fill_rectangle(x, y, width, 5, ANIM_COLOR)
        sleep_ms(50)
        display.fill_rectangle(x, y, width, 5, BG_COLOR)
    elif side == "bottom":
        y = HEIGHT - 5
        x = max(0, ball_x - effect_size // 2)
        width = min(effect_size, WIDTH - x)
        display.fill_rectangle(x, y, width, 5, ANIM_COLOR)
        sleep_ms(50)
        display.fill_rectangle(x, y, width, 5, BG_COLOR)

def fill_ball(framebuf, x0, y0, r, color):
    """Draw a filled circle at (x0, y0) in the local coordinate space."""
    r_sq = r * r
    for dy in range(-r, r + 1):
        yy = y0 + dy
        dy_sq = dy * dy
        for dx in range(-r, r + 1):
            xx = x0 + dx
            if dx * dx + dy_sq <= r_sq:
                framebuf.pixel(xx, yy, color)

# Clear the full screen at startup
display.fill_rectangle(0, 0, WIDTH, HEIGHT, BG_COLOR)

try:
    while True:
        new_x, new_y, dx, dy = update_ball_position(ball_x, ball_y, dx, dy)

        if new_x != ball_x or new_y != ball_y:
            # Compute bounding box around old & new positions
            padding = 0
            x_min = min(ball_x, new_x) - BALL_RADIUS - padding
            y_min = min(ball_y, new_y) - BALL_RADIUS - padding
            x_max = max(ball_x, new_x) + BALL_RADIUS + padding
            y_max = max(ball_y, new_y) + BALL_RADIUS + padding

            # Clip to screen
            x_min, y_min = max(0, x_min), max(0, y_min)
            x_max, y_max = min(WIDTH - 1, x_max), min(HEIGHT - 1, y_max)
            region_width, region_height = x_max - x_min + 1, y_max - y_min + 1

            # Allocate a buffer for this region
            region_buf = bytearray(region_width * region_height * 2)
            fb = FrameBuffer(region_buf, region_width, region_height, RGB565)

            # Fill the region with background
            fb.fill(BG_COLOR)

            # Draw the new ball in the buffer
            offset_x = new_x - x_min
            offset_y = new_y - y_min
            fill_ball(fb, offset_x, offset_y, BALL_RADIUS, BALL_COLOR)

            # Write the buffer to the display
            display.block(x_min, y_min, x_max, y_max, region_buf)

            # Update ball position
            ball_x, ball_y = new_x, new_y

        sleep_ms(FRAME_TIME)

except KeyboardInterrupt:
    display.cleanup() 

def is_button_pressed(x, y):
    return BUTTON_X <= x <= BUTTON_X + BUTTON_WIDTH and BUTTON_Y <= y <= BUTTON_Y + BUTTON_HEIGHT

button_pressed = False

# Interrupt handler
def touch_handler(x, y):
    global button_pressed
    if is_button_pressed(x, y):
        button_pressed = True

# Set up Touch
touch_spi = SPI(2, baudrate=1_000_000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
touch = Touch(
    touch_spi,
    cs=Pin(33),
    int_pin=Pin(36),
    width=HEIGHT,
    height=WIDTH,
    int_handler=touch_handler
)

def cleanup():
    touch.int_pin.irq(handler=None)  # Disable interrupt handler
    touch_spi.deinit()
    display.cleanup()

try:
    draw_startup_screen()
    connect_to_wifi()
    while True:
        if button_pressed:
            print("Button pressed. Starting game...")
            break
        sleep(0.1)

except KeyboardInterrupt:
    display.cleanup()

finally:
    cleanup()