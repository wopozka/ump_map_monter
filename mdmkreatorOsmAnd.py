import tkinter
import mont_demont
import os
import queue
import subprocess
import threading
import mdmMp2xml

class txt2osmArgumenty(object):
    def __init__(self, katalogroboczy):
        self.borders_file = None
        self.threadnum = 1
        self.index_file = None
        self.nominatim_file = None
        self.navit_file = None
        self.nonumber_file = None
        self.verbose = False
        self.skip_housenumbers = False
        self.positive_ids = False
        self.normalize_ids = False
        self.ignore_errors = False
        self.regions = False
        self.outputfile = katalogroboczy + 'MapaOSMAnd.osm'

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
                self.configure(state='Normal')
        except queue.Empty:
            #self.previousFunkcjaPrzyciskuPracuje = self.funkcjaPrzyciskuPracuje = 0
            pass
        #self.master.update_idletasks()
        self.after(100, self.update_me)

class OSMAndKreator(tkinter.Toplevel):
    def __init__(self, parent, obszary, **options):
        if 1:
            tkinter.messagebox.showwarning(u'Na razie nie działa',u'Kreator dla OSMAnd na razie nie działa')
        else:
            self.args = Argumenty()
            self.Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
            self.obszary = obszary
            self.logerrqueue = queue.Queue()
            tkinter.Toplevel.__init__(self, parent, **options)
            self.transient(parent)
            self.title(u'Kreator tworzenia mapy dla OSMAnda')
            self.parent = parent
            self.kolejnyetap = 'uaktualnianie'

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
            self.uaktualnianie = tkinter.Label(statusFrame, text = u'Uaktualniam źródła', bg = self.nal)
            self.uaktualnianie.pack(side = 'left', fill = 'x', expand=1)
            space1 = tkinter.Frame(statusFrame, width = sfd)
            space1.pack(side = 'left')
            self.montowanie = tkinter.Label(statusFrame, text = u'Montuje mapę', bg = self.nal)
            self.montowanie.pack(side = 'left', fill = 'x', expand=1)
            space2 = tkinter.Frame(statusFrame, width=sfd)
            space2.pack(side='left')
            self.mp2OSM = tkinter.Label(statusFrame, text = u'Konwertuję mapę do formatu OSM', bg = self.nal)
            self.mp2OSM.pack(side = 'left', fill = 'x', expand=1)
            space3 = tkinter.Frame(statusFrame, width=sfd)
            space3.pack(side='left')
            self.kompilacja = tkinter.Label(statusFrame, text = u'Przygotowuję mapę', bg = self.nal)
            self.kompilacja.pack(side = 'left', fill = 'x', expand=1)
            space4 = tkinter.Frame(statusFrame, width=sfd)
            space4.pack(side='left')
            self.gotowe = tkinter.Label(statusFrame, text = 'Gotowe!', bg = self.nal)
            self.gotowe.pack(side = 'left', fill = 'x', expand=1)
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
            buttonNext = tkinter.ttk.Button(buttonFrame, text = u'Dalej', command = self.next)
            buttonNext.pack(side = 'left')
            # space8 = tkinter.Frame(buttonFrame, width=sfd)
            # space8.pack(side='left')

            textDistanceFrame = tkinter.Frame(body, height='10')
            textDistanceFrame.pack(fill='x', expand=1)
            textFrame = tkinter.ttk.LabelFrame(body, text = 'Komunikaty')
            textFrame.pack()
            self.text = LogErrText(textFrame, self.logerrqueue)
            self.text.pack(fill='both', expand=1)



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

    def next(self):
        if self.kolejnyetap == 'uaktualnianie':
            thread = threading.Thread(target=self.cvsup)
            thread.start()

        elif self.kolejnyetap == 'montowanie':
            self.args.obszary = []
            self.args.obszary = self.obszary
            self.args.plikmp = 'wynik.mp'
            self.args.adrfile = 1
            self.args.cityidx = 0
            self.args.nocity = 0
            self.args.noszlaki = 1
            # self.args.nopnt=self.nopnt.get()
            self.args.nopnt = 1
            # self.args.hash=self.monthash.get()
            self.args.hash = 1
            # self.args.extratypes=self.extratypes.get()
            self.args.extratypes = 0
            # self.args.graniceczesciowe=self.graniceczesciowe.get()
            self.args.trybosmand = 1

            self.args.stderrqueue = self.logerrqueue
            self.args.stdoutqueue = self.logerrqueue
            thread = threading.Thread(target=mont_demont.montujpliki, args=(self.args,))
            thread.start()
            self.kolejnyetap = 'konwertowanie'


        elif self.kolejnyetap == 'konwertowanie':
            # Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
            self.logerrqueue.put('Ujednolicam kodowanie latin2->cp1250.\n')
            with open(self.Zmienne.KatalogRoboczy + self.Zmienne.InputFile, encoding=self.Zmienne.Kodowanie,
                      errors=self.Zmienne.WriteErrors) as f:
                zawartosc = f.read()
            zawartosc = zawartosc.translate(str.maketrans("±ćęłńó¶ĽżˇĆĘŁŃÓ¦¬Ż", "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"))
            with open(self.Zmienne.KatalogRoboczy + self.Zmienne.InputFile, 'w', encoding=self.Zmienne.Kodowanie,
                      errors=self.Zmienne.WriteErrors) as f:
                f.write(zawartosc)
            self.logerrqueue.put('Gotowe.\n')
            self.kolejnyetap = 'mp2osm'

        elif self.kolejnyetap == 'mp2osm':
            
            args = txt2osmArgumenty(self.Zmienne.KatalogRoboczy)
            mdmMp2xml.main(args, [self.Zmienne.KatalogRoboczy + self.Zmienne.InputFile])

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
        self.kolejnyetap = 'montowanie'
        self.uaktualnianie.config(bg = self.al)

