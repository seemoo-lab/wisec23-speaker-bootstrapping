import threading
import driver.database as db
import time
import pairing
import driver.announce as an

# provide threaded framework for pairing procedure

blocked = False
sem_pairing_start = threading.Semaphore(0)
sem_access_blocked = threading.Semaphore(1)

#thread-safe function to read blocked variable
def get_blocked():
    sem_access_blocked.acquire()
    bl = blocked
    sem_access_blocked.release()
    return bl

#thread-safe function to write blocked variable
def set_blocked(bval):
    global blocked
    sem_access_blocked.acquire()
    blocked = bval
    sem_access_blocked.release()

#request pairing procedure to start
def request_pairing():
    if(get_blocked()):
        return False
    sem_pairing_start.release()
    return True

# check if initial pairing becomes necessary during runtime
# called as thread
def check_initial_necessary():
    dbcon = db.DB()
    while(True):
        if (dbcon.num_users() == 0) and get_blocked() == False:
            request_pairing()
        time.sleep(1)

# main loop that waits for any condition that requires pairing
# to start
def pairing_loop():
    while(True):
        dbcon = db.DB()
        sem_pairing_start.acquire() # wait for request
        print("pairing started!")
        set_blocked(True) # signal that pairing is running
        initial = dbcon.num_users() == 0 # find out if initial is necessary
        if(initial):
            an.disannounce() # if initial is necessary, disannounce service
        p_result = pairing.pair(dbcon.get_uuid(), initial)
        if(initial):
            an.announce() # if initial, reannounce service
        if(p_result[0]):
                # store new client to db
                dbcon.insert_user(str(p_result[1]), p_result[3], p_result[2][0], p_result[2][1], p_result[2][2])
        set_blocked(False) # signal that pairing is free to restart

# init function, creates threads
def init():
    pth = threading.Thread(target=pairing_loop)
    pth.daemon = True
    pth.start()

    wth = threading.Thread(target=check_initial_necessary)
    wth.daemon = True
    wth.start()

