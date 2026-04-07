import RPi.GPIO as GPIO
import time
import logging
import signal
import sys

PIN_PAIRS = {
"MESIN_1": (4, 17),
"MESIN_2": (27, 22),
"MESIN_3": (5, 6),
"MESIN_4": (13,19),
"MESIN_5": (26, 21),
"MESIN_6": (20, 16),
}

PIN_TO_MACHINE = {}

logging.basicConfig(
level = logging.INFO,
format="%(asctime)s = %(message)s",
datefmt="%H:%M:%S"
)

GPIO.setmode(GPIO.BCM)

previous_state = {}
machine_status = {}

for machine, (pin1,pin2) in PIN_PAIRS.items():
	GPIO.setup(pin1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.setup(pin2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

	state = (GPIO.input(pin1), GPIO.input(pin2))

	previous_state[machine] = state
	machine_status[machine] = None

	PIN_TO_MACHINE[pin1] = machine
	PIN_TO_MACHINE[pin2] = machine

def decode_status(state):
	if state == (1,1):
		return "RUNNING"
	if state == (1,0):
		return "IDLE"
	if state == (0,0):
		return "OFF"
	if state == (0,1):
		return "ERROR"
	else:
		return "UNKNOWN"

def input_changed(channel):

	machine = PIN_TO_MACHINE[channel]
	pin1, pin2 = PIN_PAIRS[machine]

	time_sleep(0.1)

	current_state = (
		GPIO.input(pin1),
		GPIO.input(pin2)
	)

	if current_state != previous_state[machine]:

		status = decode_status(current_state)

		logging.info(
			f"{machine} -> "
			f"Pin({pin1},{pin2}) = {current_state} "
			f"Status = {status}"
		)

		previous_state[machine] = current_state
		machine_status[machine] = status

for pin in PIN_TO_MACHINE.keys():
	GPIO.add_event_detect(
		pin ,
		GPIO.BOTH,
		callback = input_changed,
		bouncetime=1
	)

print("Monitoring status mesin mulai....")

def cleanup(sig,frame):
	print("\nProgram dihentikan")
	GPIO.cleanup()
	sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.pause()
