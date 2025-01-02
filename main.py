from machine import Pin, SPI
from ili9341 import Display, color565
from framebuf import FrameBuffer, RGB565
from time import sleep_ms, ticks_ms, ticks_diff
from random import randint
import gc

# --------------------------------------------------------------------------------
# Global Configuration
# --------------------------------------------------------------------------------

# Screen dimensions
WIDTH = 240
HEIGHT = 320

# Ball
BALL_RADIUS = 10
BALL_COLOR = color565(0, 0, 255)   # Blue
BG_COLOR = color565(0, 0, 0)       # Black

# Anims
ANIMS = True                       # Set True to enable side animations
ANIM_COLOR = color565(255, 0, 0)   # Red (BGR for MPython framebuf)
SIDE_ANIM_DURATION = 100           # Animation duration in ms

# Physics
GRAVITY = 0.025

# Frame timing
FRAME_TIME = 0  # ~120 FPS

# Initial position & velocity
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
dx = 1
dy = 1

# Turn on display backlight
backlight = Pin(21, Pin.OUT)
backlight.on()

# Set up SPI + Display
spi = SPI(1, baudrate=40_000_000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15), rotation=270, bgr=False)

# --------------------------------------------------------------------------------
# Non-blocking Side Animation State
# --------------------------------------------------------------------------------

# We'll store info about an active side animation here:
# e.g. {
#   'side': 'left' or 'right' or 'top' or 'bottom',
#   'x': ...,
#   'y': ...,
#   'width': ...,
#   'height': ...,
#   'start_time': ticks_ms() at the moment of creation
# }
current_anim = None

def update_animation():
    """
    Called each frame from the main loop.
    If an animation is active, check if enough time has passed
    (SIDE_ANIM_DURATION) to remove it.
    """
    global current_anim
    if current_anim is None: return

    if ticks_diff(ticks_ms(), current_anim['start_time']) >= SIDE_ANIM_DURATION:
        # Time to remove the animation
        side = current_anim['side']
        x = current_anim['x']
        y = current_anim['y']
        width = current_anim['width']
        height = current_anim['height']

        # Erase the animation bounding rect
        display.fill_rectangle(x, y, width, height, BG_COLOR)
        current_anim = None

