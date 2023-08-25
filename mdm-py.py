#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
from tkinter import *
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.scrolledtext
import tkinter.messagebox
import sys
import re

DownloadEverything = 0
try:
    import mont_demont as mont_demont_py
    import znajdz_wystajace
    import mdmkreatorOsmAnd
except ImportError:
    DownloadEverything = 1


if sys.version_info[0] < 3:
    sys.stderr.write(
        'u\nUżywasz	pythona w wersji %s.%s.%s\n' % (sys.version_info[0], sys.version_info[1], sys.version_info[2]))
    sys.stderr.write("Wymagany jest python w wersji conajmniej 3.\n")
    sys.exit(1)
# import	codecs
# import	locale
import os
import hashlib
import difflib
import threading
import queue
import shutil
import platform
import zipfile
import datetime
import subprocess
import time
import urllib.request
import urllib.error
from collections import defaultdict


def sprawdz_czy_cvs_obecny():
    Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
    if shutil.which('cvs') or shutil.which('cvs', path=Zmienne.KatalogzUMP):
        return ''
    if platform.system() == 'Windows':
        return 'Nie odnalazłem programu cvs. Ściągnij go poprzez menu->Pobierz do katalogu ze środłami mapy.'
    else:
        return 'Nie odnalazłem programu cvs. Zainstaluj go.'


def cvs_sprawdz_czy_tylko_dozwolone_klucze_i_brak_konfliktow(pliki_do_sprawdzenia, zmienne):
    """
    funkcja sprawdza czy w plikach zaznaczonych do commitu sa tylko dozwolone klucze, jesli sa niedozwolone
    to zwraca ich nazwy w postaci tupli, jesli nie ma zwraca pusta tuple
    dodatkowo sprawddzamy obecnosc konfliktow
    :param pliki_do_sprawdzenia = nazwy plikow do sprawdzenia, zmienne = inicjowane zmienne
    :return (pliki_z_niepoprawnymi_kluczami, pliki_z_konfliktami)
    """
    pliki_z_niepoprawnymi_kluczami = defaultdict(lambda: set())
    pliki_z_konfliktami = set()
    for n_pliku in pliki_do_sprawdzenia:
        nazwa_pliku = os.path.join(zmienne.KatalogzUMP, n_pliku)
        with open(nazwa_pliku, 'r', encoding=zmienne.Kodowanie, errors=zmienne.ReadErrors) as plik_w_cvs:
            for zawartosc in plik_w_cvs.readlines():
                if zawartosc.startswith(';'):
                    continue
                if zawartosc.startswith("<<<<<<<") or zawartosc.startswith("=======") \
                        or zawartosc.startswith(">>>>>>>"):
                    pliki_z_konfliktami.add(n_pliku)
                if n_pliku.endswith('.txt') and '=' in zawartosc:
                    klucz, wartosc = zawartosc.split('=', 1)
                    if klucz in mont_demont_py.TestyPoprawnosciDanych.DOZWOLONE_KLUCZE or \
                            klucz in mont_demont_py.TestyPoprawnosciDanych.DOZWOLONE_KLUCZE_PRZESTARZALE:
                        continue
                    else:
                        klucz_z_numerem_znaleziony = False
                        for k_z_numerem in mont_demont_py.TestyPoprawnosciDanych.DOZWOLONE_KLUCZE_Z_NUMEREM:
                            if klucz.startswith(k_z_numerem):
                                klucz_z_numerem_znaleziony = True
                                break
                        if not klucz_z_numerem_znaleziony:
                            pliki_z_niepoprawnymi_kluczami[n_pliku].add(klucz)
    return pliki_z_niepoprawnymi_kluczami, pliki_z_konfliktami


def pobierz_pliki_z_internetu(temporary_file, url, inputqueue):

    nazwa_pliku = url.split('/')[-1]
    try:
        u = urllib.request.urlopen(url)
        meta = u.info()
        print(meta['Content-Length'])
        inputqueue.put(('max', '100',))
        filesize = int(meta['Content-Length'])
        print("Downloading: %s Bytes: %s" % (nazwa_pliku, filesize))
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            # f.write(buffer)
            temporary_file.write(buffer)
            inputqueue.put(('act', str(int(file_size_dl * 100 / filesize)),))
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / filesize)
            status = status + chr(8) * (len(status) + 1)
            sys.stdout.write(status)
            sys.stdout.flush()
            # print(status)

    except urllib.error.HTTPError:
        print('Nie moge sciagnac pliku:' + nazwa_pliku)
        return
    temporary_file.close()
    inputqueue.put(('koniec', 'koniec', ))


def createToolTip(widget, text):
    toolTip = ToolTip(widget)

    def enter(event):
        toolTip.schedule(text)

    def leave(event):
        toolTip.unschedule()
        toolTip.hidetip()

    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)


