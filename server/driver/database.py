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

    # write a key-value-pair
    def write_setting(self, setting, value):
        if self.cur != None and self.con != None:
            self.cur.execute("DELETE from keyval WHERE setting=?", (setting,))
            self.cur.execute("insert into keyval values (?, ?)", (setting, value))
            self.con.commit()

    # delete all key value pairs
    def drop_settings(self):
        if self.cur != None and self.con != None:
            self.cur.execute("DELETE FROM keyval")
            self.con.commit()

    # get a key-value pair
    def read_setting(self, setting):
        if self.cur != None:
            self.cur.execute('''SELECT value from keyval WHERE setting=? ''', (setting,))
            return self.cur.fetchone()

    # insert user keys
    def insert_user(self, uuid, name, encrypt, authenticate, verify):
        if self.cur != None and self.con != None:
            self.drop_user(uuid)
            self.cur.execute("insert into users values (?, ?, ?, ?, ?)", (uuid, name, encrypt, authenticate, verify))
            self.con.commit()

    # get stored user entries
    def num_users(self):
        if self.cur != None:
            self.cur.execute('''SELECT COUNT(*) from users''')
            return self.cur.fetchone()[0]

    # get all users
    def get_users(self):
        if self.cur != None:
            self.cur.execute('''SELECT uuid, name from users''')
            return self.cur.fetchall()

    # get all keys
    def get_keys(self, name_or_uuid):
        if self.cur != None:
            self.cur.execute('''SELECT encrypt, authenticate, verify from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            return self.cur.fetchall()

    # delete user
    def drop_user(self, name_or_uuid):
        if self.cur != None:
            self.cur.execute('''SELECT encrypt, authenticate, verify from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            if(self.cur.fetchall() == []):
                return -1
            self.cur.execute('''DELETE from users WHERE uuid=? OR name=?''', (name_or_uuid, name_or_uuid))
            self.con.commit()
            return 0

    # delete all users
    def drop_users(self):
        if self.cur != None:
            self.cur.execute('''DELETE from users''')
            self.con.commit()
            return 0

    # get uuid, initialize it if not available
    def get_uuid(self):
        uuid = None
        if self.read_setting("UUID") != None:
            uuid = uuid_lib.UUID(self.read_setting("UUID")[0])
        else:
            uuid = uuid_lib.uuid4()
            self.write_setting("UUID",  str(uuid))
        return uuid

    # get pairmode, initialize it if unavailble
    def get_pairmode(self):
        pm = "always"
        if self.read_setting("pair_mode") != None:
            pm = self.read_setting("pair_mode")[0]
        else:
            self.write_setting("pair_mode",  pm)
        return pm
