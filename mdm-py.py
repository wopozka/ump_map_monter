﻿#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import *
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.scrolledtext
import tkinter.messagebox

DownloadEverything = 0
try:
	import mont_demont as mont_demont_py
	import znajdz_wystajace
	import mdmkreatorOsmAnd
except ImportError:
	DownloadEverything=1
	
import string
import sys

if sys.version_info[0] < 3:
	sys.stderr.write(
		'u\nUżywasz	pythona w wersji %s.%s.%s\n'%(sys.version_info[0],sys.version_info[1],sys.version_info[2]))
	sys.stderr.write("Wymagany jest python w wersji conajmniej 3.\n")
	sys.exit(1)
#	import	codecs
#import	locale
import os
import argparse
import glob
import hashlib
#import timeit
import difflib
#import _thread
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
import collections

class ToolTip(object):

	def __init__(self, widget):
		self.widget = widget
		self.tipwindow = None
		self.id = None
		self.x = self.y = 0
		self.waittime = 500     #miliseconds

	def showtip(self, text):
		"Display text in tooltip window"
		self.text = text
		if self.tipwindow or not self.text:
			return
		x, y, cx, cy = self.widget.bbox("insert")
		x = x + self.widget.winfo_rootx() + 27
		y = y + cy + self.widget.winfo_rooty() +27
		self.tipwindow = tw = Toplevel(self.widget)
		tw.wm_overrideredirect(1)
		tw.wm_geometry("+%d+%d" % (x, y))
		try:
			# For Mac OS
			tw.tk.call("::tk::unsupported::MacWindowStyle",
					"style", tw._w,
					"help", "noActivates")
		except TclError:
			pass
		label = Label(tw, text=self.text, justify=LEFT,
					background="#ffffe0", relief=SOLID, borderwidth=1,
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
		id = self.id
		self.id = None
		if id:
			self.widget.after_cancel(id)

def createToolTip(widget, text):
	toolTip = ToolTip(widget)
	def enter(event):
		toolTip.schedule(text)
	def leave(event):
		toolTip.unschedule()
		toolTip.hidetip()

	widget.bind('<Enter>', enter)
	widget.bind('<Leave>', leave)


class AutoScrollbar(tkinter.ttk.Scrollbar):
	# a scrollbar that hides itself if it's not needed.  only
	# works if you use the grid geometry manager.
	def set(self, lo, hi):
		if float(lo) <= 0.0 and float(hi) >= 1.0:
			# grid_remove is currently missing from Tkinter!
			self.tk.call("grid", "remove", self)
			#self.grid()
		else:
			self.grid()
		tkinter.Scrollbar.set(self, lo, hi)
	def pack(self, **kw):
		raise TclError 
	def place(self, **kw):
		raise TclError 

class ListaPlikowFrame(tkinter.Frame):
	def __init__(self, master, Zmienne,**options):
		tkinter.Frame.__init__(self, master, **options)
		self.queueListaPlikowFrame=queue.Queue()
		#self.zmienionepliki=[]
		self.mdm_mode=Zmienne.mdm_mode
		self.Zmienne=Zmienne
		self.listaNazwPlikowDoObejrzenia=[]
		self.listaPlikowOknoZmienionePliki=[]
		self.listaDodanoOknoZmienionePliki=[]
		self.skasowanoPlikowOknoZmienionePliki=[]
		self.zobaczButtonPlikowOknoZmienionePliki=[]
		self.skopiujCheckButtonPlikowOknoZmienionePliki=[]
		self.listaPlikowDiffDoSkopiowania={}
		self.update_me()
		self.master=master
	
#	def write(self,line):
#		self.queueListaPlikowFrame.put(line)
	
	def update_me(self):
		try:
			while 1:
				zmienioneplikihash=self.queueListaPlikowFrame.get_nowait()
				abc=0
				style=tkinter.ttk.Style()
				style.configure('Helvetica.TLabel',font=('Helvetica',9))
				for a in zmienioneplikihash[0][:]:
					iloscdodanych='-1'
					iloscusunietych='-1'
					try:
						with open(self.Zmienne.KatalogRoboczy+a.replace('/','-')+'.diff',encoding=self.Zmienne.Kodowanie,errors=self.Zmienne.ReadErrors) as file:
							for bbb in file.readlines():
								if bbb.startswith('+'):
									iloscdodanych=str(int(iloscdodanych)+1)
								elif bbb.startswith('-'):
									iloscusunietych=str(int(iloscusunietych)+1)
					except FileNotFoundError:
						iloscdodanych='n/a'
						iloscusunietych='n/a'
					self.listaNazwPlikowDoObejrzenia.append(a)
					self.listaPlikowOknoZmienionePliki.append(tkinter.ttk.Label(self,text=a,width=60,anchor='w',style='Helvetica.TLabel'))
					self.listaPlikowOknoZmienionePliki[abc].grid(row=abc+1,column=0)
					newtags=self.listaPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
					self.listaPlikowOknoZmienionePliki[abc].bindtags(newtags)
										
					self.listaDodanoOknoZmienionePliki.append(tkinter.ttk.Label(self,text=iloscdodanych,width=5,anchor='w',style='Helvetica.TLabel'))
					self.listaDodanoOknoZmienionePliki[abc].grid(row=abc+1,column=1)
					newtags=self.listaDodanoOknoZmienionePliki[abc].bindtags()+('movewheel',)
					self.listaDodanoOknoZmienionePliki[abc].bindtags(newtags)
					
					self.skasowanoPlikowOknoZmienionePliki.append(tkinter.ttk.Label(self,text=iloscusunietych,width=5,anchor='w',style='Helvetica.TLabel'))
					self.skasowanoPlikowOknoZmienionePliki[abc].grid(row=abc+1,column=2)
					newtags=self.skasowanoPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
					self.skasowanoPlikowOknoZmienionePliki[abc].bindtags(newtags)
					
					self.zobaczButtonPlikowOknoZmienionePliki.append(tkinter.ttk.Button(self,text='Zobacz',
																	command= lambda tmp=a: self.OnButtonClickZobacz(tmp)))
					self.zobaczButtonPlikowOknoZmienionePliki[abc].grid(row=abc+1,column=3)
					newtags=self.zobaczButtonPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
					self.zobaczButtonPlikowOknoZmienionePliki[abc].bindtags(newtags)
					
					self.listaPlikowDiffDoSkopiowania[a]=tkinter.IntVar()
					self.listaPlikowDiffDoSkopiowania[a].set(0)
					self.skopiujCheckButtonPlikowOknoZmienionePliki.append(tkinter.ttk.Checkbutton(self,text='Skopiuj',onvalue=1, offvalue=0,variable=self.listaPlikowDiffDoSkopiowania[a]))
					self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].grid(row=abc+1,column=4)
					newtags=self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].bindtags()+('movewheel',)
					self.skopiujCheckButtonPlikowOknoZmienionePliki[abc].bindtags(newtags)
					
					abc+=1
					if a.startswith('_nowosci.') and self.mdm_mode=='edytor':
						self.skopiujCheckButtonPlikowOknoZmienionePliki[abc-1].configure(state='disabled')
					if a.find('granice-czesciowe.txt')>=0 and self.mdm_mode=='edytor':
						self.skopiujCheckButtonPlikowOknoZmienionePliki[abc-1].configure(state='disabled')
					self.nazwapliku_Hash=zmienioneplikihash[1]
					self.update_idletasks()
					self.master.config(scrollregion=self.master.bbox("all"))
					self.master.update_idletasks()
					
		except queue.Empty:
			pass
		self.after(500,self.update_me)
	
	def WyczyscPanelzListaPlikow(self):
		for aaa in self.listaPlikowOknoZmienionePliki + self.listaDodanoOknoZmienionePliki + self.skasowanoPlikowOknoZmienionePliki + self.zobaczButtonPlikowOknoZmienionePliki + self.skopiujCheckButtonPlikowOknoZmienionePliki:
			aaa.destroy()
		
		self.listaPlikowOknoZmienionePliki=[]
		self.listaDodanoOknoZmienionePliki=[]
		self.skasowanoPlikowOknoZmienionePliki=[]
		self.zobaczButtonPlikowOknoZmienionePliki=[]
		self.skopiujCheckButtonPlikowOknoZmienionePliki=[]
		self.listaNazwPlikowDoObejrzenia=[]
		self.listaPlikowDiffDoSkopiowania={}
		self.update_idletasks()
		self.master.config(scrollregion=self.master.bbox("all"))
		self.master.update_idletasks()
		
	def OnButtonClickZobacz(self,plik):
		plikdootw=plik.replace('/','-')
		if not plikdootw.startswith('_nowosci.') and self.nazwapliku_Hash[plik]!='MD5HASH=NOWY_PLIK':
			plikdootw += '.diff'
		with open(self.Zmienne.KatalogRoboczy+plikdootw,encoding=self.Zmienne.Kodowanie,errors=self.Zmienne.ReadErrors) as f:
			aaa=f.readlines()
		oknopodgladu=tkinter.Toplevel(self)
		oknopodgladu.title(plik)
		frameInOknoPodgladu=tkinter.Frame(oknopodgladu)
		frameInOknoPodgladu.pack(fill='both',expand=1)
		
		Scroll=tkinter.Scrollbar(frameInOknoPodgladu)
		Scroll.pack(side='right',fill='y',expand=0)
		zawartoscokna=zobaczDiffText(frameInOknoPodgladu, plik, width=100,yscrollcommand=Scroll.set,wrap='none')
		#zawartoscokna.tag_config('sel',background='yellow')
		zawartoscokna.tag_config('removed',foreground='red',background='snow3')
		zawartoscokna.tag_config('added',foreground='blue',background='snow3')
		zawartoscokna.tag_config('normal',foreground='black')
		zawartoscokna.tag_raise('sel')
		#jak zmusic by zaznaczanie działało
		#http://stackoverflow.com/questions/23289214/tkinter-text-tags-select-user-highlight-colour
		
		#przenosimy focus na okno podgladu, aby alt+f4 na nim działało a nie na głównym oknie aplikacji
		oknopodgladu.focus_set()
		
		#bindujemy klawisz escape to zamykania okna
		oknopodgladu.bind('<Escape>', lambda event: oknopodgladu.destroy())
		
		wiersz=0
		for tmpa in aaa:
			if tmpa.startswith('+'):
				zawartoscokna.insert('end',tmpa.rstrip('\n'),('added'))
				zawartoscokna.insert('end','\n','normal')
			elif tmpa.startswith('-'):
				zawartoscokna.insert('end',tmpa.rstrip('\n'),'removed')
				zawartoscokna.insert('end','\n','normal')
			else:
				zawartoscokna.insert('end',tmpa,'normal')
				
		#zawartoscokna.insert(1.0,aaa,'removed')
		zawartoscokna.config(state='disabled')
		zawartoscokna.pack(fill='both',expand=1,side='right')
		Scroll.config(command=zawartoscokna.yview)
		
		ScrollX=tkinter.Scrollbar(oknopodgladu,orient='horizontal',command=zawartoscokna.xview)
		ScrollX.pack(fill='x',expand=0)
		zawartoscokna.config(xscrollcommand=ScrollX.set)
		#zawartoscokna.grid(row=0,column=0)
		#zawartoscokna.grid_columnconfigure(0,weight=1)
		#zawartoscokna.grid_rowconfigure(0,weight=1)

class HelpWindow(tkinter.Toplevel):
	def __init__(self, parent, **options):
		tkinter.Toplevel.__init__(self, parent, **options)
		self.transient(parent)
		self.title(u'Skróty klawiaturowe')
		self.parent = parent
		
		body = tkinter.Frame(self)
		# self.initial_focus = self
		body.pack(padx=5, pady=5, fill='both', expand=1)
		
		self.text=tkinter.scrolledtext.ScrolledText(body)
		self.text.pack(fill='both', expand = 1)
		self.wypiszListeSkrotow(self.text)
		
		buttonZamknij = tkinter.ttk.Button(body, text='Zamknij', command=self.destroy)
		buttonZamknij.pack()

		# self.buttonbox()
		# self.keyboardShortcuts()

		self.grab_set()

		#if not self.initial_focus:
		#	self.initial_focus = self

		self.protocol("WM_DELETE_WINDOW", self.destroy)
		self.bind('<Escape>', lambda event: self.destroy())
		#self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
		#							parent.winfo_rooty()+50))

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
					'ctrl + C', '                   -> ', u'wyczyść katalog roboczy z plików źródłowych, diff i wynik.mp\n',
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
			okienko.insert('end',a)
		
		okienko.config(state='disabled')
					

		
