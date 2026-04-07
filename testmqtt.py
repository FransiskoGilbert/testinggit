import RPi.GPIO as GPIO
import logging
import signal
import sys
import time
import csv
import json
from datetime import datetime
import paho.mqtt.client as mqtt

# ==============================
# GPIO CONFIG
# ==============================
PIN_PAIRS = {
    "MESIN_1": (4, 17),
    "MESIN_2": (27, 22),
    "MESIN_3": (5, 6),
    "MESIN_4": (13, 19),
    "MESIN_5": (26, 21),
    "MESIN_6": (20, 16),
}

PIN_TO_MACHINE = {}

# ==============================
# MQTT CONFIG
# ==============================
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_BASE_TOPIC = "factory/machine"

# ==============================
# CSV FILE
# ==============================
csv_file = open("log_mesin.csv", "a", newline="")
csv_writer = csv.writer(csv_file)

if csv_file.tell() == 0:
    csv_writer.writerow([
        "timestamp",
        "machine",
        "pin1_state",
        "pin2_state",
        "status"
    ])

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)

# ==============================
# MQTT CLIENT
# ==============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("MQTT connected")
    else:
        logging.info("MQTT connection failed")

def on_disconnect(client, userdata, rc):
    logging.info("MQTT disconnected, reconnecting...")

mqtt_client = mqtt.Client()

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)

mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, 60)

mqtt_client.loop_start()

# ==============================
# GPIO SETUP
# ==============================
GPIO.setmode(GPIO.BCM)

previous_state = {}

for machine, (pin1, pin2) in PIN_PAIRS.items():

    GPIO.setup(pin1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(pin2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    state = (GPIO.input(pin1), GPIO.input(pin2))

    previous_state[machine] = state

    PIN_TO_MACHINE[pin1] = machine
    PIN_TO_MACHINE[pin2] = machine

# ==============================
# STATUS DECODER
# ==============================
def decode_status(state):

    if state == (1,1):
        return "RUNNING"

    elif state == (1,0):
        return "IDLE"

    elif state == (0,0):
        return "OFF"

    elif state == (0,1):
        return "ERROR"

    return "UNKNOWN"

# ==============================
# INTERRUPT CALLBACK
# ==============================
def input_changed(channel):

    machine = PIN_TO_MACHINE[channel]
    pin1, pin2 = PIN_PAIRS[machine]

    time.sleep(0.0005)

    state = (
        GPIO.input(pin1),
        GPIO.input(pin2)
    )

    if state != previous_state[machine]:

        status = decode_status(state)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logging.info(
            f"{machine} -> {status} | pin({pin1},{pin2})={state}"
        )

        # CSV logging
        csv_writer.writerow([
            timestamp,
            machine,
            state[0],
            state[1],
            status
        ])
        csv_file.flush()

        # MQTT publish
        payload = {
            "machine": machine,
            "status": status,
            "pin1": state[0],
            "pin2": state[1],
            "timestamp": timestamp
        }

        topic = f"{MQTT_BASE_TOPIC}/{machine}/status"

        mqtt_client.publish(
            topic,
            json.dumps(payload),
            qos=1,
            retain=True
        )

        previous_state[machine] = state

# ==============================
# ENABLE INTERRUPTS
# ==============================
for pin in PIN_TO_MACHINE:

    GPIO.add_event_detect(
        pin,
        GPIO.BOTH,
        callback=input_changed,
        bouncetime=1
    )

print("Monitoring mesin dimulai...")

# ==============================
# CLEAN EXIT
# ==============================
def cleanup(sig, frame):

    print("\nProgram dihentikan")

    GPIO.cleanup()
    csv_file.close()
    mqtt_client.loop_stop()

    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)

signal.pause()