class CvsAnnotate(tkinter.Toplevel):
    def __init__(self, parent, zmienne, *args, **kwargs):
        self.log_annotate_file = os.path.join(os.path.expanduser('~'), '.log_annotate_file')
        self.parent = parent
        self.zmienne = zmienne
        self.annotate_log_content = list()
        self.log_content = list()
        self.cursor_index = '1.0'
        self.text_widgets = {'annotate': None, 'revision_log': None, 'log': None}
        self.annotate_log_content = {'annotate': [], 'log': []}
        self.revision_log = None
        super().__init__(parent, *args, **kwargs)
        body = tkinter.Frame(self)
        body.pack(padx=5, pady=5, fill='both', expand=1)
        buttons_frame = tkinter.Frame(body)
        buttons_frame.pack(fill='x')
        self.cvs_f_name_var = tkinter.StringVar()
        # self.cvs_f_name = tkinter.Label(buttons_frame, textvariable=self.cvs_f_name_var, width=60, bg='ivory2')
        self.cvs_f_name = tkinter.ttk.Combobox(buttons_frame, textvariable=self.cvs_f_name_var, width=60)
        self.cvs_f_name.pack(side='left')
        self.cvs_f_name['values'] = self.wczytaj_log_annotate()
        if self.cvs_f_name['values']:
            self.cvs_f_name_var.set(self.cvs_f_name['values'][0])
        sel_file_button = tkinter.ttk.Button(buttons_frame, text=u'Wybierz plik', command=self.wybierz_plik)
        sel_file_button.pack(side='left')
        rev_label = tkinter.Label(buttons_frame, text=u'Numer rewizji/tag')
        rev_label.pack(side='left')
        self.rev_var = tkinter.StringVar()
        rev_entry = tkinter.Entry(buttons_frame, textvariable=self.rev_var)
        rev_entry.pack(side='left')
        date_label = tkinter.Label(buttons_frame, text=u'Data commitu')
        date_label.pack(side='left')
        self.date_var = tkinter.StringVar()
        date_entry = tkinter.Entry(buttons_frame, textvariable=self.date_var)
        date_entry.pack(side='left')
        annotate_log_button = tkinter.ttk.Button(buttons_frame, text=u'Annotate/Log', command=self.run_cvs_log_cvs_annotate_save_results)
        annotate_log_button.pack(side='left')
        close_button = tkinter.ttk.Button(buttons_frame, text=u'Zamknij', command=self.destroy)
        close_button.pack(side='left')
        self.log_annotate_nbook = tkinter.ttk.Notebook(body)
        self.log_annotate_nbook.pack(fill='both', expand=1)
        annotate_text_frame = tkinter.Frame(self.log_annotate_nbook)
        annotate_text_frame.pack(fill='both', expand=1)
        log_text_frame = tkinter.Frame(self.log_annotate_nbook)
        log_text_frame.pack(fill='both', expand=1)
        self.text_widgets['annotate'] = tkinter.scrolledtext.ScrolledText(annotate_text_frame)
        self.text_widgets['annotate'].pack(fill='both', expand=1)
        revision_log_diff_frame = tkinter.Frame(annotate_text_frame)
        revision_log_diff_frame.pack(expand=1, fill='x')
        self.text_widgets['revision_log'] = tkinter.scrolledtext.ScrolledText(revision_log_diff_frame, height=10)
        self.text_widgets['revision_log'].pack(fill='x', side='left', expand=1)
        self.text_widgets['diff_log'] = tkinter.scrolledtext.ScrolledText(revision_log_diff_frame, height=10)
        self.text_widgets['diff_log'].pack(fill='x', side='left', expand=1)
        self.text_widgets['log'] = tkinter.scrolledtext.ScrolledText(log_text_frame)
        self.text_widgets['log'].pack(fill='both', expand=1)
        self.log_annotate_nbook.add(annotate_text_frame, text='annotate')
        self.log_annotate_nbook.add(log_text_frame, text='log')
        wysz_filtracja_frame = tkinter.ttk.LabelFrame(body, text=u'Wyszukiwanie i filtracja')
        wysz_filtracja_frame.pack(fill='x')
        wysz_label = tkinter.Label(wysz_filtracja_frame, text=u'Szukaj')
        wysz_label.pack(side='left')
        self.wyszukaj_var = tkinter.StringVar()
        wyszukaj_entry = tkinter.Entry(wysz_filtracja_frame, textvariable=self.wyszukaj_var)
        wyszukaj_entry.pack(side='left', fill='x', expand=1)
        wyszukaj_entry.bind('<Return>', self.wyszukaj_w_dol_bind)
        wyszukaj_entry.bind('<Up>', self.wyszukaj_w_gore_bind)
        wyszukaj_entry.bind('<Down>', self.wyszukaj_w_dol_bind)
        szukaj_w_gore = tkinter.ttk.Button(wysz_filtracja_frame, text='<<', command=self.wyszukaj_w_gore)
        szukaj_w_gore.pack(side='left')
        szukaj_w_dol = tkinter.ttk.Button(wysz_filtracja_frame, text='>>', command=self.wyszukaj_w_dol)
        szukaj_w_dol.pack(side='left')
        pokaz_zawierajace_label = tkinter.Label(wysz_filtracja_frame, text=u'Pokaż linie zawierające tylko (RegEx)')
        pokaz_zawierajace_label.pack(side='left')
        self.pokaz_zawierajace_var = tkinter.StringVar()
        pokaz_zawierajace_entry = tkinter.Entry(wysz_filtracja_frame, textvariable=self.pokaz_zawierajace_var)
        pokaz_zawierajace_entry.pack(side='left', expand=1, fill='x')
        pokaz_zawierajace_entry.bind('<Return>', self.filtruj_bind)
        filtruj_button = tkinter.ttk.Button(wysz_filtracja_frame, text=u'Filtruj', command=self.filtruj)
        filtruj_button.pack(side='left')
        self.text_widgets['annotate'].tag_config('revision', foreground='red')
        self.text_widgets['annotate'].tag_bind('revision', '<Button-1>', self.revision_clicked)
        self.text_widgets['annotate'].tag_bind('revision', '<Double-Button-1>', self.revision_double_clicked)
        self.text_widgets['annotate'].tag_config('podswietl', background='yellow')
        self.text_widgets['log'].tag_config('podswietl', background='yellow')
        self.transient(self.parent)
        self.focus_set()
        self.grab_set()
        self.wait_window(self)

    def wczytaj_log_annotate(self):
        try:
            with open(self.log_annotate_file, 'r') as logfile:
                return [a.strip() for a in logfile.readlines()]
        except (FileNotFoundError, IOError):
            return []

    def zapisz_log_annotate(self):
        try:
            with open(self.log_annotate_file, 'w') as logfile:
                for no, file_n in enumerate(self.cvs_f_name['values']):
                    logfile.write(file_n + '\n')
                    if no > 20:
                        break
        except IOError:
            return


    def wybierz_plik(self):
        plik_do_annotate = tkinter.filedialog.askopenfilename(title=u'Plik cvs do adnotacji',
                                                              initialdir=self.zmienne.KatalogzUMP)
        if plik_do_annotate:
            if self.cvs_f_name['values']:
                if plik_do_annotate not in self.cvs_f_name['values']:
                    self.cvs_f_name['values'] = [plik_do_annotate] + list(self.cvs_f_name['values'])
            else:
                self.cvs_f_name['values'] = [plik_do_annotate]
            self.cvs_f_name_var.set(plik_do_annotate)
            self.zapisz_log_annotate()

    def cvs_command(self, cvs_command, revision1, revision2):
        f_name = self.cvs_f_name_var.get()
        if not f_name:
            return
        else:
            f_name = os.path.relpath(f_name, self.zmienne.KatalogzUMP)
        CVSROOT = '-d:pserver:' + self.zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        os.chdir(self.zmienne.KatalogzUMP)
        cvs_commandline = ['cvs', CVSROOT, cvs_command]
        if cvs_command == 'annotate' and self.rev_var.get():
            cvs_commandline += ['-r', self.rev_var.get()]
        if cvs_command == 'annotate' and self.date_var.get():
            cvs_commandline += ['-d', self.date_var.get()]
        if cvs_command == 'diff':
            cvs_commandline += ['-u', '-r', revision1, '-r', revision2]
        process = subprocess.Popen(cvs_commandline + [f_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stdout:
            lines_to_print = stdout.decode(self.zmienne.Kodowanie, errors='backslashreplace')
        elif stderr:
            lines_to_print = stderr.decode(self.zmienne.Kodowanie, errors='backslashreplace')
        else:
            lines_to_print = []
        output_str = ''
        log_list = []
        for literka in lines_to_print:
            output_str += literka
            if literka == '\n':
                log_list.append(output_str)
                output_str = ''
        return log_list


    def run_cvs_log_cvs_annotate_save_results(self):
        self.annotate_log_content['annotate'] = self.cvs_command('annotate', '', '')
        self.annotate_log_content['log'] = self.cvs_command('log', '', '')
        self.wypelnij_okno_annotate('')
        self.wypelnij_okno_log('')

    def wypelnij_okno_annotate(self, reg_expr):
        self.text_widgets['annotate'].delete('1.0', 'end')
        for l_no, line in enumerate(self.annotate_log_content['annotate']):
            if not reg_expr or reg_expr and re.search(reg_expr, line) is not None:
                ind_start = self.text_widgets['annotate'].index('insert')
                ind_end = ind_start.split('.', 1)[0] + '.' + str(line.find(' '))
                self.text_widgets['annotate'].insert('insert', line)
                self.text_widgets['annotate'].tag_add('revision', ind_start, ind_end)

    def wypelnij_okno_log(self, reg_expr):
        self.text_widgets['log'].delete('1.0', 'end')
        revision = ''
        revision_log = defaultdict(str)
        for line in self.annotate_log_content['log']:
            if not reg_expr or reg_expr and re.search(reg_expr, line) is not None:
                self.text_widgets['log'].insert('insert', line)
            if line.startswith('revision'):
                revision = line.rstrip()
            elif line.startswith('-----') or line.startswith('====='):
                revision = ''
            if revision:
                revision_log[revision] += line
        self.revision_log = {a: revision_log[a] for a in revision_log}

    def wyszukaj_w_gore_bind(self, event):
        self.wyszukaj(forwards=False, backwards=True)

    def wyszukaj_w_gore(self):
        self.wyszukaj(forwards=False, backwards=True)

    def wyszukaj_w_dol_bind(self, event):
        self.wyszukaj(forwards=True, backwards=False)

    def wyszukaj_w_dol(self):
        self.wyszukaj(forwards=True, backwards=False)

    def wyszukaj(self, forwards=None, backwards=None):
        tabname = self.log_annotate_nbook.tab(self.log_annotate_nbook.select(), option='text')
        if self.wyszukaj_var.get():
            found_index = self.text_widgets[tabname].search(self.wyszukaj_var.get(), self.cursor_index,
                                                            backwards=backwards, forwards=forwards, nocase=True)
            if found_index:
                self.text_widgets[tabname].tag_remove('podswietl', '1.0', 'end')
                line_n, char_n = found_index.split('.', 1)
                found_end_index = line_n + '.' + str(int(char_n) + len(self.wyszukaj_var.get()))
                self.text_widgets[tabname].tag_add('podswietl', found_index, found_end_index)
                self.text_widgets[tabname].see(found_index)
                if forwards:
                    self.cursor_index = found_end_index
                else:
                    self.cursor_index = found_index
            else:
                if forwards:
                    self.cursor_index = '1.0'
                else:
                    self.cursor_index = 'end'

    def filtruj_bind(self, event):
        tabname = self.log_annotate_nbook.tab(self.log_annotate_nbook.select(), option='text')
        reg_expr = self.pokaz_zawierajace_var.get()
        if tabname == 'annotate':
            self.wypelnij_okno_annotate(reg_expr)
        else:
            self.wypelnij_okno_log(reg_expr)

    def filtruj(self):
        self.filtruj_bind(None)

    def revision_clicked(self, event):
        row = self.text_widgets['annotate'].index('current').split('.')[0]
        revision = self.annotate_log_content['annotate'][int(row) - 1].split(' ', 1)[0]
        self.text_widgets['revision_log'].delete('1.0', 'end')
        self.text_widgets['revision_log'].insert('insert', self.revision_log['revision ' + revision])

    def revision_double_clicked(self, event):
        self.revision_clicked(event)
        row = self.text_widgets['annotate'].index('current').split('.')[0]
        revision = self.annotate_log_content['annotate'][int(row) - 1].split(' ', 1)[0]
        if revision.count('.') == 1:
            rev_main, rev_side = revision.split('.')
            if rev_side not in ('0', '1'):
                revision0 = rev_main + '.' + str(int(rev_side) - 1)
                self.text_widgets['diff_log'].delete('1.0', 'end')
                for line in self.cvs_command('diff', revision0, revision):
                    self.text_widgets['diff_log'].insert('insert', line)


class PaczujResult(tkinter.Toplevel):
    """klasa przechowuje okienko w którym pokazywane są wyniki łatania plików"""
    def __init__(self, parent, spaczowane_pliki, *args, **kwargs):
        """
        spaczowane_pliki = dict() załatanych plików, gdzie klucz to nazwa pliku, wartość to wynik łatania
        wartości mogą przyjować wartość 0, 1, 2 gdzie 0 to ok, 1 udało się z małymi problemami, 2 i więcej jest
        dramat
        """
        super().__init__(parent, *args, **kwargs)
        self.spaczowane_pliki = spaczowane_pliki
        self.body = tkinter.Frame(self)
        self.body.pack(padx=5, pady=5, fill='both', expand=1)
        self.wypelnij_spaczowane_pliki()
        self.initial_focus = self.focus_set()
        self.grab_set()


    def wypelnij_spaczowane_pliki(self):
        canvas_i_scroll_pionowy = tkinter.Frame(self.body)
        canvas_i_scroll_pionowy.pack(expand=True, fill='both')
        ramka_pliku_canvas = tkinter.Canvas(canvas_i_scroll_pionowy, width=900, height=500)
        ramka_pliku_canvas.pack(side='left', anchor='n')
        belka_przewijania_pionowa = tkinter.ttk.Scrollbar(canvas_i_scroll_pionowy, orient='vertical',
                                                          command=ramka_pliku_canvas.yview)
        belka_przewijania_pionowa.pack(side='right', fill='y')
        belka_przewijania_pozioma = tkinter.ttk.Scrollbar(self.body, orient='horizontal',
                                                          command=ramka_pliku_canvas.xview)
        belka_przewijania_pozioma.pack(fill='x')
        ramka_pliku_canvas.config(xscrollcommand=belka_przewijania_pozioma.set,
                                  yscrollcommand=belka_przewijania_pionowa.set)
        ramka_pliku = tkinter.Frame(ramka_pliku_canvas)

        wynik_paczowania_frame = tkinter.Frame(ramka_pliku)
        wynik_paczowania_frame.pack(anchor='w', expand=True)
        nazwa_pliku_label = tkinter.Label(wynik_paczowania_frame, width=100, text='Nazwa pliku', relief='groove')
        nazwa_pliku_label.pack(side='left')
        status_latania_label = tkinter.Label(wynik_paczowania_frame, width=15, text=u'Status łatania', relief='groove')
        status_latania_label.pack(side='left')
        mozliwe_akcje_label = tkinter.Label(wynik_paczowania_frame, text=u'Możliwe akcje', relief='groove')
        mozliwe_akcje_label.pack(side='right')
        for nazwa_pliku in self.spaczowane_pliki:
            wynik_paczowania_frame = tkinter.Frame(ramka_pliku)
            wynik_paczowania_frame.pack(anchor='w', expand=True)
            nazwa_pliku_label = tkinter.Label(wynik_paczowania_frame, width=100, text=nazwa_pliku)
            nazwa_pliku_label.pack(side='left')
            if self.spaczowane_pliki[nazwa_pliku] == 0:
                status_latania = 'OK'
                kolor_statusu = 'green'
            elif self.spaczowane_pliki[nazwa_pliku] == 1:
                status_latania = 'z problemami'
                kolor_statusu = 'yellow'
            else:
                status_latania = 'katastrofa'
                kolor_statusu = 'red'
            status_latania_label = tkinter.Label(wynik_paczowania_frame, width=15, text=status_latania,
                                                 bg=kolor_statusu)
            status_latania_label.pack(side='left')
            zobacz_plik_button = tkinter.Button(wynik_paczowania_frame, text='Zobacz')
            zobacz_plik_button.pack(side='right')
        ramka_pliku_canvas.create_window(30, 30, window=ramka_pliku, anchor='nw')
        ramka_pliku_canvas.update_idletasks()
        ramka_pliku_canvas.config(scrollregion=ramka_pliku_canvas.bbox("all"))


class ModulCVS(object):
    def __init__(self):
        self.modulyCVS = {'AUSTRIA': ['UMP-AT-Graz', 'UMP-AT-Innsbruck', 'UMP-AT-Linz', 'UMP-AT-Wien'],
                          'BALKANY': ['UMP-Albania', 'UMP-Bosnia', 'UMP-Bulgaria', 'UMP-Chorwacja', 'UMP-Czarnogora',
                                      'UMP-Grecja', 'UMP-Kosowo', 'UMP-Macedonia', 'UMP-Moldawia', 'RUMUNIA',
                                      'UMP-Serbia', 'UMP-Slowenia', 'UMP-Turcja'],
                          'BRYTANIA': ['UMP-GB-Belfast', 'UMP-GB-Edinburgh', 'UMP-GB-Bristol', 'UMP-GB-Leeds',
                                       'UMP-GB-Leicester', 'UMP-GB-London', 'UMP-GB-Manchester', 'UMP-GB-Plymouth'],
                          'CZECHY': ['UMP-CZ-Brno', 'UMP-CZ-Budejovice', 'UMP-CZ-Jihlava', 'UMP-CZ-KarlovyVary',
                                     'UMP-CZ-Olomouc', 'UMP-CZ-Ostrava', 'UMP-CZ-Pardubice', 'UMP-CZ-Plzen',
                                     'UMP-CZ-Praha'],
                          'DANIA': ['UMP-Dania', 'UMP-WyspyOwcze'],
                          'ESTONIA': ['UMP-EE-Tallin', 'UMP-EE-Tartu'],
                          'EUROPA': ['BALKANY', 'NIEMCY', 'SKANDYNAWIA', 'BRYTANIA', 'UMP-Andora', 'AUSTRIA',
                                     'UMP-Belgia', 'UMP-Bialorus', 'UMP-Cypr', 'CZECHY', 'ESTONIA', 'FRANCJA',
                                     'HISZPANIA', 'HOLANDIA', 'UMP-Irlandia', 'UMP-RU-Krolewiec', 'UMP-Lichtenstein',
                                     'UMP-Litwa', 'UMP-Lotwa', 'UMP-Luksemburg', 'UMP-Malta', 'PORTUGALIA', 'ROSJA',
                                     'UMP-Slowacja', 'UMP-Szwajcaria', 'UMP-Ukraina', 'UMP-Wegry', 'WLOCHY'],
                          'FINLANDIA': ['UMP-FI-Helsinki', 'UMP-FI-Oulu', 'UMP-FI-Tampere', 'UMP-FI-Vaasa'],
                          'FRANCJA': ['UMP-FR-Ajaccio', 'UMP-FR-ClermontFerrand', 'UMP-FR-Dijon', 'UMP-FR-LeHavre',
                                      'UMP-FR-Lille', 'UMP-FR-Limoges', 'UMP-FR-Lyon', 'UMP-FR-Marseille',
                                      'UMP-FR-Montpellier', 'UMP-FRpantes', 'UMP-FR-Orleans', 'UMP-FR-Paris',
                                      'UMP-FR-Rennes', 'UMP-FR-SaintEtienne', 'UMP-FR-Strasbourg', 'UMP-FR-Toulouse'],
                          'HISZPANIA': ['UMP-ES-Madrid', 'UMP-ES-Kanary', 'UMP-ES-Albacete', 'UMP-ES-Badajoz',
                                        'UMP-ES-Barcelona', 'UMP-ES-Gijon', 'UMP-ES-Murcia', 'UMP-ES-Palma',
                                        'UMP-ES-Sevilla', 'UMP-ES-Valencia', 'UMP-ES-Valladolid', 'UMP-ES-Vigo',
                                        'UMP-ES-Zaragoza'],
                          'HOLANDIA': ['UMP-NL-Amsterdam', 'UMP-NL-Eindhoven', 'UMP-NL-Groningen', 'UMP-NL-Rotterdam',
                                       'UMP-NL-Tilburg', 'UMP-NL-Utrecht', 'UMP-NL-Zwolle'],
                          'NIEMCY': ['UMP-DE-Baden', 'UMP-DE-Bayern', 'UMP-DE-Brandenburg', 'UMP-DE-Hessen',
                                     'UMP-DE-Mecklenburg', 'UMP-DE-Niedersachsen', 'UMP-DE-Rheinland', 'UMP-DE-Sachsen',
                                     'UMP-DE-SachsenAnhalt', 'UMP-DE-Schleswig', 'UMP-DE-Thuringen',
                                     'UMP-DE-Westfalen'],
                          'NORWEGIA': ['UMP-NO-Alta', 'UMP-NO-Bergen', 'UMP-NO-Tromso', 'UMP-NO-Trondheim',
                                       'UMP-NO-Oslo'],
                          'POLSKA': ['UMP-PL-Warszawa', 'UMP-PL-Bialystok', 'UMP-PL-Ciechanow', 'UMP-PL-Gdansk',
                                     'UMP-PL-GorzowWlkp', 'UMP-PL-JeleniaGora', 'UMP-PL-Kalisz', 'UMP-PL-Katowice',
                                     'UMP-PL-Kielce', 'UMP-PL-Klodzko', 'UMP-PL-Koszalin', 'UMP-PL-Krakow',
                                     'UMP-PL-Leszno', 'UMP-PL-Lodz', 'UMP-PL-Lublin', 'UMP-PL-NowySacz',
                                     'UMP-PL-Olsztyn', 'UMP-PL-Opole', 'UMP-PL-Pila', 'UMP-PL-Plock', 'UMP-PL-Poznan',
                                     'UMP-PL-Przemysl', 'UMP-PL-Radom', 'UMP-PL-Rzeszow', 'UMP-PL-Siedlce',
                                     'UMP-PL-Suwalki', 'UMP-PL-Szczecin', 'UMP-PL-Tarnow', 'UMP-PL-Tczew',
                                     'UMP-PL-Torun', 'UMP-PL-Wloclawek', 'UMP-PL-Wroclaw', 'UMP-PL-Zamosc',
                                     'UMP-radary'],
                          'PORTUGALIA': ['UMP-PT-Lisbona', 'UMP-PT-Azory', 'UMP-PT-Madera'],
                          'ROSJA': ['UMP-RU-Moskwa', 'UMP-RU-Krolewiec'],
                          'RUMUNIA': ['UMP-RO-Bucuresti', 'UMP-RO-Timisoara'],
                          'SKANDYNAWIA': ['DANIA', 'SZWECJA', 'FINLANDIA', 'NORWEGIA', 'UMP-Islandia'],
                          'SZWECJA': ['UMP-SE-Goteborg', 'UMP-SE-Linkoping', 'UMP-SE-Malmo', 'UMP-SE-Norrkoping',
                                      'UMP-SE-Orebro', 'UMP-SE-Stockholm', 'UMP-SE-Umea'],
                          'WLOCHY': ['UMP-IT-Bari', 'UMP-IT-Bologna', 'UMP-IT-Bolzano', 'UMP-IT-Cagliari',
                                     'UMP-IT-Cosenza', 'UMP-IT-Firenze', 'UMP-IT-Genova', 'UMP-IT-Milano',
                                     'UMP-IT-Napoli', 'UMP-IT-Palermo', 'UMP-IT-Perugia', 'UMP-IT-Pescara',
                                     'UMP-IT-Roma', 'UMP-IT-Torino', 'UMP-IT-Trieste'],
                          'all': ['narzedzia', 'POLSKA', 'EUROPA', 'UMP-Egipt', 'UMP-Tunezja', 'UMP-Algieria',
                                  'UMP-Maroko', 'UMP-Nepal', 'Makefile.common'],
                          'inne': ['UMP-Karaiby', 'UMP-ZielonyPrzyladek', 'UMP-Afryka', 'UMP-Ameryka', 'UMP-Australia',
                                   'UMP-Azja']
                          }

    def pobierz_modul_cvs(self, nazwy_modulow):
        """
        Funkcja pobiera dany modulow z cvsu
        :param nazwy_modulow: nazwy modulow w postaci tupli
        :return: None
        """


class MyProgressBar(tkinter.Toplevel):
    """Progress bar używany podczas ściągania plików z internetu"""
    def __init__(self, parent, temporary_file, url, **options):
        tkinter.Toplevel.__init__(self, parent,  **options)
        self.temporary_file = temporary_file
        self.url = url
        self.transient(parent)
        self.title(u'Status pobierania z internetu')
        self.parent = parent
        body = tkinter.Frame(self)
        body.pack(padx=5, pady=5, fill='both', expand=1)
        self.progressbar = tkinter.ttk.Progressbar(body, mode='determinate', length=300)
        self.progressbar.pack()
        self.progressbar["maximum"] = 100
        self.progress_var = tkinter.DoubleVar()
        self.geometry('320x60')
        self.grab_set()
        # self.wait_window(self)
        self.inputqueue = queue.Queue()
        # self.protocol("WM_DELETE_WINDOW", self.destroy)
        # self.bind('<Escape>', lambda event: self.destroy())
        # self.geometry("+%d+%d" % (parent.winfo_rootx()+50, parent.winfo_rooty()+50))
        self.pobierz_plik()
        self.update_me()

    def pobierz_plik(self):
        # temporary_file = tempfile.NamedTemporaryFile(delete=False)
        thread1 = threading.Thread(target=pobierz_pliki_z_internetu, args=(self.temporary_file,
                                                                           self.url, self.inputqueue))
        thread1.start()

    def update_me(self):
        try:
            while 1:
                string1, string2 = self.inputqueue.get_nowait()
                if string1.startswith('koniec'):
                    self.destroy()
                else:
                    if string1 == 'max':
                        self.progressbar["maximum"] = int(string2)
                    else:
                        self.progressbar["value"] = int(string2)
        except queue.Empty:
            pass
        self.after(100, self.update_me)


class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.waittime = 500     # miliseconds
        self.text = ''

    def showtip(self, text):
        """Display text in tooltip window"""
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w, "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT, background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    def schedule(self, text):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip(text))

    def unschedule(self):
        tmp_id = self.id
        self.id = None
        if tmp_id:
            self.widget.after_cancel(tmp_id)


class AutoScrollbar(tkinter.ttk.Scrollbar):
    # a scrollbar that hides itself if it's not needed.  only
    # works if you use the grid geometry manager.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # grid_remove is currently missing from Tkinter!
            self.tk.call("grid", "remove", self)
            # self.grid()
        else:
            self.grid()
        tkinter.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise TclError

    def place(self, **kw):
        raise TclError


class ListaPlikowFrame(tkinter.Frame):
    def __init__(self, master, Zmienne, **options):
        tkinter.Frame.__init__(self, master, **options)
        self.queueListaPlikowFrame = queue.Queue()
        # self.zmienionepliki=[]
        self.mdm_mode = Zmienne.mdm_mode
        self.Zmienne = Zmienne
        self.listaNazwPlikowDoObejrzenia = []
        self.listaPlikowOknoZmienionePliki = []
        self.listaDodanoOknoZmienionePliki = []
        self.skasowanoPlikowOknoZmienionePliki = []
        self.zobaczButtonPlikowOknoZmienionePliki = []
        self.skopiujCheckButtonPlikowOknoZmienionePliki = []
        self.listaPlikowDiffDoSkopiowania = {}
        self.update_me()
        self.master = master
        self.nazwapliku_Hash = None

    # def write(self,line):
    #   self.queueListaPlikowFrame.put(line)

    def update_me(self):
        try:
            while 1:
                zmienioneplikihash = self.queueListaPlikowFrame.get_nowait()
                abc = 0
                style = tkinter.ttk.Style()
                style.configure('Helvetica.TLabel', font=('Helvetica', 9))
                for a in zmienioneplikihash[0][:]:
                    iloscdodanych = '-1'
                    iloscusunietych = '-1'
                    try:
                        plik_do_otwarcia = os.path.join(self.Zmienne.KatalogRoboczy, a.replace(os.sep, '-')) + '.diff'
                        with open(plik_do_otwarcia, encoding=self.Zmienne.Kodowanie,
                                  errors=self.Zmienne.ReadErrors) as file:
                            for bbb in file.readlines():
                                if bbb.startswith('+'):
                                    iloscdodanych = str(int(iloscdodanych) + 1)
                                elif bbb.startswith('-'):
                                    iloscusunietych = str(int(iloscusunietych) + 1)
                    except FileNotFoundError:
                        iloscdodanych = 'n/a'
                        iloscusunietych = 'n/a'
                    self.listaNazwPlikowDoObejrzenia.append(a)
                    self.listaPlikowOknoZmienionePliki.append(tkinter.ttk.Label(self, text=a, width=60, anchor='w',
                                                                                style='Helvetica.TLabel'))
                    self.listaPlikowOknoZmienionePliki[abc].grid(row=abc+1, column=0)
                    newtags = self.listaPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
                    self.listaPlikowOknoZmienionePliki[abc].bindtags(newtags)

                    self.listaDodanoOknoZmienionePliki.append(tkinter.ttk.Label(self, text=iloscdodanych, width=5,
                                                                                anchor='w', style='Helvetica.TLabel'))
                    self.listaDodanoOknoZmienionePliki[abc].grid(row=abc+1, column=1)
                    newtags = self.listaDodanoOknoZmienionePliki[abc].bindtags()+('movewheel',)
                    self.listaDodanoOknoZmienionePliki[abc].bindtags(newtags)

                    self.skasowanoPlikowOknoZmienionePliki.append(tkinter.ttk.Label(self, text=iloscusunietych, width=5,
                                                                                    anchor='w', style='Helvetica.TLabel'))
                    self.skasowanoPlikowOknoZmienionePliki[abc].grid(row=abc+1, column=2)
                    newtags = self.skasowanoPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
                    self.skasowanoPlikowOknoZmienionePliki[abc].bindtags(newtags)

                    self.zobaczButtonPlikowOknoZmienionePliki.append(tkinter.ttk.Button(self, text='Zobacz',
                                                                    command=lambda tmp=a: self.OnButtonClickZobacz(tmp)))
                    self.zobaczButtonPlikowOknoZmienionePliki[abc].grid(row=abc+1, column=3)
                    newtags = self.zobaczButtonPlikowOknoZmienionePliki[abc].bindtags() + ('movewheel',)
                    self.zobaczButtonPlikowOknoZmienionePliki[abc].bindtags(newtags)

                    self.listaPlikowDiffDoSkopiowania[a] = tkinter.IntVar()
                    self.listaPlikowDiffDoSkopiowania[a].set(0)
                    self.skopiujCheckButtonPlikowOknoZmienionePliki.append(tkinter.ttk.Checkbutton(self,
                                                                                                   text='Skopiuj',
                                                                                                   onvalue=1,
                                                                                                   offvalue=0,
                                                                                                   variable=self.listaPlikowDiffDoSkopiowania[a]))
                    self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].grid(row=abc+1, column=4)
                    newtags = self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].bindtags() + ('movewheel',)
                    self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].bindtags(newtags)

                    abc += 1
                    if a.startswith('_nowosci.') and self.mdm_mode == 'edytor':
                        self.skopiujCheckButtonPlikowOknoZmienionePliki[abc-1].configure(state='disabled')
                    if a.find('granice-czesciowe.txt') >= 0 and self.mdm_mode == 'edytor':
                        self.skopiujCheckButtonPlikowOknoZmienionePliki[abc-1].configure(state='disabled')
                    self.nazwapliku_Hash = zmienioneplikihash[1]
                    self.update_idletasks()
                    self.master.config(scrollregion=self.master.bbox("all"))
                    self.master.update_idletasks()

        except queue.Empty:
            pass
        self.after(500, self.update_me)

    def WyczyscPanelzListaPlikow(self):
        for aaa in self.listaPlikowOknoZmienionePliki + self.listaDodanoOknoZmienionePliki + \
                   self.skasowanoPlikowOknoZmienionePliki + self.zobaczButtonPlikowOknoZmienionePliki + \
                   self.skopiujCheckButtonPlikowOknoZmienionePliki:
            aaa.destroy()

        self.listaPlikowOknoZmienionePliki = []
        self.listaDodanoOknoZmienionePliki = []
        self.skasowanoPlikowOknoZmienionePliki = []
        self.zobaczButtonPlikowOknoZmienionePliki = []
        self.skopiujCheckButtonPlikowOknoZmienionePliki = []
        self.listaNazwPlikowDoObejrzenia = []
        self.listaPlikowDiffDoSkopiowania = {}
        self.update_idletasks()
        self.master.config(scrollregion=self.master.bbox("all"))
        self.master.update_idletasks()

    def OnButtonClickZobacz(self, plik):
        print(plik)
        plikdootw = plik.replace(os.sep, '-')
        if not plikdootw.startswith('_nowosci.') and self.nazwapliku_Hash[plik] != 'MD5HASH=NOWY_PLIK':
            plikdootw += '.diff'
        with open(os.path.join(self.Zmienne.KatalogRoboczy, plikdootw), encoding=self.Zmienne.Kodowanie,
                  errors=self.Zmienne.ReadErrors) as f:
            aaa = f.readlines()
        oknopodgladu = tkinter.Toplevel(self)
        oknopodgladu.title(plik)
        frameInOknoPodgladu = tkinter.Frame(oknopodgladu)
        frameInOknoPodgladu.pack(fill='both', expand=1)

        Scroll = tkinter.Scrollbar(frameInOknoPodgladu)
        Scroll.pack(side='right', fill='y', expand=0)
        zawartoscokna = zobaczDiffText(frameInOknoPodgladu, plik, width=100, yscrollcommand=Scroll.set, wrap='none')
        # zawartoscokna.tag_config('sel',background='yellow')
        zawartoscokna.tag_config('removed', foreground='red', background='snow3')
        zawartoscokna.tag_config('added', foreground='blue', background='snow3')
        zawartoscokna.tag_config('normal', foreground='black')
        zawartoscokna.tag_raise('sel')
        # jak zmusic by zaznaczanie działało
        # http://stackoverflow.com/questions/23289214/tkinter-text-tags-select-user-highlight-colour

        # przenosimy focus na okno podgladu, aby alt+f4 na nim działało a nie na głównym oknie aplikacji
        oknopodgladu.focus_set()

        # bindujemy klawisz escape to zamykania okna
        oknopodgladu.bind('<Escape>', lambda event: oknopodgladu.destroy())

        wiersz = 0
        for tmpa in aaa:
            if tmpa.startswith('+'):
                zawartoscokna.insert('end', tmpa.rstrip('\n'), 'added')
                zawartoscokna.insert('end', '\n', 'normal')
            elif tmpa.startswith('-'):
                zawartoscokna.insert('end', tmpa.rstrip('\n'), 'removed')
                zawartoscokna.insert('end', '\n', 'normal')
            else:
                zawartoscokna.insert('end', tmpa, 'normal')

        # zawartoscokna.insert(1.0,aaa,'removed')
        zawartoscokna.config(state='disabled')
        zawartoscokna.pack(fill='both', expand=1, side='right')
        Scroll.config(command=zawartoscokna.yview)

        ScrollX = tkinter.Scrollbar(oknopodgladu, orient='horizontal', command=zawartoscokna.xview)
        ScrollX.pack(fill='x', expand=0)
        zawartoscokna.config(xscrollcommand=ScrollX.set)
        # zawartoscokna.grid(row=0,column=0)
        # zawartoscokna.grid_columnconfigure(0,weight=1)
        # zawartoscokna.grid_rowconfigure(0,weight=1)


