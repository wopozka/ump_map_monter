import tkinter
import mont_demont
import os
import queue
import subprocess
import threading
import mdmMp2xml
import os.path

class ButtonZdalnieSterowany(tkinter.ttk.Button):
    def __init__(self, parent, **options):
        self.master = parent
        self.statusqueue=queue.Queue()
        tkinter.ttk.Button.__init__(self, self.master, **options)
        self.update_me()
     
    def update_me(self):
        try:
            string = self.statusqueue.get_nowait()
            if string.startswith('Koniec'):
                self.configure(state='normal')
        except queue.Empty:
            #self.previousFunkcjaPrzyciskuPracuje = self.funkcjaPrzyciskuPracuje = 0
            pass
        #self.master.update_idletasks()
        self.after(100, self.update_me)

class OSMAndKreator(tkinter.Toplevel):
    def __init__(self, parent, mdm_config, obszary, **options):
        if 0:
            tkinter.messagebox.showwarning(u'Na razie nie działa',u'Kreator dla OSMAnd na razie nie działa')
        else:
            self.args = mdm_config.zwroc_args_do_kompilacji_osmand()
            self.Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
            self.obszary = obszary
            self.logerrqueue = queue.Queue()
            tkinter.Toplevel.__init__(self, parent, **options)
            self.transient(parent)
            self.title(u'Kreator tworzenia mapy dla OSMAnda')
            self.parent = parent
            self.kolejnyetap = 'uaktualnianie'
            self.kolejka_komunikacyjna = queue.Queue()

            body = tkinter.Frame(self)
            # self.initial_focus = self
            body.pack(padx=5, pady=5, fill='both', expand=1)

            # ramka z aktualnymi czynnosciami
            # odległość pomiędzy Labelami
            sfd = 10
            # kolor nieaktywnej czynnosci
            self.nal = 'grey'
            # kolor aktywnej czynnosci
            self.al = 'blue'

            statusFrame = tkinter.Frame(body)
            statusFrame.pack()
            sfd = 10
            self.labele_stanow = {}
            self.labele_stanow['uaktualnianie'] = tkinter.Label(statusFrame, text=u'Uaktualniam źródła', bg=self.nal)
            self.labele_stanow['uaktualnianie'].pack(side='left', fill='x', expand=1)
            space1 = tkinter.Frame(statusFrame, width=sfd)
            space1.pack(side='left')
            self.labele_stanow['montowanie'] = tkinter.Label(statusFrame, text=u'Montuje mapę', bg=self.nal)
            self.labele_stanow['montowanie'].pack(side='left', fill='x', expand=1)
            space2 = tkinter.Frame(statusFrame, width=sfd)
            space2.pack(side='left')
            self.labele_stanow['mp2OSM'] = tkinter.Label(statusFrame, text=u'Konwertuję mapę do formatu OSM', bg=self.nal)
            self.labele_stanow['mp2OSM'].pack(side='left', fill='x', expand=1)
            space3 = tkinter.Frame(statusFrame, width=sfd)
            space3.pack(side='left')
            self.labele_stanow['kompilacja'] = tkinter.Label(statusFrame, text=u'Przygotowuję mapę', bg=self.nal)
            self.labele_stanow['kompilacja'].pack(side='left', fill='x', expand=1)
            space4 = tkinter.Frame(statusFrame, width=sfd)
            space4.pack(side='left')
            self.labele_stanow['gotowe'] = tkinter.Label(statusFrame, text=u'Gotowe!', bg=self.nal)
            self.labele_stanow['gotowe'].pack(side='left', fill='x', expand=1)
            space6 = tkinter.Frame(statusFrame, width=sfd)
            space6.pack(side='left')

            buttonDistanceFrame = tkinter.Frame(body, height = '10')
            buttonDistanceFrame.pack(fill = 'x', expand = 1)

            buttonFrame = tkinter.Frame(body)
            buttonFrame.pack()
            buttonZamknij = tkinter.ttk.Button(buttonFrame, text='Zamknij', command=self.destroy)
            buttonZamknij.pack(side = 'left')
            space7 = tkinter.Frame(buttonFrame, width=sfd)
            space7.pack(side = 'left')
            self.buttonNext = tkinter.ttk.Button(buttonFrame, text = u'Dalej', command = self.next)
            self.buttonNext.pack(side = 'left')
            # space8 = tkinter.Frame(buttonFrame, width=sfd)
            # space8.pack(side='left')

            textDistanceFrame = tkinter.Frame(body, height='10')
            textDistanceFrame.pack(fill='x', expand=1)
            textFrame = tkinter.ttk.LabelFrame(body, text = 'Komunikaty')
            textFrame.pack()
            self.text = LogErrText(textFrame, self.logerrqueue)
            self.text.pack(fill='both', expand=1)
            self.update_me()



            # self.buttonbox()
            # self.keyboardShortcuts()

            self.grab_set()

            # if not self.initial_focus:
            #	self.initial_focus = self

            self.protocol("WM_DELETE_WINDOW", self.destroy)
            self.bind('<Escape>', lambda event: self.destroy())
            # self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
            #							parent.winfo_rooty()+50))

            self.focus_set()
            self.wait_window(self)

    def update_me(self):
        try:
            while 1:
                _obj, _var = self.kolejka_komunikacyjna.get_nowait()
                if _obj == 'kolejnyetap':
                    self.kolejnyetap = _var
                elif _obj in ('uaktualnianie', 'montowanie', 'mp2OSM', 'kompilacja', 'gotowe'):
                    self.labele_stanow[_obj].config(bg=self.al)
                    self.buttonNext.config(state='normal')
                else:
                    break
        except queue.Empty:
            pass
        self.after(100, self.update_me)

    def next(self):
        self.buttonNext.config(state='disabled')
        if self.kolejnyetap == 'uaktualnianie':
            thread = threading.Thread(target=self.cvsup)
            thread.start()

        elif self.kolejnyetap == 'montowanie':
            thread = threading.Thread(target=self.montuj_pliki, args=(self.args,))
            thread.start()

        elif self.kolejnyetap == 'mp2osm':
            thread = threading.Thread(target=self.mp2osm)
            thread.start()

        elif self.kolejnyetap == 'kompilowanie':
            pass
        else:
            pass

    def cvsup(self):
        Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
        CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
        os.chdir(Zmienne.KatalogzUMP)
        self.logerrqueue.put(('cd ' + Zmienne.KatalogzUMP + '\n'))
        self.logerrqueue.put(('CVSROOT=' + CVSROOT + '\n'))

        for obszary in self.obszary:


            self.logerrqueue.put(('cvs up ' + obszary + '\n'))
            process = subprocess.Popen(['cvs', '-q', CVSROOT, 'up', obszary], stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT)
            processexitstatus = process.poll()

            while processexitstatus == None:
                line = process.stdout.readline()
                if line.decode(Zmienne.Kodowanie) != '':
                    self.logerrqueue.put(line.decode(Zmienne.Kodowanie))
                # time.sleep(0.1)
                processexitstatus = process.poll()

            # okazuje sie, że trzeba jeszcze sprawdzić czy całe stdout zostało odczytane.
            # Bywa że nie i trzeba doczytać tutaj.

            while line.decode(Zmienne.Kodowanie) != '':
                line = process.stdout.readline()
                self.logerrqueue.put(line.decode(Zmienne.Kodowanie))
        self.logerrqueue.put('Gotowe\n')
        self.kolejka_komunikacyjna.put(('kolejnyetap', 'montowanie'))
        self.kolejka_komunikacyjna.put(('uaktualnianie', ''))

    def latin2_to_cp1250(self):
        # Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
        self.logerrqueue.put('Ujednolicam kodowanie latin2->cp1250.\n')
        with open(os.path.join(self.Zmienne.KatalogRoboczy, self.Zmienne.InputFile), 'r',
                  encoding=self.Zmienne.Kodowanie, errors=self.Zmienne.WriteErrors) as f:
            zawartosc = f.read()
        zawartosc = zawartosc.translate(str.maketrans("±ćęłńó¶ĽżˇĆĘŁŃÓ¦¬Ż", "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"))
        with open(os.path.join(self.Zmienne.KatalogRoboczy, self.Zmienne.InputFile), 'w',
                  encoding=self.Zmienne.Kodowanie, errors=self.Zmienne.WriteErrors) as f:
            f.write(zawartosc)
        self.logerrqueue.put('Gotowe.\n')


    def montuj_pliki(self, args):
        args.obszary = []
        args.obszary = self.obszary
        args.plikmp = 'wynik.mp'
        args.adrfile = 1
        args.cityidx = 1
        args.format_indeksow = 'cityname'
        args.nocity = 0
        args.noszlaki = 1
        # self.args.nopnt=self.nopnt.get()
        args.nopnt = 1
        # self.args.hash=self.monthash.get()
        args.monthash = 1
        # self.args.extratypes=self.extratypes.get()
        args.extratypes = 0
        # self.args.graniceczesciowe=self.graniceczesciowe.get()
        args.trybosmand = 1

        args.stderrqueue = self.logerrqueue
        args.stdoutqueue = self.logerrqueue
        mont_demont.montujpliki(self.args)
        self.latin2_to_cp1250()
        self.kolejka_komunikacyjna.put(('kolejnyetap', 'mp2osm'))
        self.kolejka_komunikacyjna.put(('montowanie', ''))

    def mp2osm(self):
        self.logerrqueue.put(u'Rozpoczynam przetwarzanie mp->xml\n')
        args = self.args
        args.outputfile = os.path.join(self.Zmienne.KatalogRoboczy, 'MapaOSMAnd.osm')
        mdmMp2xml.main(args, [os.path.join(self.Zmienne.KatalogRoboczy, self.Zmienne.InputFile)])
        if os.path.exists(args.outputfile):
            self.logerrqueue.put(u'Przetwawrzanie mp->xml zakonczone sukcesem. Utworzono plik %s' % args.outputfile)
        else:
            self.logerrqueue.put(u'Przetwawrzanie mp->xml zakonczone błędem. Nie utworzono pliku %s' % args.outputfile)
        self.kolejka_komunikacyjna.put(('kolejnyetap', 'kompilowanie'))
        self.kolejka_komunikacyjna.put(('mp2OSM', ''))



