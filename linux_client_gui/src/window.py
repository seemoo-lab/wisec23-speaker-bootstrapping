# window.py
#
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

from gi.repository import GLib

"""! @module UI definitions.
    Maps button presses to correct functions and instantiates windows.
    """

from . import pairing, listupdate, database, control, wifi_discovery
import threading
import random
from multiprocessing import Process, Queue
import sys
from gi.repository import Gtk, Gio, Adw

@Gtk.Template(resource_path='/de/seemoo/speakerclient/window.ui')
class LinuxClientGuiWindow(Gtk.Window):
    __gtype_name__ = 'LinuxClientGuiWindow'

    # get all Gtk Widgets
    # var name must match ID of Widget in UI XML
    naming_layout = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    wifi_layout = Gtk.Template.Child()
    word_select = Gtk.Template.Child()
    ssid = Gtk.Template.Child()
    wpass = Gtk.Template.Child()
    word1 = Gtk.Template.Child()
    word2 = Gtk.Template.Child()
    word3 = Gtk.Template.Child()
    word4 = Gtk.Template.Child()
    word5 = Gtk.Template.Child()
    spk_name = Gtk.Template.Child()
    img_layout = Gtk.Template.Child()
    img_view = Gtk.Template.Child()
    img_text = Gtk.Template.Child()

    def __init__(self, **kwargs):

        initial = kwargs['initial']
        del kwargs['initial']

        ip = kwargs['ip']
        del kwargs['ip']

        name = kwargs['name']
        del kwargs['name']

        super().__init__(**kwargs)
        self.wpass.set_visibility(False)
        self.wpass.set_invisible_char("*")
        pairing.run_pair(initial, self, ip, name)
        self.set_modal(True)
        



    # name setup screen

    spk_sem = None
    @Gtk.Template.Callback()
    def name_confirm(self, button):
        print("confirmed nw settings")
        if self.spk_sem != None:
            self.spk_sem.release()

    def set_wifi(self, ssid, psk):
        GLib.idle_add(self.ssid.set_text,ssid)
        GLib.idle_add(self.wpass.set_text,psk)

    # icon and text
    def show_icon_text(self, icon_name, text):
        GLib.idle_add(self.stack.set_visible_child,self.img_layout)
        GLib.idle_add(self.img_view.set_from_icon_name,icon_name)
        GLib.idle_add(self.img_text.set_label,text)

    def get_spkname(self):
        GLib.idle_add(self.stack.set_visible_child,self.naming_layout)
        self.spk_sem = threading.Semaphore(0)
        self.spk_sem.acquire()
        self.spk_sem = None

        return self.spk_name.get_text()

    # Network setup screen

    nw_sem = None
    @Gtk.Template.Callback()
    def nw_confirm(self, button):
        print("confirmed nw settings")
        if self.nw_sem != None:
            self.nw_sem.release()

    def get_wifi_settings(self):
        GLib.idle_add(self.stack.set_visible_child,self.wifi_layout)
        self.nw_sem = threading.Semaphore(0)
        self.nw_sem.acquire()
        self.nw_sem = None

        return (self.ssid.get_text(), self.wpass.get_text())


    # word select confirmation screen

    golden = None
    word_sem = None
    def check(self):
        if not self.get_realized():
            raise Exception("User aborted!")

    @Gtk.Template.Callback()
    def word_sel(self, button):
        if self.word_sem != None:
            if button.get_label() == self.golden:
                self.golden = True
                print("correct word")
            else:
                self.golden = False
                print("wrong word")
            self.word_sem.release()

    def get_word_select(self, words):
        GLib.idle_add(self.stack.set_visible_child,self.word_select)
        # get word buttons
        self.golden = words[0]

        random.shuffle(words)

        word_btn = (self.word1, self.word2, self.word3, self.word4, self.word5)

        for w in zip(word_btn, words):
            GLib.idle_add(w[0].set_label,w[1])

        self.word_sem = threading.Semaphore(0)
        self.word_sem.acquire()
        self.word_sem = None
        tmp = self.golden
        self.golden = None
        return tmp


    @Gtk.Template.Callback()
    def close_req(self, win):
        listupdate.update()
        pairing.error()



