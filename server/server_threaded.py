#
#Copyright (C) 2022 SEEMOO Lab TU Darmstadt (mscheck@seemoo.tu-darmstadt.de)
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import driver.pairing_thread as pt
import driver.database as db
import driver.sock_server.put_get as pg
import driver.wifi.wifi_control as ap
import driver.announce as an
import example_app as ea

# Main entry point
if __name__ == "__main__":
    print("SEEMOOSPEAKER Server")

    #initialize modules
    dbcon = db.DB() # database
    pt.init() # pairing thread
    pg.Tcp_server_init() # put-get for pairing
    an.announce() # service announcement
    ea.init() # example application

    #print UUID of this server
    print(dbcon.get_uuid())


    # command line
    # for debug purposes

    try:
        while True:
            command = input("> ")

            # help text

            if(command == "help"):
                print("""SpeakerServer

Available commands:

help                          - print this message
pair                          - bind new client
list                          - list bound clients
keys ( U:<uuid> | N:<name>)   - get keys for device
drop ( U:<uuid> | N:<name>)   - remove client
reset                         - delete all connected clients and drop generated UUID""")

            # List known clients   
            elif(command == "list"):
                # list users
                users = dbcon.get_users()
                for user in users:
                    print(user) 

            # list keys for one client
            elif(command[0:4] == "keys"):
                keys = dbcon.get_keys(command[5::]) # get from DB
                if keys == []:
                    print(f"No user with name or UUID {command[5::]} found")
                else:
                    print(keys)

            # delete a client
            elif(command[0:4] == "drop"):
                # remove user
                ret = dbcon.drop_user(command[5::])
                if ret == -1:
                    print(f"No user with name or UUID {command[5::]} found")

            # fully reset server
            elif(command == "reset"):
                    ap.purge_nm()
                    dbcon.drop_users()
                    dbcon.drop_settings()
                    an.disannounce()

    # teardown             
    finally:
        ea.close() # close example app
        ap.stop_ap() # teardown wifi ap if currently open
        pg.sock_teardown() # teardown put-get if open