class Klasy2EndLevelCreator(tkinter.Toplevel):
    def __init__(self, parent, mdm_config, obszary, **options):
        if 'UMP-radary' in obszary:
            obszary.remove('UMP-radary')
        self.args = mdm_config.zwroc_args_dla_rozdzialu_klas()
        self.Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
        self.obszary = obszary
        self.args.obszary = obszary
        if self.obszary:
            self.logerrqueue = queue.Queue()
            self.args.stdoutqueue = self.logerrqueue
            tkinter.Toplevel.__init__(self, parent, **options)
            self.transient(parent)
            self.title(u'Tworzenie mapy z wizualizacją klas')
            self.parent = parent
                
            try:
                os.remove(self.Zmienne.KatalogRoboczy + 'wynik-klasy.mp')
            except FileNotFoundError:
                pass
            
            body = tkinter.Frame(self)
            # self.initial_focus = self
            body.pack(padx=5, pady=5, fill='both', expand=1)

            #ramka z obszarami
            obszaryFrame = tkinter.ttk.LabelFrame(body, text = 'Wybrane obszary')
            obszaryFrame.pack()
            obszaryLista = tkinter.scrolledtext.ScrolledText(obszaryFrame, height=10)
            obszaryLista.pack()
            #uzupełniamy ramkę z obszarami
            for aaa in self.obszary:
                obszaryLista.insert('end', aaa)
                obszaryLista.insert('end', '\n')
            obszaryLista.see(tkinter.END)
            

            textFrame = tkinter.ttk.LabelFrame(body, text = 'Komunikaty')
            textFrame.pack()
            self.text = LogErrText(textFrame, self.logerrqueue, heigh=10)
            self.text.pack(fill='both', expand=1)
            
            
            buttonFrame = tkinter.Frame(body)
            buttonFrame.pack()
            buttonAnuluj = tkinter.ttk.Button(buttonFrame, text='Anuluj', command=self.destroy)
            buttonAnuluj.pack(side = 'left')
            self.buttonUtworz = tkinter.ttk.Button(buttonFrame, text=u'Utwórz', command=self.utworz)
            self.buttonUtworz.pack(side = 'left')
            if not self.obszary:
                self.buttonUtworz.configure(state='disabled')
            self.buttonZobacz = ButtonZdalnieSterowany(buttonFrame, text=u'Otwórz plik', command=self.zobacz)
            self.buttonZobacz.pack(side = 'left')
            self.buttonZobacz.configure(state='disabled')
            # self.buttonbox()
            # self.keyboardShortcuts()

            self.grab_set()

            # if not self.initial_focus:
            #	self.initial_focus = self

            self.protocol("WM_DELETE_WINDOW", self.destroy)
            self.bind('<Escape>', lambda event: self.destroy())
            # self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
            #							parent.winfo_rooty()+50))

            self.focus_set()
            self.wait_window(self)
        else:
            tkinter.messagebox.showwarning(u'Brak zaznaczenia',u'Musisz zaznaczyć conajmniej jeden obszar i nie mogą to być radary')
    
    def utworz(self):
        self.args.zobaczbuttonqueue = self.buttonZobacz.statusqueue
        self.buttonUtworz.configure(state='disabled')
        thread = threading.Thread(target=mont_demont.rozdziel_na_klasy, args=(self.args, ))
        thread.start()
        
    def zobacz(self):
        self.args.InputFile = 'wynik-klasy.mp'
        self.args.mapedit2 = 0
        self.args.plikmp=None
        thread = threading.Thread(target=mont_demont.edytuj, args=(self.args, ))
        thread.start()