class ConfigWindow(tkinter.Toplevel):
	def __init__(self,parent,**options):
		tkinter.Toplevel.__init__(self,parent,**options)
		self.transient(parent)
		self.title('Konfiguracja')
		self.parent=parent
		
		#self.parent.title='Konfiguracja'
		self.Konfiguracja = mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		self.Konfiguracja.wczytajKonfiguracje()
		#print(self.Konfiguracja.KatalogzUMP)
		#print(self.Konfiguracja.MapEditExe)
		#print(self.Konfiguracja.NetGen)
						
		self.umpSourceValue = tkinter.StringVar()
		self.umpRoboczyValue = tkinter.StringVar()
		self.umpMapeditPath = tkinter.StringVar()
		self.umpMapedit2Path = tkinter.StringVar()
		self.umpNetGenPath = tkinter.StringVar()
		self.ump_mdm_mode = tkinter.IntVar()
		self.umpcvsusername = tkinter.StringVar()
		self.umpPatchProgramPath = tkinter.StringVar()
		
		
		self.umpSourceValue.set(self.Konfiguracja.KatalogzUMP)
		self.umpRoboczyValue.set(self.Konfiguracja.KatalogRoboczy)
		self.umpMapeditPath.set(self.Konfiguracja.MapEditExe)
		self.umpMapedit2Path.set(self.Konfiguracja.MapEdit2Exe)
		self.umpNetGenPath.set(self.Konfiguracja.NetGen)
		self.umpcvsusername.set(self.Konfiguracja.CvsUserName)
		if self.Konfiguracja.mdm_mode=='edytor':
			self.ump_mdm_mode.set(1)
		else:
			self.ump_mdm_mode.set(0)
		
		umpConfigFrame=tkinter.Frame(self,borderwidth=2,pady=10,padx=10)
		umpConfigFrame.grid(column=0,row=0)
		
		umpsourceLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Katalog ze źródłami UMP')
		umpsourceLabelFrame.grid(row=0,column=0,sticky='we',columnspan=2)
		umpsource=tkinter.Label(umpsourceLabelFrame,textvariable=self.umpSourceValue)
		umpsource.grid(row=0,column=0,sticky='w')
		umpsourceLabelFrame.grid_columnconfigure(0,weight=1)
		umpsourceWybierzButton=tkinter.ttk.Button(umpsourceLabelFrame,text='Wybierz',command=self.OnButtonClickUMPSource)
		umpsourceWybierzButton.grid(row=0,column=1,sticky='e')
		
		umproboczyLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Katalog roboczy')
		umproboczyLabelFrame.grid(row=1,column=0,sticky='we',columnspan=2)
		umproboczy=tkinter.Label(umproboczyLabelFrame,textvariable=self.umpRoboczyValue)
		umproboczy.grid(row=0,column=0,sticky='w')
		umproboczyLabelFrame.grid_columnconfigure(0,weight=1)
		umproboczyWybierzButton=tkinter.ttk.Button(umproboczyLabelFrame,text='Wybierz',command=self.OnButtonClickUMPRoboczy)
		umproboczyWybierzButton.grid(row=0,column=1,sticky='e')
		
		umpmapeditLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Ścieżka do programu mapedit')
		umpmapeditLabelFrame.grid(row=2,column=0,sticky='we',columnspan=2)
		umpmapedit=tkinter.Label(umpmapeditLabelFrame,textvariable=self.umpMapeditPath)
		umpmapedit.grid(row=0,column=0,sticky='w')
		umpmapeditLabelFrame.grid_columnconfigure(0,weight=1)
		umpmapeditWybierzButton=tkinter.ttk.Button(umpmapeditLabelFrame,text='Wybierz',command=self.OnButtonClickMapedit)
		umpmapeditWybierzButton.grid(row=0,column=1,sticky='e')
		
		umpmapedit2LabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Ścieżka do programu mapedit (druga wersja)')
		umpmapedit2LabelFrame.grid(row=3,column=0,sticky='we',columnspan=2)
		umpmapedit2=tkinter.Label(umpmapedit2LabelFrame,textvariable=self.umpMapedit2Path)
		umpmapedit2.grid(row=0,column=0,sticky='w')
		umpmapedit2LabelFrame.grid_columnconfigure(0,weight=1)
		umpmapedit2WybierzButton=tkinter.ttk.Button(umpmapedit2LabelFrame,text='Wybierz',command=self.OnButtonClickMapedit2)
		umpmapedit2WybierzButton.grid(row=0,column=1,sticky='e')
		
		umpnetgenLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Ścieżka do programu netgen.exe')
		umpnetgenLabelFrame.grid(row=4,column=0,sticky='we',columnspan=2)
		umpnetgen=tkinter.Label(umpnetgenLabelFrame,textvariable=self.umpNetGenPath)
		umpnetgen.grid(row=0,column=0,sticky='w')
		umpnetgenLabelFrame.grid_columnconfigure(0,weight=1)
		umpnetgenWybierzButton=tkinter.ttk.Button(umpnetgenLabelFrame,text='Wybierz',command=self.OnButtonClickNetgen)
		umpnetgenWybierzButton.grid(row=0,column=1,sticky='e')
		
		#login dla cvs
		umpcvsloginLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Login do CVS, jeśli nie masz pozostaw guest')
		umpcvsloginLabelFrame.grid(row=5,column=0,sticky='we',columnspan=2)
		umpcvsloginLabelFrame.grid_columnconfigure(0,weight=1)
		umpcvsEntry=tkinter.Entry(umpcvsloginLabelFrame,textvariable=self.umpcvsusername)
		umpcvsEntry.grid(row=0,column=0,sticky='ew')
		
		#tryb pracy gui
		umpmdmmodeLabelFrame=tkinter.ttk.LabelFrame(umpConfigFrame,text=u'Tryb pracy mdm')
		umpmdmmodeLabelFrame.grid(row=6,column=0,columnspan=2, sticky='we')
		umpmdmmodeRadio1=tkinter.ttk.Radiobutton(umpmdmmodeLabelFrame,text='Edytor',value=1,variable=self.ump_mdm_mode)
		umpmdmmodeRadio1.grid(row=0,column=0)
		umpmdmmodeRadio2=tkinter.ttk.Radiobutton(umpmdmmodeLabelFrame,text='Wrzucacz',value=0,variable=self.ump_mdm_mode)
		umpmdmmodeRadio2.grid(column=1,row=0)
		

		self.buttonbox()
		self.grab_set()
		#if not self.initial_focus:
		#	self.initial_focus = self
		#self.initial_focus.focus_set()
		self.focus_set()
		self.wait_window(self)
		
	def buttonbox(self):
		box=tkinter.Frame(self,padx=10,pady=10)
		box.grid(row=4,column=0,columnspan=2,sticky='ew')
		box.grid_columnconfigure(0,weight=1)
		
		saveButton=tkinter.ttk.Button(box,text=u'Zapisz konfigurację',command=self.OnButtonClickZapisz)
		saveButton.grid(column=0,row=0,sticky='w')
		
		cancelButton=tkinter.ttk.Button(box,text=u'Anuluj',command=self.destroy)
		cancelButton.grid(column=1,row=0,sticky='e')
		
		self.bind("<Return>",self.ok)
		self.bind("<Escape>",self.anuluj)
	
	def ok(self,event=None):
		self.withdraw()
		self.update_idletasks()
		self.OnButtonClickZapisz()
		
	def anuluj(self,event=None):
		self.parent.focus_set()
		self.destroy()
	
	def OnButtonClickZapisz(self):
		with open(os.path.expanduser('~')+'/.mont-demont-py.config','w') as configfile:
			configfile.write('UMPHOME='+self.Konfiguracja.KatalogzUMP)
			configfile.write('\n')
			configfile.write('KATALOGROBOCZY='+self.Konfiguracja.KatalogRoboczy)
			configfile.write('\n')
			configfile.write('MAPEDITEXE='+self.Konfiguracja.MapEditExe)
			configfile.write('\n')
			configfile.write('MAPEDIT2EXE='+self.Konfiguracja.MapEdit2Exe)
			configfile.write('\n')
			configfile.write('NETGEN='+self.Konfiguracja.NetGen)
			configfile.write('\n')
			if self.ump_mdm_mode.get()==1:
				configfile.write('MDMMODE=edytor')
			else:
				configfile.write('MDMMODE=wrzucacz')
			configfile.write('\n')
			configfile.write('CVSUSERNAME='+self.umpcvsusername.get())
				
			command=self.destroy()
	
	def OnButtonClickMapedit(self):
		aaa=tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu mapedit.exe')
		if len(aaa)>0:
			self.umpMapeditPath.set(aaa)
			self.Konfiguracja.MapEditExe=aaa
			
	def OnButtonClickMapedit2(self):
		aaa=tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu mapedit.exe')
		if len(aaa)>0:
			self.umpMapedit2Path.set(aaa)
			self.Konfiguracja.MapEdit2Exe=aaa
	
	def OnButtonClickNetgen(self):
		aaa=tkinter.filedialog.askopenfilename(title=u'Ścieżka do programu netgen.exe')
		if len(aaa)>0:
			self.umpNetGenPath.set(aaa)
			self.Konfiguracja.NetGen=aaa
		
	def OnButtonClickUMPSource(self):
		aaa=tkinter.filedialog.askdirectory(title=u'Katalog ze źródłami UMP')
		if len(aaa)>0:
			self.umpSourceValue.set(aaa)
			self.Konfiguracja.KatalogzUMP=aaa
		
	def OnButtonClickUMPRoboczy(self):
		aaa=tkinter.filedialog.askdirectory(title=u'Katalog roboczy')
		if len(aaa)>0:
			self.umpRoboczyValue.set(aaa)
			self.Konfiguracja.KatalogRoboczy=aaa
		

class mdmConfig(object):
	#zapisywanie i odczytywanie opcji montażu i demontażu, tak aby można było sobie zaznaczyć raz i aby tak pozostało
	def __init__(self):
		self.montDemontOptions= {'cityidx': tkinter.BooleanVar()}
		self.montDemontOptions['cityidx'].set(False)
		self.montDemontOptions['adrfile']=tkinter.BooleanVar()
		self.montDemontOptions['adrfile'].set(False)
		self.montDemontOptions['noszlaki']=tkinter.BooleanVar()
		self.montDemontOptions['noszlaki'].set(False)
		self.montDemontOptions['nocity']=tkinter.BooleanVar()
		self.montDemontOptions['nocity'].set(False)
		self.montDemontOptions['nopnt']=tkinter.BooleanVar()
		self.montDemontOptions['nopnt'].set(False)
		self.montDemontOptions['monthash']=tkinter.BooleanVar()
		self.montDemontOptions['monthash'].set(False)
		self.montDemontOptions['extratypes']=tkinter.BooleanVar()
		self.montDemontOptions['extratypes'].set(False)
		self.montDemontOptions['graniceczesciowe']=tkinter.BooleanVar()
		self.montDemontOptions['graniceczesciowe'].set(False)
		self.montDemontOptions['demonthash']=tkinter.BooleanVar()
		self.montDemontOptions['demonthash'].set(False)
		self.montDemontOptions['autopoi']=tkinter.BooleanVar()
		self.montDemontOptions['autopoi'].set(False)
		self.montDemontOptions['X']=tkinter.StringVar()
		self.montDemontOptions['X'].set('0')
		self.montDemontOptions['autopolypoly']=tkinter.BooleanVar()
		self.montDemontOptions['autopolypoly'].set(False)
		self.readConfig()
		
	
	def saveConfig(self):
		#try:
		with open(os.path.expanduser('~')+'/.mdm_config','w') as configfile:
			for key in self.montDemontOptions.keys():
				if self.montDemontOptions[key].get():
					value = 1
				else:
					value = 0
				linia=key+'='+str(value)+'\n'
				configfile.write(linia)
		

	def readConfig(self):
	
		try:
			with open(os.path.expanduser('~')+'/.mdm_config','r') as configfile:
				opcje=configfile.readlines()
			for a in opcje:
				abc=a.split('=')
				if abc[0] not in self.montDemontOptions:
					pass
				else:
					if abc[0]!='X':
						if abc[1].startswith('0'):
							self.montDemontOptions[abc[0]].set(False)
						elif abc[1].startswith('1'):
							self.montDemontOptions[abc[0]].set(True)
						else:
							pass
					elif abc[0]=='X':
						print('ustawiam dokladnosc zaokraglania')
						if abc[1].startswith('0'):
							self.montDemontOptions[abc[0]].set('0')
						elif abc[1].startswith('5'):
							self.montDemontOptions[abc[0]].set('5')
						elif abc[1].startswith('6'):
							self.montDemontOptions[abc[0]].set('6')
						else:
							pass
					else:
						pass
		except FileNotFoundError:
			pass
			
#klasa dla okienek z błędami oraz z informacjami na dole okna mdm-py. Definicje kolejek do odbioru komunikatów, menu itd.
class stdOutstdErrText(tkinter.scrolledtext.ScrolledText):
	def __init__(self, master,**options):
		tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
		self.inputqueue=queue.Queue()
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
		self.menu.entryconfigure(u'Wyczyść wszystko',command=self.event_clear_all)
		
		self.bind("Text", "<Control-a>", self.event_select_all)  
		self.bind("<Button-3><ButtonRelease-3>", self.show_menu)
		self.bind("<Double-Button-1>",self.event_double_click)
		
		#zmieniamy kolejność bindtags, najpierw klasa, potem widget tak aby podwójne kliknięcie na współrzędnych kopiowało je do schowka:
		tags=list(self.bindtags())
		tags.remove('Text')
		tags=['Text']+tags
		self.bindtags(tuple(tags))
		self.update_me()
		
	def event_select_all(self, *args):
		self.focus_force()        
		self.tag_add("sel","1.0","end")
		
	def event_clear_all_event(self, event):
		if (str(app.sprawdzButton['state']) != 'disabled'):
			self.event_clear_all()

	def event_clear_all(self):
		self.focus_force()
		self.delete("1.0","end")
	
	def show_menu(self, e):
		self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)
	
	def event_double_click(self,event):
		self.focus_force()
		self.event_generate("<<Copy>>")
		return 'break'
	
	def update_me(self):
		try:
			while 1:
				string = self.inputqueue.get_nowait()
				if string.startswith('\rProcent:'):
					#	self.output.insert('%linestart'%tkinter.END,string)
					self.delete('insert linestart','insert lineend')
					self.insert('end linestart',string.lstrip())
				else:
					self.insert(tkinter.END, string)
					self.see(tkinter.END)
		except queue.Empty:
			pass
		self.after(100, self.update_me)