class HelpWindow(tkinter.Toplevel):
    def __init__(self, parent, **options):
        tkinter.Toplevel.__init__(self, parent, **options)
        self.transient(parent)
        self.title(u'Skróty klawiaturowe')
        self.parent = parent

        body = tkinter.Frame(self)
        # self.initial_focus = self
        body.pack(padx=5, pady=5, fill='both', expand=1)

        self.text = tkinter.scrolledtext.ScrolledText(body)
        self.text.pack(fill='both', expand=1)
        self.wypiszListeSkrotow(self.text)

        buttonZamknij = tkinter.ttk.Button(body, text='Zamknij', command=self.destroy)
        buttonZamknij.pack()

        # self.buttonbox()
        # self.keyboardShortcuts()

        self.grab_set()

        # if not self.initial_focus:
        # self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind('<Escape>', lambda event: self.destroy())
        # self.geometry("+%d+%d" % (parent.winfo_rootx()+50, parent.winfo_rooty()+50))

        self.focus_set()
        self.wait_window(self)

    def wypiszListeSkrotow(self, okienko):
        listaSkrotowKlawiaturowych = [u'Skróty klawiaturowe okna głównego\n',
                    'ctrl + m', '                   -> ', 'montuj\n',
                    'ctrl + d', '                   -> ', 'demontuj\n',
                    'ctrl + e', '                   -> ', 'edytuj\n',
                    'ctrl + s', '                   -> ', u'sprawdz błędy\n',
                    'ctrl + u', '                   -> ', u'uaktualnij źródła (wybrany obszar, albo wszystkie obszary w przypadku braku zaznaczenia)\n',
                    'R', '                          -> ', u'włącz klawisz Montuj\n',
                    'ctrl + prawy klawisz myszy', ' -> ', u'włącz klawisz Montuj\n',
                    'E', '                          -> ', u'zamontuj źródła i uruchom mapedit\n',
                    'ctrl + lewy klawisz myszy', '  -> ', u'zamontuj źródła i uruchom mapedit\n',
                    'ctrl + shift + c', '           -> ', u'wyczyść katalog roboczy z plików źródłowych, diff i wynik.mp\n',
                    '\n',
                    u'Skróty dla wyboru obszarów\n',
                    'ctrl + lewy klawisz myszy', ' -> ', u'zaznaczenie obszaru i wywołanie cvs up',
                    '\n\n',
                    u'Skróty klawiaturowe cvs\n',
                    'ctrl + o', ' -> ', 'OK\n',
                    'Escape', '   -> ', 'Cancel\n',
                    '\n\n',
                    'Menu kontekstowe\n',
                    'Dla wyboru obszarów oraz okien z komunikatami i błędami zdefiniowane jest menu kontekstowe - prawy klawisz myszy\n'
                    ]

        for a in listaSkrotowKlawiaturowych:
            okienko.insert('insert', a)

        okienko.config(state='disabled')