class Klasy2EndLevelCreator(tkinter.Toplevel):
    def __init__(self, parent, obszary, **options):
        if 'UMP-radary' in obszary:
            obszary.remove('UMP-radary')
        self.args = Argumenty()
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
        self.args.zobaczbuttonqueue=self.buttonZobacz.statusqueue
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
    def __init__(self, parent, **options):
        self.parent = parent
        super().__init__(parent, **options)
        self.transient(self.parent)
        self.title(u'Tworzenie i kompilacja pliku typ')
        body = tkinter.Frame(self)
        body.pack(padx=5, pady=5, fill='both', expand=1)
        # ramka z wyborem pliku typ
        self.wybor_typ_variable = tkinter.StringVar()
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
        family_id_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Family ID mapy (1-65535')
        family_id_frame.pack(side='left')
        family_entry = tkinter.Entry(family_id_frame)
        family_entry.pack()
        warstwice_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Uwzglednij warstwice')
        warstwice_frame.pack(side='left')
        self.warstwice_variable = tkinter.BooleanVar()
        self.warstwice_variable.set(False)
        warstwice_tak = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Tak', variable=self.warstwice_variable,
                                                value=True)
        warstwice_tak.pack(side='left')
        warstwice_nie = tkinter.ttk.Radiobutton(warstwice_frame, text=u'Nie', variable=self.warstwice_variable,
                                                value=False)
        warstwice_nie.pack(side='left')
        kodowanie_frame = tkinter.ttk.LabelFrame(dodatkowe_opcje_frame, text=u'Kodowanie')
        kodowanie_frame.pack(side='left')
        self.kodowanie_variable = tkinter.StringVar()
        self.kodowanie_variable.set('cp1250')
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
        przycisk_utworz = tkinter.ttk.Button(buttons_frame, text=u'Utworz i skompiluj plik typ')
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

class LogErrText(tkinter.scrolledtext.ScrolledText):
    def __init__(self, master, logqueue, **options):
        tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
        self.logqueue = logqueue
        self.update_me()

    def update_me(self):
        try:
            while 1:
                string = self.logqueue.get_nowait()
                self.insert('end', string.lstrip())
                self.see(tkinter.END)

        except queue.Empty:
            pass

        self.after(100, self.update_me)

class Argumenty(object):
    def __init__(self):
        self.umphome = None
        self.plikmp = None
        self.katrob = None
        self.obszary = []
        self.notopo = 0