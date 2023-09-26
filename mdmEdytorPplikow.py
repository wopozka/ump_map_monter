import tkinter
class MdmEdytorPlikow(tkinter.Toplevel):
    def __init__(self, parent, *args, *kwargs):
        self.pliki_do_commit = pliki_do_commit
        super().__init__(parent, *args, **kwargs)
        ramka_glowna = tkinter.Frame(self)
        ramka_glowna.pack()
        ramka_znajdz = tkinter.ttk.LabelFrame(ramka_glowna, text=u'Znajdz')
        ramka_znajdz.pack(side='left')
        self.znajdz_var = tkinter.StringVar()
        znajdz_entry = tkinter.Entry(ramka_znajdz, textvariable=self.znajdz_var)
        znajdz_entry.pack(side='left')
        znajdz_button = tkinter.ttk.Button(ramka_znajdz, text=u'Wyszukaj')
        znajdz_button.pack(side='left')
        idz_do_lini_frame = tkinter.ttk.LabelFrame(ramka_glowna, text=u'Idz do linii')
        idz_do_lini_frame.pack(side='left')
        self.idz_do_lini_frame_var = tkinter.StringVar()
        idz_do_lini_entry=tkinter.Entry(idz_do_lini_frame, textvariable=self.idz_do_lini_frame_var)
        idz_do_lini_entry.pack(side='left')
        idz_do_lini_button = tkinter.ttk.Button(idz_do_lini_frame, text=u'Idz do linii')
        idz_do_lini_button.pack(side='left')