class ConfigWindow(tkinter.Toplevel):
    def __init__(self, parent, **options):
        tkinter.Toplevel.__init__(self, parent, **options)
        self.transient(parent)
        self.title('Konfiguracja')
        self.parent = parent

        # self.parent.title='Konfiguracja'
        self.Konfiguracja = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        self.Konfiguracja.wczytajKonfiguracje()
        # print(self.Konfiguracja.KatalogzUMP)
        # print(self.Konfiguracja.MapEditExe)
        # print(self.Konfiguracja.NetGen)

        self.umpSourceValue = tkinter.StringVar()
        self.umpRoboczyValue = tkinter.StringVar()
        self.umpMapeditPath = tkinter.StringVar()
        self.umpMapedit2Path = tkinter.StringVar()
        self.umpNetGenPath = tkinter.StringVar()
        self.ump_mdm_mode = tkinter.IntVar()
        self.umpcvsusername = tkinter.StringVar()
        self.umpPatchProgramPath = tkinter.StringVar()
        self.mkgmmap_jar_path = tkinter.StringVar()

        self.umpSourceValue.set(self.Konfiguracja.KatalogzUMP)
        self.umpRoboczyValue.set(self.Konfiguracja.KatalogRoboczy)
        self.umpMapeditPath.set(self.Konfiguracja.MapEditExe)
        self.umpMapedit2Path.set(self.Konfiguracja.MapEdit2Exe)
        self.umpNetGenPath.set(self.Konfiguracja.NetGen)
        self.umpcvsusername.set(self.Konfiguracja.CvsUserName)
        self.mkgmmap_jar_path.set(self.Konfiguracja.mkgmap_jar_path)
        if self.Konfiguracja.mdm_mode == 'edytor':
            self.ump_mdm_mode.set(1)
        else:
            self.ump_mdm_mode.set(0)

        umpConfigFrame = tkinter.Frame(self, borderwidth=2, pady=10, padx=10)
        umpConfigFrame.grid(column=0, row=0)

        umpsourceLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Katalog ze źródłami UMP')
        umpsourceLabelFrame.grid(row=0, column=0, sticky='we', columnspan=2)
        umpsource = tkinter.Label(umpsourceLabelFrame, textvariable=self.umpSourceValue)
        umpsource.grid(row=0, column=0, sticky='w')
        umpsourceLabelFrame.grid_columnconfigure(0, weight=1)
        umpsourceWybierzButton = tkinter.ttk.Button(umpsourceLabelFrame, text='Wybierz',
                                                    command=self.OnButtonClickUMPSource)
        umpsourceWybierzButton.grid(row=0, column=1, sticky='e')

        umproboczyLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Katalog roboczy')
        umproboczyLabelFrame.grid(row=1, column=0, sticky='we', columnspan=2)
        umproboczy = tkinter.Label(umproboczyLabelFrame, textvariable=self.umpRoboczyValue)
        umproboczy.grid(row=0, column=0, sticky='w')
        umproboczyLabelFrame.grid_columnconfigure(0, weight=1)
        umproboczyWybierzButton = tkinter.ttk.Button(umproboczyLabelFrame, text='Wybierz',
                                                     command=self.OnButtonClickUMPRoboczy)
        umproboczyWybierzButton.grid(row=0, column=1, sticky='e')

        umpmapeditLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Ścieżka do programu mapedit')
        umpmapeditLabelFrame.grid(row=2, column=0, sticky='we', columnspan=2)
        umpmapedit = tkinter.Label(umpmapeditLabelFrame, textvariable=self.umpMapeditPath)
        umpmapedit.grid(row=0, column=0, sticky='w')
        umpmapeditLabelFrame.grid_columnconfigure(0, weight=1)
        umpmapeditWybierzButton = tkinter.ttk.Button(umpmapeditLabelFrame, text='Wybierz',
                                                     command=self.OnButtonClickMapedit)
        umpmapeditWybierzButton.grid(row=0, column=1, sticky='e')

        umpmapedit2LabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame,
                                                       text=u'Ścieżka do programu mapedit (druga wersja)')
        umpmapedit2LabelFrame.grid(row=3, column=0, sticky='we', columnspan=2)
        umpmapedit2 = tkinter.Label(umpmapedit2LabelFrame, textvariable=self.umpMapedit2Path)
        umpmapedit2.grid(row=0, column=0, sticky='w')
        umpmapedit2LabelFrame.grid_columnconfigure(0, weight=1)
        umpmapedit2WybierzButton = tkinter.ttk.Button(umpmapedit2LabelFrame, text='Wybierz',
                                                      command=self.OnButtonClickMapedit2)
        umpmapedit2WybierzButton.grid(row=0, column=1, sticky='e')

        # sciezka do programu netgen
        umpnetgenLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Ścieżka do programu netgen.exe')
        umpnetgenLabelFrame.grid(row=4, column=0, sticky='we', columnspan=2)
        umpnetgen = tkinter.Label(umpnetgenLabelFrame, textvariable=self.umpNetGenPath)
        umpnetgen.grid(row=0, column=0, sticky='w')
        umpnetgenLabelFrame.grid_columnconfigure(0, weight=1)
        umpnetgenWybierzButton = tkinter.ttk.Button(umpnetgenLabelFrame, text='Wybierz',
                                                    command=self.OnButtonClickNetgen)
        umpnetgenWybierzButton.grid(row=0, column=1, sticky='e')

        # sciezka do mkgmap
        mkgmap_jar_path_frame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Ścieżka do programu mkgmap.jar')
        mkgmap_jar_path_frame.grid(row=5, column=0, columnspan=2, sticky='we')
        mkgmap_jar_path_label = tkinter.Label(mkgmap_jar_path_frame, textvariable=self.mkgmmap_jar_path)
        mkgmap_jar_path_label.grid(row=0, column=0, sticky='w')
        mkgmap_jar_path_frame.grid_columnconfigure(0, weight=1)
        mkgmap_jar_path_label_button = tkinter.ttk.Button(mkgmap_jar_path_frame, text='Wybierz',
                                                          command=self.OnButtonClickMkgmapJarPath)
        mkgmap_jar_path_label_button.grid(row=0, column=1, sticky='e')

        # login dla cvs
        umpcvsloginLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame,
                                                       text=u'Login do CVS, jeśli nie masz pozostaw guest')
        umpcvsloginLabelFrame.grid(row=6, column=0, sticky='we', columnspan=2)
        umpcvsloginLabelFrame.grid_columnconfigure(0, weight=1)
        umpcvsEntry = tkinter.Entry(umpcvsloginLabelFrame, textvariable=self.umpcvsusername)
        umpcvsEntry.grid(row=0, column=0, sticky='ew')

        # tryb pracy gui
        umpmdmmodeLabelFrame = tkinter.ttk.LabelFrame(umpConfigFrame, text=u'Tryb pracy mdm')
        umpmdmmodeLabelFrame.grid(row=7, column=0, columnspan=2, sticky='we')
        umpmdmmodeRadio1 = tkinter.ttk.Radiobutton(umpmdmmodeLabelFrame, text='Edytor', value=1,
                                                   variable=self.ump_mdm_mode)
        umpmdmmodeRadio1.grid(row=0, column=0)
        umpmdmmodeRadio2 = tkinter.ttk.Radiobutton(umpmdmmodeLabelFrame, text='Wrzucacz', value=0,
                                                   variable=self.ump_mdm_mode)
        umpmdmmodeRadio2.grid(column=1, row=0)

        self.buttonbox()
        self.grab_set()
        # if not self.initial_focus:
        #   self.initial_focus = self
        # self.initial_focus.focus_set()
        self.focus_set()
        self.wait_window(self)

    def buttonbox(self):
        box = tkinter.Frame(self, padx=10, pady=10)
        box.grid(row=4, column=0, columnspan=2, sticky='ew')
        box.grid_columnconfigure(0, weight=1)

        saveButton = tkinter.ttk.Button(box, text=u'Zapisz konfigurację', command=self.OnButtonClickZapisz)
        saveButton.grid(column=0, row=0, sticky='w')

        cancelButton = tkinter.ttk.Button(box, text=u'Anuluj', command=self.destroy)
        cancelButton.grid(column=1, row=0, sticky='e')

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.anuluj)

    def ok(self, event=None):
        self.withdraw()
        self.update_idletasks()
        self.OnButtonClickZapisz()

    def anuluj(self, event=None):
        self.parent.focus_set()
        self.destroy()

    def OnButtonClickZapisz(self):
        with open(os.path.join(os.path.expanduser('~'), '.mont-demont-py.config'), 'w') as configfile:
            configfile.write('UMPHOME=' + self.Konfiguracja.KatalogzUMP)
            configfile.write('\n')
            configfile.write('KATALOGROBOCZY=' + self.Konfiguracja.KatalogRoboczy)
            configfile.write('\n')
            configfile.write('MAPEDITEXE=' + self.Konfiguracja.MapEditExe)
            configfile.write('\n')
            configfile.write('MAPEDIT2EXE=' + self.Konfiguracja.MapEdit2Exe)
            configfile.write('\n')
            configfile.write('NETGEN=' + self.Konfiguracja.NetGen)
            configfile.write('\n')
            if self.ump_mdm_mode.get() == 1:
                configfile.write('MDMMODE=edytor')
            else:
                configfile.write('MDMMODE=wrzucacz')
            configfile.write('\n')
            configfile.write('CVSUSERNAME=' + self.umpcvsusername.get())
            configfile.write('\n')
            configfile.write('MKGMAPJARPATH=' + self.mkgmmap_jar_path.get())
            configfile.write('\n')

            command = self.destroy()

    def OnButtonClickMapedit(self):
        aaa = os.path.normcase(tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu mapedit.exe'))
        if len(aaa) > 0:
            self.umpMapeditPath.set(aaa)
            self.Konfiguracja.MapEditExe = aaa

    def OnButtonClickMapedit2(self):
        aaa = os.path.normcase(tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu mapedit.exe'))
        if len(aaa) > 0:
            self.umpMapedit2Path.set(aaa)
            self.Konfiguracja.MapEdit2Exe = aaa

    def OnButtonClickNetgen(self):
        aaa = os.path.normcase(tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu netgen.exe'))
        if len(aaa) > 0:
            self.umpNetGenPath.set(aaa)
            self.Konfiguracja.NetGen = aaa

    def OnButtonClickUMPSource(self):
        aaa = os.path.normcase(tkinter.filedialog.askdirectory(title=u'Katalog ze źródłami UMP'))
        if len(aaa) > 0:
            self.umpSourceValue.set(aaa)
            self.Konfiguracja.KatalogzUMP = aaa

    def OnButtonClickUMPRoboczy(self):
        aaa = os.path.normcase(tkinter.filedialog.askdirectory(title=u'Katalog roboczy'))
        if len(aaa) > 0:
            self.umpRoboczyValue.set(aaa)
            self.Konfiguracja.KatalogRoboczy = aaa

    def OnButtonClickMkgmapJarPath(self):
        aaa = os.path.normcase(tkinter.filedialog.askopenfilename(title=u'Ścieżka do pliku mkgmap.jar'))
        if aaa:
            self.mkgmmap_jar_path.set(aaa)
            self.Konfiguracja.mkgmap_jar_path = aaa


class mdmConfig(object):
    # zapisywanie i odczytywanie opcji montażu i demontażu, tak aby można było sobie zaznaczyć raz i aby tak pozostało
    def __init__(self):
        self.montDemontOptions = {}
        self.mont_opcje = {'adrfile': False, 'noszlaki': False, 'nocity': False, 'nopnt': False, 'no_osm': False,
                           'monthash': False, 'graniceczesciowe': False,
                           'entry_otwarte_do_extras': False, 'format_indeksow': 'cityidx', 'sprytne_entrypoints': False}
        self.demont_opcje = {'demonthash': False, 'autopoi': False, 'X': '0', 'autopolypoly': False,
                             'standaryzuj_komentarz': False, 'usun_puste_numery': False}
        self.mont_demont_opcje = {'savememory': False, 'cityidx': False, 'extratypes': False}
        self.kompiluj_typ_opcje = {'mkgmap_path': '', 'maksymalna_pamiec': '1G', 'family_id': '6324',
                                   'uwzglednij_warstwice': False, 'code_page': 'cp1250', 'nazwa_typ': 'domyslny'}
        self.kompiluj_mape_opcje = {'uwzglednij_warstwice': False, 'format_mapy': 'gmapsupp',
                                    'dodaj_routing': False, 'index': False, 'max_jobs': '0', 'wlasne_typy': '',
                                    'dodaj_adresy': False, 'uruchom_wojka': True, 'podnies_poziom': True}
        self.stworz_zmienne_mont_demont(self.mont_opcje)
        self.stworz_zmienne_mont_demont(self.demont_opcje)
        self.stworz_zmienne_mont_demont(self.mont_demont_opcje)
        self.stworz_zmienne_mont_demont(self.kompiluj_typ_opcje)
        self.stworz_zmienne_mont_demont(self.kompiluj_mape_opcje)
        self.readConfig()

    def zwroc_zmienna_opcji(self, nazwa_opcji):
        return self.montDemontOptions[nazwa_opcji]

    def stworz_zmienne_mont_demont(self, zmienne):
        for key in zmienne:
            if isinstance(zmienne[key], bool):
                self.montDemontOptions[key] = tkinter.BooleanVar(value=zmienne[key])
            else:
                self.montDemontOptions[key] = tkinter.StringVar(value=zmienne[key])

    def zwroc_args_do_kompiluj_typ(self):
        args = self.zwroc_args(self.kompiluj_typ_opcje)
        return args

    def zwroc_args_do_montuj_mkgmap(self):
        options = {}
        for key in self.kompiluj_mape_opcje:
            options[key] = self.kompiluj_mape_opcje[key]
        for key in self.kompiluj_typ_opcje:
            options[key] = self.kompiluj_typ_opcje[key]
        args = self.zwroc_args(options)
        setattr(args, 'trybosmand', False)
        return args

    def zwroc_args_do_mont(self):
        args = self.zwroc_args(self.mont_opcje)
        args = self.zwroc_args(self.mont_demont_opcje, args)
        args.plikmp = 'wynik.mp'
        return args

    def zwroc_args_do_demont(self):
        args = self.zwroc_args(self.demont_opcje)
        args = self.zwroc_args(self.mont_demont_opcje, args)
        args.katrob = None
        return args

    def zwroc_args_do_kompilacji_osmand(self):
        args = Argumenty()
        args.borders_file = None
        args.threadnum = 1
        args.monoprocess_outputs = False
        args.index_file = None
        args.nominatim_file = None
        args.navit_file = None
        args.nonumber_file = None
        args.verbose = False
        args.skip_housenumbers = False
        args.positive_ids = False
        args.normalize_ids = False
        args.ignore_errors = False
        args.regions = False
        args.no_osm = True
        return args

    def zwroc_args_dla_rozdzialu_klas(self):
        return Argumenty()

    def zwroc_args(self, argumenty, args_=None):
        if args_ is None:
            args = Argumenty()
        else:
            args = args_
        for atrybut in argumenty:
            setattr(args, atrybut, self.montDemontOptions[atrybut].get())
        return args

    def saveConfig(self):
        with open(os.path.join(os.path.expanduser('~'), '.mdm_config'), 'w') as configfile:
            for key in self.montDemontOptions:
                value = self.montDemontOptions[key].get()
                if isinstance(value, bool):
                    value = str(int(value))
                linia = key + '=' + value + '\n'
                configfile.write(linia)

    def readConfig(self):
        try:
            with open(os.path.join(os.path.expanduser('~'), '.mdm_config'), 'r') as configfile:
                opcje = configfile.readlines()
            for a in opcje:
                a = a.strip()
                if not a and '=' not in a:
                    continue
                klucz, wartosc = a.split('=', 1)
                if klucz not in self.montDemontOptions:
                    pass
                else:
                    if isinstance(self.montDemontOptions[klucz], tkinter.BooleanVar):
                        self.montDemontOptions[klucz].set(int(wartosc))
                    else:
                        self.montDemontOptions[klucz].set(wartosc)
        except FileNotFoundError:
            pass


class stdOutstdErrText(tkinter.scrolledtext.ScrolledText):
    """klasa dla okienek z błędami oraz z informacjami na dole okna mdm-py. Definicje kolejek
       do odbioru komunikatów, menu itd."""
    def __init__(self, master, **options):
        tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
        self.inputqueue = queue.Queue()
        self.menu = tkinter.Menu(self, tearoff=0)
        self.menu.add_command(label="Wytnij")
        self.menu.add_command(label="Kopiuj")
        self.menu.add_command(label="Wklej")
        self.menu.add_separator()
        self.menu.add_command(label="Zaznacz wszystko")
        self.menu.add_command(label=u'Wyczyść wszystko')
        self.menu.entryconfigure("Wytnij", command=lambda: self.event_generate("<<Cut>>"))
        self.menu.entryconfigure("Kopiuj", command=lambda: self.event_generate("<<Copy>>"))
        self.menu.entryconfigure("Wklej", command=lambda: self.event_generate("<<Paste>>"))
        self.menu.entryconfigure("Zaznacz wszystko", command=self.event_select_all)
        self.menu.entryconfigure(u'Wyczyść wszystko', command=self.event_clear_all)

        self.bind("Text", "<Control-a>", self.event_select_all)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)
        self.bind("<Double-Button-1>", self.event_double_click)

        # zmieniamy kolejność bindtags, najpierw klasa, potem widget tak aby podwójne kliknięcie
        # na współrzędnych kopiowało je do schowka:
        tags = list(self.bindtags())
        tags.remove('Text')
        tags = ['Text']+tags
        self.bindtags(tuple(tags))
        self.update_me()

    def event_select_all(self, *args):
        self.focus_force()
        self.tag_add("sel", "1.0", "end")

    def event_clear_all_event(self, event):
        if str(app.sprawdzButton['state']) != 'disabled':
            self.event_clear_all()

    def event_clear_all(self):
        self.focus_force()
        self.delete("1.0", "end")

    def show_menu(self, e):
        self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def event_double_click(self, event):
        self.focus_force()
        self.event_generate("<<Copy>>")
        return 'break'

    def update_me(self):
        try:
            while 1:
                string = self.inputqueue.get_nowait()
                if string.startswith('\rProcent:'):
                    # self.output.insert('%linestart'%tkinter.END,string)
                    self.delete('insert linestart', 'insert lineend')
                    self.insert('end linestart', string.lstrip())
                else:
                    self.insert(tkinter.END, string)
                    self.see(tkinter.END)
        except queue.Empty:
            pass
        self.after(100, self.update_me)


# ScrolledText który przyjmuje informacje z wątków pobocznych, dla operacji cvs up i cvs co
class cvsOutText(tkinter.scrolledtext.ScrolledText):
    def __init__(self, master, **options):
        tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
        self.master = master
        self.inputqueue = queue.Queue()
        self.menu = tkinter.Menu(self, tearoff=0)
        self.menu.add_command(label="Wytnij")
        self.menu.add_command(label="Kopiuj")
        self.menu.add_command(label="Wklej")
        self.menu.add_separator()
        self.menu.add_command(label="Zaznacz wszystko")
        self.menu.entryconfigure("Wytnij", command=lambda: self.event_generate("<<Cut>>"))
        self.menu.entryconfigure("Kopiuj", command=lambda: self.event_generate("<<Copy>>"))
        self.menu.entryconfigure("Wklej", command=lambda: self.event_generate("<<Paste>>"))
        self.menu.entryconfigure("Zaznacz wszystko", command=self.event_select_all)

        self.bind("Text", "<Control-a>", self.event_select_all)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)
        self.tag_config('P', foreground='green')
        self.tag_config('U', foreground='green')
        self.tag_config('questionmark', foreground='olive drab')
        self.tag_config('C', foreground='red')
        self.tag_config('M', foreground='deep pink')
        self.tag_config('normal', foreground='black')
        self.tag_config('error', foreground='red')
        self.tag_config('wskazowka', foreground='blue')
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()

        # usuwam skróty klawiautorwe które powinny być przechwytywane globalnie, tak żeby nie łapało ich też okienko do
        # wpisywania komentarza. Np ctrl+o dodawało nową linię i przez to mój walidador się psuł :D.

        self.bind("<Control-o>", lambda e: None)
        self.bind("<Escape>", lambda e: None)

        # Zmieniamy kolejność bindtags. Z niewiadomego dla mnie powodu '.' nie działała.
        tags = list(self.bindtags())
        tags.remove('Text')
        tags.append('Text')
        self.bindtags(tuple(tags))
        self.update_me()

    def event_select_all(self, *args):
        self.focus_force()
        self.tag_add("sel", "1.0", "end")

    def show_menu(self, e):
        self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def update_me(self):
        try:
            while 1:
                string = self.inputqueue.get_nowait()
                if string.startswith('P '):
                    self.insert('end', string.lstrip(), 'P')
                elif string.startswith('U '):
                    self.insert('end', string.lstrip(), 'U')
                elif string.startswith('? '):
                    self.insert('end', string.lstrip(), 'questionmark')
                elif string.startswith('C '):
                    self.insert('end', string.lstrip(), 'C')
                    self.insert('end', u'Uwaga! Łączenie zmian się nie powiodło. W pliku występują konflikty!\n', 'error')
                    self.insert('end', u'Otwórz plik w edytorze i usuń konflikty ręcznie.\n\n', 'wskazowka')
                elif string.startswith('M '):
                    self.insert('end', string.lstrip(), 'M')
                elif string.startswith(u'Błąd'):
                    self.insert('end', string.lstrip(), 'error')
                elif string.startswith(u'>'):
                    self.insert('end', string.lstrip('>'), 'wskazowka')
                elif string.startswith(u'nieprzeslane'):
                    self.insert('end', string.lstrip('nieprzeslane'), 'error')

                else:
                    self.insert('end', string.lstrip(), 'normal')
                self.see(tkinter.END)

        except queue.Empty:
            pass
        self.after(100, self.update_me)


class myCheckbutton(tkinter.ttk.Checkbutton):
    # checkbutton ktory umieszczony jest w liscie obszarow. Ma dodatkowo dolozone menu do cvs up i cvs co
    def __init__(self, master, args, obszar, zmienna, regionVariableDictionary, **options):
        self.args = args
        self.obszar = obszar
        self.zmienna = zmienna
        # poniższa zmienna używana jest do cvs ci dla zaznaczonych obszarów, pozwala odczytać
        # które obszary są zaznaczone
        self.regionVariableDictionary = regionVariableDictionary
        tkinter.ttk.Checkbutton.__init__(self, master, **options)
        self.menu = tkinter.Menu(self, tearoff=0)
        a = 'cvs up ' + self.obszar
        self.menu.add_command(label=a, command=self.cvsup)
        self.menu.add_command(label='cvs up narzedzia' + os.sep + 'granice.txt', command=self.cvsupgranice)
        a = 'cvs ci ' + self.obszar
        self.menu.add_command(label=a, command=self.cvsci)
        a = 'cvs ci dla zaznaczonych obszarów'
        self.menu.add_command(label=a, command=self.cvsci_zaznaczone_obszary)
        a = 'cvs diff -u ' + self.obszar
        self.menu.add_command(label=a, command=self.cvsdiff)
        self.menu_testy = tkinter.Menu(self.menu, tearoff=0)
        self.menu_testy.add_command(label=u'Znajdź współrzędne poza obszarem', command=self.znajdz_wyst)
        self.menu_testy.add_command(label=u'Drogi bez wjazdu - bez jednokierunkowych',
                                    command=self.sprawdz_siatke_dwukierunkowa)
        self.menu_testy.add_command(label=u'Drogi bez wjazdu - uwzgl. jednokierunkowe',
                                    command=self.sprawdz_siatke_jednokierunkowa)
        self.menu.add_cascade(label=u'Różne testy', menu=self.menu_testy)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)
        self.bind("<Control-ButtonRelease-1>", self.sel_then_cvsup)

    def sprawdz_siatke_dwukierunkowa(self):
        self.sprawdz_ciaglosc_grafow_routingowych('sprawdz_siatke_dwukierunkowa')

    def sprawdz_siatke_jednokierunkowa(self):
        self.sprawdz_ciaglosc_grafow_routingowych('sprawdz_siatke_jednokierunkowa')

    def sprawdz_ciaglosc_grafow_routingowych(self, mode):
        self.args.plikmp = None
        self.args.mode = mode
        thread1 = threading.Thread(target=mont_demont_py.sprawdz_numeracje, args=(self.args,))
        thread1.start()

    def znajdz_wyst(self):
        Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        argumenty = [self.obszar, Zmienne.KatalogzUMP, Zmienne.KatalogRoboczy]
        thread = threading.Thread(target=znajdz_wystajace.main, args=[argumenty])
        thread.start()

    def sel_then_cvsup(self, e):
        if not self.zmienna.get():
            self.zmienna.set(1)
            self.cvsup()
            self.zmienna.set(0)
        else:
            self.zmienna.set(1)

    def show_menu(self, e):
        self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def cvsup(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
            if os.path.isfile(os.path.join(Zmienne.KatalogRoboczy, 'wynik.mp')):
                if tkinter.messagebox.askyesno(u'Plik wynik.mp istnieje', u'W katalogu roboczym istniej plik wynik.mp.\nCvs up może uniemożliwić demontaż. Czy kontynuować pomimo tego?'):
                    aaa = cvsOutputReceaver(self, [self.obszar], '', 'up')
                else:
                    pass
            else:
                aaa = cvsOutputReceaver(self, [self.obszar], '', 'up')

    def cvsco(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            aaa = cvsOutputReceaver(self, [self.obszar], '', 'co')

    def cvsdiff(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            aaa = cvsOutputReceaver(self, [self.obszar], '', 'diff')

    def cvsupgranice(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            doCVS = cvsOutputReceaver(self, ['narzedzia' + os.sep + 'granice.txt'], '', 'up')

    def cvsci(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            oknodialogowe = cvsDialog(self, [self.obszar], title=u'Prześlij pliki do repozytorium cvs')
            if oknodialogowe.iftocommit == 'tak':
                doCVS = cvsOutputReceaver(self, [self.obszar], oknodialogowe.message, 'ci')
            else:
                pass

    def cvsci_zaznaczone_obszary(self):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            aaa = tkinter.messagebox.showwarning(message=cvs_status)
        else:
            zaznaczone_obszary = [aaa for aaa in self.regionVariableDictionary if
                                  self.regionVariableDictionary[aaa].get()]
            if not zaznaczone_obszary:
                tkinter.messagebox.showwarning(u'Brak wybranego obszaru!', u'Nie zaznaczyłeś żadnego obszaru do wysłania na serwer. Wybierz chociaż jeden.')
                return
            oknodialogowe = cvsDialog(self, zaznaczone_obszary, title=u'Prześlij pliki do repozytorium cvs')
            if oknodialogowe.iftocommit == 'tak':
                doCVS = cvsOutputReceaver(self, zaznaczone_obszary, oknodialogowe.message, 'ci')
            else:
                pass


class cvsDialog(tkinter.Toplevel):
    # używane do CVS commit, aby wpisać komentarz do transakcji
    def __init__(self, parent, pliki, title=None):

        tkinter.Toplevel.__init__(self, parent)
        self.transient(parent)
        self.pliki = pliki
        self.iftocommit = 'nie'
        self.last_cvs_log = []
        self.mdm_cvs_last_log_file = os.path.join(os.path.expanduser('~'), '.mdm_cvs_last_log')

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tkinter.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.buttonbox()
        self.keyboardShortcuts()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        # self.initial_focus.focus_set()
        # ustawiamy focus na okienko do wpisywania logu, tak aby kursor do wpisywania od razu tam był.
        self.logwindow.focus_set()
        self.wait_window(self)

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        katalog = tkinter.Label(self, text='AAAAA')
        katalog.pack()
        logwindowsFrame = tkinter.ttk.Labelframe(self, text='Komentarz')
        logwindowsFrame.pack()
        self.logwindow = cvsOutText(logwindowsFrame, width=70, height=6, font='Arial 10')
        self.logwindow.pack(fill='y', expand=True)

        # wczytujemy ostatni log cvs
        last_cvs_log = self.read_last_commit_log()
        if last_cvs_log:
            last_cvs_log[-1] = last_cvs_log[-1].rstrip()
            for a in last_cvs_log:
                self.logwindow.insert('end', a)
            # zaznaczamy go aby było łatwo usunąć
            self.logwindow.tag_add("sel", "1.0", "end")

        commitedFilesFrame = tkinter.ttk.Labelframe(self, text=u'Obszary lub/i pliki do zatwierdzenia')
        commitedFilesFrame.pack()
        commitedFiles = cvsOutText(commitedFilesFrame, width=70, height=6, font='Arial 10')
        commitedFiles.pack()
        for a in self.pliki:
            commitedFiles.insert('insert', a)
            commitedFiles.insert('insert', '\n')
        commitedFiles.configure(state='disabled')

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons
        box = tkinter.Frame(self)
        w = tkinter.Button(box, text="OK", width=10, command=self.ok, default='active')
        w.pack(side='left', padx=5, pady=5)
        w = tkinter.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side='left', padx=5, pady=5)
        box.pack()

    def keyboardShortcuts(self):
        # łączymy skróty klawiaturowe do ok oraz cancel
        self.bind("<Control-o>", self.ok)
        self.bind("<Escape>", self.cancel)

    # standard button semantics
    def ok(self, event=None):
        if self.validate():
            # self.initial_focus.focus_set() # put focus back
            self.logwindow.focus_set()
            return "break"

        self.save_last_commit_log()
        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()
        return "break"

    def cancel(self, event=None):

        # put focus back to the parent window

        self.parent.focus_set()
        self.destroy()
        return 'break'

    def validate(self):
        a = self.logwindow.get(1.0, 'end')
        if len(a) <= 1:
            return 1
        else:
            self.message = a
            return 0

    def apply(self):
        self.iftocommit = 'tak'

    def read_last_commit_log(self):
        last_cvs_log = []
        try:
            with open(self.mdm_cvs_last_log_file, 'r', encoding='utf-8', errors='ignore') as lastlog:
                last_cvs_log = lastlog.readlines()
        except FileNotFoundError:
            pass
        return last_cvs_log

    def save_last_commit_log(self):
        try:
            with open(self.mdm_cvs_last_log_file, 'w', encoding='utf-8', errors='ignore') as lastlog:
                lastlog.writelines(self.message)
        except FileNotFoundError:
            pass


class cvsOutputReceaver(tkinter.Toplevel):
    # okienko które wyświetla wyjście z programu cvs
    def __init__(self, parent, obszary, message, cvscommand, title=None):
        tkinter.Toplevel.__init__(self, parent)
        self.parent = parent
        self.transient(parent)
        self.stopthreadqueue = queue.Queue()
        self.progreststartstopqueue = queue.Queue()
        self.uncommitedfiles = set()
        self.commitedfiles = set()

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tkinter.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5, fill='both', expand=0)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.closewindows)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+50, parent.winfo_rooty()+50))

        self.initial_focus.focus_set()

        if cvscommand == 'up':
            thread = threading.Thread(target=self.cvsup, args=(obszary, self.stopthreadqueue,
                                                               self.progreststartstopqueue))
        elif cvscommand == 'diff':
            thread = threading.Thread(target=self.cvsdiff, args=(obszary, self.stopthreadqueue,
                                                                 self.progreststartstopqueue))
        elif cvscommand == 'co':
            thread = threading.Thread(target=self.cvsco, args=(obszary, self.stopthreadqueue,
                                                               self.progreststartstopqueue))
        else:
            thread = threading.Thread(target=self.cvsci, args=(obszary, message, self.stopthreadqueue,
                                                               self.progreststartstopqueue))
        thread.start()
        # self.cvsci(self.args.obszary,self.args.message)
        # mont_demont_py.cvsup(self.args)
        self.progres_start_stop_check()
        self.wait_window(self)

    def progres_start_stop_check(self):
        try:
            while 1:
                string = self.progreststartstopqueue.get_nowait()
                if string == 'start':
                    self.progressbar.start()
                    self.OKButton.configure(state='disabled')
                elif string == 'stop':
                    self.progressbar.stop()
                    self.OKButton.configure(state='active')
                    self.przerwijButton.configure(state='disabled')
                    #po zakończeniu działania cvs warto aby OK button dostał focus
                    self.OKButton.focus_set()
                else:
                    pass

        except queue.Empty:
            pass
        self.after(100, self.progres_start_stop_check)

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        katalog = tkinter.Label(self, text='AAAAA')
        katalog.pack(fill='x', expand=0)
        logwindowsFrame = tkinter.ttk.Labelframe(self, text=u'Dane wyjściowe')
        logwindowsFrame.pack(fill='both', expand=1)
        self.outputwindow = cvsOutText(logwindowsFrame, width=80, height=10, font='Arial 10')
        self.outputwindow.config(wrap='none')
        self.outputwindow.pack(fill='both', expand=1)

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = tkinter.Frame(self)

        self.progressbar = tkinter.ttk.Progressbar(box, mode='indeterminate', length=100)
        self.progressbar.pack(side='left', anchor='w', expand=1)
        self.OKButton = tkinter.Button(box, text="OK", width=10, command=self.ok, default='active')
        self.OKButton.pack(side='left', padx=5, pady=5, anchor='e')
        # do guzika OK bindujemy klawisz Return, aby można było zamknąć enterem oraz klawiszem escape
        self.OKButton.bind('<Return>', self.ok)
        self.OKButton.bind('<Escape>', self.ok)

        self.przerwijButton = tkinter.Button(box, text="Przerwij", width=10, command=self.cancel)
        self.przerwijButton.pack(side='left', padx=5, pady=5, anchor='e')

        # self.bind("<Return>", self.ok)
        # self.bind("<Escape>", self.cancel)

        box.pack(fill='x', expand=0)

    # standard button semantics
    def ok(self, event=None):

        if self.validate():
            self.initial_focus.focus_set() #  put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.parent.focus_set()
        self.destroy()

    def cancel(self, event=None):

        # put focus back to the parent window
        # self.parent.focus_set()
        # self.destroy()
        self.stopthreadqueue.put('stop')

    #
    # command hooks
    def closewindows(self, event=None):
        if self.OKButton.config('state')[-1] != 'disabled':
            self.ok()

    def validate(self):
        return 0

    def apply(self):
        pass  # override

    def cvsci(self, obszary, message, stopthreadqueue, progreststartstopqueue):
        """
        Commitowanie zmian przy pomocy cvs
        :param obszary: list(), lista plików do zacommitowania w postaci sciezki np. w wersji dla win będzie
                                ['UMP-PL-Lodz\\src\\LODZ.zielone.txt', 'UMP-PL-Lodz\\src\\SKIERNIEWICE.drogi.txt']
        :param message: string, log to commita
        :param stopthreadqueue: queue, kolejka z której przychodzi komunikat o przerwaniu dzialania
        :param progreststartstopqueue: queue, kolejka do progressbarru, start, stop
        :return:
        """

        progreststartstopqueue.put('start')
        Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        cvs_string = ''

        os.chdir(Zmienne.KatalogzUMP)
        self.outputwindow.inputqueue.put(('cd ' + Zmienne.KatalogzUMP + '\n'))
        self.outputwindow.inputqueue.put(('CVSROOT=' + CVSROOT + '\n'))
        for a in obszary:
            self.outputwindow.inputqueue.put(('cvs ci -m "' + message.strip() + '" ' + a + '\n'))
            process = subprocess.Popen(['cvs', '-q', CVSROOT, 'ci', '-m', message, a], stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            while process.poll() is None:
                try:
                    cvs_string = stopthreadqueue.get_nowait()
                    if cvs_string == 'stop':
                        process.terminate()
                        break
                except queue.Empty:
                    pass
                time.sleep(1)
            stderr = process.stderr.readlines()
            stdout = process.stdout.readlines()

            if len(stderr) > 0:
                if stderr[0].decode(Zmienne.Kodowanie).find('Up-to-date check failed') >= 0:
                    for line in stderr:
                        self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
                    self.outputwindow.inputqueue.put(u'Błąd, polecenie CVS nieudane!\n\n')
                    self.outputwindow.inputqueue.put(u'>Wskazówka. Ktoś inny zatwierdził w repozytorium nowszą wersję pliku lub plików, dla których\n')
                    self.outputwindow.inputqueue.put(u'>próbujesz wykonac operację commit. Musisz wykonać polecenie update,\n')
                    self.outputwindow.inputqueue.put(u'>a następnie commit.\n\n')
                    self.uncommitedfiles.add(a)
                else:
                    for line in stderr:
                        self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))

            else:
                if len(stdout) > 0:
                    for line in stdout:
                        self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
                        if line.decode(Zmienne.Kodowanie).find('<--  ' + os.path.basename(a)) >= 0:
                            self.commitedfiles.add(a)
                    if cvs_string == 'stop':
                        self.outputwindow.inputqueue.put(u'Commit przerwany na żądanie użytkownika!\n')
                        self.outputwindow.inputqueue.put('Gotowe\n')
                        break
                    else:
                        pass
                else:
                    self.commitedfiles.add(a)

        for a in obszary:
            if os.path.dirname(a).endswith('src') and (a not in self.commitedfiles):
                self.uncommitedfiles.add(a)
        if self.uncommitedfiles:
            self.outputwindow.inputqueue.put(u'\nObszary których nie udało się przesłać:\n')
            for a in self.uncommitedfiles:
                self.outputwindow.inputqueue.put(('nieprzeslane' + a + '\n'))

        self.outputwindow.inputqueue.put('Gotowe\n')
        progreststartstopqueue.put('stop')


    def cvsdiff(self, obszary, stopthreadqueue, progreststartstopqueue):
        progreststartstopqueue.put('start')
        Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        queue_string = ''
        czyzatrzymac = 0

        os.chdir(Zmienne.KatalogzUMP)
        self.outputwindow.inputqueue.put(('cd '+Zmienne.KatalogzUMP+'\n'))
        self.outputwindow.inputqueue.put(('CVSROOT=' + CVSROOT + '\n'))

        for a in obszary:
            self.outputwindow.inputqueue.put(('cvs diff -u ' + a + os.sep + 'src\n'))
            process = subprocess.Popen(['cvs', '-q', CVSROOT, 'diff', '-u', a + os.sep + 'src'], stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            processexitstatus = process.poll()

            while processexitstatus is None:
                try:
                    queue_string = stopthreadqueue.get_nowait()
                    if queue_string == 'stop':
                        process.terminate()
                        czyzatrzymac = 1
                        break
                    #
                except queue.Empty:
                    pass
                line = process.stdout.readline()
                if line.decode(Zmienne.Kodowanie) != '':
                    self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))

                #time.sleep(0.1)
                processexitstatus=process.poll()

            if czyzatrzymac:
                break

        if queue_string == 'stop':
            self.outputwindow.inputqueue.put(u'Cvs diff -u przerwany na żądanie użytkownika!\n')

        else:
            #okazuje sie, że trzeba jeszcze sprawdzić czy całe stdout zostało odczytane. Bywa że nie i trzeba doczytać tutaj.
            while line.decode(Zmienne.Kodowanie) != '':
                line = process.stdout.readline()
                self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
        self.outputwindow.inputqueue.put('\n\nGotowe\n')
        progreststartstopqueue.put('stop')

    def cvsup(self, obszary, stopthreadqueue, progreststartstopqueue):
        self.cvsup_cvsco('up', obszary, stopthreadqueue, progreststartstopqueue)

    def cvsco(self, obszary, stopthreadqueue, progreststartstopqueue):
        self.cvsup_cvsco('co', obszary, stopthreadqueue, progreststartstopqueue)

    def cvsup_cvsco(self, komenda, obszary, stopthreadqueue, progreststartstopqueue):

        progreststartstopqueue.put('start')
        Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        string = ''
        czyzatrzymac = 0

        os.chdir(Zmienne.KatalogzUMP)
        self.outputwindow.inputqueue.put(('cd ' + Zmienne.KatalogzUMP + '\n'))
        self.outputwindow.inputqueue.put(('CVSROOT=' + CVSROOT + '\n'))

        for a in obszary:
            self.outputwindow.inputqueue.put(('cvs ' + komenda + ' ' + a + '\n'))
            process = subprocess.Popen(['cvs', '-q', CVSROOT, komenda, a], stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            processexitstatus = process.poll()

            while processexitstatus is None:
                try:
                    string = stopthreadqueue.get_nowait()
                    if string == 'stop':
                        process.terminate()
                        czyzatrzymac = 1
                        break
                    #
                except queue.Empty:
                    pass
                line = process.stdout.readline()
                if line.decode(Zmienne.Kodowanie) != '':
                    self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))

                # time.sleep(0.1)
                processexitstatus = process.poll()

            if czyzatrzymac:
                break

        if string == 'stop':
            self.outputwindow.inputqueue.put(u'Proces uaktualniania przerwany na żądanie użytkownika!\n')

        else:
            # okazuje sie, że trzeba jeszcze sprawdzić czy całe stdout zostało odczytane. Bywa że nie i
            # trzeba doczytać tutaj.
            while line.decode(Zmienne.Kodowanie) != '':
                line = process.stdout.readline()
                self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
        self.outputwindow.inputqueue.put('Gotowe\n')
        progreststartstopqueue.put('stop')


