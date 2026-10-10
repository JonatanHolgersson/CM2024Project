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

            # Send exact BLE data into datastoragebt.c

            sys.stdout.buffer.write(data)

            sys.stdout.buffer.flush()


        except (BrokenPipeError, OSError):

            # datastoragebt.c has finished and
            # closed its side of the pipe.

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

                await client.stop_notify(
                    TX_UUID
                )

            except Exception:

                pass


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        pass