class KreatorKompilacjiTyp(tkinter.Toplevel):
    def __init__(self, parent, mdm_config, **options):
        self.parent = parent
        self.mdm_config = mdm_config
        super().__init__(parent, **options)
        self.transient(self.parent)
        self.title(u'Tworzenie i kompilacja pliku typ')
        body = tkinter.Frame(self)
        body.pack(padx=5, pady=5, fill='both', expand=1)
        # ramka z wyborem pliku typ
        self.wybor_typ_variable = self.mdm_config.zwroc_zmienna_opcji('nazwa_typ')
        if self.wybor_typ_variable.get() == 'brak':
            self.wybor_typ_variable.set('domyslny')
        wybor_typ_frame = tkinter.ttk.LabelFrame(body, text=u'Wybór pliku typ do stworzenia')
        wybor_typ_frame.pack()
        typ_domyslny = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'domyślny', variable=self.wybor_typ_variable,
                                               value='domyslny')
        typ_domyslny.pack(side='left')
        typ_reczniak = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'reczniak', variable=self.wybor_typ_variable,
                                               value='reczniak')
        typ_reczniak.pack(side='left')
        typ_rzuq = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'rzuq', variable=self.wybor_typ_variable,
                                           value='rzuq')
        typ_rzuq.pack(side='left')
        typ_olowos = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'olowos', variable=self.wybor_typ_variable,
                                             value='olowos')
        typ_olowos.pack(side='left')

        # ramka na dodatkowe opcje tworzenia pliku typ
        self._dodaj_odstep_pionowy(body)
        dodatkowe_opcje_frame = tkinter.ttk.Frame(body)
        dodatkowe_opcje_frame.pack()
        family_id_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Family ID mapy (1-65535)')
        family_id_frame.pack(side='left')
        self.family_id_entry_var = self.mdm_config.zwroc_zmienna_opcji('family_id')
        self.family_entry = tkinter.Entry(family_id_frame, textvariable=self.family_id_entry_var)
        self.family_entry.pack()
        warstwice_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Uwzglednij warstwice')
        warstwice_frame.pack(side='left')
        self.warstwice_variable = self.mdm_config.zwroc_zmienna_opcji('uwzglednij_warstwice')
        warstwice_tak = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Tak', variable=self.warstwice_variable,
                                                value=True)
        warstwice_tak.pack(side='left')
        warstwice_nie = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Nie', variable=self.warstwice_variable,
                                                value=False)
        warstwice_nie.pack(side='left')
        kodowanie_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Kodowanie')
        kodowanie_frame.pack(side='left')
        self.kodowanie_variable = self.mdm_config.zwroc_zmienna_opcji('code_page')
        kodowanie_ascii = tkinter.ttk.Radiobutton(kodowanie_frame, text=u'Kodowanie ASCII',
                                                  variable=self.kodowanie_variable, value='ascii')
        kodowanie_ascii.pack(side='left')
        kodowanie_cp1250 = tkinter.ttk.Radiobutton(kodowanie_frame, text=u'Kodowanie cp1250',
                                                  variable=self.kodowanie_variable, value='cp1250')
        kodowanie_cp1250.pack(side='left')

        # ramka z guzikami
        self._dodaj_odstep_pionowy(body)
        buttons_frame = tkinter.Frame(body)
        buttons_frame.pack(fill='both', expand=1)
        przycisk_utworz = tkinter.ttk.Button(buttons_frame, text=u'Utworz i skompiluj plik typ',
                                             command=self.utworz_i_kompiluj_typ)
        przycisk_utworz.pack(side='left')
        przycisk_anuluj = tkinter.ttk.Button(buttons_frame, text=u'Anuluj', command=self.destroy)
        przycisk_anuluj.pack(side='right')
        # ramka z komunikatami
        self._dodaj_odstep_pionowy(body)
        self.logerrqueue = queue.Queue()
        textFrame = tkinter.ttk.LabelFrame(body, text='Komunikaty')
        textFrame.pack(fill='both', expand=1)
        self.log_err_text = LogErrText(textFrame, self.logerrqueue, heigh=10)
        self.log_err_text.pack(fill='both', expand=1)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.focus_set()
        self.wait_window(self)

    def _dodaj_odstep_pionowy(self, frame):
        space = tkinter.Frame(frame, height=10)
        space.pack()

    def utworz_i_kompiluj_typ(self):
        self.mdm_config.saveConfig()
        args = self.mdm_config.zwroc_args_do_kompiluj_typ()
        args.nazwa_typ = self.wybor_typ_variable.get()
        args.family_id = self.family_entry.get()
        if not args.family_id[0].isdigit() or 0 > int(args.family_id[0]) > 65535:
            args.family_id = '6324'
        args.uwzglednij_warstwice = True if self.warstwice_variable.get() == 'Tak' else False
        args.code_page = self.kodowanie_variable.get()
        args.stderrqueue = self.logerrqueue
        args.stdoutqueue = self.logerrqueue
        args.mkgmap_path = ''
        args.maksymalna_pamiec = '1G'
        mont_demont.stworz_plik_typ(args)