#ScrolledText który przyjmuje informacje z wątków pobocznych, dla operacji cvs up i cvs co
class cvsOutText(tkinter.scrolledtext.ScrolledText):
	def __init__(self, master,**options):
		tkinter.scrolledtext.ScrolledText.__init__(self, master, **options)
		self.master=master
		self.inputqueue=queue.Queue()
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
		self.tag_config('P',foreground='green')
		self.tag_config('U',foreground='green')
		self.tag_config('questionmark',foreground='olive drab')
		self.tag_config('C',foreground='red')
		self.tag_config('M',foreground='deep pink')
		self.tag_config('normal',foreground='black')
		self.tag_config('error',foreground='red')
		self.tag_config('wskazowka',foreground='blue')
		self.height = self.winfo_reqheight()
		self.width = self.winfo_reqwidth()
		
		#usuwam skróty klawiautorwe które powinny być przechwytywane globalnie, tak żeby nie łapało ich też okienko do wpisywania komentarza. 
		#Np ctrl+o dodawało nową linię i przez to mój walidador się psuł :D.
		
		self.bind("<Control-o>",lambda e:None)
		self.bind("<Escape>",lambda e:None)
		
		#Zmieniamy kolejność bindtags. Z niewiadomego dla mnie powodu '.' nie działała.
		tags=list(self.bindtags())
		tags.remove('Text')
		tags.append('Text')
		self.bindtags(tuple(tags))

		self.update_me()
	
	def event_select_all(self, *args):
		self.focus_force()        
		self.tag_add("sel","1.0","end")
	
	def show_menu(self, e):
		self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)
			
	def update_me(self):
		try:
			while 1:
				string = self.inputqueue.get_nowait()
				if string.startswith('P '):
					self.insert('end',string.lstrip(),'P')
				elif string.startswith('U '):
					self.insert('end',string.lstrip(),'U')
				elif string.startswith('? '):
					self.insert('end',string.lstrip(),'questionmark')
				elif string.startswith('C '):
					self.insert('end',string.lstrip(),'C')
					self.insert('end',u'Uwaga! Łączenie zmian się nie powiodło. W pliku występują konflikty!\n','error')
					self.insert('end',u'Otwórz plik w edytorze i usuń konflikty ręcznie.\n\n','wskazowka')
				elif string.startswith('M '):
					self.insert('end',string.lstrip(),'M')
				elif string.startswith(u'Błąd'):
					self.insert('end',string.lstrip(),'error')
				elif string.startswith(u'>'):
					self.insert('end',string.lstrip('>'),'wskazowka')
				elif string.startswith(u'nieprzeslane'):
					self.insert('end',string.lstrip('nieprzeslane'),'error')
					
				else:
					self.insert('end',string.lstrip(),'normal')
				self.see(tkinter.END)
					
		except queue.Empty:
			pass
		self.after(100, self.update_me)

class myCheckbutton(tkinter.ttk.Checkbutton):
	#checkbutton ktory umieszczony jest w liscie obszarow. Ma dodatkowo dolozone menu do cvs up i cvs co
	def __init__(self, master, args, obszar,zmienna, regionVariableDictionary, **options):
		self.args = args
		self.obszar=obszar
		self.zmienna=zmienna
		# poniższa zmienna używana jest do cvs ci dla zaznaczonych obszarów, pozwala odczytać które obszary są zaznaczone 
		self.regionVariableDictionary=regionVariableDictionary
		tkinter.ttk.Checkbutton.__init__(self,master,**options)
		self.menu=tkinter.Menu(self,tearoff=0)
		a='cvs up '+self.obszar
		self.menu.add_command(label=a,command=self.cvsup)
		self.menu.add_command(label='cvs up narzedzia/granice.txt',command=self.cvsupgranice)
		a='cvs ci '+self.obszar
		self.menu.add_command(label=a,command=self.cvsci)
		a= 'cvs ci dla zaznaczonych obszarów'
		self.menu.add_command(label=a,command=self.cvsci_zaznaczone_obszary)
		a = 'cvs diff -u ' + self.obszar
		self.menu.add_command(label=a,command=self.cvsdiff)
		self.menu_testy=tkinter.Menu(self.menu,tearoff=0)
		self.menu_testy.add_command(label = u'Znajdź współrzędne poza obszarem', command=self.znajdz_wyst)
		self.menu_testy.add_command(label = u'Drogi bez wjazdu - bez jednokierunkowych', command = self.sprawdz_siatke_dwukierunkowa)
		self.menu_testy.add_command(label = u'Drogi bez wjazdu - uwzgl. jednokierunkowe', command = self.sprawdz_siatke_jednokierunkowa)
		self.menu.add_cascade(label=u'Różne testy', menu = self.menu_testy)
		self.bind("<Button-3><ButtonRelease-3>", self.show_menu)
		self.bind("<Control-ButtonRelease-1>", self.sel_then_cvsup)
		
	def sprawdz_siatke_dwukierunkowa(self):
		self.sprawdz_ciaglosc_grafow_routingowych('sprawdz_siatke_dwukierunkowa')
		
	def sprawdz_siatke_jednokierunkowa(self):
		self.sprawdz_ciaglosc_grafow_routingowych('sprawdz_siatke_jednokierunkowa')
		
	def sprawdz_ciaglosc_grafow_routingowych(self, mode):
		self.args.plikmp=None
		self.args.mode = mode
		thread1=threading.Thread(target=mont_demont_py.sprawdz_numeracje, args=(self.args,))
		thread1.start()
		
	def znajdz_wyst(self):
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		argumenty=[self.obszar, Zmienne.KatalogzUMP, Zmienne.KatalogRoboczy]
		thread=threading.Thread(target=znajdz_wystajace.main,args=[argumenty])
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
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		if os.path.isfile(Zmienne.KatalogRoboczy+'wynik.mp'):
			if tkinter.messagebox.askyesno(u'Plik wynik.mp istnieje',u'W katalogu roboczym istniej plik wynik.mp.\nCvs up może uniemożliwić demontaż. Czy kontynuować pomimo tego?'):
				aaa=cvsOutputReceaver(self,[self.obszar],'','up')
			else:
				pass
		else:
			aaa=cvsOutputReceaver(self,[self.obszar],'','up')
	
	def cvsdiff(self):
		aaa=cvsOutputReceaver(self,[self.obszar],'','diff')
	
	def cvsupgranice(self):
		doCVS=cvsOutputReceaver(self,['narzedzia/granice.txt'],'','up')
		
	def cvsci(self):
		oknodialogowe=cvsDialog(self,[self.obszar],title=u'Prześlij pliki do repozytorium cvs')
		if oknodialogowe.iftocommit=='tak':
			doCVS=cvsOutputReceaver(self,[self.obszar],oknodialogowe.message,'ci')
		else:
			pass
	
	def cvsci_zaznaczone_obszary(self):
		zaznaczone_obszary=[]
		for aaa in self.regionVariableDictionary.keys():
			if self.regionVariableDictionary[aaa].get()==1:
				print(aaa)
				zaznaczone_obszary.append(aaa)
		if not zaznaczone_obszary:
			tkinter.messagebox.showwarning(u'Brak wybranego obszaru!',u'Nie zaznaczyłeś żadnego obszaru do wysłania na serwer. Wybierz chociaż jeden.')
			return
		oknodialogowe=cvsDialog(self,zaznaczone_obszary,title=u'Prześlij pliki do repozytorium cvs')
		if oknodialogowe.iftocommit=='tak':
			doCVS=cvsOutputReceaver(self,zaznaczone_obszary,oknodialogowe.message,'ci')
		else:
			pass

		
class cvsDialog(tkinter.Toplevel):
#używane do CVS commit, aby wpisać komentarz do transakcji

	def __init__(self, parent,pliki, title = None):

		tkinter.Toplevel.__init__(self, parent)
		self.transient(parent)
		self.pliki=pliki[:]
		self.iftocommit='nie'
		self.last_cvs_log = []

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

		self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
									parent.winfo_rooty()+50))

		#self.initial_focus.focus_set()
		#ustawiamy focus na okienko do wpisywania logu, tak aby kursor do wpisywania od razu tam był.
		self.logwindow.focus_set()
		self.wait_window(self)


	def body(self, master):
		# create dialog body.  return widget that should have
		# initial focus.  this method should be overridden
		katalog=tkinter.Label(self,text='AAAAA')
		katalog.pack()
		logwindowsFrame=tkinter.ttk.Labelframe(self,text='Komentarz')
		logwindowsFrame.pack()
		self.logwindow=cvsOutText(logwindowsFrame,width=70,height=6,font='Arial 10')
		self.logwindow.pack(fill='y',expand=True)
		
		# wczytujemy ostatni log cvs
		last_cvs_log = self.read_last_commit_log()
		if last_cvs_log:
			last_cvs_log[-1] = last_cvs_log[-1].rstrip()
			for a in last_cvs_log:
				self.logwindow.insert('end',a)
			# zaznaczamy go aby było łatwo usunąć
			self.logwindow.tag_add("sel","1.0","end")
			
		commitedFilesFrame=tkinter.ttk.Labelframe(self,text=u'Obszary lub/i pliki do zatwierdzenia')
		commitedFilesFrame.pack()
		commitedFiles=cvsOutText(commitedFilesFrame,width=70,height=6,font='Arial 10')
		commitedFiles.pack()
		for a in self.pliki:
			commitedFiles.insert('insert',a)
			commitedFiles.insert('insert','\n')
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
		#łączymy skróty klawiaturowe do ok oraz cancel
		self.bind("<Control-o>", self.ok)
		self.bind("<Escape>", self.cancel)

	# standard button semantics
	def ok(self, event=None):
		if self.validate():
			#self.initial_focus.focus_set() # put focus back
			self.logwindow.focus_set()
			return  "break"
		
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
	#
	# command hooks
	def validate(self):
		a=self.logwindow.get(1.0,'end')
		if len(a)<=1:
			return 1
		else:
			self.message=a
			return 0

	def apply(self):
		
		self.iftocommit='tak'
		#print('stosuje')
		#doCVS=cvsOutputReceaver(self.parent,self.pliki,self.message,'ci')
		#pass # override
	
	def read_last_commit_log(self):
		last_cvs_log = []
		
		try:
			with open(os.path.expanduser('~')+'/.mdm_cvs_last_log','r', encoding='utf-8', errors='ignore') as lastlog:
				last_cvs_log = lastlog.readlines()
		except FileNotFoundError:
			pass
		return last_cvs_log
			
	def save_last_commit_log(self):
		try:
			with open(os.path.expanduser('~')+'/.mdm_cvs_last_log','w', encoding='utf-8', errors='ignore') as lastlog:
				lastlog.writelines(self.message)
		except FileNotFoundError:
			pass

