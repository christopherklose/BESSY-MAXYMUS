#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 16 11:00:34 2017

@author: Michael Schneider mschneid@mbi-berlin.de
"""

import mwclient
from os import path, linesep
import tkinter
from tkinter.filedialog import askopenfilenames
from tkinter.simpledialog import askstring
from tkinter.messagebox import showinfo
from tkinter.simpledialog import Dialog
import sys


wikiurl = 'wiki1.mbi-berlin.de'


class gui_upload(object):
    def __init__(self):
        self.results = []
        self.root = tkinter.Tk()
        self.root.withdraw()

    def get_user(self):
        self.user = askstring('username', 'sg username')
        if self.user is None:
            self.root.destroy()
            sys.exit("Aborted")
            return

    def get_pass(self):
        self.passwd = askstring('password', 'sg wiki password', show='*')
        if self.passwd is None:
            self.root.destroy()
            sys.exit("Aborted")
        return

    def get_files(self):
        self.files = askopenfilenames(title='Select files to upload')
        if self.files is None:
            self.root.destroy()
            sys.exit("Aborted")
        return

    def connect(self, wikiurl):
        try:
            self.wiki = mwclient.Site(wikiurl, path='/sg/')
            self.wiki.login(self.user, self.passwd, domain='MBI-LDAP')
        except Exception as e:
            message = ('An error occured during login. '
                       'The error message was: ' + str(e))
            showinfo(wikiurl, message)
            self.root.destroy()
            sys.exit()
        return

    def upload(self):
        for fname in self.files:
            with open(fname, 'rb') as f:
                self.results.append(self.wiki.upload(f, path.split(fname)[-1], ignore=True))
        return

    def get_recent_changes(self):
        changes = self.wiki.recentchanges()
        changelist = []
        while len(changelist) <= 10:
            ch = changes.next()
            if ch['title'] not in changelist and ch['type'] != 'log':
                changelist.append(ch['title'])
        return changelist
    
    def write_gallery_string(self):
        gallerypage = asklistchoice('Add gallery statement to page?',
                                     self.get_recent_changes())
        if gallerypage != '':
            page = self.wiki.pages[gallerypage]
            gallerystring = '<gallery>\n'
            for f in self.files:
                gallerystring += 'Image: %s | \n' % path.split(f)[-1]
            gallerystring += '</gallery>'
            page.save(page.text(cache=False) + '\n' + gallerystring, minor=True)
        return

    def show_results(self):
        result_str = ''
        for f, r in zip(self.files, self.results):
            if 'warnings' in r.keys():
                warns = ['%s: %s\n' % (k, v) for k, v in r['warnings'].items()]
                result_str += linesep.join(warns)
            else:
                result_str += '%s: %s' % (f, r['result']) + linesep
        showinfo('upload summary', result_str)
        return

    def close_gui(self):
        self.root.destroy()


class _QueryListChoice(Dialog):
    def __init__(self, title, choices):
        self.choices = choices
        parent = tkinter._default_root
        Dialog.__init__(self, parent, title)
        
    def body(self, master):
        label = tkinter.Label(master, justify=tkinter.LEFT,
                              text='Or type in the page name here')
        label.grid(row=11, sticky=tkinter.W + tkinter.E)
        self.listbox = tkinter.simpledialog.Listbox(master)
        self.listbox.grid(row=1, rowspan=10, sticky=tkinter.NW)
        for item in self.choices:
            self.listbox.insert(tkinter.END, item)
        
        self.manual_entry = tkinter.Entry(master, name='wiki page')
        self.manual_entry.grid(row=10, sticky=tkinter.SW)
        return self.listbox
    
    def destroy(self):
        self.entry = None
        self.listbox = None
        Dialog.destroy(self)
    
    def validate(self):
        manual = self.manual_entry.get()
        if manual == '':
            index = self.listbox.curselection()[0]
            self.result = self.choices[index]
        else:
            self.result = manual
        return 1
    
    
def asklistchoice(title, choices, **kw):
    '''ask the user to select an item in a list.

    Arguments:

        title -- the dialog title
        prompt -- the string list of choices
        **kw -- see SimpleDialog class

    Return value is a string
    '''
    d = _QueryListChoice(title, choices, **kw)
    if d.result is None:
        return ''
    return d.result


if __name__ == "__main__":
    if '--nocertcheck' in sys.argv[1:]:
        import ssl
#        if True:
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context
    g = gui_upload()
    g.get_user()
    g.get_pass()
    g.connect(wikiurl)
    g.get_files()
    g.upload()
    g.write_gallery_string()
    g.show_results()
    g.close_gui()