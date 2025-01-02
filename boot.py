from machine import Pin, SPI # type: ignore
from ili9341 import Display, color565
from xpt2046 import Touch
from time import sleep
from wifi import connect_to_wifi

# Screen dimensions
WIDTH = 320
HEIGHT = 240

# Colors
BG_COLOR = color565(0, 0, 0)       # Black
TEXT_COLOR = color565(255, 255, 255)  # White
BUTTON_COLOR = color565(255, 0, 0)  # Blue (account for BGR565 for some reason here?)

# Set up SPI + Display
spi = SPI(1, baudrate=40_000_000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15), bgr=False)
Pin(21, Pin.OUT).on() #Backlight on

# Button Dimensions
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 50
BUTTON_X = (WIDTH - BUTTON_WIDTH) // 2
BUTTON_Y = HEIGHT - 100

def draw_startup_screen():
    display.fill_rectangle(0, 0, WIDTH, HEIGHT, BG_COLOR)

    # Game info
    display.draw_text8x8(WIDTH // 2 - 40, HEIGHT // 3, "AutoPong", TEXT_COLOR)
    display.draw_text8x8(WIDTH // 2 - 50, HEIGHT // 2, "By: Ben Pople", TEXT_COLOR)

    # Start button
    display.fill_rectangle(BUTTON_X, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_COLOR)
    display.draw_text8x8(BUTTON_X + 30, BUTTON_Y + 20, "START", TEXT_COLOR)

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