@Gtk.Template(resource_path='/de/seemoo/speakerclient/intro.ui')
class IntroWindow(Gtk.Window):
    __gtype_name__ = 'IntroWindow'

    # storage list of different items
    store = Gtk.ListStore(str, str, str)

    list_spk = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_resizable(True)

        # Create list view

        sel = self.list_spk.get_selection()
        sel.set_mode(0)
        self.list_spk.set_headers_visible(False)
        self.list_spk.set_activate_on_single_click(True)

        # column renderers
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn(cell_renderer=renderer, icon_name=0)
        column.set_expand(False)
        self.list_spk.append_column(column)
        #
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(cell_renderer=renderer, text=1, weight=1)
        column.set_expand(True)
        self.list_spk.append_column(column)
        #
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("del", cell_renderer=renderer, icon_name=2)
        column.set_expand(False)
        self.list_spk.append_column(column)

        # Add to main view
        self.list_spk.set_model(self.store)

        # example data
        self.store.append(["changes-prevent-symbolic",
                         "Paired\nUUID | IP", "user-trash-symbolic"])
        self.store.append(["changes-allow-symbolic",
                     f"Unpaired\nUUID | IP", ""])
        self.store.append(["preferences-desktop-screensaver-symbolic",
                         "Unavailable\nUUID | -", "user-trash-symbolic"])


@Gtk.Template(resource_path='/de/seemoo/speakerclient/main.ui')
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MainWindow'

    # storage list of different items
    store = Gtk.ListStore(str, str, str)

    list_spk = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    img_layout = Gtk.Template.Child()
    list_layout = Gtk.Template.Child()
    topBtn = Gtk.Template.Child()

    def stackupd(self):
        if(len(self.store) == 0):
            GLib.idle_add(self.stack.set_visible_child,self.img_layout)
        else:
            GLib.idle_add(self.stack.set_visible_child,self.list_layout)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_resizable(True)

        # Create list view

        sel = self.list_spk.get_selection()
        sel.set_mode(0)
        self.list_spk.set_headers_visible(False)
        self.list_spk.set_activate_on_single_click(True)

        # column renderers
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn(cell_renderer=renderer, icon_name=0)
        column.set_expand(False)
        self.list_spk.append_column(column)
        #
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(cell_renderer=renderer, text=1, weight=1)
        column.set_expand(True)
        self.list_spk.append_column(column)
        #
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("del", cell_renderer=renderer, icon_name=2)
        column.set_expand(False)
        self.list_spk.append_column(column)

        # Add to main view
        self.list_spk.set_model(self.store)

        listupdate.start(self.store, self)
        GLib.idle_add(listupdate.update)

        # discover mint speakers
        GLib.idle_add(self.topBtn.set_sensitive, False)
        GLib.idle_add(self.topBtn.set_tooltip_text,"No new speaker nearby")
        wifi_discovery.start(self.topBtn)

        dbcon = database.DB()
        if dbcon.read_setting("firstuse") == None:
            win = IntroWindow(parent=self)
            win.set_transient_for(self)
            win.present()
            dbcon.write_setting("firstuse", "yes")


    @Gtk.Template.Callback()
    def cell_hover(self, tree):
        pass

    @Gtk.Template.Callback()
    def row_clicked(self, tree, path, focus_col):
        path, focus_col = tree.get_cursor()
        print(f"cell clicked {path} {focus_col}")
        # ignore initial treeview selection
        if focus_col != None and path != None:
            row = self.store[path]

            dat = row[1].split()
            name = row[1].split('\n')[0]
            uuid_spk = dat[-3]
            ip_spk = dat[-1]

            if focus_col.get_title() == "del" and row[0] != "changes-allow-symbolic":
                database.DB().drop_speaker(uuid_spk)
                GLib.idle_add(listupdate.update)
                return

            # already paired speaker
            if row[0] == "changes-prevent-symbolic":
                print("paired spk selected")
                win = ControlWindow(parent=self, ip=ip_spk, uuid=uuid_spk)
                win.set_transient_for(self)
                win.present()
            elif row[0] == "changes-allow-symbolic":
                print("unpaired spk selected")
                pair_window(self, False, ip_spk, name)
            else:
                print("unavailable spk selected")



    @Gtk.Template.Callback()
    def add(self, button):
        #self.topBtn.set_icon_name("go-first-symbolic")
        pair_window(self, True)