class zobaczDiffText(tkinter.Text):
    def __init__(self, master, nazwapliku, **options):
        tkinter.Text.__init__(self, master, **options)
        self.bind("<Double-Button-1>", self.event_double_click)
        self.typpliku = ''
        if nazwapliku.endswith('.txt'):
            self.typpliku = 'txt'
        elif nazwapliku.endswith('.pnt'):
            self.typpliku = 'pnt'
        elif nazwapliku.endswith('.adr'):
            self.typpliku = 'adr'
        if nazwapliku.startswith("_nowosci"):
            self.ofset = 0
        else:
            self.ofset = 1

    def event_double_click(self, event):
        znaki_dla_wspolrzednych = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ',', '(', ')', '.']
        znaki_dla_wsp_txt = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ',', '.']
        self.focus_force()
        indeks_literki_pod_kursorem = self.index('current')
        literka_pod_kursorem = self.get(indeks_literki_pod_kursorem)
        nr_linii, nr_znaku = indeks_literki_pod_kursorem.split('.')
        linia = self.get(nr_linii + ".0", nr_linii + ".end")
        # podwójne kliknięcie powinno zaznaczyć parę współrzędnych
        # para współrzędnych to (XX,XXXXX,YY,YYYYY), a
        # musimy kliknąć na liczbie, przecinku lub  nawiasie by zacząć wyszukiwać w przeciwnym przypadku
        # zaznacza całą linię
        if literka_pod_kursorem not in znaki_dla_wspolrzednych:
            # zaznaczamy całą linię:
            self.tag_add("sel", nr_linii + ".0", nr_linii + ".end")
        else:
            try:
                if self.typpliku == 'txt':
                    index0 = index1 = int(nr_znaku)
                    if linia[self.ofset:].startswith('Data'):
                        if literka_pod_kursorem == '(':
                            while linia[index1] != ')':
                                index1 += 1
                            self.tag_add("sel", nr_linii + "." + str(index0+1), nr_linii + "." + str(index1))
                        elif literka_pod_kursorem == ')':
                            while linia[index0] != '(':
                                index0 -= 1
                            self.tag_add("sel", nr_linii + "." + str(index0+1), nr_linii + "." + str(index1))
                        else:
                            while linia[index0] in znaki_dla_wsp_txt:
                                index0 -= 1
                            while linia[index1] in znaki_dla_wsp_txt:
                                index1 += 1
                            self.tag_add("sel", nr_linii + "." + str(index0 + 1), nr_linii+"." + str(index1))
                    else:
                        return 0
                elif self.typpliku == 'pnt' or self.typpliku == 'adr':
                    if linia[self.ofset:].startswith('  ') or linia.startswith('  '):
                        x = 2
                        z = 0
                        while x > 0:
                            if linia[z] == ',':
                                x -= 1
                            z += 1
                        self.tag_add("sel", nr_linii+"."+str(2+self.ofset), nr_linii + "." + str(z-1))

                    else:
                        return 0
            except IndexError:
                return 0

        self.event_generate("<<Copy>>")
        return 'break'


class ButtonZaleznyOdWynik(tkinter.ttk.Button):
    def __init__(self, master, KatalogRoboczy, **options):
        self.master = master
        self.statusqueue = queue.Queue()
        self.KatalogRoboczy = KatalogRoboczy
        # self.buttonName = options['text']
        self.previousfile = 1
        self.actfile = 0
        self.funkcjaPrzyciskuPracuje = 0
        self.previousFunkcjaPrzyciskuPracuje = 1
        tkinter.ttk.Button.__init__(self, master, **options)
        self.bind('<Enter>', self.enter)
        self.bind('<Leave>', self.leave)
        self.update_me()

    def enter(self, event):
        if os.path.isfile(os.path.join(self.KatalogRoboczy, 'wynik.mp')) and not self.funkcjaPrzyciskuPracuje:
            self.configure(state='active')

    def leave(self, event):
        if os.path.isfile(os.path.join(self.KatalogRoboczy, 'wynik.mp')) and not self.funkcjaPrzyciskuPracuje:
            self.configure(state='normal')

    def update_me(self):

        try:
            string = self.statusqueue.get_nowait()
            if string.startswith('Koniec'):
                self.funkcjaPrzyciskuPracuje = 0
                self.previousFunkcjaPrzyciskuPracuje = 1
            elif string.startswith('Pracuje'):
                self.funkcjaPrzyciskuPracuje = 1
                self.previousFunkcjaPrzyciskuPracuje = 0
        except queue.Empty:
            # self.previousFunkcjaPrzyciskuPracuje = self.funkcjaPrzyciskuPracuje = 0
            pass

        self.actfile = os.path.isfile(os.path.join(self.KatalogRoboczy, 'wynik.mp'))

        if self.previousFunkcjaPrzyciskuPracuje != self.funkcjaPrzyciskuPracuje:
            if self.funkcjaPrzyciskuPracuje:
                self.configure(state='disabled')
            else:
                self.configure(state='normal')
            self.previousFunkcjaPrzyciskuPracuje = self.funkcjaPrzyciskuPracuje = 1

        else:
            if self.actfile != self.previousfile:
                # przypadek gdy plik wynik.mp pojawil sie
                if self.actfile:
                    self.configure(state='normal')
                elif not self.actfile:
                    self.configure(state='disabled')
                self.previousfile = self.actfile
            # elif self.configure('state')[-1] == 'disabled':
        self.master.update_idletasks()
        self.after(100, self.update_me)


class Argumenty(object):
    def __init__(self):
        self.umphome = None
        self.plikmp = None
        self.katrob = None
        self.obszary = []
        self.notopo = 0


