# AutoPong

AutoPong is a simple pong game implemented for a microcontroller with an ILI9341 display and XPT2046 touch controller. The game features a bouncing ball and a start button on the touchscreen, it'll be a game eventually.

ILI9341 & XPT2046 drivers - [credit to rdagger](https://github.com/rdagger/micropython-ili9341)

## Requirements

- Microcontroller with SPI support
- ILI9341 display
- XPT2046 touch controller
- MicroPython or CircuitPython

## Installation

1. Clone the repository to your local machine.
2. Copy all the files to your microcontroller.

## How to Run

1. Connect the ILI9341 display and XPT2046 touch controller to your microcontroller as per the pin configuration in the code.
2. Power on the microcontroller.
3. The game will start automatically, displaying a startup screen with a "START" button.
4. Touch the "START" button to begin the game.

## File Descriptions

- `boot.py`: Initializes the display and touch controller, draws the startup screen, and handles the touch input to start the game.
- `ili9341.py`: Driver for the ILI9341 display.
- `main.py`: Contains the main game logic, including ball movement and touch input handling.
- `memory.py`: Utility functions for checking free memory and disk space.
- `wifi.py`: Connects the microcontroller to a Wi-Fi network.
- `xpt2046.py`: Driver for the XPT2046 touch controller.
- `pymakr.conf`: Configuration file for the Pymakr plugin.

## Pin Configuration

- ILI9341 Display:
  - SCK: Pin 14
  - MOSI: Pin 13
  - DC: Pin 2
  - CS: Pin 15
  - RST: Pin 15
  - Backlight: Pin 21

- XPT2046 Touch Controller:
  - SCK: Pin 25
  - MOSI: Pin 32
  - MISO: Pin 39
  - CS: Pin 33
  - INT: Pin 36

## License

This project is licensed under the MIT License, apart from device drivers, where license lies with their respective owners.