class cvsOutputReceaver(tkinter.Toplevel):
#okienko które wyświetla wyjście z programu cvs

	def __init__(self, parent, obszary,message,cvscommand,title = None):

		tkinter.Toplevel.__init__(self, parent)
		self.parent=parent
		self.transient(parent)
		self.stopthreadqueue=queue.Queue()
		self.progreststartstopqueue=queue.Queue()
		self.uncommitedfiles=[]
		self.commitedfiles=[]
				
		if title:
			self.title(title)

		self.parent = parent

		self.result = None

		body = tkinter.Frame(self)
		self.initial_focus = self.body(body)
		body.pack(padx=5, pady=5,fill='both',expand=0)

		self.buttonbox()

		self.grab_set()

		if not self.initial_focus:
			self.initial_focus = self

		self.protocol("WM_DELETE_WINDOW", self.closewindows)

		self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
									parent.winfo_rooty()+50))

		self.initial_focus.focus_set()
		
		if cvscommand=='up':
			thread=threading.Thread(target=self.cvsup,args=(obszary,self.stopthreadqueue,self.progreststartstopqueue))
			thread.start()
		elif cvscommand == 'diff':
			thread = threading.Thread(target=self.cvsdiff, args=(obszary,self.stopthreadqueue,self.progreststartstopqueue))
			thread.start()
		else:
			thread=threading.Thread(target=self.cvsci,args=(obszary,message,self.stopthreadqueue,self.progreststartstopqueue))
			thread.start()
			#self.cvsci(self.args.obszary,self.args.message)
		#mont_demont_py.cvsup(self.args)
		self.progres_start_stop_check()
		self.wait_window(self)
		

	def progres_start_stop_check(self):
		try:
			while 1:
				string = self.progreststartstopqueue.get_nowait()
				if string=='start':
					self.progressbar.start()
					self.OKButton.configure(state='disabled')
				elif string=='stop':
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
		katalog=tkinter.Label(self,text='AAAAA')
		katalog.pack(fill='x',expand=0)
		logwindowsFrame=tkinter.ttk.Labelframe(self,text=u'Dane wyjściowe')
		logwindowsFrame.pack(fill='both',expand=1)
		self.outputwindow=cvsOutText(logwindowsFrame,width=80,height=10,font='Arial 10')
		self.outputwindow.config(wrap='none')
		self.outputwindow.pack(fill='both',expand=1)
		

	def buttonbox(self):
		# add standard button box. override if you don't want the
		# standard buttons

		box = tkinter.Frame(self)
		
		self.progressbar=tkinter.ttk.Progressbar(box,mode='indeterminate',length=100)
		self.progressbar.pack(side='left',anchor='w',expand=1)
		self.OKButton = tkinter.Button(box, text="OK", width=10, command=self.ok, default='active')
		self.OKButton.pack(side='left', padx=5, pady=5,anchor='e')
		#do guzika OK bindujemy klawisz Return, aby można było zamknąć enterem oraz klawiszem escape
		self.OKButton.bind('<Return>',self.ok)
		self.OKButton.bind('<Escape>',self.ok)
		
		self.przerwijButton = tkinter.Button(box, text="Przerwij", width=10, command=self.cancel)
		self.przerwijButton.pack(side='left', padx=5, pady=5,anchor='e')

		#self.bind("<Return>", self.ok)
		#self.bind("<Escape>", self.cancel)

		box.pack(fill='x',expand=0)
			
	
	# standard button semantics
	def ok(self, event=None):

		if self.validate():
			self.initial_focus.focus_set() # put focus back
			return

		self.withdraw()
		self.update_idletasks()

		self.apply()

		self.parent.focus_set()
		self.destroy()

	def cancel(self, event=None):

		# put focus back to the parent window
		#self.parent.focus_set()
		#self.destroy()
		self.stopthreadqueue.put('stop')

	#
	# command hooks
	def closewindows(self,event=None):
		if self.OKButton.config('state')[-1] != 'disabled':
			self.ok()
		
	def validate(self):
		return 0

	def apply(self):

		pass # override
	
	def cvsci(self,obszary,message,stopthreadqueue,progreststartstopqueue):
		
		progreststartstopqueue.put('start')
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		CVSROOT='-d:pserver:'+Zmienne.CvsUserName+'@cvs.ump.waw.pl:/home/cvsroot'
		string=''
		
		os.chdir(Zmienne.KatalogzUMP)
		self.outputwindow.inputqueue.put(('cd '+Zmienne.KatalogzUMP+'\n'))
		self.outputwindow.inputqueue.put(('CVSROOT='+CVSROOT+'\n\n'))
		for a in obszary:
			self.outputwindow.inputqueue.put(('cvs ci -m "'+message.strip()+'" '+a+'\n'))
			process = subprocess.Popen(['cvs', '-q',CVSROOT,'ci','-m',message,a],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			
			while process.poll()==None:
				try:
					string = stopthreadqueue.get_nowait()
					if string=='stop':
						process.terminate()
						break
				except queue.Empty:
					pass
				
				time.sleep(1)
			
			stderr=process.stderr.readlines()
			stdout=process.stdout.readlines()
			
			if len(stderr)>0:
				if stderr[0].decode(Zmienne.Kodowanie).find('Up-to-date check failed')>=0:
					for line in stderr:
						self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
					self.outputwindow.inputqueue.put(u'Błąd, polecenie CVS nieudane!\n\n')
					self.outputwindow.inputqueue.put(u'>Wskazówka. Ktoś inny zatwierdził w repozytorium nowszą wersję pliku lub plików, dla których\n')
					self.outputwindow.inputqueue.put(u'>próbujesz wykonac operację commit. Musisz wykonać polecenie update,\n')
					self.outputwindow.inputqueue.put(u'>a następnie commit.\n\n')
					self.uncommitedfiles.append(a)
				else:
					for line in stderr:
						self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))

			else:
				if len(stdout)>0:
					for line in stdout:
						self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
						if line.decode(Zmienne.Kodowanie).find('<--  '+a.split('/')[-1])>=0:
							self.commitedfiles.append(a)
					if string == 'stop':
						self.outputwindow.inputqueue.put(u'Commit przerwany na żądanie użytkownika!\n')
						self.outputwindow.inputqueue.put('Gotowe\n')
						break
					else:
						pass
				else:
					self.commitedfiles.append(a)
		
		for a in obszary:
			if (a.find('/src')>0) and (a not in self.commitedfiles):
				self.uncommitedfiles.append(a)
		
		if len(self.uncommitedfiles)>0:
			self.outputwindow.inputqueue.put(u'\nObszary których nie udało się przesłać:\n')
			for a in self.uncommitedfiles:
				self.outputwindow.inputqueue.put(('nieprzeslane'+a+'\n'))
				
		self.outputwindow.inputqueue.put('Gotowe\n')
		progreststartstopqueue.put('stop')
		
	
	def cvsdiff(self,obszary,stopthreadqueue,progreststartstopqueue):
		progreststartstopqueue.put('start')
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		CVSROOT='-d:pserver:'+Zmienne.CvsUserName+'@cvs.ump.waw.pl:/home/cvsroot'
		string=''
		czyzatrzymac=0
		
		os.chdir(Zmienne.KatalogzUMP)
		self.outputwindow.inputqueue.put(('cd '+Zmienne.KatalogzUMP+'\n'))
		self.outputwindow.inputqueue.put(('CVSROOT='+CVSROOT+'\n'))
		
		for a in obszary:
			self.outputwindow.inputqueue.put(('cvs diff -u '+a+'/src\n'))
			process = subprocess.Popen(['cvs','-q', CVSROOT,'diff', '-u', a+'/src'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
			processexitstatus=process.poll()
			
			while processexitstatus==None:
				try:
					string = stopthreadqueue.get_nowait()
					if string=='stop':
						process.terminate()
						czyzatrzymac=1
						break
					#		
				except queue.Empty:
					pass
				line=process.stdout.readline()
				if line.decode(Zmienne.Kodowanie) !='':
					self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
				
				#time.sleep(0.1)
				processexitstatus=process.poll()
				
			if czyzatrzymac:
				break
			
		if string == 'stop':
			self.outputwindow.inputqueue.put(u'Cvs diff -u przerwany na żądanie użytkownika!\n')
		
		else:
			#okazuje sie, że trzeba jeszcze sprawdzić czy całe stdout zostało odczytane. Bywa że nie i trzeba doczytać tutaj.
			while line.decode(Zmienne.Kodowanie)!='':
				line=process.stdout.readline()
				self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
		self.outputwindow.inputqueue.put('\n\nGotowe\n')
		progreststartstopqueue.put('stop')
	
	def cvsup(self,obszary,stopthreadqueue,progreststartstopqueue):
		
		progreststartstopqueue.put('start')
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		CVSROOT='-d:pserver:'+Zmienne.CvsUserName+'@cvs.ump.waw.pl:/home/cvsroot'
		string=''
		czyzatrzymac=0
		
		os.chdir(Zmienne.KatalogzUMP)
		self.outputwindow.inputqueue.put(('cd '+Zmienne.KatalogzUMP+'\n'))
		self.outputwindow.inputqueue.put(('CVSROOT='+CVSROOT+'\n'))
		
		for a in obszary:
			self.outputwindow.inputqueue.put(('cvs up '+a+'\n'))
			process = subprocess.Popen(['cvs','-q', CVSROOT,'up', a],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
			processexitstatus=process.poll()
			
			while processexitstatus==None:
				try:
					string = stopthreadqueue.get_nowait()
					if string=='stop':
						process.terminate()
						czyzatrzymac=1
						break
					#		
				except queue.Empty:
					pass
				line=process.stdout.readline()
				if line.decode(Zmienne.Kodowanie) !='':
					self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
				
				#time.sleep(0.1)
				processexitstatus=process.poll()
				
			if czyzatrzymac:
				break
			
		if string == 'stop':
			self.outputwindow.inputqueue.put(u'Proces uaktualniania przerwany na żądanie użytkownika!\n')
		
		else:
			#okazuje sie, że trzeba jeszcze sprawdzić czy całe stdout zostało odczytane. Bywa że nie i trzeba doczytać tutaj.
			while line.decode(Zmienne.Kodowanie)!='':
				line=process.stdout.readline()
				self.outputwindow.inputqueue.put(line.decode(Zmienne.Kodowanie))
		self.outputwindow.inputqueue.put('Gotowe\n')
		progreststartstopqueue.put('stop')

class zobaczDiffText(tkinter.Text):
	def __init__(self, master, nazwapliku, **options):
		tkinter.Text.__init__(self, master, **options)
		self.bind("<Double-Button-1>",self.event_double_click)
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
				
	def event_double_click(self,event):
		znaki_dla_wspolrzednych = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ',', '(', ')', '.']
		znaki_dla_wsp_txt = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ',', '.']
		self.focus_force()
		indeks_literki_pod_kursorem = self.index('current')
		literka_pod_kursorem = self.get(indeks_literki_pod_kursorem)
		nr_linii, nr_znaku = indeks_literki_pod_kursorem.split('.')
		linia = self.get(nr_linii+".0",nr_linii+".end")
		# podwójne kliknięcie powinno zaznaczyć parę współrzędnych
		# para współrzędnych to (XX,XXXXX,YY,YYYYY), a
		# musimy kliknąć na liczbie, przecinku lub  nawiasie by zacząć wyszukiwać w przeciwnym przypadku zaznacza całą linię
		if literka_pod_kursorem not in znaki_dla_wspolrzednych:
			# zaznaczamy całą linię:
			self.tag_add("sel",nr_linii+".0",nr_linii+".end")
		else:
			try:
				if self.typpliku == 'txt':
					index0 = index1 = int(nr_znaku)
					if linia[self.ofset:].startswith('Data'):
						if literka_pod_kursorem == '(':
							while linia[index1] != ')':
								index1 += 1
							self.tag_add("sel", nr_linii+"."+str(index0+1),nr_linii+"."+ str(index1))
						elif literka_pod_kursorem == ')':
							while linia[index0] != '(':
								index0 -= 1
							self.tag_add("sel", nr_linii+"."+str(index0+1),nr_linii+"."+ str(index1))
						else:
							while linia[index0] in znaki_dla_wsp_txt:
								index0 -= 1
							while linia[index1] in znaki_dla_wsp_txt:
								index1 += 1
							self.tag_add("sel", nr_linii+"."+str(index0+1),nr_linii+"."+ str(index1))
					else:
						return 0
				elif self.typpliku =='pnt' or self.typpliku == 'adr':
					if linia[self.ofset:].startswith('  ') or linia.startswith('  '):
						x=2
						z=0
						while x >0:
							if linia[z] == ',':
								x -= 1
							z += 1
						self.tag_add("sel", nr_linii+"."+str(2+self.ofset),nr_linii+"."+ str(z-1))

					else:
						return 0
			except IndexError:
				return 0

		self.event_generate("<<Copy>>")
		return 'break'
		
class ButtonZaleznyOdWynik(tkinter.ttk.Button):
	def __init__(self, master,KatalogRoboczy,**options):
		self.master = master
		self.statusqueue=queue.Queue()
		self.KatalogRoboczy=KatalogRoboczy
		#self.buttonName = options['text']
		self.previousfile = 1
		self.actfile = 0
		self.funkcjaPrzyciskuPracuje = 0
		self.previousFunkcjaPrzyciskuPracuje = 1
		tkinter.ttk.Button.__init__(self, master, **options)
		self.bind('<Enter>',self.enter)
		self.bind('<Leave>',self.leave)
		self.update_me()

				
	def enter(self,event):
		if os.path.isfile(self.KatalogRoboczy+'wynik.mp') and not self.funkcjaPrzyciskuPracuje:
			self.configure(state='active')
		
	def leave(self,event):
		if os.path.isfile(self.KatalogRoboczy+'wynik.mp') and not self.funkcjaPrzyciskuPracuje:
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
			#self.previousFunkcjaPrzyciskuPracuje = self.funkcjaPrzyciskuPracuje = 0
			pass
			
		self.actfile = os.path.isfile(self.KatalogRoboczy+'wynik.mp')
		
		
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
				self.previousfile=self.actfile
			#elif self.configure('state')[-1] == 'disabled':
		self.master.update_idletasks()
		self.after(100, self.update_me)
		
		
class Argumenty(object):
	def __init__(self):
		self.umphome = None
		self.plikmp=None
		self.katrob=None
		self.obszary=[]
		self.notopo=0

class SetupMode(object):
	def __init__(self):
		self.modulyCVSLista = ['AUSTRIA', 'BALKANY', 'BRYTANIA', 'CZECHY', 'DANIA', 'ESTONIA', 'EUROPA', 'FINLANDIA', 'FRANCJA', 'HISZPANIA', 'HOLANDIA', 'NIEMCY', 'NORWEGIA', 'POLSKA', 
								'PORTUGALIA', 'ROSJA', 'RUMUNIA', 'SKANDYNAWIA', 'SZWECJA', 'WLOCHY', 'all', 'inne']
		self.modulyCVS = {'AUSTRIA':['UMP-AT-Graz', 'UMP-AT-Innsbruck', 'UMP-AT-Linz', 'UMP-AT-Wien'],
							'BALKANY':['UMP-Albania', 'UMP-Bosnia', 'UMP-Bulgaria', 'UMP-Chorwacja', 'UMP-Czarnogora', 'UMP-Grecja', 'UMP-Kosowo', 'UMP-Macedonia', 'UMP-Moldawia', 'RUMUNIA', 'UMP-Serbia', 'UMP-Slowenia', 'UMP-Turcja'],
							'BRYTANIA':['UMP-GB-Belfast', 'UMP-GB-Edinburgh', 'UMP-GB-Bristol', 'UMP-GB-Leeds', 'UMP-GB-Leicester', 'UMP-GB-London', 'UMP-GB-Manchester', 'UMP-GB-Plymouth',],
							'CZECHY':['UMP-CZ-Brno', 'UMP-CZ-Budejovice', 'UMP-CZ-Jihlava', 'UMP-CZ-KarlovyVary', 'UMP-CZ-Olomouc', 'UMP-CZ-Ostrava', 'UMP-CZ-Pardubice', 'UMP-CZ-Plzen', 'UMP-CZ-Praha'],
							'DANIA':['UMP-Dania', 'UMP-WyspyOwcze'],
							'ESTONIA':['UMP-EE-Tallin', 'UMP-EE-Tartu'],
							'EUROPA':['BALKANY', 'NIEMCY', 'SKANDYNAWIA', 'BRYTANIA', 'UMP-Andora', 'AUSTRIA', 'UMP-Belgia', 'UMP-Bialorus', 'UMP-Cypr', 'CZECHY', 'ESTONIA', 'FRANCJA', 'HISZPANIA', 'HOLANDIA', 'UMP-Irlandia', 'UMP-RU-Kaliningrad', 'UMP-Lichtenstein', 'UMP-Litwa', 'UMP-Lotwa', 'UMP-Luksemburg', 'UMP-Malta', 'PORTUGALIA', 'ROSJA', 'UMP-Slowacja', 'UMP-Szwajcaria', 'UMP-Ukraina', 'UMP-Wegry', 'WLOCHY'],
							'FINLANDIA':['UMP-FI-Helsinki', 'UMP-FI-Oulu', 'UMP-FI-Tampere', 'UMP-FI-Vaasa'],
							'FRANCJA':['UMP-FR-Ajaccio', 'UMP-FR-ClermontFerrand', 'UMP-FR-Dijon', 'UMP-FR-LeHavre', 'UMP-FR-Lille', 'UMP-FR-Limoges', 'UMP-FR-Lyon', 'UMP-FR-Marseille', 'UMP-FR-Montpellier', 'UMP-FRpantes', 'UMP-FR-Orleans', 'UMP-FR-Paris', 'UMP-FR-Rennes', 'UMP-FR-SaintEtienne', 'UMP-FR-Strasbourg', 'UMP-FR-Toulouse'],
							'HISZPANIA':['UMP-ES-Madrid', 'UMP-ES-Kanary', 'UMP-ES-Albacete', 'UMP-ES-Badajoz', 'UMP-ES-Barcelona', 'UMP-ES-Gijon', 'UMP-ES-Murcia', 'UMP-ES-Palma', 'UMP-ES-Sevilla', 'UMP-ES-Valencia', 'UMP-ES-Valladolid', 'UMP-ES-Vigo', 'UMP-ES-Zaragoza'],
							'HOLANDIA':['UMP-NL-Amsterdam', 'UMP-NL-Eindhoven', 'UMP-NL-Groningen', 'UMP-NL-Rotterdam', 'UMP-NL-Tilburg', 'UMP-NL-Utrecht', 'UMP-NL-Zwolle'],
							'NIEMCY':['UMP-DE-Baden', 'UMP-DE-Bayern', 'UMP-DE-Brandenburg', 'UMP-DE-Hessen', 'UMP-DE-Mecklenburg', 'UMP-DE-Niedersachsen', 'UMP-DE-Rheinland', 'UMP-DE-Sachsen', 'UMP-DE-SachsenAnhalt', 'UMP-DE-Schleswig', 'UMP-DE-Thuringen', 'UMP-DE-Westfalen'],
							'NORWEGIA':['UMP-NO-Alta', 'UMP-NO-Bergen', 'UMP-NO-Tromso', 'UMP-NO-Trondheim', 'UMP-NO-Oslo'],
							'POLSKA':['UMP-PL-Warszawa', 'UMP-PL-Bialystok', 'UMP-PL-Ciechanow', 'UMP-PL-Gdansk', 'UMP-PL-GorzowWlkp', 'UMP-PL-JeleniaGora', 'UMP-PL-Kalisz', 'UMP-PL-Katowice', 'UMP-PL-Kielce', 'UMP-PL-Klodzko', 'UMP-PL-Koszalin', 'UMP-PL-Krakow', 'UMP-PL-Leszno', 'UMP-PL-Lodz', 'UMP-PL-Lublin', 'UMP-PL-NowySacz', 'UMP-PL-Olsztyn', 'UMP-PL-Opole', 'UMP-PL-Pila', 'UMP-PL-Plock', 'UMP-PL-Poznan', 'UMP-PL-Przemysl', 'UMP-PL-Radom', 'UMP-PL-Rzeszow', 'UMP-PL-Siedlce', 'UMP-PL-Suwalki', 'UMP-PL-Szczecin', 'UMP-PL-Tarnow', 'UMP-PL-Tczew', 'UMP-PL-Torun', 'UMP-PL-Wloclawek', 'UMP-PL-Wroclaw', 'UMP-PL-Zamosc', 'UMP-radary'],
							'PORTUGALIA':['UMP-PT-Lisboa', 'UMP-PT-Azory', 'UMP-PT-Madera'],
							'ROSJA':['UMP-RU-Moskwa', 'UMP-RU-Kaliningrad'],
							'RUMUNIA':['UMP-RO-Bucuresti', 'UMP-RO-Timisoara'],
							'SKANDYNAWIA':['DANIA', 'SZWECJA', 'FINLANDIA', 'NORWEGIA', 'UMP-Islandia'],
							'SZWECJA':['UMP-SE-Goteborg', 'UMP-SE-Linkoping', 'UMP-SE-Malmo', 'UMP-SE-Norrkoping', 'UMP-SE-Orebro', 'UMP-SE-Stockholm', 'UMP-SE-Umea'],
							'WLOCHY':['UMP-IT-Bari', 'UMP-IT-Bologna', 'UMP-IT-Bolzano', 'UMP-IT-Cagliari', 'UMP-IT-Cosenza', 'UMP-IT-Firenze', 'UMP-IT-Genova', 'UMP-IT-Milano', 'UMP-IT-Napoli', 'UMP-IT-Palermo', 'UMP-IT-Perugia', 'UMP-IT-Pescara', 'UMP-IT-Roma', 'UMP-IT-Torino', 'UMP-IT-Trieste'],
							'all':['narzedzia', 'POLSKA', 'EUROPA', 'UMP-Egipt', 'UMP-Tunezja', 'UMP-Algieria', 'UMP-Maroko', 'UMP-Nepal', 'Makefile.common'],
							'inne':['UMP-Karaiby', 'UMP-ZielonyPrzyladek', 'UMP-Afryka', 'UMP-Ameryka', 'UMP-Australia', 'UMP-Azja']}
		umpfoldernames = ['ump','umpsource','umpcvs','cvsump','ump_cvs','cvsump']
		self.modulyCVSCheckboksy = {}
		
		self.plikiDoSciagniecia={'cvs.exe':'http://ump.waw.pl/pliki/cvs.exe',
								'mapedit2-1-78-10.zip':'http://www.geopainting.com/download/mapedit2-1-78-10.zip'}
		if platform.architecture() == '32bit':
			self.plikiDoSciagniecia['mapedit++(32)1.0.61.513tb_3.zip']='http://wheart.bofh.net.pl/gps/mapedit++(32)1.0.61.513tb_3.zip'
		else:
			self.plikiDoSciagniecia['mapedit++(64)1.0.61.513tb_3.zip']='http://wheart.bofh.net.pl/gps/mapedit++(64)1.0.61.513tb_3.zip'
		home=os.path.expanduser('~')+'/'
		self.CvsUserName = 'guest'
		self.CVSROOT='-d:pserver:'+self.CvsUserName+'@cvs.ump.waw.pl:/home/cvsroot'
		# self.ListaObszarow = list()
		self.modulyCvsDoSciagniecia = list()
		for a in umpfoldernames:
			try:
				abc = home+a
				os.makedirs(abc)
				self.umpHome = abc
				break
			except FileExistsError:
				pass
		
		for plik in self.plikiDoSciagniecia:
			try:
				u = urllib.request.urlopen(self.plikiDoSciagniecia[plik])
				f = open(self.umpHome+'/'+plik, 'wb')
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
					#print(status)

				f.close()
			except urllib.error.HTTPError:
				print('Nie moge sciagnac pliku cvs.exe')
			# process = subprocess.Popen(['cvs', '-q',self.CVSROOT,'ls',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		os.chdir(self.umpHome)
		
		#tworzymy katalogi mapedita i rozpakowujemy zipy
		for plik in self.plikiDoSciagniecia:
			if not plik == 'cvs.exe':
				if plik.startswith('mapedit2'):
					dir = 'mapedit2'
				elif plik.startswith('mapedit++'):
					dir = 'mapedit++'
				plikzip=zipfile.ZipFile(plik, 'r')
				os.makedirs(dir)
				print(u'Rozpakowuję plik: '+plik)
				plikzip.extractall(path=dir)
				#os.remove(plik)
				
					
		# budujemy okno z listą wszystkich obszarów
		self.glowneOknoDialkogCVS = tkinter.Tk(None)
		self.glowneOknoDialkogCVS.title(u'Lista obszarów do ściągnięcia')
		glownaRamkaOknaDialogowego = tkinter.ttk.Labelframe(self.glowneOknoDialkogCVS, text=u'Wybierz obszary do ściągnięcia')
		glownaRamkaOknaDialogowego.pack(side='left', anchor='center', fill='both',expand=1)
		listaObszarowScrollBar = tkinter.Scrollbar(self.glowneOknoDialkogCVS)
		listaObszarowScrollBar.pack(fill='y', anchor='e', expand=0, side='left')
		# dajemy 2 buttony sciagnij oraz anuluj
		self.loginEntryFrame=tkinter.ttk.Labelframe(self.glowneOknoDialkogCVS, text='Login do CVS')
		self.loginEntryFrame.pack(anchor='n')
		self.loginEntry=tkinter.Entry(self.loginEntryFrame)
		self.loginEntry.pack()
		self.loginEntry.insert('0', 'guest')
		ramkaPrzyciskow = tkinter.Frame(self.glowneOknoDialkogCVS, pady=25, padx=5)
		ramkaPrzyciskow.pack(anchor='s',fill='y', expand=1)
		sciagnijButton = tkinter.ttk.Button(ramkaPrzyciskow, text=u'Ściągnij', command = self.sciagnijButtonClick)
		sciagnijButton.pack(anchor='s', side='bottom')
		cancelButton = tkinter.ttk.Button(ramkaPrzyciskow, text='Anuluj', command = self.cancelButtonClick)
		cancelButton.pack(anchor='s', side='bottom')
		listaObszarowCanvas = tkinter.Canvas(glownaRamkaOknaDialogowego, width=900)
		listaObszarowCanvas.pack(side='left', fill='both', expand =1)


		listaObszarowScrollBar.config(command=listaObszarowCanvas.yview)
		listaObszarowCanvas.config(yscrollcommand=listaObszarowScrollBar.set)
		
		ilosc_kolumn = 5
		akt_ilosc_wierszy = 0
		pozycja_ost_widgetu = 10
		for abc in self.modulyCVSLista:
			self.modulyCVSCheckboksy[abc] = []
			obszarFrame = tkinter.ttk.Labelframe(listaObszarowCanvas, text=abc)
			
			for bbb in range(len(self.modulyCVS[abc])):
				self.modulyCVSCheckboksy[abc].append(tkinter.BooleanVar())
				self.modulyCVSCheckboksy[abc].append(tkinter.ttk.Checkbutton(obszarFrame, width=25, text=self.modulyCVS[abc][bbb],
																				variable=self.modulyCVSCheckboksy[abc][-1]))
				self.modulyCVSCheckboksy[abc][-1].grid(column=bbb%ilosc_kolumn, row=bbb//ilosc_kolumn)
				#ilosc_wierszy_danego_obszaru = bbb//ilosc_kolumn
				#print('ilosc kolumn danego obszaru: ', ilosc_wierszy_danego_obszaru)
				
			obszarFrame.update_idletasks()
			wys_widgetu=obszarFrame.winfo_reqheight()

			# ilosc_wierszy_umieszczonych = ilosc_wierszy_umieszczonych+ilosc_wierszy_danego_obszaru+1
			# print(ilosc_wierszy_umieszczonych)
			listaObszarowCanvas.create_window(50,30+pozycja_ost_widgetu, window=obszarFrame, anchor = 'nw', width=900)
			pozycja_ost_widgetu += wys_widgetu
			
		listaObszarowCanvas.config(scrollregion=listaObszarowCanvas.bbox('all'))
		self.glowneOknoDialkogCVS.mainloop()
		
		print(self.modulyCvsDoSciagniecia)
		
	def sciagnijButtonClick(self):
		for abc in self.modulyCVSLista:
			for bbb in range(0, len(self.modulyCVSCheckboksy[abc]), 2):
				if self.modulyCVSCheckboksy[abc][bbb].get():
					self.modulyCvsDoSciagniecia.append(self.modulyCVS[abc][int(bbb/2)])
		self.glowneOknoDialkogCVS.destroy()
				
		
	def cancelButtonClick(self):
		self.glowneOknoDialkogCVS.destroy()

class mdm_gui_py(tkinter.Tk):
	def __init__(self, parent):
		
		tkinter.Tk.__init__(self, parent)
		self.parent = parent
		self.cvsstatusQueue=queue.Queue()
		self.initialize()
		if os.path.isfile(self.Zmienne.KatalogzUMP+'narzedzia/ikonki/UMPlogo32.gif'):
			iconimg=tkinter.PhotoImage(file = self.Zmienne.KatalogzUMP+'narzedzia/ikonki/UMPlogo32.gif')
			self.tk.call('wm','iconphoto',self._w,iconimg)
		self.sprawdzAktualnoscZrodelandPopupMessage()
		
	def konfiguracja(self):
		aaa=ConfigWindow(self)
		
	def skrotyKlawiaturowe(self):
		aaa=HelpWindow(self)
	
	def kreatorMapaOSMAnd(self):
		# return 0
		obszary = list()
		for a in self.regionVariableDictionary.keys():
			if self.regionVariableDictionary[a].get()==1:
				obszary.append(a)
		aaa = mdmkreatorOsmAnd.OSMAndKreator(self, obszary)
	
	def kreatorKlasDrog(self):
		obszary = list()
		for a in self.regionVariableDictionary.keys():
			if self.regionVariableDictionary[a].get()==1:
				obszary.append(a)
		aaa = mdmkreatorOsmAnd.Klasy2EndLevelCreator(self, obszary)
		
	def initialize(self):
	
		#wczytywanie zapisanych opcji montazu i demontazu:
		self.protocol("WM_DELETE_WINDOW", self.Quit)
		self.mdmMontDemontOptions=mdmConfig()
		
		#pliki zmienione, do wysłania na cvs
		self.plikiDoCVS=[]
		self.uncommitedfilesqueue=queue.Queue()
		self.Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		self.args = Argumenty()
		self.grid()
		
		
		# menu Plik
		menubar=tkinter.Menu(self)		
		menuPlik=tkinter.Menu(menubar, tearoff=0)		
		menuPlik.add_command(label=u'Konfiguracja', command=self.konfiguracja)
		menuPlik.add_separator()
		menuPlik.add_command(label=u'Wyjdź', command=self.Quit)		
		menubar.add_cascade(label=u'Plik', menu=menuPlik)
		
		# menu Kreatory
		menuKreatory = tkinter.Menu(menubar, tearoff = 0)
		menuKreatory.add_command(label = u'Mapa dla OSMAnda', command = self.kreatorMapaOSMAnd)
		menuKreatory.add_command(label = u'Mapa z podziałem dróg na klasy', command = self.kreatorKlasDrog)
		menubar.add_cascade(label = u'Kreatory', menu = menuKreatory)
		
		# menu Pomoc
		menuPomoc=tkinter.Menu(menubar, tearoff=0)
		menuPomoc.add_command(label=u'Skróty klawiaturowe', command=self.skrotyKlawiaturowe)
		menubar.add_cascade(label=u'Pomoc', menu = menuPomoc)
				
		self.config(menu=menubar)

		
		self.regionyWersja = tkinter.Frame(self)
		self.regionyWersja.grid(columnspan=2, row=0, sticky='EW')
		self.regionyWersja.grid_columnconfigure(0,weight=1)
		self.regionyWersja.grid_columnconfigure(1,weight=1)
		#zmienna wskazuje czy mamy do czynienia z edytorem czy wrzucaczem. W zależności od tego możemy albo kopiować pliki bezpośrednio, albo utworzyć archiwum zip do wysłania.
		self.mdm_mode=self.Zmienne.mdm_mode
		self.os=platform.system()
		self.osVersionVariable = tkinter.StringVar()
		self.osVersionVariable.set(u'Python: %s.%s.%s na %s %s (%s)'%(sys.version_info[0],sys.version_info[1],sys.version_info[0],platform.uname()[0],platform.uname()[2], platform.architecture()[0]))
		systemLabel = tkinter.ttk.Label(self.regionyWersja, textvariable=self.osVersionVariable)
		systemLabel.grid(column=0, row=0,sticky='w')
		self.guimodeVar = tkinter.StringVar()
		self.guimodeVar.set(u'Tryb pracy mdm: %s'%self.Zmienne.mdm_mode)
		guiMode = tkinter.ttk.Label(self.regionyWersja, textvariable=self.guimodeVar)
		guiMode.grid(column=1, row=0,sticky='w')
		self.autopolypoly=tkinter.ttk.Label(self.regionyWersja,text=u'Automatyczny rozkład obszarów i linii')
		self.autopolypoly.grid(column=2,row=0,sticky='w')
		self.selectUnselect_aol(None)
		
		
		#wybor regionow
		
		self.regionVariableDictionary = {}
		self.regionCheckButtonDictionary = {}
		
		self.regionyFrame = tkinter.ttk.LabelFrame(self,text=u'Wybór regionów')
		self.regionyFrame.grid(column=0,columnspan=2, row=1,sticky='ew')
		
		
		self.regionyFrame.bind_class('kolkomyszkiregiony',"<MouseWheel>", self._on_mousewheelregionyCanvas)
		self.regionyFrame.bind_class('kolkomyszkiregiony',"<Button-4>", self._on_mousewheelregionyCanvas)
		self.regionyFrame.bind_class('kolkomyszkiregiony',"<Button-5>", self._on_mousewheelregionyCanvas)
		newtags=self.regionyFrame.bindtags()+('kolkomyszkiregiony',)
		self.regionyFrame.bindtags(newtags)
		
		regionyScroll=AutoScrollbar(self.regionyFrame)
		regionyScroll.grid(column=1,row=0,sticky='NS')
		newtags=regionyScroll.bindtags()+('kolkomyszkiregiony',)
		regionyScroll.bindtags(newtags)
		
		regionyScrollX=AutoScrollbar(self.regionyFrame,orient='horizontal')
		regionyScrollX.grid(column=0,row=1,sticky='EW')
		
		#self.regionyListbox = tkinter.Listbox(self.regionyFrame,bd=1,highlightthickness=0,bg='SystemMenu',yscrollcommand = regionyScroll.set,height=4)
		#self.regionyListbox.grid(column=0,row=0)
		
		self.regionyCanvas = tkinter.Canvas(self.regionyFrame,yscrollcommand=regionyScroll.set,xscrollcommand=regionyScrollX.set,width=846,height=126,highlightthickness=0)
		self.regionyCanvas.grid(column=0,row=0,sticky='nsew')
		newtags=self.regionyCanvas.bindtags()+('kolkomyszkiregiony',)
		self.regionyCanvas.bindtags(newtags)
		
		regionyScroll.config(command=self.regionyCanvas.yview)
		regionyScrollX.config(command=self.regionyCanvas.xview)
		
		self.regionyFrameInCanvas = tkinter.Frame(self.regionyCanvas)
		self.regionyFrameInCanvas.rowconfigure(1,weight=1)
		self.regionyFrameInCanvas.columnconfigure(1,weight=1)
		newtags=self.regionyFrameInCanvas.bindtags()+('kolkomyszkiregiony',)
		self.regionyFrameInCanvas.bindtags(newtags)
		
		self.GenerujListeObszarow()
		
		self.regionyCanvas.create_window(423,0,anchor='n', window=self.regionyFrameInCanvas)
		self.regionyFrameInCanvas.update_idletasks()
		self.regionyCanvas.config(scrollregion=self.regionyCanvas.bbox("all"))
		#regionyScroll.config(command=self.regionyListbox.yview)
		
		buttonFrame=tkinter.Frame(self.regionyFrame)
		buttonFrame.grid_columnconfigure(0,weight=1)
		buttonFrame.grid_columnconfigure(1,weight=1)
		
		odswiezRegionyButton = tkinter.ttk.Button(buttonFrame, text=u'Odśwież listę regionów',command=self.OnButtonClickOdswiezListeObszarow)
		odswiezRegionyButton.grid(column=0,row=0)
		
		cvsUaktualnijZrodlaButton=tkinter.ttk.Button(buttonFrame,text=u'Uaktualnij źródła (cvs update)',command=self.OnButtonClickCvsUp)
		cvsUaktualnijZrodlaButton.grid(column=1,row=0)
		buttonFrame.grid(column=0,columnspan=2,row=2,sticky='ew')
		

		####################################
		#montowanie
		####################################
		self.montFrame = tkinter.ttk.LabelFrame(self, text=u'Montowanie i edycja')
		self.montFrame.grid(column=0, row=3)
		
		#cityindex
		#self.mdmMontDemontOptions.montDemontOptions['cityidx']
		#self.cityidx= tkinter.BooleanVar()
		#self.cityidx.set(False)
		self.montOptionCityIdxCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Obsługa indeksu miast',
																variable=self.mdmMontDemontOptions.montDemontOptions['cityidx'],
																onvalue=True, offvalue=False)
		self.montOptionCityIdxCheckbutton.grid(column=0, row=0, sticky='W')
		
		#pliki adresow
		#self.adrfile = tkinter.BooleanVar()
		#self.adrfile.set(False)
		self.montOptionAdrCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij adresy',
															variable=self.mdmMontDemontOptions.montDemontOptions['adrfile'],
															onvalue=True, offvalue=False)
		self.montOptionAdrCheckbutton.grid(column=1, row=0, sticky='W')
		
		#szlaki
		#self.noszlaki = tkinter.BooleanVar()
		#self.noszlaki.set(False)
		self.montOptionNoszlakiCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij szlaki',
																variable=self.mdmMontDemontOptions.montDemontOptions['noszlaki'],
																onvalue=False, offvalue=True)
		self.montOptionNoszlakiCheckbutton.grid(column=0, row=1, sticky='W')

		#miasta
		#self.nocity = tkinter.BooleanVar()
		#self.nocity.set(False)
		self.montOptionNocityCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij miasta',
																variable=self.mdmMontDemontOptions.montDemontOptions['nocity'],
																onvalue=False, offvalue=True)
		self.montOptionNocityCheckbutton.grid(column=1, row=1, sticky='W')

		#punkty pnt
		#self.nopnt = tkinter.BooleanVar()
		#self.nopnt.set(False)
		self.montOptionNopntCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Uwzględnij punkty',
																variable=self.mdmMontDemontOptions.montDemontOptions['nopnt'],
																onvalue=False, offvalue=True)
		self.montOptionNopntCheckbutton.grid(column=0, row=2, sticky='W')

		#sumy kontrolne plikow
		#self.monthash= tkinter.BooleanVar()
		#self.monthash.set(False)
		self.montOptionNohashCheckbutton = tkinter.ttk.Checkbutton(self.montFrame, text=u'Generuj sumy kontrolne',
																variable=self.mdmMontDemontOptions.montDemontOptions['monthash'],
																onvalue=False, offvalue=True)
		self.montOptionNohashCheckbutton.grid(column=1, row=2, sticky='W')
		
		#extratypes
		#self.extratypes= tkinter.BooleanVar()
		#self.extratypes.set(False)
		self.montOptionExtratypesCheckbutton = tkinter.ttk.Checkbutton(self.montFrame,text=u'Specjalne traktowanie typów',
																	variable=self.mdmMontDemontOptions.montDemontOptions['extratypes'],
																	onvalue=True, offvalue=False)
		self.montOptionExtratypesCheckbutton.grid(column=0,row=3,sticky='W')
		
		#granice lokalne
		#self.graniceczesciowe=tkinter.BooleanVar()
		#self.graniceczesciowe.set(False)
		self.montOptionGraniceCzescioweCheckbutton = tkinter.ttk.Checkbutton(self.montFrame,text=u'Granice częściowe',
																	variable=self.mdmMontDemontOptions.montDemontOptions['graniceczesciowe'],
																	onvalue=True, offvalue=False)
		self.montOptionGraniceCzescioweCheckbutton.grid(column=1,row=3,sticky='W')
		
		self.montButton = tkinter.ttk.Button(self.montFrame, text=u'Montuj',command=self.OnButtonClickMont,state='disabled')
		self.montButton.grid(column=0, row=4)
		createToolTip(self.montButton, 'LPM - montuje mapę\nCtrl+PPM - odblokowuje przycisk\nCtrl+LPM - montuje mapę i uruchamia MapEdit z mapą')

		self.editButton = ButtonZaleznyOdWynik(self.montFrame, self.Zmienne.KatalogRoboczy,text=u'Edytuj',command=self.OnButtonClickEdit)
		self.editButton.bind('<Button-3>',self.OnButtonClickEdit2)
		self.editButton.grid(column=1,row=4)
		createToolTip(self.editButton, 'LPM - uruchamia podstawowy MapEdit z mapą\nPPM - uruchamia alternatywny MapEdit z mapą')
		
		#####################################
		#demontowanie
		#####################################
		
		self.demontFrame = tkinter.ttk.LabelFrame(self, text=u'Sprawdzanie i demontaż')
		self.demontFrame.grid(column=1, row=3)
		
		#obsługa indeksu miast
		self.demontOptionCityIdxCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame,text=u'Obsługa indeksu miast',
																	variable=self.mdmMontDemontOptions.montDemontOptions['cityidx'],
																	onvalue=True,offvalue=False)
		self.demontOptionCityIdxCheckbutton.grid(column=0, row=0, sticky='W')

		#obsługa sum kontrolnych
		#self.demonthash= tkinter.BooleanVar()
		#self.demonthash.set(False)
		self.demontOptionNohashCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame,text=u'Sprawdzaj sumy kontrolne',
																	variable=self.mdmMontDemontOptions.montDemontOptions['demonthash'],
																	onvalue=False, offvalue=True)
		self.demontOptionNohashCheckbutton.grid(column=0, row=1, sticky='W')
		
		#automatyczny rozkład poi
		#self.autopoi = tkinter.BooleanVar()
		#self.autopoi.set(False)
		self.demontOptionAutopoiLabel = tkinter.ttk.Checkbutton(self.demontFrame, text=u'Automatyczny rozkład poi',
															variable=self.mdmMontDemontOptions.montDemontOptions['autopoi'],
															onvalue=True, offvalue=False)
		self.demontOptionAutopoiLabel.grid(column=0, row=2, sticky='W')

		#zaokrąglanie
		#self.X = tkinter.StringVar()
		#self.X.set('0')
		self.demontOptionZaokraglanieRadio0 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Nie zaokrąglaj',
																	variable=self.mdmMontDemontOptions.montDemontOptions['X'], value='0')
		self.demontOptionZaokraglanieRadio0.grid(column=1, row=0, sticky='W')
		self.demontOptionZaokraglanieRadio5 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Zaokrąglij do 5 cyfr',
																	variable=self.mdmMontDemontOptions.montDemontOptions['X'], value='5')
		self.demontOptionZaokraglanieRadio5.grid(column=1, row=1, sticky='W')
		self.demontOptionZaokraglanieRadio6 = tkinter.ttk.Radiobutton(self.demontFrame, text=u'Zaokrąglij do 6 cyfr',
																	variable=self.mdmMontDemontOptions.montDemontOptions['X'], value='6')
		self.demontOptionZaokraglanieRadio6.grid(column=1, row=2, sticky='W')
		
		#extratypes
		self.demontOptionExtratypesCheckbutton = tkinter.ttk.Checkbutton(self.demontFrame,text=u'Specjalne traktowanie typów',
																	variable=self.mdmMontDemontOptions.montDemontOptions['extratypes'],
																	onvalue=True, offvalue=False)
		self.demontOptionExtratypesCheckbutton.grid(columnspan=2,row=3,sticky='W')

		#przycisk demontuj
		self.demontButton = ButtonZaleznyOdWynik(self.demontFrame, self.Zmienne.KatalogRoboczy,text=u'Demontuj',command=self.OnButtonClickDemont)
		self.demontButton.grid(column=1, row=4)
		
		#przycisk sprawdź
		self.sprawdzButton = ButtonZaleznyOdWynik(self.demontFrame,self.Zmienne.KatalogRoboczy,text=u'Sprawdź błędy',command=self.OnButtonClickSprawdz)
		self.sprawdzButton.grid(column=0,row=4)
		createToolTip(self.sprawdzButton, 'LPM - uruchamia sprawdzanie błędów\nPPM - czyści okno błędów')


		########################################################
		#zmienione pliki do wyswietlenia, obejrzenia itd
		########################################################
	
		self.diffFrame=tkinter.ttk.LabelFrame(self,text=u'Zmienione pliki')
		self.diffFrame.grid(columnspan=2,row=4)
		
		diffScrollY=AutoScrollbar(self.diffFrame)
		diffScrollY.grid(column=1,row=0,sticky='NS')
		newtags=diffScrollY.bindtags()+('movewheel',)
		diffScrollY.bindtags(newtags)
		
		diffScrollX=AutoScrollbar(self.diffFrame,orient='horizontal')
		diffScrollX.grid(column=0,row=1,sticky='EW')
		
		self.diffCanvas = tkinter.Canvas(self.diffFrame,yscrollcommand=diffScrollY.set,xscrollcommand=diffScrollX.set,width=835,height=160,highlightthickness=0)
		self.diffCanvas.grid(column=0,row=0,sticky='nsew')
		self.diffCanvas.bind_class('movewheel',"<MouseWheel>", self._on_mousewheediffCanvas)
		self.diffCanvas.bind_class('movewheel',"<Button-4>", self._on_mousewheediffCanvas)
		self.diffCanvas.bind_class('movewheel',"<Button-5>", self._on_mousewheediffCanvas)
		newtags=self.diffCanvas.bindtags()+('movewheel',)
		self.diffCanvas.bindtags(newtags)
		diffScrollY.config(command=self.diffCanvas.yview)
		diffScrollX.config(command=self.diffCanvas.xview)
		
		#ramka w canvas
		self.frameInDiffCanvas=ListaPlikowFrame(self.diffCanvas,self.Zmienne)
		self.frameInDiffCanvas.grid(column=0,row=0)
		newtags=self.frameInDiffCanvas.bindtags()+('movewheel',)
		self.frameInDiffCanvas.bindtags(newtags)
		
		style1=tkinter.ttk.Style()
		style1.configure('Helvetica1.TLabel',font=('Helvetica',9))
		plikLabel=tkinter.ttk.Label(self.frameInDiffCanvas,text=u'Pliki',borderwidth=4,relief='raised',width=60,anchor='w',style='Helvetica1.TLabel')
		plikLabel.grid(row=0,column=0)
		newtags=plikLabel.bindtags()+('movewheel',)
		plikLabel.bindtags(newtags)
		
		dodanoLabel=tkinter.ttk.Label(self.frameInDiffCanvas,text=u'Dodano',borderwidth=4,relief='raised',width=10,anchor='center',style='Helvetica1.TLabel')
		dodanoLabel.grid(row=0,column=1)
		newtags=dodanoLabel.bindtags()+('movewheel',)
		dodanoLabel.bindtags(newtags)
		
		skasowanoLabel=tkinter.ttk.Label(self.frameInDiffCanvas,text=u'Skasowano',borderwidth=4,relief='raised',width=10,anchor='center',style='Helvetica1.TLabel')
		skasowanoLabel.grid(row=0,column=2)
		newtags=skasowanoLabel.bindtags()+('movewheel',)
		skasowanoLabel.bindtags(newtags)
		
		akcjeLabel=tkinter.ttk.Label(self.frameInDiffCanvas,text=u'Możliwe akcje',borderwidth=4,relief='raised',width=30,anchor='center',style='Helvetica1.TLabel')
		akcjeLabel.grid(row=0,columnspan=2,column=3)
		newtags=akcjeLabel.bindtags()+('movewheel',)
		akcjeLabel.bindtags(newtags)
		
		self.diffCanvas.create_window(0,0,anchor='ne', window=self.frameInDiffCanvas)
		self.diffCanvas.update_idletasks()
		self.diffCanvas.config(scrollregion=self.diffCanvas.bbox("all"))
		
		self.diffFrameApplyButtonVariable=tkinter.StringVar()
		if self.mdm_mode=='edytor':
			self.diffFrameApplyButtonVariable.set(u'Skopiuj pliki')
		else:
			self.diffFrameApplyButtonVariable.set(u'Utwórz plik zip')
		
		buttonFrame=tkinter.Frame(self.diffFrame)
		buttonFrame.grid_columnconfigure(0,weight=1)
		buttonFrame.grid_columnconfigure(1,weight=1)
		
		diffFrameApplyButton=tkinter.ttk.Button(buttonFrame,textvariable=self.diffFrameApplyButtonVariable,command=self.OnButtonClickApply)
		diffFrameApplyButton.grid(column=1,row=0)
		
		diffFrameCVSCommitButton=tkinter.ttk.Button(buttonFrame,text=u'Zatwierdź zmiany (cvs commit)',command=self.OnButtonClickCvsCommit)
		diffFrameCVSCommitButton.grid(column=0,row=0)
		buttonFrame.grid(column=0,row=2,sticky='ew')
		
		####################################################
		#stderr będą wyświetlane tutaj
		####################################################
		
		self.stderrFrame=tkinter.ttk.LabelFrame(self, text=u'Błędy')
		self.stderrFrame.grid(column=0, row=5,sticky='news')
		self.grid_columnconfigure(0,weight=1)
		self.grid_rowconfigure(5,weight=1)
		self.stderrFrame.grid_columnconfigure(0,weight=1)
		self.stderrFrame.grid_rowconfigure(0,weight=1)
		
		self.stderrText=stdOutstdErrText(self.stderrFrame,width=60,height=6,wrap='none',font=('Courier',8))
		self.stderrText.grid(column=0,row=0,sticky='news')
		self.stderrqueue=self.stderrText.inputqueue
		# Teraz dopiero można zbindować czyszczenie błędów
		self.sprawdzButton.bind('<Button-3>', self.stderrText.event_clear_all_event)
		
		####################################################
		#stdout będą wyświetlanu tutaj
		####################################################
		
		self.stdoutFrame=tkinter.ttk.LabelFrame(self, text=u'Komunikaty')
		self.stdoutFrame.grid(column=1, row=5,sticky='news')
		self.grid_columnconfigure(1,weight=1)
		self.stdoutFrame.grid_columnconfigure(0,weight=1)
		self.stdoutFrame.grid_rowconfigure(0,weight=1)
				
		
		self.stdoutText=stdOutstdErrText(self.stdoutFrame,width=60,height=6,wrap='none',font=('Courier',8))
		self.stdoutText.grid(column=0,row=0,sticky='news')

		self.stdoutqueue=self.stdoutText.inputqueue
		
		#self.stdoutText.configure(font=(size=10,))
		
		#rozkład obszarów i linii włącza się i wyłącza skrótem klawiaturowym, tutaj robię bind do tego
		self.bind_all("<Control-a><Control-o><Control-l>", self.selectUnselect_aol)
		# skrót klawiaturowy montuj
		self.bind("<Control-m>",self.montuj_shortcut)
		# skrót do demontuj
		self.bind("<Control-d>",self.demontuj_shortcut)
		# skrót do montuj a później edit
		self.bind("<E>",self.montuj_edit_shortcut)
		self.montButton.bind("<Control-Button-1>", self.montuj_edit_shortcut)
		# skrót do edytuj
		self.bind("<Control-e>",self.edit_shortcut)
		# skrót do aktywuj klawisz mont
		self.bind("<R>", self.aktywuj_montbutton)
		self.montButton.bind("<Control-Button-3>",self.aktywuj_montbutton)		
		# skrót do cvs up
		self.bind("<Control-u>", self.cvsUpShortcut)
		# skrót do sprawdź
		self.bind("<Control-s>", self.sprawdz_shortcut)
		# skrót do usuń zawartość katalogu roboczego
		self.bind("<Control-C>", self.czysc_shortcut)
		# skrót klawiaturowy do pomocy
		self.bind('<F1>', lambda event: self.skrotyKlawiaturowe())
		
	def sprawdzAktualnoscZrodelandPopupMessage(self):
		
		try:
			while 1:
					string = self.cvsstatusQueue.get_nowait()
					if string=='aktualne':
						pass
					else:
						tkinter.messagebox.showwarning(u'Nieaktualne źródła',u'Pliki na serwerze są nowsze niż te które montujesz. Powinieneś najpierw zaktualizować źródła.')

		except queue.Empty:
			pass
		self.after(100, self.sprawdzAktualnoscZrodelandPopupMessage)
		
		
	#bindowanie do skrótów klawiaturowych
	#włączanie i wyłączanie automatycznego rozkładu polylinii i polygonów
	def selectUnselect_aol(self,event):
		
		if event:
			aaa=self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].get()
			aaa=not aaa
			self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].set(aaa)
				
		if self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].get():
			self.autopolypoly.configure(background='lawn green')
		else:
			self.autopolypoly.configure(background='orange red')
	
	def montuj_shortcut(self,event):
		
		if (str(self.montButton['state']) != 'disabled'):
			self.OnButtonClickMont()
		return 0
		
	def demontuj_shortcut(self,event):
		if (str(self.demontButton['state']) != 'disabled'):
			self.OnButtonClickDemont()
		return 0

	def sprawdz_shortcut(self,event):
		if (str(self.sprawdzButton['state']) != 'disabled'):
			self.OnButtonClickSprawdz()
		
	def edit_shortcut(self,event):
		if (str(self.editButton['state']) != 'disabled'):
			self.OnButtonClickEdit()
		
	def montuj_edit_shortcut(self,event):
		if (str(self.montButton['state']) != 'disabled'):
			self.OnButtonClickMont()
			thread=threading.Thread(target=self.help_function_montuj_edit_shortcut, args=())
			thread.start()
	
	def help_function_montuj_edit_shortcut(self):
		while(os.path.isfile(self.Zmienne.KatalogRoboczy+'wynik.mp')):
			time.sleep(0.1)
		while(not os.path.isfile(self.Zmienne.KatalogRoboczy+'wynik.mp')):
			time.sleep(0.1)
		self.OnButtonClickEdit()
				
	
	def aktywuj_montbutton(self,event):
		self.MontButtonStateSet()
	
	def cvsUpShortcut(self,event):
		self.OnButtonClickCvsUp()
	
	def czysc_shortcut(self, event):
		self.args.wszystko=1
		self.args.stderrqueue=self.stderrqueue
		self.args.stdoutqueue=self.stdoutqueue
		mont_demont_py.czysc(self.args)
		
	
	# koniec bindowania do skrótów klawiaturowych

	
	def GenerujListeObszarow(self):
		args = Argumenty()
		style2=tkinter.ttk.Style()
		style2.configure('Helvetica.TCheckbutton',font=('Helvetica',9))
		listaNazwObszarow = mont_demont_py.listujobszary(args)
		for a in self.regionCheckButtonDictionary.keys():
			self.regionCheckButtonDictionary[a].destroy()
		self.regionVariableDictionary={}
		self.regionCheckButtonDictionary={}
		#self.regionContexMenuDictionary={}
		
		for aaa in range(len(listaNazwObszarow)):
			self.regionVariableDictionary[listaNazwObszarow[aaa]] = tkinter.IntVar()
			nazwaobszaru=listaNazwObszarow[aaa].split('-',1)[1]
			if len(nazwaobszaru)>13:
				nazwaobszaru=nazwaobszaru[:12]
			self.regionCheckButtonDictionary[listaNazwObszarow[aaa]] = myCheckbutton(self.regionyFrameInCanvas, args, listaNazwObszarow[aaa],text=nazwaobszaru,
																					zmienna = self.regionVariableDictionary[listaNazwObszarow[aaa]],
																					regionVariableDictionary=self.regionVariableDictionary,
																					variable=self.regionVariableDictionary[listaNazwObszarow[aaa]],
																					onvalue=1, offvalue=0,style='Helvetica.TCheckbutton',
																					command=self.MontButtonStateSet)
			#self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].regionVariableDictionary=self.regionVariableDictionary
			newtags=self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].bindtags()+('kolkomyszkiregiony',)
			self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].bindtags(newtags)
			
			self.regionCheckButtonDictionary[listaNazwObszarow[aaa]].grid(column=aaa % 8, row=aaa // 8,sticky='W')
			

	#prawdopodobnie do usuniecia, chyba nadmiar
	#def show_menu(self, e):
	#	self.tk.call("tk_popup", self.menu, e.x_root, e.y_root)
		
		
	def _on_mousewheelregionyCanvas(self, event):
		
		if self.os=='Linux':
			if event.num==4:
				self.regionyCanvas.yview_scroll(int(-1), "units")
			elif event.num==5:
				self.regionyCanvas.yview_scroll(int(1), "units")
		elif self.os=='Windows':
			self.regionyCanvas.yview_scroll(int(-1*(event.delta/120)), "units")
		
	def _on_mousewheediffCanvas(self, event):
		
		if self.os=='Linux':
			if event.num==4:
				self.diffCanvas.yview_scroll(int(-1), "units")
			elif event.num==5:
				self.diffCanvas.yview_scroll(int(1), "units")
		elif self.os=='Windows':
			self.diffCanvas.yview_scroll(int(-1*(event.delta/120)), "units")
		
	def MontButtonStateSet(self):
		self.args.obszary=[a for a in self.regionVariableDictionary.keys() if self.regionVariableDictionary[a].get()==1]
		if len(self.args.obszary)>0:
			self.montButton.configure(state='normal')
		else:
			self.montButton.configure(state='disabled')
		return 0
		
	
	def OnButtonClickOdswiezListeObszarow(self):
		
		self.GenerujListeObszarow()
		self.MontButtonStateSet()

	def OnButtonClickApply(self):
		#tymczasowo, dopoki nie dorobie przesylania pomiedzy watkami
		#self.plikiDoCVS=[]
		
		if self.mdm_mode!='edytor' and len(self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania)>0:
			plikzipname='UMP'+str(datetime.datetime.now().year)+str(datetime.datetime.now().month)+str(datetime.datetime.now().day)+'_'+str(datetime.datetime.now().hour)+'-'+str(datetime.datetime.now().minute)+'.zip'
			plikzip=zipfile.ZipFile(self.Zmienne.KatalogRoboczy+plikzipname,'w')
		for a in self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania.keys():
			#zmienna IntVar nie moze byc odczytana bezposrednio, trzeba poprzez funkcje get()
			if self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].get() == 1:
				
				#przed kopiowaniem nalezy sprawdzic czy dany plik to naprawde dany plik, czy moze ktos 
				# w miedzyczasie go zmienil, wykorzystamy do tego hashe dla plikow
				try:
					
					with open(self.Zmienne.KatalogzUMP+a,'rb') as f:
						if hashlib.md5(f.read()).hexdigest()== self.frameInDiffCanvas.nazwapliku_Hash[a]:
							if self.mdm_mode=='edytor':
								#shutil.copy(self.Zmienne.KatalogRoboczy+a.replace('/','-'),self.Zmienne.KatalogzUMP+a.replace('/','\\'))
								#self.stdoutqueue.put('%s-->%s\n'%(a.replace('/','-'),self.Zmienne.KatalogzUMP+a.replace('/','\\')))
								#print('%s-->%s'%(a.replace('/','-'),self.Zmienne.KatalogzUMP+a.replace('/','\\')))
								shutil.copy(self.Zmienne.KatalogRoboczy+a.replace('/','-'),self.Zmienne.KatalogzUMP+a)
								self.stdoutqueue.put('%s-->%s\n'%(a.replace('/','-'),self.Zmienne.KatalogzUMP+a))
								print('%s-->%s'%(a.replace('/','-'),self.Zmienne.KatalogzUMP+a))
								if a not in self.plikiDoCVS:
									self.plikiDoCVS.append(a)
							else:									
								plikzip.write(self.Zmienne.KatalogRoboczy+a.replace('/','-')+'.diff',a.replace('/','-')+'.diff')
								self.stdoutqueue.put('%s-->%s\n'%(a.replace('/','-'),plikzipname))
								print('%s-->%s'%(a.replace('/','-'),plikzipname))
							b=self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
							self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
							self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='lawn green')
							self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
						else:
							self.stderrqueue.put(u'Suma kontrolna pliku %s\nnie zgadza sie.\nPróbuję nałożyć łatki przy pomocy patch.\n'%a)
							patch_result = self.patchExe(a.replace('/','-') + '.diff')
							b = self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
							if patch_result == 0:
								self.stdoutqueue.put(u'Łatka nałożona bezbłędnie.\n')
								self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(
									background='lawn green')
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
					if a.find('_nowosci')>=0:
						print(a)
						plikzip.write(self.Zmienne.KatalogRoboczy+a,a)
						self.stdoutqueue.put('%s-->%s\n'%(a,plikzipname))
						print('%s-->%s'%(a,plikzipname))
						b=self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
						self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
						self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='lawn green')
						self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
					else:
						self.stderrqueue.put(u'Nie moge odnaleźć pliku %s. Musisz go skopiować ręcznie.\n'%a)
						print(u'Nie moge odnaleźć pliku %s. Musisz go skopiować ręcznie.'%a,file=sys.stderr)
						b=self.frameInDiffCanvas.listaNazwPlikowDoObejrzenia.index(a)
						self.frameInDiffCanvas.skopiujCheckButtonPlikowOknoZmienionePliki[b].configure(state='disabled')
						self.frameInDiffCanvas.listaPlikowOknoZmienionePliki[b].configure(background='red')
						self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania[a].set(0)
				#c:\\ump\roboczy\UMP-PL-Leszno\-src\-POI-Leszno.sklepy.pnt
		
		if self.mdm_mode!='edytor' and len(self.frameInDiffCanvas.listaPlikowDiffDoSkopiowania)>0:
			plikzip.close()

	#obsługa poleceń cvs
	def patchExe(self, pliki_diff):
		self.args.pliki_diff = [pliki_diff]
		self.args.stderrqueue = self.stderrqueue
		self.args.stdoutqueue = self.stdoutqueue
		self.args.katrob = self.Zmienne.KatalogRoboczy
		a = mont_demont_py.patch(self.args)
		return a


	def OnButtonClickCvsUp(self):
		obszary=[]
		obszarywszystkie=[]
		for aaa in self.regionVariableDictionary.keys():
			obszarywszystkie.append(aaa)
			if self.regionVariableDictionary[aaa].get()==1:
				obszary.append(aaa)
		if not obszary:
			obszary=obszarywszystkie
			obszary.append('narzedzia')
		else:
			obszary.append('narzedzia')
			
		if os.path.isfile(self.Zmienne.KatalogRoboczy+'wynik.mp'):
			if tkinter.messagebox.askyesno(u'Plik wynik.mp istnieje',u'W katalogu roboczym istniej plik wynik.mp.\nCvs up może uniemożliwić demontaż. Czy kontynuować pomimo tego?'):
				doCVS=cvsOutputReceaver(self,obszary,'','up')
			else:
				pass
		else:
			doCVS=cvsOutputReceaver(self,obszary,'','up')
		
		#doCVS=cvsOutputReceaver(self,obszary,'','up')
		
	
	def OnButtonClickCvsCommit(self):
		
		if len(self.plikiDoCVS)>0:
			oknodialogowe=cvsDialog(self,self.plikiDoCVS,title=u'Prześlij pliki do repozytorium cvs')
			if oknodialogowe.iftocommit=='tak':
				doCVS=cvsOutputReceaver(self,self.plikiDoCVS,oknodialogowe.message,'ci')
				self.plikiDoCVS=doCVS.uncommitedfiles[:]
			else:
				pass

	def cvsSprawdzAktualnoscMontowanychObszarow(self,*obszary):
		Needs_Patch=0
		Zmienne=mont_demont_py.UstawieniaPoczatkowe('wynik.mp')
		CVSROOT='-d:pserver:'+Zmienne.CvsUserName+'@cvs.ump.waw.pl:/home/cvsroot'
		subprocess_args=['cvs','-q', CVSROOT,'status']
		for a in obszary:
			subprocess_args.append(a)
				
		subprocess_args.append('narzedzia/granice.txt')
		
		os.chdir(Zmienne.KatalogzUMP)
		process = subprocess.Popen(subprocess_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		for a in process.stdout.readlines():
			if a.decode(Zmienne.Kodowanie).find('Needs Patch')>0:
				Needs_Patch=1
				print(a.decode(Zmienne.Kodowanie))
		if Needs_Patch:
			self.cvsstatusQueue.put('nieaktualne')
		else:
			self.cvsstatusQueue.put('aktualne')
		return 0
		
		
	def OnButtonClickMont(self):

		#czyscimy liste plikow ktore pozostaly z poprzedniego demontazu
		self.frameInDiffCanvas.WyczyscPanelzListaPlikow()
		
		self.args.obszary=[]

		
		for aaa in self.regionVariableDictionary.keys():
			if self.regionVariableDictionary[aaa].get()==1:
				self.args.obszary.append(aaa)
						
		self.args.plikmp='wynik.mp'
		#self.args.adrfile=self.adrfile.get()
		self.args.adrfile=self.mdmMontDemontOptions.montDemontOptions['adrfile'].get()
		#self.args.cityidx=self.cityidx.get()
		self.args.cityidx=self.mdmMontDemontOptions.montDemontOptions['cityidx'].get()
		
		#self.args.notopo=self.notopo.get()
		#self.args.notopo=self.mdmMontDemontOptions.montDemontOptions['notopo'].get()
		
		#self.args.nocity=self.nocity.get()
		self.args.nocity=self.mdmMontDemontOptions.montDemontOptions['nocity'].get()
		#self.args.noszlaki=self.noszlaki.get()
		self.args.noszlaki=self.mdmMontDemontOptions.montDemontOptions['noszlaki'].get()
		#self.args.nopnt=self.nopnt.get()
		self.args.nopnt=self.mdmMontDemontOptions.montDemontOptions['nopnt'].get()
		#self.args.hash=self.monthash.get()
		self.args.hash=self.mdmMontDemontOptions.montDemontOptions['monthash'].get()
		#self.args.extratypes=self.extratypes.get()
		self.args.extratypes=self.mdmMontDemontOptions.montDemontOptions['extratypes'].get()
		#self.args.graniceczesciowe=self.graniceczesciowe.get()
		self.args.graniceczesciowe=self.mdmMontDemontOptions.montDemontOptions['graniceczesciowe'].get()
		# ustawiamy tryb nieosmandowy, jest on uruchamiany tylko na potrzeby konwersji do OSNAnda
		self.args.trybosmand = 0
		
		self.args.stderrqueue=self.stderrqueue
		self.args.stdoutqueue=self.stdoutqueue
		
		
		#_thread.start_new_thread(mont_demont_py.montujpliki,(self.args,))
		thread=threading.Thread(target=mont_demont_py.montujpliki, args=(self.args,))
		thread.start()
		
		thread1=threading.Thread(target=self.cvsSprawdzAktualnoscMontowanychObszarow,args=(self.args.obszary))
		thread1.start()
		
		self.montButton.configure(state='disabled')
	
	def OnButtonClickEdit(self):
		self.args.plikmp=None
		self.args.mapedit2=False
		self.args.stderrqueue=self.stderrqueue
		thread=threading.Thread(target=mont_demont_py.edytuj, args=(self.args,))
		thread.start()
		
	def OnButtonClickEdit2(self,event):
		if os.path.isfile(self.Zmienne.KatalogRoboczy+'wynik.mp'):
			self.args.plikmp=None
			self.args.mapedit2=True
			self.args.stderrqueue=self.stderrqueue
			thread=threading.Thread(target=mont_demont_py.edytuj, args=(self.args,))
			thread.start()
	
	def OnButtonClickDemont(self):
		self.frameInDiffCanvas.WyczyscPanelzListaPlikow()
		self.args.plikmp=None
		self.args.katrob=None
		self.args.umphome=None
		
		#autoobszary
		self.args.autopolypoly=self.mdmMontDemontOptions.montDemontOptions['autopolypoly'].get()
		
		#self.args.X=self.X.get()
		self.args.X=self.mdmMontDemontOptions.montDemontOptions['X'].get()
		#self.args.autopoi=self.autopoi.get()
		self.args.autopoi=self.mdmMontDemontOptions.montDemontOptions['autopoi'].get()
		#self.args.cityidx=self.cityidx.get()
		self.args.cityidx=self.mdmMontDemontOptions.montDemontOptions['cityidx'].get()
		#self.args.hash=self.demonthash.get()
		self.args.hash=self.mdmMontDemontOptions.montDemontOptions['demonthash'].get()
		#self.args.extratypes=self.extratypes.get()
		self.args.extratypes=self.mdmMontDemontOptions.montDemontOptions['extratypes'].get()
		self.montButton.configure(state='disabled')
		#self.demontButton.configure(state='disabled')
		
		#_thread.start_new_thread(mont_demont_py.demontuj,(self.args,))
		my_queue = queue.Queue()
		#self.args.queue=my_queue
		self.args.queue=self.frameInDiffCanvas.queueListaPlikowFrame
		self.args.stderrqueue=self.stderrqueue
		self.args.stdoutqueue=self.stdoutqueue
		# kolejka do informowania guzika że właśnie działa i żeby się wyłączył
		self.args.buttonqueue = self.demontButton.statusqueue
		thread=threading.Thread(target=mont_demont_py.demontuj,args=(self.args,))
		#thread=threading.Thread(target=self.demont,args=(my_queue,))
		thread.start()
		#thread.join()
		#thread1=threading.Thread(target=self.wyswietlListePlikow,args=(my_queue,))
		#thread1.start()
		#for a in my_queue.get():
		#	print(a)
		self.frameInDiffCanvas.update_idletasks()
		self.diffCanvas.config(scrollregion=self.diffCanvas.bbox("all"))
		
	def OnButtonClickSprawdz(self):
		self.args.plikmp=None
		self.args.stderrqueue=self.stderrqueue
		self.args.stdoutqueue=self.stdoutqueue
		self.args.sprawdzbuttonqueue = self.sprawdzButton.statusqueue
		thread=threading.Thread(target=mont_demont_py.sprawdz, args=(self.args,))
		thread.start()
		thread1=threading.Thread(target=mont_demont_py.sprawdz_numeracje, args=(self.args,))
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