class SetupMode(object):
    def __init__(self):
        self.umpHome = None
        self.modulyCVS = ModulCVS()
        self.modulyCVSLista = [a for a in self.modulyCVS.modulyCVS]

        self.modulyCVSCheckboksy = {}

        self.plikiDoSciagniecia = {'cvs.exe': 'http://ump.waw.pl/pliki/cvs.exe',
                                'mapedit2-1-78-18.zip': 'https://www.geopainting.com/download/mapedit2-1-78-18.zip'}
        if platform.architecture() == '32bit':
            self.plikiDoSciagniecia['mapedit++(32)1.0.61.513tb_3.zip'] = \
                'http://wheart.bofh.net.pl/gps/mapedit++(32)1.0.61.513tb_3.zip'
        else:
            self.plikiDoSciagniecia['mapedit++(64)1.0.61.513tb_3.zip'] = \
                'http://wheart.bofh.net.pl/gps/mapedit++(64)1.0.61.513tb_3.zip'
        # self.ListaObszarow = list()
        self.modulyCvsDoSciagniecia = list()
        self.utworz_katalog_ump()
        self.sciagnij_pliki()
        self.rozpakuj_pliki_do_katalogow()

        # budujemy okno z listą wszystkich obszarów
        self.glowneOknoDialkogCVS = tkinter.Tk(None)
        self.glowneOknoDialkogCVS.title(u'Lista obszarów do ściągnięcia')
        glownaRamkaOknaDialogowego = tkinter.ttk.Labelframe(self.glowneOknoDialkogCVS,
                                                            text=u'Wybierz obszary do ściągnięcia')
        glownaRamkaOknaDialogowego.pack(side='left', anchor='center', fill='both', expand=1)
        listaObszarowScrollBar_pionowy = tkinter.Scrollbar(glownaRamkaOknaDialogowego)
        listaObszarowScrollBar_pionowy.pack(fill='both', anchor='center', expand=0, side='right')
        listaObszarowScrollBar_poziomy = tkinter.Scrollbar(glownaRamkaOknaDialogowego, orient='horizontal')
        listaObszarowScrollBar_poziomy.pack(fill='both', anchor='w', expand=0, side='bottom')
        # dajemy 2 buttony sciagnij oraz anuluj
        self.loginEntryFrame = tkinter.ttk.Labelframe(self.glowneOknoDialkogCVS, text='Login do CVS')
        self.loginEntryFrame.pack(anchor='n')
        self.loginEntry = tkinter.Entry(self.loginEntryFrame)
        self.loginEntry.pack()
        self.loginEntry.insert('0', 'guest')
        ramkaPrzyciskow = tkinter.Frame(self.glowneOknoDialkogCVS, pady=25, padx=5)
        ramkaPrzyciskow.pack(anchor='s', fill='y', expand=1)
        sciagnijButton = tkinter.ttk.Button(ramkaPrzyciskow, text=u'Ściągnij', command=self.sciagnijButtonClick)
        sciagnijButton.pack(anchor='s', side='bottom')
        cancelButton = tkinter.ttk.Button(ramkaPrzyciskow, text='Anuluj', command=self.cancelButtonClick)
        cancelButton.pack(anchor='s', side='bottom')
        listaObszarowCanvas = tkinter.Canvas(glownaRamkaOknaDialogowego, width=900)
        listaObszarowCanvas.pack(side='left', fill='both', expand=1)

        listaObszarowScrollBar_pionowy.config(command=listaObszarowCanvas.yview)
        listaObszarowCanvas.config(yscrollcommand=listaObszarowScrollBar_pionowy.set)
        listaObszarowScrollBar_poziomy.config(command=listaObszarowCanvas.xview)
        listaObszarowCanvas.config(xscrollcommand=listaObszarowScrollBar_poziomy.set)

        ilosc_kolumn = 5
        akt_ilosc_wierszy = 0
        pozycja_ost_widgetu = 10
        for abc in self.modulyCVSLista:
            self.modulyCVSCheckboksy[abc] = []
            obszarFrame = tkinter.ttk.Labelframe(listaObszarowCanvas, text=abc)

            for bbb in range(len(self.modulyCVS.modulyCVS[abc])):
                self.modulyCVSCheckboksy[abc].append(tkinter.BooleanVar())
                self.modulyCVSCheckboksy[abc].append(tkinter.ttk.Checkbutton(obszarFrame, width=25,
                                                                             text=self.modulyCVS.modulyCVS[abc][bbb],
                                                                             variable=self.modulyCVSCheckboksy[abc][-1]))
                self.modulyCVSCheckboksy[abc][-1].grid(column=bbb % ilosc_kolumn, row=bbb // ilosc_kolumn)
                # ilosc_wierszy_danego_obszaru = bbb//ilosc_kolumn
                # print('ilosc kolumn danego obszaru: ', ilosc_wierszy_danego_obszaru)

            obszarFrame.update_idletasks()
            wys_widgetu = obszarFrame.winfo_reqheight()

            # ilosc_wierszy_umieszczonych = ilosc_wierszy_umieszczonych+ilosc_wierszy_danego_obszaru+1
            # print(ilosc_wierszy_umieszczonych)
            listaObszarowCanvas.create_window(50, 30 + pozycja_ost_widgetu, window=obszarFrame, anchor='nw', width=1100)
            pozycja_ost_widgetu += wys_widgetu

        listaObszarowCanvas.config(scrollregion=listaObszarowCanvas.bbox('all'))
        self.glowneOknoDialkogCVS.mainloop()

    def sciagnijButtonClick(self):
        # self.glowneOknoDialkogCVS.hide()
        cvs_user_name = self.loginEntry.get()
        for abc in self.modulyCVSLista:
            for bbb in range(0, len(self.modulyCVSCheckboksy[abc]), 2):
                if self.modulyCVSCheckboksy[abc][bbb].get():
                    self.modulyCvsDoSciagniecia.append(self.modulyCVS.modulyCVS[abc][int(bbb/2)])
        if 'narzedzia' not in self.modulyCvsDoSciagniecia:
            self.modulyCvsDoSciagniecia.append('narzedzia')
        CVSROOT = '-d:pserver:' + cvs_user_name + '@cvs.ump.waw.pl:/home/cvsroot'
        os.chdir(self.umpHome)
        process = subprocess.Popen(['cvs', '-q', CVSROOT, 'co'] + self.modulyCvsDoSciagniecia)
        processexitstatus = process.poll()

        while processexitstatus is None:
            time.sleep(1)
            processexitstatus = process.poll()

        print('Skonczylem sciaganie')
        tkinter.messagebox.showinfo(message='Skończyłeś ściąganie źródeł do katalogu:\n' + self.umpHome)
        self.glowneOknoDialkogCVS.destroy()
        return 0

    def cancelButtonClick(self):
        self.glowneOknoDialkogCVS.destroy()

    def utworz_katalog_ump(self):
        umpfoldernames = ['ump', 'umpsource', 'umpcvs', 'cvsump', 'ump_cvs', 'cvsump']
        home = os.path.expanduser('~')

        for a in umpfoldernames:
            abc = os.path.join(home, a)
            if os.path.isdir(abc):
                continue
            else:
                self.umpHome = abc
                break

        kol_numer = 1
        while not self.umpHome:
            abc = os.path.join(home, 'ump_' + str(kol_numer))
            if os.path.isdir(abc):
                kol_numer += 1
                continue
            else:
                self.umpHome = abc
        os.makedirs(self.umpHome)

    def sciagnij_pliki(self):
        for plik in self.plikiDoSciagniecia:
            try:
                u = urllib.request.urlopen(self.plikiDoSciagniecia[plik])
                f = open(os.path.join(self.umpHome, plik), 'wb')
                meta = u.info()
                print(meta['Content-Length'])
                filesize = int(meta['Content-Length'])
                print("Downloading: %s Bytes: %s" % (plik, filesize))
                file_size_dl = 0
                block_sz = 8192
                while True:
                    buffer = u.read(block_sz)
                    if not buffer:
                        break

                    file_size_dl += len(buffer)
                    f.write(buffer)
                    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / filesize)
                    status = status + chr(8)*(len(status)+1)
                    sys.stdout.write(status)
                    sys.stdout.flush()
                    # print(status)

                f.close()
            except urllib.error.HTTPError:
                print('Nie moge sciagnac pliku ' + plik)

    def rozpakuj_pliki_do_katalogow(self):
        # tworzymy katalogi mapedita i rozpakowujemy zipy
        os.chdir(self.umpHome)
        for plik in self.plikiDoSciagniecia:
            if not plik == 'cvs.exe':
                if plik.startswith('mapedit2'):
                    dest_directory = 'mapedit2'
                else:
                    dest_directory = 'mapedit++'
                with zipfile.ZipFile(plik, 'r') as plikzip:
                    os.makedirs(dest_directory)
                    print(u'Rozpakowuję plik: ' + plik)
                    plikzip.extractall(path=dest_directory)
                os.remove(plik)