def pair_window(parent, initial, ip = None, name = None):
    win = LinuxClientGuiWindow(parent=parent, initial=initial, ip=ip, name=name)
    win.set_transient_for(parent)
    win.present()

@Gtk.Template(resource_path='/de/seemoo/speakerclient/control.ui')
class ControlWindow(Gtk.Window):
    __gtype_name__ = 'ControlWindow'

    cb_tim = Gtk.Template.Child()
    cb_exp = Gtk.Template.Child()
    cb_alw = Gtk.Template.Child()
    allow_btn = Gtk.Template.Child()

    socket = None
    ip = None
    uuid = None

    def __init__(self, **kwargs):
        self.ip = kwargs['ip']
        del kwargs['ip']

        self.uuid = kwargs['uuid']
        del kwargs['uuid']

        super().__init__(**kwargs)
        self.set_modal(True)

        self.socket = control.start(self, self.ip)

        #turn toggles into radiobuttons
        self.cb_alw.set_group(self.cb_tim)
        self.cb_alw.set_group(self.cb_exp)
        self.cb_tim.set_group(self.cb_exp)

        #start bg thread
        control.run_infoservice(self, self.socket, self.uuid)


    def socket_closed(self):
        
        # add GNOME notification
        self.close()
        self.destroy()

    @Gtk.Template.Callback()
    def playb(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "PLAY", "")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def stopb(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "STOP", "")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def less(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "LESS", "")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def more(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "MORE", "")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def always(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "PMOD", "always")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def explicit(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "PMOD", "explicit")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def timer(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "PMOD", "timer")
        except:
            self.socket_closed()

    @Gtk.Template.Callback()
    def allow(self, button):
        try:
            control.send_cmd(self.socket, self.uuid, "PAIRALLOW", "")
        except:
            self.socket_closed()

    def set_pairmode(self, pm, time_rem, wait):
        if pm == 'explicit':
            GLib.idle_add(self.cb_exp.set_active,True)
            GLib.idle_add(self.allow_btn.set_label, "Allow pairing")
            GLib.idle_add(self.allow_btn.set_sensitive, wait)
        elif pm == 'timer':
            GLib.idle_add(self.cb_tim.set_active,True)
            if time_rem <= 0:
                GLib.idle_add(self.allow_btn.set_label, "Allow pairing")
                GLib.idle_add(self.allow_btn.set_sensitive, True)
            else:
                GLib.idle_add(self.allow_btn.set_label, "Pairing already allowed")
                GLib.idle_add(self.allow_btn.set_sensitive, False)
        else:
            GLib.idle_add(self.cb_alw.set_active,True)
            GLib.idle_add(self.allow_btn.set_label, "Pairing always allowed")
            GLib.idle_add(self.allow_btn.set_sensitive, False)

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'SEEMOO Speaker Client'
        self.props.version = "0.1.0"
        self.props.authors = ['Markus Scheck (Student)', 'Florentin Putz (Advisor)']
        self.props.copyright = '2022 Markus Scheck @ SEEMOO Lab | Technische Universität Darmstadt'
        self.props.logo_icon_name = 'audio-volume-high'
        self.props.modal = True
        self.set_transient_for(parent)
