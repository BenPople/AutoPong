from machine import Pin, SPI  # type: ignore
from ili9341 import Display, color565
from framebuf import FrameBuffer, RGB565  # type: ignore
from time import sleep_ms, ticks_ms, ticks_diff
from random import randint
import gc
from math import sqrt

# --------------------------------------------------------------------------------
# Global Configuration
# --------------------------------------------------------------------------------

WIDTH = 240
HEIGHT = 320

BALL_RADIUS = 10
BALL_COLOR = color565(0, 0, 255)  # Blue
BG_COLOR = color565(0, 0, 0)      # Black

ANIMS = True
ANIM_COLOR = color565(255, 0, 0)  # Red
SIDE_ANIM_DURATION = 100          # Animation duration in ms

GRAVITY = 0.025
PLAYER_NUDGE_FORCE = 2.0

FRAME_TIME = 0

ball_x = WIDTH // 2
ball_y = HEIGHT // 2
dx = 1
dy = 1

backlight = Pin(21, Pin.OUT)
backlight.on()

spi = SPI(1, baudrate=40_000_000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15), rotation=270, bgr=False)

# --------------------------------------------------------------------------------
# Non-blocking Side Animation
# --------------------------------------------------------------------------------

current_anim = None

def update_animation():
    global current_anim
    if current_anim is None:
        return

    if ticks_diff(ticks_ms(), current_anim['start_time']) >= SIDE_ANIM_DURATION:
        side = current_anim['side']
        x = current_anim['x']
        y = current_anim['y']
        width = current_anim['width']
        height = current_anim['height']
        display.fill_rectangle(x, y, width, height, BG_COLOR)
        current_anim = None

def draw_side_animation_nonblocking(side, bx, by):
    global current_anim
    gc.collect()

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
    else:
        return

    display.fill_rectangle(x, y, width, height, ANIM_COLOR)

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
    r_sq = r * r
    for dy in range(-r, r + 1):
        yy = y0 + dy
        dy_sq = dy * dy
        for dx in range(-r, r + 1):
            xx = x0 + dx
            if dx * dx + dy_sq <= r_sq:
                framebuf.pixel(xx, yy, color)

def update_ball_position(x, y, vx, vy):
    vx += GRAVITY
    nx, ny = int(x + vx), int(y + vy)
    bounce = None

    # Top/Bottom
    if ny - BALL_RADIUS < 0:
        ny, vy = BALL_RADIUS, -vy
        bounce = "top"
    elif ny + BALL_RADIUS >= HEIGHT:
        ny, vy = HEIGHT - BALL_RADIUS - 1, int(-vy * 0.9)
        bounce = "bottom"

    # Left/Right
    if nx - BALL_RADIUS < 0:
        nx, vx = BALL_RADIUS, -vx
        bounce = "left"
    elif nx + BALL_RADIUS >= WIDTH:
        nx, vx = WIDTH - BALL_RADIUS - 1, int(-vx * 0.9)
        bounce = "right"

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
# Touch Input (Pen-Down Only Once) with Transform
# --------------------------------------------------------------------------------

from xpt2046 import Touch
touch_spi = SPI(2, baudrate=1_000_000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))

# The Touch driver is created with (width=HEIGHT, height=WIDTH) because physically
# the device might be in "landscape." But our display logic is 240 (X) × 320 (Y).
touch = Touch(
    touch_spi,
    cs=Pin(33),
    int_pin=Pin(36),  
    int_handler=None, 
    width=HEIGHT,  # 320
    height=WIDTH   # 240
)

touch_down = False

def touch_handler(x, y):
    """
    Called once when the user first touches.
    If within 20 px of the ball, nudge it towards the furthest wall.
    """
    global ball_x, ball_y, dx, dy

    dist_to_ball = sqrt((x - ball_x)**2 + (y - ball_y)**2)
    print(f"Pen down at {x},{y} - distance to ball center is {dist_to_ball:.2f}")

    if dist_to_ball <= 100:
        dist_top = ball_y
        dist_bottom = HEIGHT - ball_y
        dist_left = ball_x
        dist_right = WIDTH - ball_x

        directions = {
            'top': dist_top,
            'bottom': dist_bottom,
            'left': dist_left,
            'right': dist_right
        }
        furthest_wall = max(directions, key=directions.get)

        if furthest_wall == 'top':
            dy -= PLAYER_NUDGE_FORCE
        elif furthest_wall == 'bottom':
            dy += PLAYER_NUDGE_FORCE
        elif furthest_wall == 'left':
            dx -= PLAYER_NUDGE_FORCE
        elif furthest_wall == 'right':
            dx += PLAYER_NUDGE_FORCE

def poll_touch():
    """
    - We check touch.is_pressed().
    - If newly pressed, read the raw coords from get_touch(), transform them,
      and call touch_handler.
    - If still pressed, do nothing.
    - If not pressed, reset so next press triggers again.
    """
    global touch_down

    if touch.is_pressed():
        if not touch_down:
            coords = touch.get_touch()
            if coords is not None:
                raw_x, raw_y = coords
                x_new = raw_y
                y_new = (WIDTH - raw_x - 1)
                touch_handler(x_new, y_new)

            touch_down = True
    else:
        touch_down = False

# --------------------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------------------

def cleanup():
    if touch:
        touch.int_pin.irq(handler=None)
        touch_spi.deinit()
    display.cleanup()

# --------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------

try:
    display.fill_rectangle(0, 0, WIDTH, HEIGHT, BG_COLOR)

    while True:
        poll_touch()

        new_x, new_y, dx, dy = update_ball_position(ball_x, ball_y, dx, dy)

        if new_x != ball_x or new_y != ball_y:
            x_min = min(ball_x, new_x) - BALL_RADIUS
            y_min = min(ball_y, new_y) - BALL_RADIUS
            x_max = max(ball_x, new_x) + BALL_RADIUS
            y_max = max(ball_y, new_y) + BALL_RADIUS

            x_min, y_min = max(0, x_min), max(0, y_min)
            x_max, y_max = min(WIDTH - 1, x_max), min(HEIGHT - 1, y_max)

            region_width = x_max - x_min + 1
            region_height = y_max - y_min + 1

            region_buf = bytearray(region_width * region_height * 2)
            fb = FrameBuffer(region_buf, region_width, region_height, RGB565)
            fb.fill(BG_COLOR)

            offset_x = new_x - x_min
            offset_y = new_y - y_min
            fill_ball(fb, offset_x, offset_y, BALL_RADIUS, BALL_COLOR)

            display.block(x_min, y_min, x_max, y_max, region_buf)

            ball_x, ball_y = new_x, new_y

        update_animation()
        sleep_ms(FRAME_TIME)

except KeyboardInterrupt:
    display.cleanup()

finally:
    cleanup()