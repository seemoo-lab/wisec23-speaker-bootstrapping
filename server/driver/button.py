from evdev import InputDevice, categorize, ecodes
from select import select
import time

def measure_button_time(time_thr = None):
    dev = InputDevice('/dev/input/event0')
    ev_time = 0.0
    while True:

        ret = select([dev], [], [], 0.2)[0]
        if len(ret)>0:

            for event in filter(lambda a : a.code == 76, ret[0].read()):
                if event.value == 0: # down
                    ev_time = event.sec + event.usec * 0.000001
                elif event.value == 1: # up
                    if ev_time == 0.0:
                        raise Exception("Button was pressed before launch of measurement")
                    return event.sec + event.usec * 0.000001 - ev_time

        # also return if user presses button long enough
        if not time_thr == None and not ev_time == 0.0 and time.time() - ev_time > time_thr:
            return time_thr

def accept_or_reject(time_thr):
    return measure_button_time(time_thr) >= time_thr