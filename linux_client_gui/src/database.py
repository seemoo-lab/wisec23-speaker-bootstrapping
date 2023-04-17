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

import sqlite3
import uuid as uuid_lib

class DB:
    con = None
    cur = None

    def __init__(self):
        # initialize database
        self.con = sqlite3.connect('speakerserver.db')
        self.con.commit()
        self.cur = self.con.cursor()

        # create tables if necessary
        #check for key-value settings table
        self.cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='keyval' ''')
        #if the count is 1, then table exists
        if self.cur.fetchone()[0]==0:
            self.cur.execute('''CREATE TABLE keyval (setting text, value text) ''')

        #check for key-value settings table
        self.cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users' ''')
        #if the count is 1, then table exists
        if self.cur.fetchone()[0]==0:
            self.cur.execute('''CREATE TABLE users (uuid text, name text, encrypt text, authenticate text, verify text) ''')


    def write_setting(self, setting, value):
        if self.cur != None and self.con != None:
            self.cur.execute("DELETE from keyval WHERE setting=?", (setting,))
            self.cur.execute("insert into keyval values (?, ?)", (setting, value))
            self.con.commit()

    def drop_settings(self):
        if self.cur != None and self.con != None:
            self.cur.execute("DELETE FROM keyval")
            self.con.commit()

    def read_setting(self, setting):
        if self.cur != None:
            self.cur.execute('''SELECT value from keyval WHERE setting=? ''', (setting,))
            return self.cur.fetchone()

    def insert_speaker(self, uuid, name, encrypt, authenticate, verify):
        if self.cur != None and self.con != None:
            self.drop_speaker(uuid)
            self.cur.execute("insert into users values (?, ?, ?, ?, ?)", (uuid, name, encrypt, authenticate, verify))
            self.con.commit()

    def num_speakers(self):
        if self.cur != None:
            self.cur.execute('''SELECT COUNT(*) from users''')
            return self.cur.fetchone()[0]

    def get_speakers(self):
        if self.cur != None:
            self.cur.execute('''SELECT uuid, name from users''')
            return self.cur.fetchall()

    def get_keys(self, name_or_uuid):
        if self.cur != None:
            self.cur.execute('''SELECT encrypt, authenticate, verify from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            return self.cur.fetchall()

    def drop_speaker(self, name_or_uuid):
        if self.cur != None:
            self.cur.execute('''SELECT encrypt, authenticate, verify from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            if(self.cur.fetchall() == []):
                return -1
            self.cur.execute('''DELETE from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            self.con.commit()
            return 0

    def drop_speakers(self):
        if self.cur != None:
            self.cur.execute('''DELETE from users''')
            self.con.commit()
            return 0

    def get_uuid(self):
        uuid = None
        if self.read_setting("UUID") != None:
            uuid = uuid_lib.UUID(self.read_setting("UUID")[0])
        else:
            uuid = uuid_lib.uuid4()
            self.write_setting("UUID",  str(uuid))
        return uuid