def draw_side_animation_nonblocking(side, bx, by):
    """
    Trigger a new side animation (no blocking sleep).
    Immediately draw the effect, store its position & time in current_anim,
    then remove it in update_animation() after SIDE_ANIM_DURATION ms.
    """
    global current_anim

    gc.collect()

    # If there is already an active animation, erase it immediately
    if current_anim is not None:
        display.fill_rectangle(
            current_anim['x'],
            current_anim['y'],
            current_anim['width'],
            current_anim['height'],
            BG_COLOR
        )
        current_anim = None

    effect_size = 50
    if side == "left":
        x = 0
        y = max(0, by - effect_size // 2)
        width = 5
        height = min(effect_size, HEIGHT - y)
    elif side == "right":
        x = WIDTH - 5
        y = max(0, by - effect_size // 2)
        width = 5
        height = min(effect_size, HEIGHT - y)
    elif side == "top":
        x = max(0, bx - effect_size // 2)
        y = 0
        width = min(effect_size, WIDTH - x)
        height = 5
    elif side == "bottom":
        x = max(0, bx - effect_size // 2)
        y = HEIGHT - 5
        width = min(effect_size, WIDTH - x)
        height = 5
    else: return

    # Draw the animation block now
    display.fill_rectangle(x, y, width, height, ANIM_COLOR)

    # Store the animation state data for later removal
    current_anim = {
        'side': side,
        'x': x,
        'y': y,
        'width': width,
        'height': height,
        'start_time': ticks_ms()
    }

# --------------------------------------------------------------------------------
# Ball Update & Drawing
# --------------------------------------------------------------------------------

def fill_ball(framebuf, x0, y0, r, color):
    """Draw a filled circle at (x0, y0) within the local coordinate space."""
    r_sq = r * r
    for dy in range(-r, r + 1):
        yy = y0 + dy
        dy_sq = dy * dy
        for dx in range(-r, r + 1):
            xx = x0 + dx
            if dx * dx + dy_sq <= r_sq:
                framebuf.pixel(xx, yy, color)

def update_ball_position(x, y, vx, vy):
    """
    Return new ball coordinates & velocities with gravity pulling right.
    If there's a bounce, trigger a side animation (non-blocking).
    """
    vx += GRAVITY

    nx, ny = int(x + vx), int(y + vy)
    bounce = None

    # Top/Bottom wall collision
    if ny - BALL_RADIUS < 0:
        ny, vy = BALL_RADIUS, -vy
        bounce = "top"
    elif ny + BALL_RADIUS >= HEIGHT:
        ny, vy = HEIGHT - BALL_RADIUS - 1, int(-vy * 0.9)
        bounce = "bottom"

    # Left/Right wall collision
    if nx - BALL_RADIUS < 0:
        nx, vx = BALL_RADIUS, -vx
        bounce = "left"
    elif nx + BALL_RADIUS >= WIDTH:
        nx, vx = WIDTH - BALL_RADIUS - 1, int(-vx * 0.9)
        bounce = "right"

    # Random deflection on bounce - ensure rebound is not too weak or zero
    if bounce:
        deflection = randint(-2, 2)
        if bounce in ["top", "bottom"]:
            vx += deflection
            vy = max(1, abs(vy)) * (-1 if bounce == "bottom" else 1)
        elif bounce in ["left", "right"]:
            vy += deflection
            vx = max(1, abs(vx)) * (-1 if bounce == "right" else 1)

        vx, vy = int(vx), int(vy)

        if ANIMS:
            draw_side_animation_nonblocking(bounce, nx, ny)
        else:
            gc.collect()

    return nx, ny, vx, vy

# --------------------------------------------------------------------------------
# Touch Input (Stub Implementation Below)
# --------------------------------------------------------------------------------

BUTTON_X = 10
BUTTON_Y = 10
BUTTON_WIDTH = 80
BUTTON_HEIGHT = 40

def is_button_pressed(x, y):
    return BUTTON_X <= x <= BUTTON_X + BUTTON_WIDTH and BUTTON_Y <= y <= BUTTON_Y + BUTTON_HEIGHT

button_pressed = False

def touch_handler(x, y):
    """
    Interrupt/touch handler. If user taps the “button area,” set button_pressed = True.
    """
    global button_pressed
    if is_button_pressed(x, y):
        button_pressed = True

# Touch Setup
touch_spi = SPI(2, baudrate=1_000_000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
from xpt2046 import Touch
touch = Touch(
    touch_spi,
    cs=Pin(33),
    int_pin=Pin(36),
    width=HEIGHT,
    height=WIDTH,
    int_handler=touch_handler
)

# --------------------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------------------

def cleanup():
    """
    Cleanup resources.
    """
    if touch:
        touch.int_pin.irq(handler=None)  # Disable touch interrupts
        touch_spi.deinit()
    display.cleanup()

# --------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------

try:
    display.fill_rectangle(0, 0, WIDTH, HEIGHT, BG_COLOR)

    while True:
        new_x, new_y, dx, dy = update_ball_position(ball_x, ball_y, dx, dy)

        if new_x != ball_x or new_y != ball_y:
            # Bounding box around old & new positions
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

            # Fill region with background
            fb.fill(BG_COLOR)

            # Draw the new ball in the buffer
            offset_x = new_x - x_min
            offset_y = new_y - y_min
            fill_ball(fb, offset_x, offset_y, BALL_RADIUS, BALL_COLOR)

            # Write buffer to the display
            display.block(x_min, y_min, x_max, y_max, region_buf)

            # Update ball position
            ball_x, ball_y = new_x, new_y

        update_animation()

        sleep_ms(FRAME_TIME)

except KeyboardInterrupt:
    display.cleanup()

finally:
    cleanup()