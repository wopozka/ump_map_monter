import shutil
import tkinter
import tempfile
import os
import os.path


class MdmEdytorPlikow(tkinter.Toplevel):
    def __init__(self, parent, zmienne, *args, **kwargs):
        self.parent = parent
        self.zmienne = zmienne
        self.katalog_ostatniego_pliku = self.zmienne.KatalogzUMP
        super().__init__(parent, *args, **kwargs)
        self.cursor_index = '1.0'
        ramka_glowna = tkinter.Frame(self)
        ramka_glowna.pack(fill='both', expand=1)

        wskaz_wczytaj_zapisz_zamknij_frame = tkinter.Frame(ramka_glowna, pady=4)
        wskaz_wczytaj_zapisz_zamknij_frame.pack(fill='x')
        wskaz_sciezke_frame = tkinter.Frame(wskaz_wczytaj_zapisz_zamknij_frame, padx=4)
        wskaz_sciezke_frame.pack(side='left')
        self.wybierz_plik_var = tkinter.StringVar()
        self.wybierz_plik_box = tkinter.ttk.Combobox(wskaz_sciezke_frame, width=55, textvariable=self.wybierz_plik_var)
        self.wybierz_plik_box.pack(side='left')
        self.wybierz_plik_box['values'] = [os.path.join(zmienne.KatalogRoboczy, zmienne.OutputFile)]
        wybierz_plik_button = tkinter.ttk.Button(wskaz_sciezke_frame, text=u'Wskaż ścieżkę do pliku',
                                                 command=self.wybierz_plik)
        wybierz_plik_button.pack(side='left')

        otworz_zapisz_frame = tkinter.Frame(wskaz_wczytaj_zapisz_zamknij_frame, padx=4)
        otworz_zapisz_frame.pack(side='left', fill='x')
        wybierz_plik_label = tkinter.Label(otworz_zapisz_frame)
        wybierz_plik_label.pack(side='left')
        otworz_button = tkinter.ttk.Button(otworz_zapisz_frame, text='Wczytaj plik', command=self.wczytaj_plik)
        otworz_button.pack(side='left')
        zapisz_button = tkinter.ttk.Button(otworz_zapisz_frame, text='Zapisz plik', command=self.zapisz_plik)
        zapisz_button.pack(side='left')


        zamknij_button = tkinter.ttk.Button(wskaz_wczytaj_zapisz_zamknij_frame, text='Zamknij edytor',
                                            command=self.zamknij_edytor)
        zamknij_button.pack(side='right')
        # informacja o pliku ktory jest otwarty i ktory zostanie zapisany
        otwarty_plik_frame = tkinter.Frame(ramka_glowna, pady=4)
        otwarty_plik_frame.pack(fill='x', expand=1)
        wybrany_plik_text = tkinter.Label(otwarty_plik_frame, text='Otwarty plik:')
        wybrany_plik_text.pack(side='left')
        self.otwarty_plik_variable = tkinter.StringVar()
        otwarty_plik = tkinter.Label(otwarty_plik_frame, textvariable=self.otwarty_plik_variable, bg='sky blue')
        otwarty_plik.pack(side='left', fill='x', expand=1)

        # poprawny edytor
        edytor_frame = tkinter.Frame(ramka_glowna)
        edytor_frame.pack(expand=1, fill='both')
        edytor_r_sidebar_frame = tkinter.Frame(edytor_frame)
        edytor_r_sidebar_frame.pack(fill='both', expand=1)
        self.edytor = MdmText(edytor_r_sidebar_frame)
        self.edytor.pack(side='left', fill='both', expand=1)
        r_sidebar_pionowy = tkinter.ttk.Scrollbar(edytor_r_sidebar_frame, orient='vertical', command=self.edytor.yview)
        r_sidebar_pionowy.pack(side='left', fill='y')
        b_sidebar_poziomy = tkinter.ttk.Scrollbar(edytor_frame, orient='horizontal', command=self.edytor.xview)
        b_sidebar_poziomy.pack(fill='x')
        self.edytor.config(yscrollcommand=r_sidebar_pionowy.set, xscrollcommand=b_sidebar_poziomy.set)

        ramka_znajdz_idz_do_linii = tkinter.Frame(ramka_glowna, pady=4)
        ramka_znajdz_idz_do_linii.pack(fill='x')
        ramka_znajdz = tkinter.Frame(ramka_znajdz_idz_do_linii, padx=4)
        ramka_znajdz.pack(side='left', fill='x', expand=1)
        znajdz_label = tkinter.Label(ramka_znajdz, text=u'Znajdź')
        znajdz_label.pack(side='left')
        self.znajdz_var = tkinter.StringVar()
        znajdz_entry = tkinter.Entry(ramka_znajdz, textvariable=self.znajdz_var)
        znajdz_entry.pack(side='left', fill='x', expand=1)
        znajdz_button_up = tkinter.ttk.Button(ramka_znajdz, text='<<', command=self.wyszukaj_w_gore)
        znajdz_button_up.pack(side='left')
        znajdz_button_down = tkinter.ttk.Button(ramka_znajdz, text='>>', command=self.wyszukaj_w_dol)
        znajdz_button_down.pack(side='left')

        ramka_idz_do_linii = tkinter.Frame(ramka_znajdz_idz_do_linii, padx=4)
        ramka_idz_do_linii.pack(side='left', fill='x', expand=1)
        idz_do_linii_label = tkinter.Label(ramka_idz_do_linii, text='Numer linii')
        idz_do_linii_label.pack(side='left')
        self.idz_do_linii_var = tkinter.StringVar()
        idz_do_linii_entry = tkinter.Entry(ramka_idz_do_linii, textvariable=self.idz_do_linii_var)
        idz_do_linii_entry.pack(side='left', fill='x', expand=1)
        idz_do_linii_button = tkinter.ttk.Button(ramka_idz_do_linii, text=u'Idz do linii', command=self.idz_do_linii_numer)
        idz_do_linii_button.pack(side='left')

    def zamknij_edytor(self):
        if not self.edytor.edit_modified():
            self.destroy()
        else:
            if tkinter.messagebox.askyesno(u'Czy na pewno zamknąć?',
                                           message=u'Zmiany w pliku nie zostały zapisane, czy na pewno kontynuować?',
                                           parent=self):
                self.destroy()

    def wczytaj_plik(self):
        if not self.wybierz_plik_var.get():
            return
        if self.edytor.edit_modified():
            if not tkinter.messagebox.askyesno(u'Plik niezapisany',
                                               message=u'Plik nie został zapisany. Czy kontynuować?', parent=self):
                return
        try:
            with open(self.wybierz_plik_var.get(), 'r', encoding='cp1250',
                      errors=self.zmienne.ReadErrors) as file_content:
                self.edytor.delete('1.0', 'end')
                self.edytor.mark_set('insert', '1.0')
                for linijka in file_content:
                    self.edytor.insert('insert', linijka)
                self.edytor.see('1.0')
                self.edytor.edit_modified(False)
            self.otwarty_plik_variable.set(self.wybierz_plik_var.get())
        except IOError:
            tkinter.messagebox.showinfo(parent=self, title='Problem z plikiem', message=u'Nie mogłem otworzyć pliku')

    def zapisz_plik(self):
        if not self.otwarty_plik_variable.get():
            return
        plik_tymczasowy = tempfile.NamedTemporaryFile(mode='w', encoding='cp1250', delete=False)
        try:
            plik_tymczasowy.write(self.edytor.get('1.0', 'end').rstrip('\n'))
            plik_tymczasowy.write('\n')
            if self.otwarty_plik_variable.get().edswith('.txt'):
                plik_tymczasowy.write('\n')
        except IOError:
            pass
        plik_tymczasowy.close()
        try:
            shutil.copy(plik_tymczasowy.name, self.otwarty_plik_variable.get())
        except PermissionError:
            tkinter.messagebox.showinfo(parent=self, title='Problem z plikiem',
                                        message=u'Nie mogłem zapisać pliku. Brak uprawnień')
        else:
            self.edytor.edit_modified(False)
        if os.path.exists(plik_tymczasowy.name):
            os.remove(plik_tymczasowy.name)

    def wybierz_plik(self):
        plik_do_otwarcia = tkinter.filedialog.askopenfilename(title=u'Plik cvs do otwarcia',
                                                              initialdir=self.katalog_ostatniego_pliku, parent=self,
                                                              filetypes=[('wszystkie', '*.*'),
                                                                         ('pliki tekstowe', '*.txt'),
                                                                         ('pliki adresowe', '*.adr'),
                                                                         (u'pliki punktów', '*.pnt'),
                                                                         (u'pliki mp', '*.mp'),
                                                                         (u'pliki diff', '*.diff')])
        if plik_do_otwarcia:
            if self.wybierz_plik_box['values']:
                if plik_do_otwarcia not in self.wybierz_plik_box['values']:
                    self.wybierz_plik_box['values'] = [plik_do_otwarcia] + list(self.wybierz_plik_box['values'])
            else:
                self.wybierz_plik_box['values'] = [plik_do_otwarcia]
            self.wybierz_plik_box.set(plik_do_otwarcia)
            self.katalog_ostatniego_pliku = os.path.dirname(plik_do_otwarcia)

    def wyszukaj_w_gore_bind(self, event):
        self.wyszukaj(forwards=False, backwards=True)

    def wyszukaj_w_gore(self):
        self.wyszukaj(forwards=False, backwards=True)

    def wyszukaj_w_dol_bind(self, event):
        self.wyszukaj(forwards=True, backwards=False)

    def wyszukaj_w_dol(self):
        self.wyszukaj(forwards=True, backwards=False)

    def wyszukaj(self, forwards=None, backwards=None):
        if self.znajdz_var.get():
            found_index = self.edytor.search(self.znajdz_var.get(), self.cursor_index,
                                                            backwards=backwards, forwards=forwards, nocase=True)
            if found_index:
                self.edytor.tag_remove('podswietl', '1.0', 'end')
                line_n, char_n = found_index.split('.', 1)
                found_end_index = line_n + '.' + str(int(char_n) + len(self.znajdz_var.get()))
                self.edytor.tag_add('podswietl', found_index, found_end_index)
                self.edytor.see(found_index)
                if forwards:
                    self.cursor_index = found_end_index
                else:
                    self.cursor_index = found_index
            else:
                if forwards:
                    self.cursor_index = '1.0'
                else:
                    self.cursor_index = 'end'

    def idz_do_linii_numer(self):
        try:
            no_linia = str(int(self.idz_do_linii_var.get()))
        except ValueError:
            return
        self.edytor.tag_remove('podswietl', '1.0', 'end')
        self.edytor.tag_add('podswietl', no_linia + '.0', str(no_linia) + '.end')
        self.edytor.see(no_linia + '.0')