class KreatorKompilacjiMdmmap(tkinter.Toplevel):
    def __init__(self, parent, mdm_config, obszary, **options):
        self.parent = parent
        self.mdm_config = mdm_config
        self.obszary = obszary
        super().__init__(parent, **options)
        self.transient(self.parent)
        self.title(u'Tworzenie i kompilacja pliku mp do img')
        body = tkinter.Frame(self)
        body.pack(padx=5, pady=5, fill='both', expand=1)
        # ramka z wyborem pliku typ
        max_pam_max_jobs_typ_frame = tkinter.Frame(body)
        max_pam_max_jobs_typ_frame.pack()
        maksymalna_pamiec_frame = tkinter.ttk.LabelFrame(max_pam_max_jobs_typ_frame,
                                                         text=u'Maksymalna pamięć dla Javy (GB)')
        maksymalna_pamiec_frame.pack(side='left')
        self.maksymalna_pamiec_entry_var = self.mdm_config.zwroc_zmienna_opcji('maksymalna_pamiec')
        self.maksymalna_pamiec = tkinter.Entry(maksymalna_pamiec_frame, textvariable=self.maksymalna_pamiec_entry_var)
        self.maksymalna_pamiec.pack()

        maksymalna_ilosc_watkow_frame = tkinter.ttk.LabelFrame(max_pam_max_jobs_typ_frame,
                                                         text=u'Maksymalna ilosc watkow (0 to auto)')
        maksymalna_ilosc_watkow_frame.pack(side='left')
        self.maksymalna_ilosc_watkow_entry_var = self.mdm_config.zwroc_zmienna_opcji('max_jobs')
        self.maksymalna_ilosc_watkow_entry = tkinter.Entry(maksymalna_ilosc_watkow_frame,
                                                        textvariable=self.maksymalna_ilosc_watkow_entry_var)
        self.maksymalna_ilosc_watkow_entry.pack()


        self.wybor_typ_variable = self.mdm_config.zwroc_zmienna_opcji('nazwa_typ')
        wybor_typ_frame = tkinter.ttk.LabelFrame(max_pam_max_jobs_typ_frame, text=u'Wybór pliku typ do stworzenia')
        wybor_typ_frame.pack(side='left')
        typ_domyslny = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'domyślny', variable=self.wybor_typ_variable,
                                               value='domyslny')
        typ_domyslny.pack(side='left')
        typ_reczniak = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'reczniak', variable=self.wybor_typ_variable,
                                               value='reczniak')
        typ_reczniak.pack(side='left')
        typ_rzuq = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'rzuq', variable=self.wybor_typ_variable,
                                           value='rzuq')
        typ_rzuq.pack(side='left')
        typ_olowos = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'olowos', variable=self.wybor_typ_variable,
                                             value='olowos')
        typ_olowos.pack(side='left')
        typ_brak = tkinter.ttk.Radiobutton(wybor_typ_frame, text=u'Bez pliku typ', variable=self.wybor_typ_variable,
                                           value='brak')
        typ_brak.pack(side='left')

        # ramka na dodatkowe opcje tworzenia pliku typ
        self._dodaj_odstep_pionowy(body)
        dodatkowe_opcje_frame = tkinter.ttk.Frame(body)
        dodatkowe_opcje_frame.pack()
        family_id_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Family ID mapy (1-65535)')
        family_id_frame.pack(side='left')
        self.family_id_entry_var = self.mdm_config.zwroc_zmienna_opcji('family_id')
        self.family_entry = tkinter.Entry(family_id_frame, textvariable=self.family_id_entry_var)
        self.family_entry.pack()
        warstwice_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Uwzglednij warstwice')
        warstwice_frame.pack(side='left')
        self.warstwice_variable = self.mdm_config.zwroc_zmienna_opcji('uwzglednij_warstwice')
        warstwice_tak = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Tak', variable=self.warstwice_variable,
                                                value=True)
        warstwice_tak.pack(side='left')
        warstwice_nie = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Nie', variable=self.warstwice_variable,
                                                value=False)
        warstwice_nie.pack(side='left')
        kodowanie_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Kodowanie')
        kodowanie_frame.pack(side='left')
        self.kodowanie_variable = self.mdm_config.zwroc_zmienna_opcji('code_page')
        kodowanie_ascii = tkinter.ttk.Radiobutton(kodowanie_frame, text=u'Kodowanie ASCII',
                                                  variable=self.kodowanie_variable, value='ascii')
        kodowanie_ascii.pack(side='left')
        kodowanie_cp1250 = tkinter.ttk.Radiobutton(kodowanie_frame, text=u'Kodowanie cp1250',
                                                   variable=self.kodowanie_variable, value='cp1250')
        kodowanie_cp1250.pack(side='left')

        # wybor formatu mapy: gmapsupp albo gmapii
        self._dodaj_odstep_pionowy(body)
        index_routing_format_frame = tkinter.Frame(body)
        index_routing_format_frame.pack()
        format_mapy_frame = tkinter.LabelFrame(index_routing_format_frame, text=u'Format pliku wyjściowego')
        format_mapy_frame.pack(side='left')
        self.format_skompilowanej_mapy = self.mdm_config.zwroc_zmienna_opcji('format_mapy')
        format_gmapsupp = tkinter.ttk.Radiobutton(format_mapy_frame, text=u'gmapsupp',
                                                  variable=self.format_skompilowanej_mapy, value='gmapsupp')
        format_gmapsupp.pack(side='left')
        format_gmapi = tkinter.ttk.Radiobutton(format_mapy_frame, text=u'gmapi',
                                                  variable=self.format_skompilowanej_mapy, value='gmapi')
        format_gmapi.pack(side='left')
        index_frame = tkinter.ttk.LabelFrame(index_routing_format_frame, text=u'Indeks adresów')
        index_frame.pack(side='left')
        self.indeksy_adresow = self.mdm_config.zwroc_zmienna_opcji('index')
        index_checkbutton = tkinter.ttk.Checkbutton(index_frame, text=u'Generuj indeks adresów',
                                                    variable=self.indeksy_adresow, onvalue=True, offvalue=False)
        index_checkbutton.pack(side='left')

        opcje_montowania_frame = tkinter.ttk.LabelFrame(body, text=u'Opcje montowania')
        opcje_montowania_frame.pack()
        self.routing = self.mdm_config.zwroc_zmienna_opcji('dodaj_routing')
        routing_checkbutton = tkinter.ttk.Checkbutton(opcje_montowania_frame, text=u'Generuj mapę z routingiem',
                                                    variable=self.routing, onvalue=True, offvalue=False)
        routing_checkbutton.pack(side='left')
        self.dodaj_adresy = self.mdm_config.zwroc_zmienna_opcji('dodaj_adresy')
        adresy_checkbutton = tkinter.ttk.Checkbutton(opcje_montowania_frame, text=u'Dodaj adresy z plików adr',
                                                     variable=self.dodaj_adresy, onvalue=True, offvalue=False)
        adresy_checkbutton.pack(side='left')
        self.uruchom_wojka = self.mdm_config.zwroc_zmienna_opcji('uruchom_wojka')
        wojek_checkbutton = tkinter.ttk.Checkbutton(opcje_montowania_frame, text=u'Uruchom wojka (zalecane)',
                                                     variable=self.uruchom_wojka, onvalue=True, offvalue=False)
        wojek_checkbutton.pack(side='left')
        self.podnies_poziom = self.mdm_config.zwroc_zmienna_opcji('podnies_poziom')
        poziom_checkbutton = tkinter.ttk.Checkbutton(opcje_montowania_frame,
                                                     text=u'Uruchom skrypt podnieś poziom (zalecane)',
                                                     variable=self.podnies_poziom, onvalue=True, offvalue=False)
        poziom_checkbutton.pack(side='left')

        # plik do wlasnych typow
        self._dodaj_odstep_pionowy(body)
        self.wlasne_typy_var = self.mdm_config.zwroc_zmienna_opcji('wlasne_typy')
        wlasne_typy_frame = tkinter.ttk.LabelFrame(body, text=u'Obsługa własnych definicji aliasow do typów.')
        wlasne_typy_frame.pack(fill='x')
        wlasne_typy_label = tkinter.ttk.Label(wlasne_typy_frame, textvariable=self.wlasne_typy_var, anchor='w',
                                              background='green2', width=-120)
        wlasne_typy_label.pack(side='left', fill='x')
        wlasne_typy_button_wybierz = tkinter.ttk.Button(wlasne_typy_frame, text='Wybierz',
                                                        command=self.wlasne_typy_wybierz_plik)
        wlasne_typy_button_wybierz.pack(side='right')
        wlasne_typy_button_czysc = tkinter.ttk.Button(wlasne_typy_frame, text='Czysc',
                                                        command=self.wlasne_typy_czysc_plik)
        wlasne_typy_button_czysc.pack(side='right')

        # guziki kompiluj mape oraz cancel
        self._dodaj_odstep_pionowy(body)
        kompiluj_cancel_frame = tkinter.Frame(body)
        kompiluj_cancel_frame.pack()
        kompiluj_button = tkinter.ttk.Button(kompiluj_cancel_frame, text=u'Kompiluj mapę', command=self.kompiluj_mape)
        kompiluj_button.pack(side='left')
        cancel_button = tkinter.ttk.Button(kompiluj_cancel_frame, text=u'Anuluj', command=self.destroy)
        cancel_button.pack(side='left')

        # okienko z logami
        self._dodaj_odstep_pionowy(body)
        self.logerrqueue = queue.Queue()
        textFrame = tkinter.ttk.LabelFrame(body, text='Komunikaty')
        textFrame.pack(fill='both', expand=1)
        self.log_err_text = LogErrText(textFrame, self.logerrqueue, heigh=10)
        self.log_err_text.pack(fill='both', expand=1)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.focus_set()
        self.wait_window(self)

    def _dodaj_odstep_pionowy(self, frame):
        space = tkinter.Frame(frame, height=10)
        space.pack()

    def wlasne_typy_wybierz_plik(self):
        aaa = os.path.normcase(tkinter.filedialog.askopenfilename(title=u'Ścieżka definicji wlasnych aliasow'))
        if len(aaa) > 0:
            self.wlasne_typy_var.set(aaa)

    def wlasne_typy_czysc_plik(self):
        self.wlasne_typy_var.set('')

    def kompiluj_mape(self):
        thread = threading.Thread(target=self._kompiluj_mape)
        thread.start()

    def _kompiluj_mape(self):
        # najpierw trzeba zmontować mapę dla mkgmap
        args = self.mdm_config.zwroc_args_do_montuj_mkgmap()
        args.stderrqueue = self.logerrqueue
        args.stdoutqueue = self.logerrqueue
        args.obszary = self.obszary
        mont_demont.montuj_mkgmap(args)
        mont_demont.kompiluj_mape(args)




class LogErrText(tkinter.scrolledtext.ScrolledText):
    def __init__(self, master, logqueue, **options):
        tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
        self.logqueue = logqueue
        self.update_me()

    def update_me(self):
        try:
            while 1:
                msg = self.logqueue.get_nowait()
                self.insert('end', msg.lstrip())
                self.see(tkinter.END)

        except queue.Empty:
            pass

        self.after(100, self.update_me)
