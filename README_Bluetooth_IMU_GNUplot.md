# Bluetooth IMU Data to GNUplot

This README explains how we changed the Windows data-collection program so that IMU data from the **Seeed Studio XIAO nRF52840 Sense** can be received wirelessly over Bluetooth Low Energy (BLE), saved by a C program, and plotted in GNUplot.

## System Overview

The original Windows program read IMU data directly from a USB COM port.

The new setup uses **Python + Bleak** as a small Bluetooth receiver between the XIAO and the C program:

```text
Seeed XIAO nRF52840 Sense
        |
        | Bluetooth LE / Nordic UART Service
        v
ble_receiver.py
        |
        | stdout pipe
        v
datastoragebt.c
        |
        +--> measurements.txt
        |
        +--> GNUplot
```

The XIAO still sends the same measurement format:

```text
time_ms;ax;ay;az;gx;gy;gz;a_total
```

Because the format stayed the same, most of the original C parsing and GNUplot code could be reused.

---

## 1. Install Python

Check whether Python is already installed:

```powershell
py --version
```

If this does not work, install Python 3 for Windows.

During installation, make sure:

```text
Add python.exe to PATH
```

is enabled.

After installation, close and reopen VS Code or PowerShell and run:

```powershell
py --version
```

---

## 2. Install Bleak

Bleak is the Python library used to communicate with Bluetooth Low Energy devices.

Install it once with:

```powershell
py -m pip install bleak
```

Check that the installation worked:

```powershell
py -c "import bleak; print('Bleak installed')"
```

Expected output:

```text
Bleak installed
```

---

## 3. Bluetooth Receiver

Create a file named:

```text
ble_receiver.py
```

Place it in the **same folder** as the C program.

Example folder structure:

```text
CM2024Project
|
+-- datastoragebt.c
+-- ble_receiver.py
+-- measurements.txt
```

Use the following Python code:

```python
import asyncio
import sys

from bleak import BleakClient, BleakScanner


DEVICE_NAME = "ConcussionHeadband"

TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


async def main():

    print(
        "Searching for ConcussionHeadband...",
        file=sys.stderr
    )

    device = None

    while device is None:

        device = await BleakScanner.find_device_by_name(
            DEVICE_NAME,
            timeout=10.0
        )

        if device is None:
            print(
                "Device not found. Trying again...",
                file=sys.stderr
            )

    print(
        "Device found.",
        file=sys.stderr
    )

    stop_event = asyncio.Event()
    stopping = False

    def disconnected(client):

        nonlocal stopping

        stopping = True

        print(
            "\nBluetooth disconnected.",
            file=sys.stderr
        )

        stop_event.set()

    def notification_handler(sender, data):

        nonlocal stopping

        if stopping:
            return

        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

        except (BrokenPipeError, OSError):
            stopping = True
            stop_event.set()

    async with BleakClient(
        device,
        disconnected_callback=disconnected
    ) as client:

        print(
            "Connected to ConcussionHeadband.",
            file=sys.stderr
        )

        print(
            "Receiving IMU data...",
            file=sys.stderr
        )

        await client.start_notify(
            TX_UUID,
            notification_handler
        )

        await stop_event.wait()

        if client.is_connected:

            try:
                await client.stop_notify(TX_UUID)

            except Exception:
                pass


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass
```

---

## 4. Nordic UART TX Characteristic

The Bluetooth firmware uses the **Nordic UART Service (NUS)**.

The TX characteristic used by the Python receiver is:

```text
6e400003-b5a3-f393-e0a9-e50e24dcca9e
```

This is the characteristic that sends the IMU data from the XIAO to the PC.

---

## 5. Test the Bluetooth Receiver by Itself

Before running the C program, test the Python receiver.

Make sure:

- Bluetooth LE Explorer is disconnected.
- The phone is disconnected.
- The XIAO has been reset and is advertising.

The firmware is configured with:

```text
CONFIG_BT_MAX_CONN=1
```

so only one device can be connected at a time.

Run:

```powershell
py -u ble_receiver.py
```

If the connection works, the terminal should show something similar to:

```text
Searching for ConcussionHeadband...
Device found.
Connected to ConcussionHeadband.
Receiving IMU data...
```

followed by data such as:

```text
2065671;1.124626;7.762316;6.068198;-0.033368;-0.012599;0.001527;9.916721
2065683;1.272981;7.771887;6.647261;-0.130648;-0.130648;0.067347;10.305765
```

Stop the test with:

```text
Ctrl+C
```

---

## 6. Connecting Python to the C Program

The C program automatically starts the Python Bluetooth receiver with:

```c
#define BLE_COMMAND "py -u ble_receiver.py"
```

and:

```c
FILE *ble = _popen(
    BLE_COMMAND,
    "r"
);
```

`_popen()` starts the Python program and creates a pipe between Python and C.

The Python program receives BLE notifications and writes the raw bytes to `stdout`.

The C program reads that stream using:

```c
fgets(
    line,
    sizeof(line),
    ble
);
```

This replaces the old COM-port input that used:

```c
ReadFile(serial, ...)
```

---

## 7. Why Python/Bleak Is Needed

Bluetooth LE notifications do not necessarily contain one complete measurement.

For example, one measurement could arrive as:

```text
2065671;1.12;7.76
```

followed by:

```text
;6.06;-0.03;...;9.91\n
```

Bleak writes the received chunks into one continuous byte stream.

The XIAO already adds:

```text
\n
```

to the end of every complete measurement.

Because of this, the C program can use `fgets()` to wait until one complete measurement line has arrived.

---

## 8. Parsing the Sensor Data

The C program receives data in this format:

```text
time_ms;ax;ay;az;gx;gy;gz;a_total
```

It is parsed with:

```c
int values = sscanf(
    line,
    "%u;%lf;%lf;%lf;%lf;%lf;%lf;%lf",
    &time_ms,
    &ax,
    &ay,
    &az,
    &gx,
    &gy,
    &gz,
    &a_total
);
```

A measurement is only accepted when:

```c
values == 8
```

---

## 9. Recording Time

The C program records for 20 seconds:

```c
#define RECORDING_TIME_MS 20000
```

The timer starts when the **first valid Bluetooth measurement** arrives.

This means Bluetooth connection time does not reduce the 20-second recording period.

---

## 10. Stop Early with Q

The original functionality for stopping a recording early was kept.

The program checks:

```c
if (kbhit())
{
    char key = getch();

    if (key == 'q' || key == 'Q')
    {
        break;
    }
}
```

Pressing:

```text
Q
```

stops the recording before the full 20 seconds have passed.

---

## 11. Saving the Measurements

The C program saves the accelerometer data to:

```text
measurements.txt
```

The columns are:

```text
Column 1 = Time
Column 2 = X acceleration
Column 3 = Y acceleration
Column 4 = Z acceleration
Column 5 = Total acceleration
```

Acceleration is converted from m/s² to g using:

```c
#define G 9.82
```

and:

```c
ax / G
ay / G
az / G
a_total / G
```

The saved format is therefore:

```text
time  X  Y  Z  Total
```

---

## 12. GNUplot

Live plotting was removed because repeatedly refreshing GNUplot caused performance problems.

The final sequence is:

```text
Connect over Bluetooth
        |
        v
Record IMU data
        |
        | 20 seconds or Q
        v
Close measurements.txt
        |
        v
Stop Bluetooth receiver
        |
        v
Open GNUplot
        |
        v
Plot completed measurement
```

GNUplot shows **one graph with four coloured lines**:

```text
Red     = X acceleration
Green   = Y acceleration
Blue    = Z acceleration
Purple  = Total acceleration
```

The plotting command is:

```c
fprintf(
    gnuplot,

    "plot "
    "'%s' using 1:2 with lines lw 2 lc rgb 'red' "
    "title 'X acceleration', "

    "'%s' using 1:3 with lines lw 2 lc rgb 'green' "
    "title 'Y acceleration', "

    "'%s' using 1:4 with lines lw 2 lc rgb 'blue' "
    "title 'Z acceleration', "

    "'%s' using 1:5 with lines lw 2 lc rgb 'purple' "
    "title 'Total acceleration'\n",

    filename,
    filename,
    filename,
    filename
);
```

---

## 13. Compile the C Program

Compile the Bluetooth version of the data-storage program with:

```powershell
gcc datastoragebt.c -o datastoragebt.exe
```

Then run:

```powershell
.\datastoragebt.exe
```

During normal use, **do not start `ble_receiver.py` manually**.

The C program starts it automatically.

---

## Normal Workflow

The normal workflow is:

```text
1. Reset the XIAO.

2. Make sure the phone and Bluetooth LE Explorer
   are disconnected.

3. Run:

   .\datastoragebt.exe

4. datastoragebt.exe automatically starts
   ble_receiver.py.

5. Python/Bleak searches for:
   ConcussionHeadband

6. Python subscribes to the Nordic UART TX
   characteristic.

7. IMU data is passed from Python to C.

8. C records the data for 20 seconds.

9. Press Q if the recording should stop early.

10. measurements.txt is saved.

11. GNUplot opens and plots:
    X, Y, Z and Total acceleration.
```

---

## Important Troubleshooting

### Device will not connect

Make sure the XIAO is not already connected to:

- Bluetooth LE Explorer
- a phone
- another Python process
- another copy of the C program

Because:

```text
CONFIG_BT_MAX_CONN=1
```

only one BLE connection is allowed.

Resetting the XIAO and closing other Bluetooth clients usually fixes this.

### Python cannot find `ble_receiver.py`

Make sure the file is named exactly:

```text
ble_receiver.py
```

and is in the same folder where `datastoragebt.exe` is being run.

### Check for old Python processes

In PowerShell:

```powershell
Get-Process python* -ErrorAction SilentlyContinue
```

To stop old Python receiver processes:

```powershell
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Check that Bleak is installed

```powershell
py -c "import bleak; print('Bleak installed')"
```

### GNUplot shows an old graph

Close old GNUplot windows before testing the newly compiled program.

If necessary:

```powershell
taskkill /F /IM wgnuplot.exe /T
```

Then rebuild:

```powershell
gcc datastoragebt.c -o datastoragebt.exe
```

and run:

```powershell
.\datastoragebt.exe
```

---

## Final Result

The completed system allows the XIAO to operate without a USB data connection:

```text
LSM6DSL IMU
     |
     v
XIAO nRF52840 Sense
     |
     | Bluetooth LE
     v
Python / Bleak
     |
     | pipe
     v
C data-storage program
     |
     +--> measurements.txt
     |
     +--> GNUplot
```

Python/Bleak is therefore used only as the bridge between **Windows BLE** and the existing **C data-storage/GNUplot program**, allowing the original C parsing and plotting workflow to remain largely unchanged.