class MdmText(tkinter.Text):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super().__init__(parent, *args, undo=True, autoseparators=True, wrap='none', **kwargs)
        self.tag_config('podswietl', background='yellow')
        self.bind('<Key>', self.remove_tags)
        self.menu = tkinter.Menu(self, tearoff=0)
        self.menu.add_command(label='Cofnij', command=self.edit_undo)
        self.menu.add_command(label=u'Powtórz', command=self.edit_redo)
        self.menu.add_separator()
        self.menu.add_command(label="Wytnij", command=lambda: self.event_generate("<<Cut>>"))
        self.menu.add_command(label="Kopiuj", command=lambda: self.event_generate("<<Copy>>"))
        self.menu.add_command(label="Wklej", command=lambda: self.event_generate("<<Paste>>"))
        self.menu.add_separator()
        self.menu.add_command(label="Zaznacz wszystko", command=self.event_select_all)
        self.menu.add_command(label=u"Zaznacz od tej pozycji w dół", command=self.event_select_from_here_down)
        self.menu.add_command(label=u"Zaznacz od tej pozycji do góry", command=self.event_select_from_here_up)
        self.menu.add_command(label=u'Wyczyść wszystko', command=self.event_clear_all)
        self.bind("<Button-3><ButtonRelease-3>", self.show_menu)

    def remove_tags(self, event):
        self.tag_remove('podswietl', '1.0', 'end')

    def event_select_all(self):
        self.focus_force()
        self.tag_add("sel", "1.0", "end")

    def event_clear_all(self):
        self.focus_force()
        self.delete("1.0", "end")

    def event_select_from_here_up(self):
        self.focus_force()
        self.tag_add("sel", "1.0", "current")

    def event_select_from_here_down(self):
        self.focus_force()
        self.tag_add("sel", "current", "end")

    def show_menu(self, event):
        self.tk.call("tk_popup", self.menu, event.x_root, event.y_root)
