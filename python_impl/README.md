# Python Implementation of RFOutlet

This is a Python reimplementation of the RFOutlet tools (`codesend` and `RFSniffer`) using the `rpi-rf` library. This allows the tools to run on 64-bit Raspberry Pi OS where the original `wiringPi` library might be deprecated or unavailable.

## Prerequisites

You need to install the required Python libraries. It is recommended to use a virtual environment.

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### Note for Raspberry Pi OS (Bookworm) / 64-bit Users

If you are running the latest Raspberry Pi OS (Bookworm) or a 64-bit version, the traditional `RPi.GPIO` library might not work due to kernel changes. If you encounter errors, you should uninstall `RPi.GPIO` and install `rpi-lgpio` which is a compatible replacement:

```bash
pip3 uninstall RPi.GPIO
pip3 install rpi-lgpio
```

## Hardware Setup

This project uses standard 433MHz RF Transmitter and Receiver modules (like the hiBCTR sets).

### Pinout Guide

**Note:** The modules share 5V power and Ground, but require separate Data pins on the Raspberry Pi.

#### Transmitter Module (Square, 3 Pins)
| Module Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| **VCC**    | Pin 2 or 4       | 5V Power    |
| **GND**    | Pin 6            | Ground      |
| **DATA**   | Pin 11 (GPIO 17) | Data Signal |

#### Receiver Module (Rectangular, 4 Pins)
| Module Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| **VCC**    | Pin 2 or 4       | 5V Power    |
| **GND**    | Pin 9            | Ground      |
| **DATA**   | Pin 13 (GPIO 27) | Data Signal |
| **DATA**   | N/C              | Not Connected (Internal duplicate) |

*Note: You can use any 5V or GND pin on the Pi, but the Data pins must match the configuration in the scripts (GPIO 17 for TX, GPIO 27 for RX).*

## Usage

### Sending Codes (codesend)

To send a code, use `codesend.py`.

```bash
python3 codesend.py <CODE>
```

Options:
- `-g`, `--gpio`: GPIO pin to use (Default: 17)
- `-p`, `--pulselength`: Pulse length (Default: 189)
- `-t`, `--protocol`: Protocol (Default: 1)

Example:
```bash
python3 codesend.py 123456 -p 190
```

### Sniffing Codes (rfsniffer)

To listen for codes, use `rfsniffer.py`.

```bash
python3 rfsniffer.py
```

Options:
- `-g`, `--gpio`: GPIO pin to use (Default: 27)

### Controlling Outlets (controller.py)

You can use `controller.py` to toggle specific outlets using the pre-configured codes.

```bash
python3 controller.py <OUTLET_ID> <STATE>
```

Example:
```bash
python3 controller.py 1 on
python3 controller.py 1 off
```

You can edit the `OUTLETS` dictionary in `controller.py` to match your specific RF codes.

## Integration

You can update the `toggle.php` or other scripts in the parent directory to call these Python scripts instead of the compiled C++ binaries.

For example, in PHP:
```php
shell_exec("python3 /path/to/python_impl/codesend.py $code -p $pulseLength");
```