class mdm_gui_py(tkinter.Tk):
    def __init__(self, parent):

        tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.cvsstatusQueue = queue.Queue()
        self.modul_cvs = ModulCVS()
        self.Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        self.args = Argumenty()
        self.initialize()
        if os.path.isfile(os.path.join(self.Zmienne.KatalogzUMP, 'narzedzia/ikonki/UMPlogo32.gif')):
            iconimg = tkinter.PhotoImage(file=os.path.join(self.Zmienne.KatalogzUMP, 'narzedzia/ikonki/UMPlogo32.gif'))
            self.tk.call('wm', 'iconphoto', self._w, iconimg)
        self.sprawdzAktualnoscZrodelandPopupMessage()

    def konfiguracja(self):
        aaa = ConfigWindow(self)

    def skrotyKlawiaturowe(self):
        aaa = HelpWindow(self)

    def kreatorMapaOSMAnd(self):
        obszary = [a for a in self.regionVariableDictionary if self.regionVariableDictionary[a].get()]
        if obszary:
            aaa = mdmkreatorOsmAnd.KreatorKompilacjiOSMAnd(self, self.mdmMontDemontOptions, obszary)
        else:
            tkinter.messagebox.showwarning(message=u'Nie wybrano żadnego obszaru.')

    def kreatorKlasDrog(self):
        obszary = [a for a in self.regionVariableDictionary if self.regionVariableDictionary[a].get()]
        if obszary:
            aaa = mdmkreatorOsmAnd.Klasy2EndLevelCreator(self, self.mdmMontDemontOptions, obszary)
        else:
            tkinter.messagebox.showwarning(message=u'Nie wybrano żadnego obszaru.')

    def kreator_stworz_plik_typ(self):
        if shutil.which('java') is not None:
            aaa = mdmkreatorOsmAnd.KreatorKompilacjiTyp(self, self.mdmMontDemontOptions)
        else:
            tkinter.messagebox.showwarning(message=u'Nie masz zainstalowanego środowiska java. Zainstaluj!')

    def kreator_skompiluj_mape(self):
        if shutil.which('java') is None:
            tkinter.messagebox.showwarning(message=u'Nie masz zainstalowanego środowiska java. Zainstaluj!')
        elif shutil.which('perl') is None:
            tkinter.messagebox.showwarning(message=u'Nie masz zainstalowanego środowiska perl. Zainstaluj!')
        else:
            obszary = [a for a in self.regionVariableDictionary if self.regionVariableDictionary[a].get()]
            if obszary:
                aaa = mdmkreatorOsmAnd.KreatorKompilacjiMdmmap(self, self.mdmMontDemontOptions, obszary)
            else:
                tkinter.messagebox.showwarning(message=u'Nie wybrano żadnego obszaru.')


    def cvs_co(self, obszar):
        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            tkinter.messagebox.showwarning(message=cvs_status)
        else:
            aaa = cvsOutputReceaver(self, [obszar], '', 'co')

    def initialize(self):

        # wczytywanie zapisanych opcji montazu i demontazu:
        self.protocol("WM_DELETE_WINDOW", self.Quit)
        self.mdmMontDemontOptions = mdmConfig()

        # pliki zmienione, do wysłania na cvs
        self.plikiDoCVS = set()
        self.uncommitedfilesqueue = queue.Queue()
        self.grid()

        # menu Plik
        menubar = tkinter.Menu(self)
        menuPlik = tkinter.Menu(menubar, tearoff=0)
        menuPlik.add_command(label=u'Konfiguracja', command=self.konfiguracja)
        menuPlik.add_separator()
        menuPlik.add_command(label=u'Wyjdź', command=self.Quit)
        menubar.add_cascade(label=u'Plik', menu=menuPlik)

        # menu Kreatory
        menuKreatory = tkinter.Menu(menubar, tearoff=0)
        menuKreatory.add_command(label=u'Mapa dla OSMAnda', command=self.kreatorMapaOSMAnd)
        menuKreatory.add_command(label=u'Mapa z podziałem dróg na klasy', command=self.kreatorKlasDrog)
        menuKreatory.add_command(label=u'Stworz i skompiluj plik typ.', command=self.kreator_stworz_plik_typ)
        menuKreatory.add_command(label=u'Skompiluj mape przy pomocy mkgmap.', command=self.kreator_skompiluj_mape)
        menubar.add_cascade(label=u'Kreatory', menu=menuKreatory)

        # menu CVS
        menu_pobierz = tkinter.Menu(menubar, tearoff=0)
        menuCVS = tkinter.Menu(menu_pobierz, tearoff=0)
        menuCVS_obszary = dict()
        for modul_cvs in self.modul_cvs.modulyCVS:
            menuCVS_obszary[modul_cvs] = tkinter.Menu(menuCVS, tearoff=0)
            menuCVS_obszary[modul_cvs].add_command(label=modul_cvs, command=lambda x=modul_cvs: self.cvs_co(x))
            for modul_pojedynczy in self.modul_cvs.modulyCVS[modul_cvs]:
                menuCVS_obszary[modul_cvs].add_command(label=modul_pojedynczy,
                                                       command=lambda x=modul_pojedynczy: self.cvs_co(x))

            menuCVS.add_cascade(label=modul_cvs, menu=menuCVS_obszary[modul_cvs])
        menu_pobierz.add_cascade(label=u'CVS', menu=menuCVS)
        menu_pobierz.add_separator()
        menu_pobierz.add_command(label='cvs.exe', command=self.pobierz_cvs)
        menu_pobierz.add_command(label='mapedit2-1.78-18.zip', command=self.pobierz_mapedit2)
        if platform.architecture() == '32bit':
            menu_pobierz.add_command(label='mapedit++(32)1.0.61.513tb_3.zip', command=self.pobierz_mapedit_plus)
        else:
            menu_pobierz.add_command(label='mapedit++(64)1.0.61.513tb_3.zip', command=self.pobierz_mapedit_plus)
        menubar.add_cascade(label=u'Pobierz', menu=menu_pobierz)

        # menu naloz latki
        menu_patch = tkinter.Menu(menubar, tearoff=0)
        menu_patch.add_command(label=u'Nałóż łatki', command=self.paczuj)
        menubar.add_cascade(label=u'Paczuj', menu=menu_patch)

        # menu opcje
        menu_opcje = tkinter.Menu(menubar, tearoff=0)
        menu_montuj_opcje = tkinter.Menu(menu_opcje, tearoff=0)
        menu_opcje.add_cascade(label=u'Opcje montażu', menu=menu_montuj_opcje)
        menu_montuj_opcje.add_checkbutton(label=u'Otwarte i EntryPoint w extras',
                                          variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('entry_otwarte_do_extras'))
        menu_montuj_opcje.add_checkbutton(label=u'Sprytne EntryPoints',
                                          variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('sprytne_entrypoints'))
        menu_montuj_opcje.add_checkbutton(label=u'Oszczędzaj pamięć',
                                          variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('savememory'))
        menu_montuj_opcje.add_checkbutton(label=u'Bez danych OSM',
                                          variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('no_osm'))
        menu_montuj_format_indeksow = tkinter.Menu(menu_montuj_opcje, tearoff=0)
        menu_montuj_format_indeksow.add_radiobutton(label=u'cityidx',
                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('format_indeksow'))
        menu_montuj_format_indeksow.add_radiobutton(label=u'cityname',
                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('format_indeksow'))
        menu_montuj_opcje.add_cascade(label=u'Format indeksu miast', menu=menu_montuj_format_indeksow)
        menu_demontuj_opcje = tkinter.Menu(menu_opcje, tearoff=0)
        menu_opcje.add_cascade(label=u'Opcje demontażu', menu=menu_demontuj_opcje)
        menu_demontuj_opcje.add_checkbutton(label=u'Usuń pustą numeracją',
                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('usun_puste_numery'))
        menu_demontuj_opcje.add_checkbutton(label=u'Standaryzuj komentarze',
                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('standaryzuj_komentarz'))
        menu_demontuj_opcje.add_checkbutton(label=u'Oszczędzaj pamięć',
                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('savememory'))
        menu_demontuj_opcje.add_checkbutton(label=u'Automatyczny rozkład obszarów i linii',
                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('autopolypoly'),
                                            command=lambda: self.selectUnselect_aol(None))
        menubar.add_cascade(label=u'Opcje', menu=menu_opcje)

        # menu CVS
        menu_cvs = tkinter.Menu(menubar, tearoff=0)
        menu_cvs.add_command(label='cvs annotate/log', command=self.cvs_annotate)
        menubar.add_cascade(label='CVS', menu=menu_cvs)

        # menu Pomoc
        menuPomoc = tkinter.Menu(menubar, tearoff=0)
        menuPomoc.add_command(label=u'Skróty klawiaturowe', command=self.skrotyKlawiaturowe)
        menubar.add_cascade(label=u'Pomoc', menu=menuPomoc)

        self.config(menu=menubar)

        self.regionyWersja = tkinter.Frame(self)
        self.regionyWersja.grid(columnspan=2, row=0, sticky='EW')
        self.regionyWersja.grid_columnconfigure(0, weight=1)
        self.regionyWersja.grid_columnconfigure(1, weight=1)
        # zmienna wskazuje czy mamy do czynienia z edytorem czy wrzucaczem. W zależności od tego możemy
        # albo kopiować pliki bezpośrednio, albo utworzyć archiwum zip do wysłania.
        self.mdm_mode = self.Zmienne.mdm_mode
        self.os = platform.system()
        self.osVersionVariable = tkinter.StringVar()
        self.osVersionVariable.set(u'Python: %s.%s.%s na %s %s (%s)' % (sys.version_info[0], sys.version_info[1],
                                                                        sys.version_info[0], platform.uname()[0],
                                                                        platform.uname()[2],
                                                                        platform.architecture()[0]))
        systemLabel = tkinter.ttk.Label(self.regionyWersja, textvariable=self.osVersionVariable)
        systemLabel.grid(column=0, row=0, sticky='w')
        self.guimodeVar = tkinter.StringVar()
        self.guimodeVar.set(u'Tryb pracy mdm: %s' % self.Zmienne.mdm_mode)
        guiMode = tkinter.ttk.Label(self.regionyWersja, textvariable=self.guimodeVar)
        guiMode.grid(column=1, row=0, sticky='w')
        self.autopolypoly = tkinter.ttk.Label(self.regionyWersja, text=u'Automatyczny rozkład obszarów i linii')
        self.autopolypoly.grid(column=2, row=0, sticky='w')
        self.selectUnselect_aol(None)

        # wybor regionow
        self.regionVariableDictionary = {}
        self.regionCheckButtonDictionary = {}

        self.regionyFrame = tkinter.ttk.LabelFrame(self, text=u'Wybór regionów')
        self.regionyFrame.grid(column=0, columnspan=2, row=1, sticky='ew')

        self.regionyFrame.bind_class('kolkomyszkiregiony', "<MouseWheel>", self._on_mousewheelregionyCanvas)
        self.regionyFrame.bind_class('kolkomyszkiregiony', "<Button-4>", self._on_mousewheelregionyCanvas)
        self.regionyFrame.bind_class('kolkomyszkiregiony', "<Button-5>", self._on_mousewheelregionyCanvas)
        newtags = self.regionyFrame.bindtags() + ('kolkomyszkiregiony',)
        self.regionyFrame.bindtags(newtags)

        regionyScroll = AutoScrollbar(self.regionyFrame)
        regionyScroll.grid(column=1, row=0, sticky='NS')
        newtags = regionyScroll.bindtags() + ('kolkomyszkiregiony',)
        regionyScroll.bindtags(newtags)

        regionyScrollX = AutoScrollbar(self.regionyFrame, orient='horizontal')
        regionyScrollX.grid(column=0, row=1, sticky='EW')

        # self.regionyListbox = tkinter.Listbox(self.regionyFrame,bd=1,highlightthickness=0,bg='SystemMenu',yscrollcommand = regionyScroll.set,height=4)
        # self.regionyListbox.grid(column=0,row=0)

        self.regionyCanvas = tkinter.Canvas(self.regionyFrame, yscrollcommand=regionyScroll.set,
                                            xscrollcommand=regionyScrollX.set, width=846, height=126,
                                            highlightthickness=0)
        self.regionyCanvas.grid(column=0, row=0, sticky='nsew')
        newtags = self.regionyCanvas.bindtags() + ('kolkomyszkiregiony',)
        self.regionyCanvas.bindtags(newtags)

        regionyScroll.config(command=self.regionyCanvas.yview)
        regionyScrollX.config(command=self.regionyCanvas.xview)

        self.regionyFrameInCanvas = tkinter.Frame(self.regionyCanvas)
        self.regionyFrameInCanvas.rowconfigure(1, weight=1)
        self.regionyFrameInCanvas.columnconfigure(1, weight=1)
        newtags = self.regionyFrameInCanvas.bindtags()+('kolkomyszkiregiony',)
        self.regionyFrameInCanvas.bindtags(newtags)

        self.GenerujListeObszarow()

        self.regionyCanvas.create_window(423, 0, anchor='n', window=self.regionyFrameInCanvas)
        self.regionyFrameInCanvas.update_idletasks()
        self.regionyCanvas.config(scrollregion=self.regionyCanvas.bbox("all"))
        # regionyScroll.config(command=self.regionyListbox.yview)

        buttonFrame = tkinter.Frame(self.regionyFrame)
        buttonFrame.grid_columnconfigure(0, weight=1)
        buttonFrame.grid_columnconfigure(1, weight=1)

        odswiezRegionyButton = tkinter.ttk.Button(buttonFrame, text=u'Odśwież listę regionów',
                                                  command=self.OnButtonClickOdswiezListeObszarow)
        odswiezRegionyButton.grid(column=0, row=0)

        cvsUaktualnijZrodlaButton = tkinter.ttk.Button(buttonFrame, text=u'Uaktualnij źródła (cvs update)',
                                                       command=self.OnButtonClickCvsUp)
        cvsUaktualnijZrodlaButton.grid(column=1, row=0)
        buttonFrame.grid(column=0, columnspan=2, row=2, sticky='ew')

        ####################################
        # montowanie
        ####################################
        self.montFrame = tkinter.ttk.LabelFrame(self, text=u'Montowanie i edycja')
        self.montFrame.grid(column=0, row=3)

        # cityindex
        # self.mdmMontDemontOptions.montDemontOptions['cityidx']
        # self.cityidx= tkinter.BooleanVar()
        # self.cityidx.set(False)
        self.montOptionCityIdxCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Obsługa indeksu miast',
                                                                variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('cityidx'),
                                                                onvalue=True, offvalue=False)
        self.montOptionCityIdxCheckbutton.grid(column=0, row=0, sticky='W')

        # pliki adresow
        # self.adrfile = tkinter.BooleanVar()
        # self.adrfile.set(False)
        self.montOptionAdrCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij adresy',
                                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('adrfile'),
                                                            onvalue=True, offvalue=False)
        self.montOptionAdrCheckbutton.grid(column=1, row=0, sticky='W')

        # szlaki
        # self.noszlaki = tkinter.BooleanVar()
        # self.noszlaki.set(False)
        self.montOptionNoszlakiCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij szlaki',
                                                                variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('noszlaki'),
                                                                onvalue=False, offvalue=True)
        self.montOptionNoszlakiCheckbutton.grid(column=0, row=1, sticky='W')

        # miasta
        # self.nocity = tkinter.BooleanVar()
        # self.nocity.set(False)
        self.montOptionNocityCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij miasta',
                                                                variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('nocity'),
                                                                onvalue=False, offvalue=True)
        self.montOptionNocityCheckbutton.grid(column=1, row=1, sticky='W')

        # punkty pnt
        # self.nopnt = tkinter.BooleanVar()
        # self.nopnt.set(False)
        self.montOptionNopntCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij punkty',
                                                                variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('nopnt'),
                                                                onvalue=False, offvalue=True)
        self.montOptionNopntCheckbutton.grid(column=0, row=2, sticky='W')

        # sumy kontrolne plikow
        # self.monthash= tkinter.BooleanVar()
        # self.monthash.set(False)
        self.montOptionNohashCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Generuj sumy kontrolne',
                                                                variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('monthash'),
                                                                onvalue=False, offvalue=True)
        self.montOptionNohashCheckbutton.grid(column=1, row=2, sticky='W')

        # extratypes
        # self.extratypes= tkinter.BooleanVar()
        # self.extratypes.set(False)
        self.montOptionExtratypesCheckbutton = tkinter.ttk.Checkbutton(self.montFrame,
                                                                       text=u'Specjalne traktowanie typów',
                                                                       variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('extratypes'),
                                                                       onvalue=True, offvalue=False)
        self.montOptionExtratypesCheckbutton.grid(column=0, row=3, sticky='W')

        # granice lokalne
        # self.graniceczesciowe=tkinter.BooleanVar()
        # self.graniceczesciowe.set(False)
        self.montOptionGraniceCzescioweCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Granice częściowe',
                                                                             variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('graniceczesciowe'),
                                                                             onvalue=True, offvalue=False)
        self.montOptionGraniceCzescioweCheckbutton.grid(column=1, row=3, sticky='W')

        self.montButton = tkinter.ttk.Button(self.montFrame, text=u'Montuj', command=self.OnButtonClickMont,
                                             state='disabled')
        self.montButton.grid(column=0, row=4)
        createToolTip(self.montButton, 'LPM - montuje mapę\nCtrl+PPM - odblokowuje przycisk\nCtrl+LPM - montuje mapę i uruchamia MapEdit z mapą')

        self.editButton = ButtonZaleznyOdWynik(self.montFrame, self.Zmienne.KatalogRoboczy, text=u'Edytuj',
                                               command=self.OnButtonClickEdit)
        self.editButton.bind('<Button-3>', self.OnButtonClickEdit2)
        self.editButton.grid(column=1, row=4)
        createToolTip(self.editButton, 'LPM - uruchamia podstawowy MapEdit z mapą\nPPM - uruchamia alternatywny MapEdit z mapą')

        #####################################
        # demontowanie
        #####################################

        self.demontFrame = tkinter.ttk.LabelFrame(self, text=u'Sprawdzanie i demontaż')
        self.demontFrame.grid(column=1, row=3)

        # obsługa indeksu miast
        self.demontOptionCityIdxCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame, text=u'Obsługa indeksu miast',
                                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('cityidx'),
                                                                    onvalue=True, offvalue=False)
        self.demontOptionCityIdxCheckbutton.grid(column=0, row=0, sticky='W')

        # obsługa sum kontrolnych
        # self.demonthash= tkinter.BooleanVar()
        # self.demonthash.set(False)
        self.demontOptionNohashCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame, text=u'Sprawdzaj sumy kontrolne',
                                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('demonthash'),
                                                                    onvalue=False, offvalue=True)
        self.demontOptionNohashCheckbutton.grid(column=0, row=1, sticky='W')

        # automatyczny rozkład poi
        # self.autopoi = tkinter.BooleanVar()
        # self.autopoi.set(False)
        self.demontOptionAutopoiLabel = tkinter.ttk.Checkbutton(self.demontFrame, text=u'Automatyczny rozkład poi',
                                                            variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('autopoi'),
                                                            onvalue=True, offvalue=False)
        self.demontOptionAutopoiLabel.grid(column=0, row=2, sticky='W')

        # zaokrąglanie
        # self.X = tkinter.StringVar()
        # self.X.set('0')
        self.demontOptionZaokraglanieRadio0 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Nie zaokrąglaj',
                                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('X'), value='0')
        self.demontOptionZaokraglanieRadio0.grid(column=1, row=0, sticky='W')
        self.demontOptionZaokraglanieRadio5 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Zaokrąglij do 5 cyfr',
                                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('X'), value='5')
        self.demontOptionZaokraglanieRadio5.grid(column=1, row=1, sticky='W')
        self.demontOptionZaokraglanieRadio6 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Zaokrąglij do 6 cyfr',
                                                                    variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('X'), value='6')
        self.demontOptionZaokraglanieRadio6.grid(column=1, row=2, sticky='W')

        # extratypes
        self.demontOptionExtratypesCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame,
                                                                         text=u'Specjalne traktowanie typów',
                                                                         variable=self.mdmMontDemontOptions.zwroc_zmienna_opcji('extratypes'),
                                                                         onvalue=True, offvalue=False)
        self.demontOptionExtratypesCheckbutton.grid(columnspan=2, row=3, sticky='W')

        # przycisk demontuj
        self.demontButton = ButtonZaleznyOdWynik(self.demontFrame, self.Zmienne.KatalogRoboczy, text=u'Demontuj',
                                                 command=self.OnButtonClickDemont)
        self.demontButton.grid(column=1, row=4)

        # przycisk sprawdź
        self.sprawdzButton = ButtonZaleznyOdWynik(self.demontFrame, self.Zmienne.KatalogRoboczy, text=u'Sprawdź błędy',
                                                  command=self.OnButtonClickSprawdz)
        self.sprawdzButton.grid(column=0, row=4)
        createToolTip(self.sprawdzButton, 'LPM - uruchamia sprawdzanie błędów\nPPM - czyści okno błędów')

        # #######################################################
        # zmienione pliki do wyswietlenia, obejrzenia itd
        # #######################################################

        self.diffFrame = tkinter.ttk.LabelFrame(self, text=u'Zmienione pliki')
        self.diffFrame.grid(columnspan=2, row=4)

        diffScrollY = AutoScrollbar(self.diffFrame)
        diffScrollY.grid(column=1, row=0, sticky='NS')
        newtags = diffScrollY.bindtags()+('movewheel',)
        diffScrollY.bindtags(newtags)

        diffScrollX = AutoScrollbar(self.diffFrame, orient='horizontal')
        diffScrollX.grid(column=0, row=1, sticky='EW')

        self.diffCanvas = tkinter.Canvas(self.diffFrame, yscrollcommand=diffScrollY.set,
                                         xscrollcommand=diffScrollX.set, width=835, height=160, highlightthickness=0)
        self.diffCanvas.grid(column=0, row=0, sticky='nsew')
        self.diffCanvas.bind_class('movewheel', "<MouseWheel>", self._on_mousewheediffCanvas)
        self.diffCanvas.bind_class('movewheel', "<Button-4>", self._on_mousewheediffCanvas)
        self.diffCanvas.bind_class('movewheel', "<Button-5>", self._on_mousewheediffCanvas)
        newtags = self.diffCanvas.bindtags()+('movewheel',)
        self.diffCanvas.bindtags(newtags)
        diffScrollY.config(command=self.diffCanvas.yview)
        diffScrollX.config(command=self.diffCanvas.xview)

        # ramka w canvas
        self.frameInDiffCanvas = ListaPlikowFrame(self.diffCanvas, self.Zmienne)
        self.frameInDiffCanvas.grid(column=0, row=0)
        newtags = self.frameInDiffCanvas.bindtags()+('movewheel',)
        self.frameInDiffCanvas.bindtags(newtags)

        style1 = tkinter.ttk.Style()
        style1.configure('Helvetica1.TLabel', font=('Helvetica', 9))
        plikLabel = tkinter.ttk.Label(self.frameInDiffCanvas, text=u'Pliki', borderwidth=4, relief='raised', width=60,
                                      anchor='w', style='Helvetica1.TLabel')
        plikLabel.grid(row=0, column=0)
        newtags = plikLabel.bindtags() + ('movewheel',)
        plikLabel.bindtags(newtags)

        dodanoLabel = tkinter.ttk.Label(self.frameInDiffCanvas, text=u'Dodano', borderwidth=4, relief='raised',
                                        width=10, anchor='center', style='Helvetica1.TLabel')
        dodanoLabel.grid(row=0, column=1)
        newtags = dodanoLabel.bindtags() + ('movewheel',)
        dodanoLabel.bindtags(newtags)

        skasowanoLabel = tkinter.ttk.Label(self.frameInDiffCanvas, text=u'Skasowano', borderwidth=4, relief='raised',
                                           width=10, anchor='center', style='Helvetica1.TLabel')
        skasowanoLabel.grid(row=0, column=2)
        newtags = skasowanoLabel.bindtags() + ('movewheel',)
        skasowanoLabel.bindtags(newtags)

        akcjeLabel = tkinter.ttk.Label(self.frameInDiffCanvas, text=u'Możliwe akcje', borderwidth=4, relief='raised',
                                       width=30, anchor='center', style='Helvetica1.TLabel')
        akcjeLabel.grid(row=0, columnspan=2, column=3)
        newtags = akcjeLabel.bindtags() + ('movewheel',)
        akcjeLabel.bindtags(newtags)

        self.diffCanvas.create_window(0, 0, anchor='ne', window=self.frameInDiffCanvas)
        self.diffCanvas.update_idletasks()
        self.diffCanvas.config(scrollregion=self.diffCanvas.bbox("all"))

        self.diffFrameApplyButtonVariable = tkinter.StringVar()
        if self.mdm_mode == 'edytor':
            self.diffFrameApplyButtonVariable.set(u'Skopiuj pliki')
        else:
            self.diffFrameApplyButtonVariable.set(u'Utwórz plik zip')

        buttonFrame = tkinter.Frame(self.diffFrame)
        buttonFrame.grid_columnconfigure(0, weight=1)
        buttonFrame.grid_columnconfigure(1, weight=1)

        diffFrameApplyButton = tkinter.ttk.Button(buttonFrame, textvariable=self.diffFrameApplyButtonVariable,
                                                  command=self.OnButtonClickApply)
        diffFrameApplyButton.grid(column=1, row=0)

        diffFrameCVSCommitButton = tkinter.ttk.Button(buttonFrame, text=u'Zatwierdź zmiany (cvs commit)',
                                                      command=self.OnButtonClickCvsCommit)
        diffFrameCVSCommitButton.grid(column=0, row=0)
        buttonFrame.grid(column=0, row=2, sticky='ew')

        # ###################################################
        # stderr będą wyświetlane tutaj
        # ###################################################
        self.stderrFrame = tkinter.ttk.LabelFrame(self, text=u'Błędy')
        self.stderrFrame.grid(column=0, row=5, sticky='news')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.stderrFrame.grid_columnconfigure(0, weight=1)
        self.stderrFrame.grid_rowconfigure(0, weight=1)

        self.stderrText = stdOutstdErrText(self.stderrFrame, width=60, height=6, wrap='none', font=('Courier', 8))
        self.stderrText.grid(column=0, row=0, sticky='news')
        self.stderrqueue = self.stderrText.inputqueue
        # Teraz dopiero można zbindować czyszczenie błędów
        self.sprawdzButton.bind('<Button-3>', self.stderrText.event_clear_all_event)

        ####################################################
        # stdout będą wyświetlanu tutaj
        ####################################################

        self.stdoutFrame = tkinter.ttk.LabelFrame(self, text=u'Komunikaty')
        self.stdoutFrame.grid(column=1, row=5, sticky='news')
        self.grid_columnconfigure(1, weight=1)
        self.stdoutFrame.grid_columnconfigure(0, weight=1)
        self.stdoutFrame.grid_rowconfigure(0, weight=1)

        self.stdoutText = stdOutstdErrText(self.stdoutFrame, width=60, height=6, wrap='none', font=('Courier', 8))
        self.stdoutText.grid(column=0, row=0, sticky='news')

        self.stdoutqueue = self.stdoutText.inputqueue

        # self.stdoutText.configure(font=(size=10,))
        # rozkład obszarów i linii włącza się i wyłącza skrótem klawiaturowym, tutaj robię bind do tego
        self.bind_all("<Control-a><Control-o><Control-l>", self.selectUnselect_aol)
        # skrót klawiaturowy montuj
        self.bind("<Control-m>", self.montuj_shortcut)
        # skrót do demontuj
        self.bind("<Control-d>", self.demontuj_shortcut)
        # skrót do montuj a później edit
        self.bind("<E>", self.montuj_edit_shortcut)
        self.montButton.bind("<Control-Button-1>", self.montuj_edit_shortcut)
        # skrót do edytuj
        self.bind("<Control-e>", self.edit_shortcut)
        # skrót do aktywuj klawisz mont
        self.bind("<R>", self.aktywuj_montbutton)
        self.montButton.bind("<Control-Button-3>", self.aktywuj_montbutton)
        # skrót do cvs up
        self.bind("<Control-u>", self.cvsUpShortcut)
        # skrót do sprawdź
        self.bind("<Control-s>", self.sprawdz_shortcut)
        # skrót do usuń zawartość katalogu roboczego
        self.bind("<Control-Shift-KeyPress-C>", self.czysc_shortcut)
        # skrót klawiaturowy do pomocy
        self.bind('<F1>', lambda event: self.skrotyKlawiaturowe())

    def sprawdzAktualnoscZrodelandPopupMessage(self):
        try:
            while 1:
                queue_string = self.cvsstatusQueue.get_nowait()
                if queue_string == 'aktualne':
                    pass
                else:
                    tkinter.messagebox.showwarning(u'Nieaktualne źródła', u'Pliki na serwerze są nowsze niż te które montujesz. Powinieneś najpierw zaktualizować źródła.')

        except queue.Empty:
            pass
        self.after(100, self.sprawdzAktualnoscZrodelandPopupMessage)

    # bindowanie do skrótów klawiaturowych
    # włączanie i wyłączanie automatycznego rozkładu polylinii i polygonów
    def selectUnselect_aol(self, event):

        if event:
            aaa = self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].get()
            aaa = not aaa
            self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].set(aaa)

        if self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].get():
            self.autopolypoly.configure(background='lawn green')
        else:
            self.autopolypoly.configure(background='orange red')

    def montuj_shortcut(self, event):
        if str(self.montButton['state']) != 'disabled':
            self.OnButtonClickMont()
        return 0

    def demontuj_shortcut(self, event):
        if str(self.demontButton['state']) != 'disabled':
            self.OnButtonClickDemont()
        return 0

    def sprawdz_shortcut(self, event):
        if str(self.sprawdzButton['state']) != 'disabled':
            self.OnButtonClickSprawdz()

    def edit_shortcut(self, event):
        if str(self.editButton['state']) != 'disabled':
            self.OnButtonClickEdit()

    def montuj_edit_shortcut(self, event):
        if str(self.montButton['state']) != 'disabled':
            self.OnButtonClickMont()
            thread = threading.Thread(target=self.help_function_montuj_edit_shortcut, args=())
            thread.start()

    def help_function_montuj_edit_shortcut(self):
        # najpierw czekamy aż wynik.mp zostanie usuniety
        while os.path.isfile(os.path.join(self.Zmienne.KatalogRoboczy, 'wynik.mp')):
            time.sleep(0.1)
        # teraz czekamy aż plik się pojawi po zamontowaniu
        while not os.path.isfile(os.path.join(self.Zmienne.KatalogRoboczy, 'wynik.mp')):
            time.sleep(0.1)
        self.OnButtonClickEdit()

    def aktywuj_montbutton(self, event):
        self.MontButtonStateSet()

    def cvsUpShortcut(self, event):
        self.OnButtonClickCvsUp()

    def czysc_shortcut(self, event):
        self.args.wszystko = 1
        self.args.stderrqueue = self.stderrqueue
        self.args.stdoutqueue = self.stdoutqueue
        mont_demont_py.czysc(self.args)

    # koniec bindowania do skrótów klawiaturowych
    def GenerujListeObszarow(self):
        args = Argumenty()
        style = tkinter.ttk.Style()
        style.configure('Helvetica.TCheckbutton', font=('Helvetica', 9))
        listaNazwObszarow = mont_demont_py.listujobszary(args)
        for a in self.regionCheckButtonDictionary:
            self.regionCheckButtonDictionary[a].destroy()
        self.regionVariableDictionary = {}
        self.regionCheckButtonDictionary = {}
        # self.regionContexMenuDictionary={}

        for aaa in range(len(listaNazwObszarow)):
            self.regionVariableDictionary[listaNazwObszarow[aaa]] = tkinter.IntVar()
            nazwaobszaru = listaNazwObszarow[aaa].split('-', 1)[1]
            if len(nazwaobszaru) > 13:
                nazwaobszaru = nazwaobszaru[:12]
            self.regionCheckButtonDictionary[listaNazwObszarow[aaa]] = myCheckbutton(self.regionyFrameInCanvas, args, listaNazwObszarow[aaa], text=nazwaobszaru,
                                                                                    zmienna=self.regionVariableDictionary[listaNazwObszarow[aaa]],
                                                                                    regionVariableDictionary=self.regionVariableDictionary,
                                                                                    variable=self.regionVariableDictionary[listaNazwObszarow[aaa]],
                                                                                    onvalue=1, offvalue=0, style='Helvetica.TCheckbutton',
                                                                                    command=self.MontButtonStateSet)
            #self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].regionVariableDictionary=self.regionVariableDictionary
            newtags = self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].bindtags() + ('kolkomyszkiregiony',)
            self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].bindtags(newtags)

            self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].grid(column=aaa % 8, row=aaa // 8, sticky='W')

    # prawdopodobnie do usuniecia, chyba nadmiar
    # def show_menu(self, e):
    # 	self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def _on_mousewheelregionyCanvas(self, event):
        if self.os == 'Linux':
            if event.num == 4:
                self.regionyCanvas.yview_scroll(int(-1), "units")
            elif event.num == 5:
                self.regionyCanvas.yview_scroll(int(1), "units")
        elif self.os == 'Windows':
            self.regionyCanvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mousewheediffCanvas(self, event):
        if self.os == 'Linux':
            if event.num == 4:
                self.diffCanvas.yview_scroll(int(-1), "units")
            elif event.num == 5:
                self.diffCanvas.yview_scroll(int(1), "units")
        elif self.os == 'Windows':
            self.diffCanvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def MontButtonStateSet(self):
        self.args.obszary = [a for a in self.regionVariableDictionary if self.regionVariableDictionary[a].get()]
        if len(self.args.obszary) > 0:
            self.montButton.configure(state='normal')
        else:
            self.montButton.configure(state='disabled')
        return 0

    def OnButtonClickOdswiezListeObszarow(self):
        self.GenerujListeObszarow()
        self.MontButtonStateSet()

    def OnButtonClickApply(self):
        # tymczasowo, dopoki nie dorobie przesylania pomiedzy watkami
        # self.plikiDoCVS=[]

        if self.mdm_mode != 'edytor' and len(self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania) > 0:
            plikzipname = 'UMP' + str(datetime.datetime.now().year) + str(datetime.datetime.now().month) + \
                          str(datetime.datetime.now().day) + '_' + str(datetime.datetime.now().hour) + '-' + \
                          str(datetime.datetime.now().minute) + '.zip'
            plikzip = zipfile.ZipFile(os.path.join(self.Zmienne.KatalogRoboczy, plikzipname), 'w')
        for a in self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania:
            # zmienna IntVar nie moze byc odczytana bezposrednio, trzeba poprzez funkcje get()
            if self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].get() == 1:

                #przed kopiowaniem nalezy sprawdzic czy dany plik to naprawde dany plik, czy moze ktos
                # w miedzyczasie go zmienil, wykorzystamy do tego hashe dla plikow
                try:
                    with open(os.path.join(self.Zmienne.KatalogzUMP, a), 'rb') as f:
                        if hashlib.md5(f.read()).hexdigest() == self.frameInDiffCanvas.nazwapliku_Hash[a]:
                            if self.mdm_mode == 'edytor':
                                kopiuj_co = os.path.join(self.Zmienne.KatalogRoboczy, a.replace(os.sep, '-'))
                                kopiuj_na_co = os.path.join(self.Zmienne.KatalogzUMP, a)
                                shutil.copy(kopiuj_co, kopiuj_na_co)
                                self.stdoutqueue.put('%s-->%s\n' % (a.replace(os.sep, '-'), kopiuj_na_co))
                                print('%s-->%s' % (a.replace(os.sep, '-'), kopiuj_na_co))
                                self.plikiDoCVS.add(a)
                            else:
                                plikzip.write(os.path.join(self.Zmienne.KatalogRoboczy, a.replace(os.sep, '-'))
                                              + '.diff', a.replace(os.sep, '-') + '.diff')
                                self.stdoutqueue.put('%s-->%s\n' % (a.replace(os.sep, '-'), plikzipname))
                                print('%s-->%s' % (a.replace(os.sep, '-'), plikzipname))
                            b = self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
                            self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
                            self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='lawn green')
                            self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
                        else:
                            self.stderrqueue.put(u'Suma kontrolna pliku %s\nnie zgadza sie.\nPróbuję nałożyć łatki przy pomocy patch.\n' % a)
                            patch_result = self.patchExe(a.replace(os.sep, '-') + '.diff')
                            b = self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
                            if patch_result == 0:
                                self.stdoutqueue.put(u'Łatka nałożona bezbłędnie.\n')
                                self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='lawn green')
                            elif patch_result == 1:
                                self.stdoutqueue.put(u'Łatka nałożona z problemami, sprawdź plik!\n')
                                self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(
                                    background='gold')
                            else:
                                self.stdoutqueue.put(u'Nakładanie łatki zakończone katastrofą. Próbuj ręcznie!\n')
                                self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='red')
                            self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(
                                state='disabled')
                            self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
                except FileNotFoundError:
                    if a.find('_nowosci') >= 0:
                        print(a)
                        plikzip.write(os.path.join(self.Zmienne.KatalogRoboczy, a), a)
                        self.stdoutqueue.put('%s-->%s\n' % (a, plikzipname))
                        print('%s-->%s' % (a, plikzipname))
                        b = self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
                        self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
                        self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='lawn green')
                        self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
                    else:
                        self.stderrqueue.put(u'Nie moge odnaleźć pliku %s. Musisz go skopiować ręcznie.\n' % a)
                        print(u'Nie moge odnaleźć pliku %s. Musisz go skopiować ręcznie.' % a, file=sys.stderr)
                        b = self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
                        self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
                        self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='red')
                        self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)

        if self.mdm_mode != 'edytor' and len(self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania) > 0:
            plikzip.close()

    # obsługa poleceń cvs
    def pobierz_cvs(self):
        self.pobierz_pliki_z_internetu('http://ump.waw.pl/pliki/cvs.exe')
        tkinter.messagebox.showinfo(u'Pobieranie zakończone', u'Plik cvs.exe został pobrany i zapisany w katalogu.')

    def pobierz_mapedit2(self):
        url = 'https://www.geopainting.com/download/mapedit2-1-78-18.zip'
        self.pobierz_pliki_z_internetu('https://www.geopainting.com/download/mapedit2-1-78-18.zip')
        tkinter.messagebox.showinfo(u'Pobieranie zakończone', u'Program mapedit2 został pobrany i zapisany w katalogu.')

    def pobierz_mapedit_plus(self):
        url = 'http://wheart.bofh.net.pl/gps/mapedit++(64)1.0.61.513tb_3.zip'
        if platform.architecture() == '32bit':
            url = 'http://wheart.bofh.net.pl/gps/mapedit++(32)1.0.61.513tb_3.zip'
        self.pobierz_pliki_z_internetu(url)
        tkinter.messagebox.showinfo(u'Pobieranie zakończone',
                                    u'Program mapedit++ został pobrany i zapisany w katalogu.')

    def pobierz_pliki_z_internetu(self, url):
        katalog_przeznaczenia = tkinter.filedialog.askdirectory(title=u'Wskaż katalog przeznaczenia')
        if not katalog_przeznaczenia:
            return
        temporary_file = tempfile.NamedTemporaryFile(delete=False)
        downloadProgressBar = MyProgressBar(self, temporary_file, url)
        downloadProgressBar.wait_window()
        if url.endswith('.zip') and \
                tkinter.messagebox.askyesno('Kopiowanie', 'Czy rozpakować edytor do katalogu przeznaczenia?'):
            with zipfile.ZipFile(temporary_file.name, 'r') as plikzip:
                plikzip.extractall(path=katalog_przeznaczenia)
        else:
            nazwa_pliku = url.split('/')[-1]
            shutil.copy(temporary_file.name, os.path.join(katalog_przeznaczenia, nazwa_pliku))
        os.remove(temporary_file.name)

    # obsługa menu paczuj
    def paczuj(self):
        # najpierw pobierz łatki do nałożenia
        lista_latek = tkinter.filedialog.askopenfilenames(title="Wskaż łatki", filetypes=((u'pliki łatek', '*.diff'),
                                                                                          (u'pliki łatek', '*.patch'),
                                                                                          (u'wszystkie pliki', '*.*')))
        if lista_latek:
            wynik_nakladania_latek = dict()
            for latka in lista_latek:
                wynik_nakladania_latek[latka] = self.patchExe(latka)
            paczuj_rezultaty = PaczujResult(self, wynik_nakladania_latek)
            paczuj_rezultaty.wait_window()

    def patchExe(self, pliki_diff):
        self.args.pliki_diff = [pliki_diff]
        self.args.stderrqueue = self.stderrqueue
        self.args.stdoutqueue = self.stdoutqueue
        self.args.katrob = self.Zmienne.KatalogRoboczy
        a = mont_demont_py.patch(self.args)
        return a

    # obsluga menu CVS
    def cvs_annotate(self):
        aaa = CvsAnnotate(self, self.Zmienne)

    def OnButtonClickCvsUp(self):
        obszary = [aaa for aaa in self.regionVariableDictionary if self.regionVariableDictionary[aaa].get()]
        obszarywszystkie = [aaa for aaa in self.regionVariableDictionary]
        if not obszary:
            obszary = obszarywszystkie
            obszary.append('narzedzia')
        else:
            obszary.append('narzedzia')

        cvs_status = sprawdz_czy_cvs_obecny()
        if cvs_status:
            tkinter.messagebox.showwarning(message=cvs_status)
        else:
            if os.path.isfile(os.path.join(self.Zmienne.KatalogRoboczy, 'wynik.mp')):
                if tkinter.messagebox.askyesno(u'Plik wynik.mp istnieje',
                                               u'W katalogu roboczym istniej plik wynik.mp.\nCvs up może uniemożliwić demontaż. Czy kontynuować pomimo tego?'):
                    doCVS = cvsOutputReceaver(self, obszary, '', 'up')
                else:
                    pass
            else:
                doCVS = cvsOutputReceaver(self, obszary, '', 'up')

        # doCVS=cvsOutputReceaver(self,obszary,'','up')

    def OnButtonClickCvsCommit(self):
        if self.plikiDoCVS:
            pliki_z_niepoprawnymi_kluczami, pliki_z_konfliktami = \
                cvs_sprawdz_czy_tylko_dozwolone_klucze_i_brak_konfliktow(self.plikiDoCVS, self.Zmienne)
            if pliki_z_niepoprawnymi_kluczami:
                l_plik = '\n'.join([n_pliku + ': ' + ', '.join(pliki_z_niepoprawnymi_kluczami[n_pliku]) for
                                          n_pliku in pliki_z_niepoprawnymi_kluczami])
                informacja = u'Uwaga. W następujacych plikach w cvs są niepoprawne klucze. ' \
                             u'Czy na pewno kontynuować?\n\n' + l_plik
                if not tkinter.messagebox.askyesno('Niepoprawne klucze w plikach!', message=informacja):
                    return
            if pliki_z_konfliktami:
                informacja = u'Uwaga. W następujacych plikach w cvs są konflikty. Usuń je przed kontynuacją.\n' + \
                             '\n'.join(pliki_z_konfliktami)
                tkinter.messagebox.showwarning(message=informacja)
            else:
                oknodialogowe = cvsDialog(self, self.plikiDoCVS, title=u'Prześlij pliki do repozytorium cvs')
                if oknodialogowe.iftocommit == 'tak':
                    cvs_status = sprawdz_czy_cvs_obecny()
                    if cvs_status:
                        tkinter.messagebox.showwarning(message=cvs_status)
                    else:
                        doCVS = cvsOutputReceaver(self, self.plikiDoCVS, oknodialogowe.message, 'ci')
                        self.plikiDoCVS = doCVS.uncommitedfiles
        else:
            tkinter.messagebox.showwarning('Brak plików do wysłania', message='Nie mam żadnych plików do wysłania.')

    def cvsSprawdzAktualnoscMontowanychObszarow(self, *obszary):
        Needs_Patch = 0
        Zmienne = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
        CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        subprocess_args = ['cvs', '-q', CVSROOT, 'status']
        for a in obszary:
            subprocess_args.append(a)

        subprocess_args.append('narzedzia' + os.sep + 'granice.txt')

        os.chdir(Zmienne.KatalogzUMP)
        process = subprocess.Popen(subprocess_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for a in process.stdout.readlines():
            if a.decode(Zmienne.Kodowanie).find('Needs Patch') > 0:
                Needs_Patch = 1
                print(a.decode(Zmienne.Kodowanie))
        if Needs_Patch:
            self.cvsstatusQueue.put('nieaktualne')
        else:
            self.cvsstatusQueue.put('aktualne')
        return 0

    def OnButtonClickMont(self):
        # czyscimy liste plikow ktore pozostaly z poprzedniego demontazu
        self.frameInDiffCanvas.WyczyscPanelzListaPlikow()
        self.args = self.mdmMontDemontOptions.zwroc_args_do_mont()
        self.args.obszary = [a for a in self.regionVariableDictionary if self.regionVariableDictionary[a].get()]
        self.args.trybosmand = 0
        self.args.stderrqueue = self.stderrqueue
        self.args.stdoutqueue = self.stdoutqueue
        thread = threading.Thread(target=mont_demont_py.montujpliki, args=(self.args,))
        thread.start()
        thread1 = threading.Thread(target=self.cvsSprawdzAktualnoscMontowanychObszarow, args=(self.args.obszary))
        thread1.start()
        self.montButton.configure(state='disabled')

    def OnButtonClickEdit(self):
        self.args.plikmp = None
        self.args.mapedit2 = False
        self.args.stderrqueue = self.stderrqueue
        thread = threading.Thread(target=mont_demont_py.edytuj, args=(self.args,))
        thread.start()

    def OnButtonClickEdit2(self, event):
        if os.path.isfile(os.path.join(self.Zmienne.KatalogRoboczy, 'wynik.mp')):
            self.args.plikmp = None
            self.args.mapedit2 = True
            self.args.stderrqueue = self.stderrqueue
            thread = threading.Thread(target=mont_demont_py.edytuj, args=(self.args,))
            thread.start()

    def OnButtonClickDemont(self):
        self.frameInDiffCanvas.WyczyscPanelzListaPlikow()
        self.args = self.mdmMontDemontOptions.zwroc_args_do_demont()
        my_queue = queue.Queue()
        self.args.queue = self.frameInDiffCanvas.queueListaPlikowFrame
        self.args.stderrqueue = self.stderrqueue
        self.args.stdoutqueue = self.stdoutqueue
        # kolejka do informowania guzika że właśnie działa i żeby się wyłączył
        self.args.buttonqueue = self.demontButton.statusqueue
        thread = threading.Thread(target=mont_demont_py.demontuj, args=(self.args,))
        thread.start()
        self.frameInDiffCanvas.update_idletasks()
        self.diffCanvas.config(scrollregion=self.diffCanvas.bbox("all"))

    def OnButtonClickSprawdz(self):
        self.args.plikmp = None
        self.args.stderrqueue = self.stderrqueue
        self.args.stdoutqueue = self.stdoutqueue
        self.args.sprawdzbuttonqueue = self.sprawdzButton.statusqueue
        thread = threading.Thread(target=mont_demont_py.sprawdz, args=(self.args,))
        thread.start()
        thread1 = threading.Thread(target=mont_demont_py.sprawdz_numeracje, args=(self.args,))
        thread1.start()

    def Quit(self):
        self.mdmMontDemontOptions.saveConfig()
        self.quit()

    def GenerujListeLatek(self):
        pass


if __name__ == "__main__":

    if DownloadEverything:
        abcd = SetupMode()
        sys.exit(1)
    else:
        app = mdm_gui_py(None)
        app.title(u'mdm-py')

        app.mainloop()
