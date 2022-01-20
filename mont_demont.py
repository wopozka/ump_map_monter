#!/usr/bin/env python3
# -*- coding: iso-8859-2 -*-
# Skrypt pythonowy montujacy.

import string
import sys
if sys.version_info[0] < 3:
    print('\nUzywasz pythona w wersji %s.%s.%s\n' % (sys.version_info[0], sys.version_info[1], sys.version_info[2]),
          file=sys.stderr)
    print('Wymagany jest python w wersji conajmniej 3.\n', file=sys.stderr)
    sys.exit(1)
import os
import os.path
import argparse
import glob
import hashlib
import difflib
import subprocess
import tempfile
import shutil
import kdtree
import znajdz_bledy_numeracji
from collections import OrderedDict
from collections import defaultdict


class errOutWriter(object):
    def __init__(self, args):
        self.args = args

    def stderrorwrite(self, string):
        if hasattr(self.args, 'stderrqueue'):
            if not string.endswith('\n'):
                string += '\n'
            if string.startswith('\n'):
                string = string.lstrip()
            self.args.stderrqueue.put(string)
        else:
            print(string, file=sys.stderr)

    def stdoutwrite(self, string):
        if hasattr(self.args, 'stdoutqueue'):
            if not string.endswith('\n'):
                string += '\n'
            if string.startswith('\n'):
                string = string.lstrip()
            self.args.stdoutqueue.put(string)
        else:
            print(string, file=sys.stdout)


class TestyPoprawnosciDanych(object):
    def __init__(self, args):
        # Typ dla roznych drog, ktore powinny posiadac wpis Miasto=
        self.error_out_writer = errOutWriter(args)
        self.typy_label_z_miastem = [
            '0x1',  # motorway
            '0x2',  # principal highway
            '0x3',  # principal highway
            '0x4',  # arterial road
            '0x5',  # collector road
            '0x6',  # residential street
            '0x7',  # alleway
            '0x8',  # highway ramp, low speed
            '0x9',  # highway ramp, hight speed
            '0xa',  # unpaved road
            '0xb',  # highway connector
            '0xc',  # roundabout
            '0x16',  # walkway]
            # '0x1a',#ferry
            # ' 0x1b'#water or rail ferry
        ]
        self.typy_data_0_only = self.typy_label_z_miastem + ['0x14', '0x10e10', '0x10e14', '0x10e15']
        self.literyWojewodztw = [
            'B',  # województwo podlaskie
            'C',  # województwo kujawsko-pomorskie
            'D',  # województwo dolnolšskie
            'E',  # województwo łódzkie
            'F',  # województwo lubuskie
            'G',  # województwo pomorskie
            'K',  # województwo małopolskie
            'L',  # województwo lubelskie
            'N',  # województwo warmińsko-mazurskie
            'O',  # województwo opolskie
            'P',  # województwo wielkopolskie
            'R',  # województwo podkarpackie
            'S',  # województwo lšskie
            'T',  # województwo więtokrzyskie
            'W',  # województwo mazowieckie
            'Z',  # województwo zachodniopomorskie
        ]
        self.ruchLewostronny = ['UMP-GB']

    def sprawdz_label_dla_drogi_z_numerami(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] in ('[POLYGON]', '[POI]',):
            return ''
        if 'Label' in dane_do_zapisu and dane_do_zapisu['Label']:
            return ''
        if 'adrLabel' in dane_do_zapisu and dane_do_zapisu['adrLabel']:
            return ''
        if any(a.startswith('Numbers') for a in dane_do_zapisu):
            if 'Label' not in dane_do_zapisu or ('Label' in dane_do_zapisu and not dane_do_zapisu['Label']):
                data = [a for a in dane_do_zapisu if a.startswith('Data')]
                self.error_out_writer.stderrorwrite('Numeracja drogi bez Label %s' % dane_do_zapisu[data[0]])
                return 'brak_label_przy_numeracji'
            return ''

    def sprawdzData0Only(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] == '[POLYGON]':
            return ''
        data = [a for a in dane_do_zapisu if a.startswith('Data')]
        if dane_do_zapisu['POIPOLY'] == '[POI]' and len(data) > 1:
            self.error_out_writer.stderrorwrite('Data 1 albo wyzej dla drogi/kolei %s' % dane_do_zapisu[data[0]])
            return 'Data1'
        elif dane_do_zapisu['Type'] in self.typy_data_0_only:
            if len(data) == 1 and data[0].startswith('Data0'):
                return ''
            else:
                self.error_out_writer.stderrorwrite('Data 1 albo wyzej dla drogi/kolei %s' % dane_do_zapisu[data[0]])
                return 'Data1'
        else:
            return ''

    def sprawdz_label_dla_poi(self, dane_do_zapisu):
        if 0x2900 <= int(dane_do_zapisu['Type'], 16) <= 0x3008:
            if 'Label' not in dane_do_zapisu or ('Label' in dane_do_zapisu and not dane_do_zapisu['Label']):
                szerokosc, dlugosc = \
                    [dane_do_zapisu[data] for data in dane_do_zapisu if data.startswith('Data')][0][1:-1].split(',')
                self.error_out_writer.stderrorwrite(
                    '\nBrak Label dla punktu o wspolrzednych %s,%s.\nWyszukiwanie nie będzie działać.'
                    % (szerokosc, dlugosc))
                return 'brak_label'
            elif 'Miasto' not in dane_do_zapisu or ('Miasto' in dane_do_zapisu and not dane_do_zapisu['Miasto']):
                szerokosc, dlugosc = \
                    [dane_do_zapisu[data] for data in dane_do_zapisu if data.startswith('Data')][0][1:-1].split(',')
                self.error_out_writer.stderrorwrite(
                    '\nBrak Miasto dla punktu o wspolrzednych %s,%s.\nWyszukiwanie nie będzie działać.'
                    % (szerokosc, dlugosc))
                return 'brak_miasto'
            return ''
        elif dane_do_zapisu['Type'] in City.rozmiar2Type:
            if 'Label' not in dane_do_zapisu or ('Label' in dane_do_zapisu and not dane_do_zapisu['Label']):
                szerokosc, dlugosc = \
                    [dane_do_zapisu[data] for data in dane_do_zapisu if data.startswith('Data')][0][1:-1].split(',')
                self.error_out_writer.stderrorwrite(
                    '\nBrak nazwy Miasta dla punktu o wspolrzednych %s,%s.' % (szerokosc, dlugosc))
                return 'brak_nazwy_miasta'

    def sprawdz_label_dla_poly(self, dane_do_zapisu):
        if dane_do_zapisu['Type'] in self.typy_label_z_miastem and dane_do_zapisu['POIPOLY'] == '[POLYLINE]':
            # gdy label w nawiasach klamrowych
            if dane_do_zapisu['Label'].startswith('{'):
                return ''
            elif dane_do_zapisu['Label'].startswith('~'):
                Label1 = dane_do_zapisu['Label'].split(' ', 1)
                if len(Label1) == 1:
                    return ''
                else:
                    if Label1[1].startswith('{') and Label1[1].endswith('}'):
                        return ''
                    wspolrzedne = dane_do_zapisu[[b for b in dane_do_zapisu if b.startswith('Data')][0]].split('),(')[
                        -1].rstrip(')')
                    self.error_out_writer.stderrorwrite(('Brak Miasto= dla {!s} {!s}'.format(dane_do_zapisu['Label'],
                                                                                             wspolrzedne)))
                    return 'miasto potrzebne'
            # w przypadku gdyby nazwa zaczynala sie mala litera
            else:
                wspolrzedne = dane_do_zapisu[[b for b in dane_do_zapisu if b.startswith('Data')][0]].split('),(')[
                    -1].rstrip(')')
                self.error_out_writer.stderrorwrite(('Brak Miasto= dla {!s} {!s}'.format(dane_do_zapisu['Label'],
                                                                                         wspolrzedne)))
                return 'miasto potrzebne'
        else:
            return ''

    @staticmethod
    def clockwisecheck(wspolrzedne):
        """
        funkcja sprawdza wielokat jest w prawo czy w lewo. Jesli kreci sie w lewo zwraca -1,
        jesli kreci sie w prawo zwraca 1
        """
        Pole = 0
        wspolrzedne = wspolrzedne.lstrip('(')
        wspolrzedne = wspolrzedne.rstrip(')')
        c = wspolrzedne.split('),(')
        # rondo musi byc zamkniete wiec powtarzamy ostatni element
        if c[0] != c[-1]:
            c.append(c[0])
        n = int(len(c) - 1)
        XY = []

        for bbb in c:
            aaa = bbb.split(',')
            XY.append(float(aaa[0]))
            XY.append(float(aaa[1]))
        for i in range(n):
            x1 = XY[(2 * i)]
            y1 = XY[(2 * i + 1)]
            x2 = XY[(2 * i + 2)]
            y2 = XY[(2 * i + 3)]
            Pole = Pole + (x1 * y2 - x2 * y1)
        if Pole > 0:
            return 1
        elif Pole < 0:
            return -1
        elif Pole == 0:
            return 0

    def sprawdzKierunekRonda(self, dane_do_zapisu):
        Data = dane_do_zapisu[[b for b in dane_do_zapisu if b.startswith('Data')][0]]
        wspolrzedneOstPara = Data.split('),(')[-1].rstrip(')')
        if 'DirIndicator' not in dane_do_zapisu:
            print(dane_do_zapisu)
            self.error_out_writer .stderrorwrite(('Brak ustawionej kierunkowosci dla ronda {!s}'.format(wspolrzedneOstPara)))
            return 'brak_DirIndicator'
        if dane_do_zapisu['Plik'].startswith('_nowosci'):
            self.error_out_writer.stderrorwrite('Nie moge sprawdzic kierunkowosci bo rondo w _nowosci.txt')
            return 'NOWOSCI.TXT'
        ruch_lewostronny = 0

        # sprawdz kierunek, dla a=1 kierunek w prawo, dla a=-1 kierunek w lewo, dla a = 0 nie mozna okreslic kierunku
        a = self.clockwisecheck(Data)
        for b in self.ruchLewostronny:
            if dane_do_zapisu['Plik'].startswith(b):
                ruch_lewostronny = 1
        if a == -1 and not ruch_lewostronny:
            return ''
        elif a == 1 and ruch_lewostronny:
            return ''
        elif a == 0:
            self.error_out_writer .stderrorwrite(
                'Nie moge okreslic kierunku ronda {!s}.\nZbyt malo punktow.'.format(wspolrzedneOstPara))
            return 'NIE_WIEM'
        else:
            self.error_out_writer.stderrorwrite('Rondo z odwrotnym kierunkiem {!s}'.format(wspolrzedneOstPara))
            return 'ODWROTNE'

    def testy_poprawnosci_danych_poi(self, dane_do_zapisu):
        self.sprawdzData0Only(dane_do_zapisu)
        self.sprawdz_label_dla_poi(dane_do_zapisu)

    def testy_poprawnosci_danych_txt(self, dane_do_zapisu):
        wyniki_testow = list()
        wyniki_testow.append(self.testuj_kierunkowosc_ronda(dane_do_zapisu))
        wyniki_testow.append(self.sprawdzData0Only(dane_do_zapisu))
        wyniki_testow.append(self.testuj_label(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_label_dla_drogi_z_numerami(dane_do_zapisu))
        if wyniki_testow:
            return ','.join(a for a in wyniki_testow if a)
        return ''

    def testuj_kierunkowosc_ronda(self, dane_do_zapisu):
        if dane_do_zapisu['Type'] == '0xc' and dane_do_zapisu['POIPOLY'] == '[POLYLINE]':
            return self.sprawdzKierunekRonda(dane_do_zapisu)
        else:
            return ''

    def testuj_label(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] == '[POI]':
            return self.sprawdz_label_dla_poi(dane_do_zapisu)
        else:
            if 'Label' not in dane_do_zapisu:
                return ''
            if 'Miasto' not in dane_do_zapisu:
                return self.sprawdz_label_dla_poly(dane_do_zapisu)
        return ''

class PaczerGranicCzesciowych(object):
    def __init__(self, Zmienne, plik_z_granicami_do_testow=None):
        """
        Klasa obsluguje latanie granic czesciowych. Przy demontazu granic czesciowych dostajemy plik diff dla tylko
        granic czesciowych. Poniewaz mdm kopiuje pliki, dlatego nie ma jak skopiowac pliku z granicami czesciowymi
        na oryginalny plik z narzedzia/granice.txt. W tym celu do katalogu roboczego kopiowany jest oryginalny plik
        z granice.txt pod nazwa narzedzia-granice.txt i na niego nakladana jest latka po konwersji. Jesli wszystko sie
        uda, wtedy mozna spokojnie skopiowac plik do katalogu narzedzia
        :param Zmienne:
        :param plik_z_granicami: plik z granicami, uzywany do testow jednostkowych
        """
        self.Zmienne = Zmienne
        self.tryb_testowy = False
        self.separator = os.sep
        if plik_z_granicami_do_testow:
            self.tryb_testowy = True
            # w testach jednostkowych potrzebujemy aby byly niezalezne od systemu, dlatego separator ustawiamy
            # na sztywno
            self.separator = '/'
            plik_z_granicami_txt = plik_z_granicami_do_testow
        else:
            plik_z_granicami_txt = os.path.join(self.Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'granice.txt')
        with open(plik_z_granicami_txt, 'r', encoding=self.Zmienne.Kodowanie) as f:
            self.granice_txt = f.readlines()
            self.granice_orig = self.granice_txt[:]
        with open(plik_z_granicami_txt, 'rb') as f:
            self.granice_txt_hash = hashlib.md5(f.read()).hexdigest()

    def konwertujLatke(self, granice_czesciowe_diff):
        """
        konwersja latki ktora jest stworzona dla granicy czesciowej na latki stworzona dla pliku granice z narzedzi.
        :param granice_czesciowe_diff:
        :return: list() nowy diff w przypadku sukcesu, pusta liste w przypadku porazki
        """
        granice_czesciowe_rekordy = []
        rekord_granic_czesciowych = []
        for a in granice_czesciowe_diff[:]:
            if a.startswith('+++') or a.startswith('---'):
                pass
            # jesli mamy @@ oznacza to ze zaczyna sie nowy oddzielny rekord
            elif a.startswith('@@'):
                # jesli sa juz jakies dane w rekordzie granic czesciowych dolacz go to granicy_czesciowe i
                # zacznij od nowa, przypisujac mu wartosc z @@
                if len(rekord_granic_czesciowych) > 0:
                    granice_czesciowe_rekordy.append(rekord_granic_czesciowych)
                rekord_granic_czesciowych = [a]
            else:
                rekord_granic_czesciowych.append(a)
        granice_czesciowe_rekordy.append(rekord_granic_czesciowych)


        # tworzymy dwie osobne listy, zamien_co zawiera informacje co zamienic, zamien na co informacje na co zamienic
        for a in granice_czesciowe_rekordy[:]:
            zamien_co = []
            zamien_co_kontekst = []
            zamien_na_co = []
            zamien_na_co_kontekst = []
            for b in a[:]:
                # @ jest czescia latki, wiec to nalezy zignorowac
                if b.startswith('@'):
                    pass
                # od srednika zaczyna sie komentarz, komentarz ktory sie lapie to niestety nie ten z poczatku ale ten
                # z konca rekordu. Trzeba to zignorowac, ale z drugiej strony trzeba miec pewnosc ze wystepuje on na
                # koncu rekordu. Dlatego mamy a[-1] == b, w srodku rekordu moze byc i nie stanowi to zadnego problemu
                elif b.startswith(' ;') and a[-1] == b:
                    pass
                elif b.startswith(' '):
                    linia_tmp = b.replace(' ', '', 1)
                    zamien_co.append(linia_tmp)
                    zamien_co_kontekst.append('kontekst')
                    zamien_na_co.append(linia_tmp)
                    zamien_na_co_kontekst.append('kontekst')
                elif b.startswith('-'):
                    zamien_co.append(b.replace('-', '', 1))
                    zamien_co_kontekst.append('-')
                elif b.startswith('+'):
                    zamien_na_co.append(b.replace('+', '', 1))
                    zamien_na_co_kontekst.append('+')
            zamien_co = zamien_co
            zamien_na_co = zamien_na_co
            self.granice_txt = self.zwroc_zalatane_granice(zamien_co, zamien_co_kontekst,
                                                           zamien_na_co, zamien_na_co_kontekst)
            if not self.granice_txt:
                return []

        granice_po_konw = list(difflib.unified_diff(self.granice_orig, self.granice_txt,
                                                    fromfile='narzedzia' + self.separator + 'granice.txt',
                                                    tofile='narzedzia_Nowe' + self.separator + 'granice.txt'))
        if not self.tryb_testowy:
            with open(os.path.join(self.Zmienne.KatalogRoboczy, 'narzedzia-granice.txt'), 'w',
                      encoding=self.Zmienne.Kodowanie) as f:
                f.writelines(self.granice_txt)
            with open(os.path.join(self.Zmienne.KatalogRoboczy, 'narzedzia-granice.txt.diff'), 'w',
                      encoding=self.Zmienne.Kodowanie) as f:
                f.writelines(granice_po_konw)
        return granice_po_konw

    def zwroc_zalatane_granice(self, zamien_co, zamien_co_kontekst, zamien_na_co, zamien_na_co_kontekst):
        przesuniecie = -1
        # jesli plik jest pusty dopisujemy do niego od poczatku, wtedy nie zajmujmy sie takim przypadkiem
        # niech user sie martwi
        if not zamien_co_kontekst:
            return []
        # jesli linijki zostaly dopisane na koncu albo na poczatku pliku z granicami, wtedy caly
        # plik zamien_co_kontekst bedzie tylko kontekstem
        elif all(a == 'kontekst' for a in zamien_co_kontekst):
            # jesli piszemy na koncu pliku
            if zamien_na_co_kontekst[-1] == '+' and zamien_na_co_kontekst[0] == 'kontekst':
                przesuniecie = len(zamien_co_kontekst)
                return self.granice_txt + zamien_na_co[przesuniecie:]
            # jesli piszemy na poczatku pliku
            elif not zamien_na_co_kontekst[0] == '+' and zamien_na_co_kontekst[-1] == 'kontekst':
                return []
            else:
                return []
        # nalepszym wyznacznikiem pozycji bedzie jakies data, dlatego szukamy data w tym co trzeba zamienic
        else:
            DataX = ''
            DataX_index = -1
            for b in zamien_co[:]:
                if b.find('Data') >= 0:
                    DataX = b
                    DataX_index = zamien_co.index(DataX)
                    break
            if DataX_index == -1:
                return []
            przesuniecie = self.granice_txt.index(DataX) - DataX_index
            for b in range(len(zamien_co)):
                aaa = zamien_co[b]
                bbb = self.granice_txt[przesuniecie + b]
                if zamien_co[b] == self.granice_txt[przesuniecie + b]:
                    pass
                else:
                    return []
            granice_przed = self.granice_txt[:przesuniecie]
            granice_po = self.granice_txt[przesuniecie + len(zamien_co):]
            return granice_przed + zamien_na_co + granice_po


# ustawienia poczatkowe
class UstawieniaPoczatkowe(object):
    def __init__(self, plikmp):
        self.KatalogzUMP = "c:\\ump"
        self.OutputFile = plikmp
        self.InputFile = plikmp
        self.KatalogRoboczy = os.path.join(self.KatalogzUMP, 'roboczy')
        self.MapEditExe = 'c:\\ump\\mapedit++\\MapEdit++.exe'
        self.MapEdit2Exe = 'c:\\ump\\mapedit\\mapedit.exe'
        self.NetGen = 'c:\\ump\\narzedzia\\netgen.exe'
        self.mdm_mode = 'edytor'
        self.CvsUserName = 'guest'
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            self.Kodowanie = 'latin2'
        else:
            self.Kodowanie = 'cp1250'
        self.ReadErrors = 'ignore'
        self.WriteErrors = 'ignore'
        self.wczytajKonfiguracje()

    def ustaw_katalog_home(self, katalog_home):
        self.KatalogzUMP = katalog_home
        self.uaktualnijZalezneHome()

    def uaktualnijZalezneHome(self):
        self.KatalogRoboczy = os.path.join(self.KatalogzUMP, 'roboczy')
        self.NetGen = os.path.join(os.path.join(self.KatalogzUMP, 'narzedzia'), 'netgen.exe')

    def wczytajKonfiguracje(self):
        konf = {}
        try:
            with open(os.path.join(os.path.expanduser('~'), '.mont-demont-py.config'), encoding=self.Kodowanie) as b:
                for zawartosc in b.readlines():
                    kluczwartosc = zawartosc.split('=')
                    if len(kluczwartosc) == 2:
                        konf[kluczwartosc[0].strip()] = os.path.normpath(kluczwartosc[1].strip())

                if 'UMPHOME' in konf and 'KATALOGROBOCZY' not in konf:
                    if konf['UMPHOME'].startswith('~'):
                        konf['UMPHOME'] = os.path.join(os.path.expanduser('~') + konf['UMPHOME'][1:])
                    self.KatalogzUMP = konf['UMPHOME']
                    self.uaktualnijZalezneHome()
                elif 'UMPHOME' in konf and 'KATALOGROBOCZY' in konf:
                    if konf['UMPHOME'].startswith('~'):
                        konf['UMPHOME'] = os.path.join(os.path.expanduser('~'), konf['UMPHOME'][1:])
                    if konf['KATALOGROBOCZY'].startswith('~'):
                        konf['KATALOGROBOCZY'] = os.path.join(os.path.expanduser('~'), konf['KATALOGROBOCZY'][1:])
                    self.KatalogzUMP = konf['UMPHOME']
                    self.KatalogRoboczy = konf['KATALOGROBOCZY']
                elif 'UMPHOME' not in konf and 'KATALOGROBOCZY' in konf:
                    if konf['KATALOGROBOCZY'].startswith('~'):
                        konf['KATALOGROBOCZY'] = os.path.join(os.path.expanduser('~'), konf['KATALOGROBOCZY'][1:])
                    self.KatalogRoboczy = konf['KATALOGROBOCZY']
                if 'MAPEDITEXE' in konf:
                    self.MapEditExe = konf['MAPEDITEXE']
                if 'MAPEDIT2EXE' in konf:
                    self.MapEdit2Exe = konf['MAPEDIT2EXE']
                if 'NETGEN' in konf:
                    self.NetGen = konf['NETGEN']
                if 'MDMMODE' in konf:
                    if konf['MDMMODE'] == 'edytor':
                        self.mdm_mode = konf['MDMMODE']
                    else:
                        self.mdm_mode = 'wrzucacz'
                if 'CVSUSERNAME' in konf:
                    self.CvsUserName = konf['CVSUSERNAME']
                else:
                    pass

        except FileNotFoundError:
            # probujemy zgadnac konfiguracje
            sciezkaDoSkryptu = os.getcwd()
            if sciezkaDoSkryptu.endswith('narzedzia'):
                bbb = [a for a in os.listdir(sciezkaDoSkryptu.split('narzedzia', 1)[0]) if
                       a.find('UMP-') >= 0 and os.path.isdir(sciezkaDoSkryptu.split('narzedzia', 1)[0] + a)]
                # print(bbb)
                if len(bbb) > 0:
                    self.KatalogzUMP = sciezkaDoSkryptu.split('narzedzia', 1)[0]
                    self.KatalogRoboczy = sciezkaDoSkryptu.split('narzedzia', 1)[0]
                    self.uaktualnijZalezneHome()
                else:
                    print('Nie moge zgadnac konfiguracji', file=sys.stderr)


class tabelaKonwersjiTypow(object):
    def __init__(self, Zmienne, stderr_stdout_writer):
        self.Zmienne = Zmienne
        self.type2Alias = self.create_type2Alias()
        self.name2Alias = self.create_name2Alias()
        self.stderr_stdout_writer = stderr_stdout_writer
        self.alias2Type = {y.upper(): x for x in self.type2Alias for y in self.type2Alias[x]}
        self.alias2Type['truck_stop'] = '0x2f16'
        self.alias2Type['24h'] = '0x2e06'
        self.alias2TypeFromFile = dict()
        self.type2AliasFromFile = dict()
        self.alias2File = dict()
        if not self.read_pnt2poi_txt():
            self.merge_alias2TypeFromFile_and_alias2Type()
            self.merge_type2AliasFromFile_and_type2Alias()

    def create_type2Alias(self):
        type_2_alias = {
            '0x0600': ["poi_large_citi", "poi_major_citi"],
            '0x0b00': ["city", "geo_name_man", "poi_small_citi"],
            '0x0d00': ["poi_med_cities"],
            '0x1300': ["przystan"],
            '0x1400': ["wp_dot"],
            '0x1605': ["mapa"],
            '0x1606': ["stawa"],
            '0x1607': ["bezp_woda"],
            '0x1608': ["lewa"],
            '0x1609': ["prawa"],
            '0x160a': ["nieb_odosobn"],
            '0x160b': ["specjalna"],
            '0x160c': ["kardynalna"],
            '0x160d': ["inna"],
            '0x160f': ["biale"],
            '0x1610': ["czerwone"],
            '0x1611': ["zielone"],
            '0x1612': ["zolte"],
            '0x1613': ["pomaranczowe"],
            '0x1614': ["fioletowe"],
            '0x1615': ["niebieskie"],
            '0x1616': ["wielobarwne"],
            '0x1709': ["wiadukt"],
            '0x1708': ["slepy"],
            '0x170a': ["weryfikowac"],
            '0x170b': ["uwaga"],
            '0x170d': ["watpliwy", "nie_wiem"],
            '0x1710': ["zakaz"],
            '0x1711': ["sprawdz"],
            '0x1712': ["remont"],
            '0x1806': ["stawa_r"],
            '0x1808': ["prawa_b"],
            '0x1809': ["lewa_b"],
            '0x180b': ["boja"],
            '0x180d': ["w_prawo"],
            '0x180c': ["kard_n"],
            '0x1906': ["stawa_g"],
            '0x190c': ["kard_s"],
            '0x190d': ["w_lewo"],
            '0x1a06': ["stawa_y"],
            '0x1a0c': ["kard_e"],
            '0x1a0d': ["w_lewo_b"],
            '0x1b06': ["stawa_w"],
            '0x1b0c': ["kard_w"],
            '0x1b0d': ["w_prawo_b"],
            '0x1c01': ["wrak_wid"],
            '0x1c02': ["wrak"],
            '0x1c03': ["wrak_bezp"],
            '0x1c04': ["wrak_tral"],
            '0x1c05': ["glaz_wid"],
            '0x1c07': ["przeszkoda"],
            '0x1c08': ["przeszkoda_tral"],
            '0x1c09': ["glaz_zal"],
            '0x1c0a': ["glaz"],
            '0x1c0b': ["obiekt"],
            '0x1f00': ["rejon"],
            '0x2000': ["zjazd"],
            '0x2500': ["oplata"],
            '0x2700': ["exit"],
            '0x2800': ["dzielnica", "label", "kwatera", "adr", "housenumber"],
            '0x2a00': ["jedzenie"],
            '0x2a01': ["american"],
            '0x2a02': ["asian", "sushi"],
            '0x2a03': ["kebab", "barbecue", "grill"],
            '0x2a04': ["chinese"],
            '0x2a05': ["deli", "piekarnia"],
            '0x2a06': ["restauracja", "internationa", "international", "restaurant"],
            '0x2a07': ["fastfood", "food", "burger"],
            '0x2a08': ["italian"],
            '0x2a09': ["mexican"],
            '0x2a0a': ["pizza"],
            '0x2a0b': ["seafood"],
            '0x2a0c': ["steak"],
            '0x2a0d': ["cukiernia", "bagel"],
            '0x2a0e': ["kawiarnia", "cafe", "caffe", "coffee"],
            '0x2a0f': ["french"],
            '0x2a10': ["german"],
            '0x2a11': ["british"],
            '0x2a12': ["mleczny", "vegetarian"],
            '0x2a13': ["grecka", "libanska", "greek"],
            '0x2b00': ["schronisko", "hostel"],
            '0x2b01': ["hotel", "lodging", "motel"],
            '0x2b02': ["b&b", "agro", "nocleg"],
            '0x2b03': ["camping", "polenamiot"],
            '0x2b04': ["resort"],
            '0x2c00': ["atrakcja"],
            '0x2c01': ["plac_zabaw", "amusement_park"],
            '0x2c02': ["muzeum", "galeria", "museum", "muzea"],
            '0x2c03': ["biblioteka", "video"],
            '0x2c04': ["zamek", "castle", "palac", "dworek"],
            '0x2c05': ["szkola", "zlobek", "przedszkole", "school", "szkoly", "gimnazjum", "liceum", "uczelnia"],
            '0x2c06': ["park"],
            '0x2c07': ["zoo"],
            '0x2c08': ["stadion", "stadium"],
            '0x2c09': ["targi", "fair"],
            '0x2c0a': ["winiarnia", "winery", "browar", "brewery"],
            '0x2c0b': ["kosciol", "kaplica", "cerkiew", "synagoga", "meczet", "gompa", "mandir", "stupa", "czorten"],
            '0x2c10': ["mural"],
            '0x2d00': ["esc_room"],
            '0x2d01': ["kultura", "teatr", "teatry", "theater"],
            '0x2d02': ["bar", "mug", "pub"],
            '0x2d03': ["kino", "kina", "multikino"],
            '0x2d04': ["kasyno", "casino"],
            '0x2d05': ["golf"],
            '0x2d06': ["narty"],
            '0x2d07': ["kregle", "bowling"],
            '0x2d08': ["lodowisko"],
            '0x2d09': ["basen", "baseny", "nurek"],
            '0x2d0a': ["sport", "fitness", "kort", "korty", "skatepark", "boisko"],
            '0x2d0b': ["ladowisko", "landing"],
            '0x2e00': ["sklep", "books", "ksiegarnia", "shop", "special", "specialty"],
            '0x2e01': ["hala", "dept", "store", "market"],
            '0x2e02': ["bazar", "grocery", "spozywczy"],
            '0x2e03': ["super", "supermarket"],
            '0x2e04': ["hiper", "shopping_cart", "sklepy"],
            '0x2e05': ["apteka", "apteki", "pharmacy"],
            '0x2e06': ["24h", "fuel_store"],
            '0x2e07': ["ubrania"],
            '0x2e08': ["budowlane", "budowlany", "dom_i_ogrod"],
            '0x2e09': ["meble", "wnetrza"],
            '0x2e0a': ["rowerowy", "sportowy", "turystyczny"],
            '0x2e0b': ["rtv", "komputery"],
            '0x2f01': ["benzyna", "fuel", "lpg", "cng", "stacje", "paliwo", "elektryczne", "bp", "prad"],
            '0x2f02': ["rentacar", "rent_a_bike", "rowery", "rent_a_boat", "lodki"],
            '0x2f03': ["auto", "car", "carrepair", "carservice"],
            '0x2f04': ["lotnisko", "airport"],
            '0x2f05': ["poczta", "inpost", "paczkomat", "kurier"],
            '0x2f06': ["atm", "atmbank", "bank", "banki", "kantor"],
            '0x2f07': ["cardealer"],
            '0x2f08': ["bus", "metro", "pkp", "pks", "tram", "taxi"],
            '0x2f09': ["port", "marina", "stanica"],
            '0x2f0b': ["parking"],
            '0x2f0c': ["info", "informacja"],
            '0x2f0d': ["autoklub", "tor"],
            '0x2f0e': ["myjnia", "carwash"],
            '0x2f0f': ["garmin"],
            '0x2f10': ["uslugi", "tatoo", "optyk", "fryzjer", "lombard"],
            '0x2f11': ["fabryka", "business", "firma"],
            '0x2f12': ["wifi", "hotspot"],
            '0x2f13': ["serwis", "repair", "naprawa"],
            '0x2f14': ["pralnia", "social"],
            '0x2f15': ["budynek", "building"],
            '0x2f16': ["truck_stop"],
            '0x2f17': ["turystyka"],  # ","biuro","turystyczne,","transit_services
            '0x2f18': ["biletomat"],
            '0x3000': ["emergency"],
            '0x3001': ["policja"],
            '0x3002': ["dentysta", "pogotowie", "przychodnia", "szpital", "szpitale", "uzdrowisko",
                       "weterynarz", "aed"],
            '0x3003': ["ratusz"],
            '0x3004': ["sad"],
            '0x3005': ["koncert", "concert", "hall"],
            '0x3006': ["border", "toll"],
            '0x3007': ["urzad", "instytucje", "prokuratura"],
            '0x3008': ["pozarna"],
            '0x4100': ["ryba"],
            '0x4300': ["kotwicowisko"],
            '0x4700': ["slip", "boat_ramp"],
            '0x4a00': ["picnic", "rest", "restroom"],
            '0x4f00': ["prysznic", "shower"],
            '0x5a00': ["km"],
            '0x5a01': ["slupek_granica", "slupek"],
            '0x5a02': ["km_woda"],
            '0x5100': ["telefon", "sos"],
            '0x5200': ["widok", "scenic"],
            '0x5300': ["skiing", "ski"],
            '0x5400': ["kapielisko"],
            '0x5600': ["fa", "fp", "fs", "fo", "kd", "ra", "po", "rl", "fotoradar", "radar"],
            '0x5700': ["czarnypunkt", "danger", "nm", "pk", "spk", "npk", "op"],
            '0x5800': ['REP_N-S'],
            '0x5801': ['REP_E-W'],
            '0x5802': ['REP_NW-SE'],
            '0x5803': ['REP_NE-SW'],
            '0x5804': ['REP_N'],
            '0x5805': ['REP_S'],
            '0x5806': ['REP_E'],
            '0x5807': ['REP_W'],
            '0x5808': ['REP_NW'],
            '0x5809': ['REP_NE'],
            '0x580a': ['REP_SW'],
            '0x580b': ['REP_SE'],
            '0x5901': ["airportbig"],
            '0x5902': ["airportmed", "lotnisko_srednie"],
            '0x5903': ["airportsmall", "lotnisko_male", "aeroklub"],
            '0x5904': ["heli"],
            '0x593f': ["transport"],
            '0x5e00': ["wozek"],
            '0x5f00': ["trafo"],
            '0x6100': ["bunkier"],
            '0x6101': ["ruiny"],
            '0x6200': ["glebokosc"],
            '0x6300': ["wysokosc"],
            '0x6400': ["pomnik", "zabytek"],
            '0x6401': ["most", "bridge"],
            '0x6402': ["dom", "house"],
            '0x6403': ["cmentarz", "cemetery", "kirkut", "mizar"],
            '0x6404': ["krzyz", "kapliczka"],
            '0x6405': ["lesniczowka"],
            '0x6406': ["crossing", "prom"],
            '0x6407': ["tama"],
            '0x6409': ["jaz"],
            '0x640a': ["kamera", "webcam"],
            '0x640b': ["wojsko"],
            '0x640c': ["kopalnia"],
            '0x640d': ["platforma"],
            '0x640e': ["rezerwat", "rv_park"],
            '0x640f': ["postbox"],
            '0x6411': ["wieza", "short_tower", "tall_tower", "tower"],
            '0x6412': ["szlak", "trail"],
            '0x6413': ["tunel", "cave", "jaskinia"],
            '0x6414': ["oligocen"],
            '0x6415': ["fort"],
            '0x6502': ["brod"],
            '0x6503': ["zatoka"],
            '0x6505': ["canal"],
            '0x6506': ["river"],
            '0x6508': ["wodospad"],
            '0x6509': ["fontanna"],
            '0x650a': ["lodowiec"],
            '0x650c': ["wyspa"],
            '0x650d': ["jezioro"],
            '0x650f': ["wc", "toitoi"],
            '0x6511': ["zrodlo", "spring"],
            '0x6512': ["stream"],
            '0x6513': ["pond"],
            '0x6600': ["kurhan"],
            '0x6602': ["obszar", "area"],
            '0x6604': ["kapielisko", "plaza"],
            '0x6605': ["sluza"],
            '0x6606': ["przyladek"],
            '0x6607': ["urwisko"],
            '0x660a': ["drzewo", "tree"],
            '0x660f': ["wiatrak"],
            '0x6610': ["elevation", "plain"],
            '0x6614': ["skala"],
            '0x6616': ["gora", "hill", "mountain", "mountains", "przelecz", "summit"],
            '0x6617': ["dolina"],
            '0xf201': ["swiatla"],
            '0x6701': ["szlak_g"],
            '0x6702': ["szlak_r"],
            '0x6703': ["szlak_b"],
            '0x6704': ["szlak_y"],
            '0x6705': ["szlak_k"],
            '0x6707': ["rower_g"],
            '0x6708': ["rower_r"],
            '0x6709': ["rower_b", "premia"],
            '0x670a': ["rower_y"],
            '0x670b': ["rower_k"]
        }
        return type_2_alias

    def create_name2Alias(self):
        # mozna uzupelniac tabele konwersji nazwy na typ. Format jak ponizej. Prosze dodawac alfabetycznie
        # sortowanie po nazwie
        name_2_alias = {
            'Aldi': 'SUPER',
            'apteka': 'APTEKA',
            'basen': 'BASEM',
            'benzyna': 'PALIWO',
            'biblioteka': 'BIBLIOTEKA',
            'Biedronka': 'SUPER',
            'Burger King': 'FASTFOOD',
            'Castorama': 'BUDOWLANE',
            'Decathlon': 'SPORTOWY',
            'kaplica': 'KAPLICA',
            'kapliczka': 'KRZYZ',
            'KFC': 'FASTFOOD',
            'kościół': 'KOSCIOL',
            'krzyż': 'KRZYZ',
            'Leroy Merlin': 'BUDOWLANE',
            'Lidl': 'SUPER',
            'Lotos': 'PALIWO',
            'LPG': 'LPG',
            'lpg': 'LPG',
            'McDonalds': 'FASTFOOD',
            'Moya': 'PALIWO',
            'myjnia': 'MYJNIA',
            'Obi': 'BUDOWLANE',
            'Orlen': 'PALIWO',
            'parking': 'PARKING',
            'PKP': 'PKP',
            'Policja': 'POLICJA',
            'policja': 'POLICJA',
            'Praktiker': 'BUDOWLANE',
            'Real': 'HIPER',
            'Shell': 'PALIWO',
            'spożywczy': 'SPOZYWCZY',
            'stacja paliw': 'PALIWO',
            'Statoil': 'PALIWO',
            'Tesco': 'SUPER',
            'Żabka': 'GROCERY'
        }
        return name_2_alias

    def zwrocTypPoLabel(self, Label, Type):
        """
        zwraca typ w zaleznosci od label
        :param Label:
        :param Type:
        :return: typ dokladny, typ najlepiej pasujacy
        jesli typ dokladny nie moze byc ustalony to zwraca '', typ najelpiej pasujacy
        """
        if Label in self.name2Alias:
            return self.name2Alias[Label], '0x0'
        else:
            if Type in self.type2Alias:
                pasujaceTypy = [a for a in Label.strip().split(' ') if a.lower() in self.type2Alias[Type]]
                if pasujaceTypy:
                    if len(pasujaceTypy) > 1:
                        self.stderr_stdout_writer.stderrorwrite('Nie moge jednoznacznie dopasowac Type po Label.'
                                                                '\nUzywam pierwszej wartosci z listy: %s'
                                                                % pasujaceTypy[0])
                    return '', pasujaceTypy[0]
                self.stderr_stdout_writer.stderrorwrite('Nie moge jednoznacznie dopasowac Type po Label.'
                                                        '\nUzywam pierwszej wartosci z listy: %s'
                                                        % self.type2Alias[Type][0])
                return '', self.type2Alias[Type][0]
            else:
                return '', Type

    def merge_alias2TypeFromFile_and_alias2Type(self):
        for a in self.alias2TypeFromFile:
            if a not in self.alias2Type:
                self.alias2Type[a] = self.alias2TypeFromFile[a]

    def merge_type2AliasFromFile_and_type2Alias(self):
        for a in self.alias2TypeFromFile:
            klucz = a
            wartosc = self.alias2TypeFromFile[klucz]
            if wartosc in self.type2Alias:
                self.type2Alias[wartosc].append(klucz)
            else:
                self.type2Alias[wartosc] = [klucz]
        # print(self.type2AliasFromFile)
        return 0

    def read_pnt2poi_txt(self):
        sekcja = ''
        nr_linii = 0
        plik_pnt2poi = 'narzedzia' + os.sep + 'pnt2poi.txt'
        try:
            with open(os.path.join(self.Zmienne.KatalogzUMP, plik_pnt2poi), encoding=self.Zmienne.Kodowanie,
                      errors=self.Zmienne.ReadErrors) as f:
                # zawartosc_pliku_pnt2poi = f.read().split('[END]')
                zawartosc_pliku_pnt2poi = f.readlines()
        # w przypadku gdyby pliku nie bylo obsluz wyjatek i pozostan przy ustawieniach domyslnych
        except FileNotFoundError:
            self.stderr_stdout_writer.stderrorwrite('Brak pliku ' + plik_pnt2poi + ', wczytuje definicje domyslne')
            return 1
        else:
            for a in zawartosc_pliku_pnt2poi:
                nr_linii += 1
                a = a.strip()
                # po strip powstaja nieraz puste linie wiec takich nie ma co przeszukiwac stad ten if
                if a:
                    if a.startswith('[DEF-POI]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii - 1))
                        sekcja = '[DEF-POI]'
                    elif a.startswith('[DEF-LINE]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii - 1))
                        sekcja = '[DEF-LINE]'
                    elif a.startswith('[DEF-REVPOI]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii - 1))
                        sekcja = '[DEF-REVPOI]'
                    elif a.startswith('[END'):
                        sekcja = ''
                    elif a.startswith('_plik'):
                        pass
                    else:
                        if sekcja == '[DEF-POI]':
                            if a.startswith('#'):
                                pass
                            else:
                                # print(a)
                                alias, type = a.split('=')
                                type = type.split('#')[0].strip()
                                alias = alias.strip()
                                if alias in self.alias2TypeFromFile:
                                    self.stderr_stdout_writer.stderrorwrite('Uwaga! Podwojna definicja aliasu %s w pliku ' +
                                    plik_pnt2poi + '.' % alias)
                                self.alias2TypeFromFile[alias] = type
            # print(self.alias2TypeFromFile)
            return 0


class Obszary(object):
    """
    klasa wczytuje obszary z pliku narzedzia/obszary.txt w celu automatycznego umieszczania
    poi w odpowiednich plikach
    """
    def __init__(self, obszary, Zmienne):
        self.polygonyObszarow = {}
        with open(os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'obszary.txt'), encoding=Zmienne.Kodowanie,
                  errors=Zmienne.ReadErrors) as f:
            zawartosc_pliku_obszary = f.read().split('[END]')
        for a in zawartosc_pliku_obszary:
            for b in obszary:
                if a.find(b) > 0:
                    Data0 = a.split('Data0=(')[1].strip().rstrip(')').replace('),(', ',').split(',')
                    Data0.append(Data0[0])
                    Data0.append(Data0[1])
                    self.polygonyObszarow[b] = Data0

    def zwroc_obszar(self, x, y):
        for a in self.polygonyObszarow:
            if self.point_inside_polygon(
                    x, y,
                    [float(b) for b in self.polygonyObszarow[a] if self.polygonyObszarow[a].index(b) % 2 == 0],
                    [float(b) for b in self.polygonyObszarow[a] if self.polygonyObszarow[a].index(b) % 2 != 0]
            ):
                return a
        return 'None'

    def point_inside_polygon(self, x, y, polyx, polyy):
        n = len(polyx)
        inside = False
        p1x = polyx[0]
        p1y = polyy[0]
        for i in range(n + 1):
            p2x = polyx[i % n]
            p2y = polyy[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def czy_wspolrzedne_w_jednym_obszarze(self, dane_do_zapisu):
        listawspolrzednychdosprawdzenia = []
        for lista_wsp in (data for data in dane_do_zapisu if data.startswith('Data')):
            listawspolrzednychdosprawdzenia += dane_do_zapisu[lista_wsp].split('=')[-1].strip()[1:-1].split('),(')
            # print(listawspolrzednychdosprawdzenia)
        obszar_dla_poly = set()
        for lista_wsp in listawspolrzednychdosprawdzenia:
            # musimy sprawdzic czy dany polygon lub polyline w calosci lezy na terenie jednego obszaru
            # jesli tak, obszar_dla_poly przyjmie konkretna wartosc, jesli nie to wtedy bedzie 'Nieznany'
            x, y = lista_wsp.split(',')
            obszar_dla_poly.add(self.zwroc_obszar(float(x), float(y)))
            if len(obszar_dla_poly) > 1:
                return False, obszar_dla_poly.pop(), listawspolrzednychdosprawdzenia[0]
        return True, obszar_dla_poly.pop(), listawspolrzednychdosprawdzenia[0]


class autoPlikDlaPoi(object):
    def __init__(self):
        self.obszar_typ_plik = defaultdict(lambda: defaultdict(lambda: 0))
        self.typ_plik = defaultdict(lambda: defaultdict(lambda: 0))
        self.autopoiWykluczoneWartosciPlik = ('.BP.paliwo.pnt', '.PGP.pnt', '.ORLEN.paliwo.pnt', '.MPK.pnt',
                                              '.ZTM.pnt', '.ZKM.pnt', 'POI-Baltyk.pnt', '.MOYA.paliwo.pnt',
                                              '.nextbike.pnt', '.poczta-polska.pnt', '.ZABKA.sklepy.pnt',
                                              '.paczkomaty.pnt',)
        self.wykluczone_dozwolone_pliki = defaultdict(lambda: False)

    def czy_plik_jest_wykluczony(self, plik):
        if plik in self.wykluczone_dozwolone_pliki:
            return self.wykluczone_dozwolone_pliki[plik]
        if any(a for a in self.autopoiWykluczoneWartosciPlik if plik.endswith(a)):
            self.wykluczone_dozwolone_pliki[plik] = True
        else:
            self.wykluczone_dozwolone_pliki[plik] = False
        return self.wykluczone_dozwolone_pliki[plik]

    def dodaj_plik_dla_poi(self, dane_do_zapisu):
        if 'Plik' not in dane_do_zapisu or 'Type' not in dane_do_zapisu or \
                self.czy_plik_jest_wykluczony(dane_do_zapisu['Plik']):
            return
        if dane_do_zapisu['Type'] in City.rozmiar2Type:
            self.typ_plik['MIASTO'][dane_do_zapisu['Plik']] += 1
        # dla miast Typ= nie jest dodawany, więc nie można go w pierwszym teście wykluczyć, dopiero teraz
        elif 'Typ' not in dane_do_zapisu:
            return
        else:
            self.typ_plik[dane_do_zapisu['Typ']][dane_do_zapisu['Plik']] += 1
        return

    def przygotuj_obszar_typ_plik(self):
        for typ in self.typ_plik:
            for obszar in (obsz.split(os.sep)[0].split('-')[-1] for obsz in self.typ_plik[typ]):
                pliki = [p for p in self.typ_plik[typ] if obszar in p]
                typy_dict = self.typ_plik[typ]
                plik_z_maksymalna_wartoscia = max(pliki, key=typy_dict.get)
                self.obszar_typ_plik[obszar][typ] = plik_z_maksymalna_wartoscia

    def zwroc_plik_dla_typu(self, obszar, typ):
        if not self.obszar_typ_plik:
            self.przygotuj_obszar_typ_plik()
        if obszar in self.obszar_typ_plik and typ in self.obszar_typ_plik[obszar]:
            return self.obszar_typ_plik[obszar][typ]
        return ''
 

class autoPolylinePolygone(object):
    def __init__(self, Zmienne, plik_nowosci_txt):
        # zmienne z nazwami plikow, tak aby w razie czego zmieniac w jedny miejscu, a nie w wielu
        WODA = 'woda.txt'
        ZAKAZY = 'zakazy.txt'
        GRANICE = 'granice.txt'
        SZLAKI = 'szlaki.topo.txt'
        TRAMWAJE = 'tramwaje.txt'
        KOLEJ = 'kolej.txt'
        OBSZARY = 'obszary.txt'
        BUDYNKI = 'budynki.txt'
        ZIELONE = 'zielone.txt'
        self.Zmienne = Zmienne
        self.plik_nowosci_txt = plik_nowosci_txt
        self.wykluczonePliki = ['BIALYSTOK.BPN.szlaki.topo.txt', 'BIALYSTOK.SDGN.szlaki.topo.txt']
        self.dozwolonePliki = [WODA, ZAKAZY, GRANICE, SZLAKI, TRAMWAJE, KOLEJ, OBSZARY, BUDYNKI, ZIELONE]

        # zmienna bedzie zawierac slownik z obszarami. Klucze slownika beda wskazywaly na inny slownik w ktorym beda
        # pliki wraz z ich wspolrzednymi w postaci kd-tree
        # self.autoObszar = {}
        self.autoObszar = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
        # self.autoTypyPlikowwObszarze={}
        # self.autoPliki={}

        self.TypPolyline2Plik = {'0x14': [KOLEJ],  # koleje
                                 '0x15': [WODA],  # coastline, linia brzegowa
                                 '0x18': [WODA],  # strumien
                                 '0x19': [ZAKAZY],  # zakazy
                                 '0x1c': [GRANICE],  # granice
                                 '0x1d': [GRANICE],  # granice
                                 '0x1e': [GRANICE],  # granice miedzynarodowe
                                 '0x1f': [WODA],  # rzeka
                                 '0x26': [WODA],  # strumien sezonowy
                                 '0x2f': [ZAKAZY],  # podpowiedzi
                                 '0x10e00': [SZLAKI],  # szlak pieszy czerwony
                                 '0x10e01': [SZLAKI],  # szlak pieszy zolty
                                 '0x10e02': [SZLAKI],  # szlak pieszy zielony
                                 '0x10e03': [SZLAKI],  # szlak pieszy niebieski
                                 '0x10e04': [SZLAKI],  # szlak pieszy czarny
                                 '0x10e07': [SZLAKI],  # szlak pieszy wielokolorowy
                                 '0x10e08': [SZLAKI],  # szlak rowerowy czerwony
                                 '0x10e09': [SZLAKI],  # szlak rowerowy zolty
                                 '0x10e0a': [SZLAKI],  # szlak rowerowy zielony
                                 '0x10e0b': [SZLAKI],  # szlak rowerowy niebieski
                                 '0x10e0c': [SZLAKI],  # szlak rowerowy czarny
                                 '0x10e0d': [SZLAKI],  # szlak rowerowy inny
                                 '0x10e0f': [SZLAKI],  # szlak konski, sciezka dydaktyczna
                                 '0x10e10': [TRAMWAJE, KOLEJ],  # tramwaj
                                 '0x10e14': [KOLEJ],  # koleje
                                 '0x10e15': [KOLEJ],  # koleje podziemne
                                 }

        self.TypPolygon2Plik = {'0x1': [OBSZARY],  # city
                                '0x2': [OBSZARY],  # city
                                '0x3': [OBSZARY],  # rual housing
                                '0x4': [OBSZARY],  # baza wojskowa
                                '0x5': [OBSZARY],  # parking
                                '0x7': [BUDYNKI, OBSZARY],  # terminal lotniska
                                '0x8': [BUDYNKI, OBSZARY],  # sklep
                                '0x9': [OBSZARY],  # porty
                                '0xa': [BUDYNKI, OBSZARY],  # szkola
                                '0xb': [BUDYNKI, OBSZARY],  # szpital
                                '0xc': [OBSZARY],  # industrial
                                '0xd': [OBSZARY],  # reservation
                                '0xe': [OBSZARY],  # pas startowy
                                '0x13': [BUDYNKI, OBSZARY],  # budynek
                                '0x14': [ZIELONE],  # lasy
                                '0x15': [ZIELONE],  # parki narodowe
                                '0x16': [ZIELONE],  # parki narodowe
                                '0x17': [ZIELONE],  # park miejski
                                '0x18': [ZIELONE],  # pole golfowe
                                '0x19': [OBSZARY],  # obiekty sportowe
                                '0x1a': [ZIELONE],  # cmentarz
                                '0x1e': [ZIELONE],  # park stanowy
                                '0x1f': [ZIELONE],  # park stanowy
                                '0x20': [ZIELONE],  # park stanowy
                                '0x28': [WODA],  # ocean
                                '0x29': [WODA],  # woda
                                '0x32': [WODA],  # morze
                                '0x3b': [WODA],  # woda
                                '0x3c': [WODA],  # duze jezioro
                                '0x3d': [WODA],  # duze jezioro
                                '0x3e': [WODA],  # srednie jezioro
                                '0x3f': [WODA],  # srednie jezioro
                                '0x40': [WODA],  # male jezioro
                                '0x41': [WODA],  # male jezioro
                                '0x42': [WODA],  # glowne jezioro
                                '0x43': [WODA],  # glowne jezioro
                                '0x44': [WODA],  # ogromne jezioro
                                '0x45': [WODA],  # woda
                                '0x46': [WODA],  # glowna rzeka
                                '0x47': [WODA],  # duza rzeka
                                '0x48': [WODA],  # srednia jezioro
                                '0x49': [WODA],  # male rzeka
                                '0x4e': [ZIELONE],  # plantacja, ogrodki dzialkowe
                                '0x4f': [ZIELONE],  # zarosla
                                '0x51': [WODA],  # bagno
                                '0x52': [ZIELONE],  # tundra
                                '0x53': [OBSZARY],  # piasek, wydmy
                                }

    def wypelnijObszarPlikWspolrzedne(self, pliki):
        for a in pliki:
            if a.startswith('UMP-'):
                tmp = a.split(os.sep)
                obszar = tmp[0].split('-')[-1]
                plik = tmp[-1]
                typpliku = plik.split('.', 1)[-1]
                if plik not in self.wykluczonePliki and typpliku in self.dozwolonePliki:
                    tree = kdtree.create(dimensions=2)
                    with open(os.path.join(self.Zmienne.KatalogzUMP, a), encoding=self.Zmienne.Kodowanie,
                              errors=self.Zmienne.ReadErrors) as f:
                        for zawartoscpliku in f.read().strip().split('Data0=')[1:]:
                            zawartoscpliku = zawartoscpliku.split('\n')[0]
                            for wspolrzedne in zawartoscpliku.strip().lstrip('(').rstrip(')').split('),(')[1::10]:
                                szerokosc, dlugosc = wspolrzedne.split(',')
                                tree.add([float(dlugosc), float(szerokosc)])
                    self.autoObszar[obszar][typpliku][a] = tree

    def znajdz_najblizszy(self, obszar, typ_pliku, wspolrzedne):
        y, x = wspolrzedne.split(',')
        wsp = (float(x), float(y),)
        if typ_pliku in self.autoObszar[obszar]:
            if len(self.autoObszar[obszar][typ_pliku]) == 1:
                return list(self.autoObszar[obszar][typ_pliku])[0]
            else:
                lista_odleglosci = []
                slownik_plik_odleglosc = {}
                for abc in self.autoObszar[obszar][typ_pliku]:
                    odl = self.autoObszar[obszar][typ_pliku][abc].search_nn(wsp)
                    odleglosc = odl[1]
                    print(abc, odl)
                    if odleglosc not in lista_odleglosci:
                        lista_odleglosci.append(odleglosc)
                        slownik_plik_odleglosc[odleglosc] = abc
                return slownik_plik_odleglosc[sorted(lista_odleglosci)[0]]
        else:
            return 'brak_klucza'

    def zwroc_plik_dla_poly(self, typobiektu, type, obszar, wspolrzedne):
        try:
            if typobiektu == '[POLYGON]':
                auto_obszary_typy = self.TypPolygon2Plik[type]
            else:
                auto_obszary_typy = self.TypPolyline2Plik[type]
        except KeyError:
            return self.plik_nowosci_txt
        for mozliwepliki in auto_obszary_typy:
            auto_plik = self.znajdz_najblizszy(obszar, mozliwepliki, wspolrzedne)
            if auto_plik != 'brak_klucza':
                return auto_plik
        return self.plik_nowosci_txt


class IndeksyMiast(object):
    def __init__(self):
        # indeks mias lepiej przechowywac w postaci slownika, bo dziala to zdecydowanie szybciej.
        # Trzeba za to osobno pamietac numer aktualnego miasta
        self.globalCityIdx = {}
        self.actCityIdx = 0
        self.sekcja_cityidx = ['[Countries]', 'Country1=Polska~[0x1d]PL', '[END-Countries]\n', '[Regions]',
                               'Region1=Wszystkie', 'CountryIdx1=1', '[END-Regions]\n', '[Cities]']
        self.sekcja_cityname = ('CountryName=Polska~[0x1d]PL', 'RegionName=Wszystkie', 'DistrictName=',)

    def zwrocIndeksMiasta(self, nazwaMiasta):
        if nazwaMiasta not in self.globalCityIdx:
            self.actCityIdx += 1
            self.globalCityIdx[nazwaMiasta] = self.actCityIdx
            self.sekcja_cityidx.append('City' + str(self.actCityIdx) + '=' + nazwaMiasta)
            self.sekcja_cityidx.append('RegionIdx' + str(self.actCityIdx) + '=1')
        return self.globalCityIdx[nazwaMiasta]


class plikMP1(object):
    """przechowuje zawartosc pliku mp do zapisu"""
    def __init__(self, Zmienne, args, tabela_konwersji_typow, Montuj=1):

        # zawartosc nowo tworzonego pliku mp, zawartosc z plikow skladowych do montazu
        self.zawartosc = []
        self.plik_nowosci_txt = '_nowosci.txt'
        self.plik_nowosci_pnt = '_nowosci.pnt'
        self.Zmienne = Zmienne
        self.args = args
        self.tabela_konwersji_typow = tabela_konwersji_typow
        self.domyslneMiasta2 = {}
        self.cityIdxMiasto = []
        self.errOutWriter = errOutWriter(args)
        self.sciezka_zwalidowana = set()
        self.auto_pliki_dla_poi = autoPlikDlaPoi()
        self.dozwolone_obszary_dla_plikow = set()

        # przechowywanie hashy dla danego pliku w postaci slownika: nazwapliku:wartosc hash
        self.plikHash = {}
        if Montuj:
            self.plikDokladnosc = {}
            try:
                plik_naglowka_nazwa = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'header.txt')
                with open(plik_naglowka_nazwa, encoding=Zmienne.Kodowanie, errors=Zmienne.ReadErrors) as plik_naglowka:
                    self.naglowek = plik_naglowka.read()
            # self.zawartosc.append(self.naglowek.rstrip()+'\n')
            except FileNotFoundError:
                self.stderrorwrite('nie moge zaladowac pliku header.txt')
            else:
                self.stdoutwrite('Wczytalem naglowek mapy z pliku header.txt')
        else:
            self.plikDokladnosc = {self.plik_nowosci_txt: '5', self.plik_nowosci_pnt: '5'}
            self.plikizMp = {self.plik_nowosci_txt: [], self.plik_nowosci_pnt: []}
            self.osobne_pliki_dla_miast = list()

            # Zmienna z obszarami ktore sa zamontowane, wykorzystywana do autorozkladu linii i polygonow do
            # odpowiednich plikow, na poczatku ustawione jako None,
            # zmienia sie po pierwszym wywolaniu zapiszTXT poprzez funkcje ustawObszary
            self.obszary = None
            self.autoobszary = autoPolylinePolygone(self.Zmienne, self.plik_nowosci_txt)

    def stderrorwrite(self, error_msg):
        self.errOutWriter.stderrorwrite(error_msg)

    def stdoutwrite(self, info_msg):
        self.errOutWriter.stdoutwrite(info_msg)

    def dodaj(self, aaa):
        """
        funkcja dodaje zawartosc pliku mp o nowe dane po ich wczytaniu -
        w praktyce dodaje nowe dane do zmiennej zawartosc
        """
        self.zawartosc.extend(aaa)

    def dodajplik(self, nazwapliku):
        """
        Dodaje nowy plik z ktorego wlasnie wczytywane sa dane i ustala jego dokladnosc na 0
        co oznacza ze dokladnosc trzeba pozniej ustalic
        """
        self.plikDokladnosc[nazwapliku] = 0
        return

    def ustawDokladnosc(self, nazwaPliku, dokladnosc):
        self.plikDokladnosc[nazwaPliku] = dokladnosc + ';' + self.plikHash[nazwaPliku]

    def ustawObszary(self):
        # ustala zamontowane obszary oraz ustawia je pod zmienna self.obszary,
        # tam potem mozna sprawdzic do ktorego obszaru nalezy dany punkt/wielokat
        tmp_obszary = set()
        for a_obsz in (obszar for obszar in self.plikizMp if obszar.startswith('UMP')):
            wyodrebniony_obszar = a_obsz.split(os.sep)[0].split('-')[-1]
            tmp_obszary.add(wyodrebniony_obszar)
        self.obszary = Obszary(tmp_obszary, self.Zmienne)
        return 0

    def zbuduj_dozwolone_obszary_dla_plikow(self):
        # tworzymy zbior obszarow dla plikow ktore sa zamontowane + plik z granicami. Ma to zabezpieczac
        # w przypadku gdybysmy przez pomylke wpisali do Plik= obszar spoza ktorego byly montowane pliki. Powodowalo
        # to usuwanie wszystkich danych z danego pliku.
        tmp_pliki = []
        for nazwa_pliku in self.plikizMp:
            if nazwa_pliku.startswith('UMP-'):
                tmp_pliki.append(os.path.split(os.path.split(nazwa_pliku)[0]))
            else:
                tmp_pliki.append(nazwa_pliku)
        self.dozwolone_obszary_dla_plikow = set(tmp_pliki)

    def czy_nazwa_obszar_dla_pliku_jest_dozwolony(self, nazwa_pliku):
        if nazwa_pliku.startswith('UMP'):
            return os.path.split(os.path.split(nazwa_pliku)[0]) in self.dozwolone_obszary_dla_plikow
        return nazwa_pliku in self.dozwolone_obszary_dla_plikow

    def zwaliduj_sciezki_do_plikow(self):
        if not self.dozwolone_obszary_dla_plikow:
            self.zbuduj_dozwolone_obszary_dla_plikow()
        for plik in self.plikizMp:
            if not self.sprawdz_poprawnosc_sciezki(plik):
                self.sciezka_zwalidowana.add(plik)

    def cyfryHash(self, liniazCyframiHashem, zaokraglij):
        """
        Wczytuje dokladnosc danego pliku oraz hash tego pliku zapisany w pliku mp. Nastepnie otwiera plik z dysku.
        Jesli oba hashe sa sobie rowne wtedy zwraca 0, w przeciwnym wypadku 1. Gdy nie ma hasha - jest pusty zwraca 2
        """
        plik, dokladnosc, wartosc_hash, Miasto = liniazCyframiHashem.strip().split(';', 4)
        if zaokraglij != '0':
            dokladnosc = zaokraglij

        self.plikDokladnosc[plik] = dokladnosc
        self.plikDokladnosc[self.plik_nowosci_txt] = dokladnosc
        self.plikDokladnosc[self.plik_nowosci_pnt] = dokladnosc
        # slownik z kluczami w postaci nazwy pliku a haslami jest zawartosc pliku
        if Miasto != '':
            self.plikizMp[plik] = ['MD5HASH=' + wartosc_hash + '\n']
            self.plikizMp[plik].append('Miasto=' + Miasto + '\n')
            self.plikizMp[plik].append('\n')
            self.osobne_pliki_dla_miast.append(plik)
        else:
            self.plikizMp[plik] = ['MD5HASH=' + wartosc_hash + '\n']
        if wartosc_hash == '':
            return 2

        if plik.find('granice-czesciowe.txt') > 0:
            plikdootwarcia = plik
        else:
            plikdootwarcia = os.path.join(self.Zmienne.KatalogzUMP, plik)

        with open(plikdootwarcia, 'rb') as f:
            if hashlib.md5(f.read()).hexdigest() != wartosc_hash:
                return 1
            return 0

    # def ustawDomyslneMiasta(self, liniazMiastami):
    #     miasto, plik = liniazMiastami.split(';')
    #     self.plikizMp[plik].append('Miasto=' + miasto)
    #     return 0

    @staticmethod
    def zaokraglij(DataX, dokladnosc):
        # DataX ma postac (xx.xxxxx,yy.yyyyy),(xx.xxxxx,yy.yyyyy)
        # wartosci -1 lub 0 byly ustawiane dla plikow pustych, albo takich dla ktorych nie mozna bylo
        # odczytac dokladnosci.
        # W takim przypadku wpisz tam co zostalo zapisane przez mapedit
        if dokladnosc not in ('5', '6'):
            return DataX
        if DataX[9] == ',' and dokladnosc == '5' or DataX[10] == ',' and dokladnosc == '6':
            return DataX
        lista_wspolrzednych = DataX[1:-1].split('),(')
        noweData = ''
        dokFormat = '%.5f'
        if dokladnosc == '6':
            dokFormat = '%.6f'
        for para_wspolrzednych in lista_wspolrzednych:
            X, Y = para_wspolrzednych.split(',')
            X = dokFormat % float(X)
            Y = dokFormat % float(Y)
            noweData = noweData + ',(' + X + ',' + Y + ')'
        return noweData.lstrip(',')

    def sprawdz_poprawnosc_sciezki(self, sciezka):
        if not self.czy_nazwa_obszar_dla_pliku_jest_dozwolony(sciezka):
            return 1
        if sciezka in self.sciezka_zwalidowana:
            return 0
        if 'granice-czesciowe' in sciezka or 'narzedzia' + os.sep + 'granice.txt' in sciezka:
            self.sciezka_zwalidowana.add(sciezka)
            return 0
        skladowe = sciezka.split(os.sep)
        if len(skladowe) != 3:
            return 1
        elif os.path.isdir(os.path.join(self.Zmienne.KatalogzUMP, sciezka)):
            return 1
        elif not skladowe[0].startswith('UMP-'):
            return 1
        elif skladowe[1] != 'src':
            return 1
        elif skladowe[2] == '':
            return 1
        else:
            self.sciezka_zwalidowana.add(sciezka)
            return 0

    def plikNormalizacja(self, nazwa_pliku):
        """pliki pod windows nie sa case sensitive, dlatego trzeba kombinowac ze zmianami nazw"""
        if nazwa_pliku in self.plikizMp:
            return nazwa_pliku
        else:
            # no dobra prosto sie nie udalo, nie ma nazwy pliku w pliku mp, trzeba przeiterowac po wszystkich plikach i
            # sprawdzic czy cos pasuje, robiac przy okazji lowercase
            for abc in self.plikizMp:
                if abc.lower() == nazwa_pliku.lower():
                    # znalazles nazwe pliku w lowercase, zastap wiec nazwe pliku ta znaleziona
                    return abc
            # nie znalazl nic, zwroc wiec oryginalna nazwe pliku
            return nazwa_pliku

    def stworz_misc_info(self, dane_do_zapisu):
        # jesli dla poi mamy przypisany plik txt, wtedy nie tworz MiscInfo
        if dane_do_zapisu['Plik'].endswith('.txt') or 'Komentarz' not in dane_do_zapisu \
                or dane_do_zapisu['Type'] in City.rozmiar2Type:
            return dane_do_zapisu

        punkty_z_wysokoscia = ('0x6616', '0x6617',)
        skroty_dla_wysokosci = (';wys=', ';wys:')
        skroty = OrderedDict({';https://': ';', ';http://': ';', ';fb://': ';fb://', ';fb:': ';fb:', ';fb=': ';fb=',
                              ';wiki://': ';wiki://', ';wiki=': ';wiki=', ';wiki:': ';wiki:'})
        przedrostek = OrderedDict({';https://': 'url=', ';http://': 'url=', ';fb://': 'fb=', ';fb:': 'fb=',
                                   ';fb=': 'fb=', ';wiki://': 'wiki=', ';wiki=': 'wiki=', ';wiki:': 'wiki='})
        tmp_komentarz = []

        if dane_do_zapisu['Type'] in punkty_z_wysokoscia:
            for skrot_dla_wys in skroty_dla_wysokosci:
                if 'Komentarz' not in dane_do_zapisu:
                    break
                for wysokosc_w_komentarzu in \
                        [wys for wys in dane_do_zapisu['Komentarz'] if wys.startswith(skrot_dla_wys)]:
                    dane_do_zapisu['StreetDesc'] = wysokosc_w_komentarzu.split(skrot_dla_wys, 1)[1]
                    dane_do_zapisu['Komentarz'].remove(wysokosc_w_komentarzu)
                    if not dane_do_zapisu['Komentarz']:
                        del(dane_do_zapisu['Komentarz'])
            return dane_do_zapisu
        else:
            for linia_komentarza in dane_do_zapisu['Komentarz']:
                czy_dodac_linie_do_tmp_komentarz = True
                for skrot in skroty:
                    if linia_komentarza.startswith(skrot):
                        if 'MiscInfo' in dane_do_zapisu:
                            self.stderrorwrite(('Komentarz sugeruje dodanie linka %s,\nale MiscInfo juz istnieje: %s.\nPozostawiam niezmienione i zostawiam komentarz!\n' % (
                                                   linia_komentarza, dane_do_zapisu['MiscInfo'])))
                            czy_dodac_linie_do_tmp_komentarz = True
                        else:
                            dane_do_zapisu['MiscInfo'] = przedrostek[skrot] + \
                                                         linia_komentarza.split(skroty[skrot], 1)[1]
                            czy_dodac_linie_do_tmp_komentarz = False
                        break
                if czy_dodac_linie_do_tmp_komentarz:
                    tmp_komentarz.append(linia_komentarza)
            if tmp_komentarz:
                dane_do_zapisu['Komentarz'] = tmp_komentarz
            else:
                del dane_do_zapisu['Komentarz']
            return dane_do_zapisu

    def procesuj_rekordy_mp(self, dane_do_zapisu):
        if self.args.cityidx:
            dane_do_zapisu = self.koreguj_miasto_przy_pomocy_indeksow_miast(dane_do_zapisu)
        # iterujemy po kolejnych linijkach rekordu pliku mp
        if self.args.extratypes:
            dane_do_zapisu = self.zamien_type_na_orig_type(dane_do_zapisu)
        if dane_do_zapisu['POIPOLY'] == '[POLYLINE]' or dane_do_zapisu['POIPOLY'] == '[POLYGON]':
            dane_do_zapisu = self.modyfikuj_plik_dla_polygon_polyline(dane_do_zapisu)
            dane_do_zapisu = self.zaokraglij_klucze_ze_wspolrzednymi(dane_do_zapisu)
            self.zapiszTXT(dane_do_zapisu)
        elif dane_do_zapisu['POIPOLY'] == '[POI]':
            if dane_do_zapisu['Type'] in City.rozmiar2Type:
                dane_do_zapisu = self.koreguj_wpisy_dla_miast(dane_do_zapisu)
            dane_do_zapisu = self.modyfikuj_plik_dla_poi(dane_do_zapisu)
            dane_do_zapisu = self.zaokraglij_klucze_ze_wspolrzednymi(dane_do_zapisu)
            dane_do_zapisu = self.przenies_otwarte_i_entrypoint_do_komentarza(dane_do_zapisu)
            dane_do_zapisu = self.stworz_misc_info(dane_do_zapisu)
            if hasattr(self.args, 'standaryzuj_komentarz') and self.args.standaryzuj_komentarz:
                dane_do_zapisu = self.standaryzuj_otwarte_i_entrypoint(dane_do_zapisu)
            self.zapiszPOI(dane_do_zapisu)

    def zapiszPOI(self, daneDoZapisu):
        komentarz_w_pliku_pnt = list()
        rekord_danych_do_mp = list()
        if daneDoZapisu['Plik'].endswith('.txt'):
            for klucz_danych_do_zapisu in (klucze for klucze in daneDoZapisu if not klucze.startswith('Plik')):
                if klucz_danych_do_zapisu == 'Komentarz':
                    for tmpbbb in daneDoZapisu['Komentarz']:
                        rekord_danych_do_mp.append(tmpbbb + '\n')
                elif klucz_danych_do_zapisu == 'POIPOLY':
                    rekord_danych_do_mp.append('[POI]\n')
                elif klucz_danych_do_zapisu.startswith('Data'):
                    rekord_danych_do_mp.append(klucz_danych_do_zapisu.split('_')[0] + '=' +
                                                               daneDoZapisu[klucz_danych_do_zapisu] + '\n')

                # wartosci bez kluczy doddane jako dziwne zapisz tutaj
                elif klucz_danych_do_zapisu == 'Dziwne':
                    for tmpbbb in daneDoZapisu['Dziwne']:
                        rekord_danych_do_mp.append(tmpbbb + '\n')
                else:
                    rekord_danych_do_mp.append(klucz_danych_do_zapisu + '=' +
                                                               daneDoZapisu[klucz_danych_do_zapisu] + '\n')

            rekord_danych_do_mp.append('[END]\n')
            rekord_danych_do_mp.append('\n')

        # w przypadku gdy mamy do czynienia z miastem
        elif daneDoZapisu['Type'] in City.rozmiar2Type:
            daneDoZapisu = self.koreguj_wpisy_dla_miast(daneDoZapisu)
            # nie wiem czy jest Data0 1, 2 itd, więc sprawdzam tak i biorę pierwsza wartosc
            tmpData = [b for b in daneDoZapisu if b.startswith('Data')]
            # print('Wielokrotne DataX= dla miasta o wspolrzednych %s'%tmpData[0],file=sys.stderr)
            if 'Label' not in daneDoZapisu:
                self.stderrorwrite('Brakuje nazwy miasta dla wspolrzednych %s' % daneDoZapisu[tmpData[0]])
                daneDoZapisu['Label'] = ''
            else:
                daneDoZapisu['Label'] = daneDoZapisu['Label'].replace(',', '°')
            if 'Rozmiar' not in daneDoZapisu:
                daneDoZapisu['Rozmiar'] = City.type2Rozmiar[daneDoZapisu['Type']]

            szerokosc, dlugosc = daneDoZapisu[tmpData[0]].lstrip('(').rstrip(')').split(',')
            liniaDoPnt = '  ' + szerokosc + ',  ' + dlugosc + ',{:>3}'.format(daneDoZapisu['Rozmiar']) + ',' + \
                         daneDoZapisu['Label']+'\n'
            if 'Komentarz' in daneDoZapisu:
                for tmpbbb in daneDoZapisu['Komentarz']:
                    komentarz_w_pliku_pnt.append(tmpbbb+'\n')
            # dodaj plik do automatycznego przenoszenia plikow poi
            # auto_poi_kolejka_wejsciowa.put(daneDoZapisu)
            if komentarz_w_pliku_pnt:
                rekord_danych_do_mp = komentarz_w_pliku_pnt + [liniaDoPnt]
            else:
                rekord_danych_do_mp = [liniaDoPnt]
        else:
            # pozostale poi powinny powinny byc zapisane w plikach pnt, ale nie moga to byc pliki cities
            # jesli bedzie to plik cities, zamien na _nowosci.pnt
            try:
                if int(daneDoZapisu['Type'], 16) > int('0x1100', 16) and daneDoZapisu['Plik'].find('cities-') > 0:
                    daneDoZapisu['Plik'] = self.plik_nowosci_pnt
            except ValueError:
                # jezeli ktos sie pomylil i zamiast Typ wpisal Type=alias to program sie tutaj wylozy, obslugujemy to.
                self.stderrorwrite('Nieznany Type:%s. Prawdopodobnie literowka Type zamiast Typ.'
                                  % daneDoZapisu['Type'])

            tmpData = [b for b in daneDoZapisu if b.startswith('Data')]
            if 'Miasto' not in daneDoZapisu:
                daneDoZapisu['Miasto'] = ''
            if 'Typ' not in daneDoZapisu:
                # obslugujemy tworzenie typu po nazwie
                if 'Label' in daneDoZapisu:
                    zgadnietyTypDokladny, zgdanietyTypPoAliasie = \
                        self.tabela_konwersji_typow.zwrocTypPoLabel(daneDoZapisu['Label'], daneDoZapisu['Type'])
                    if zgadnietyTypDokladny:
                        daneDoZapisu['Typ'] = zgadnietyTypDokladny
                    else:
                        if zgdanietyTypPoAliasie.startswith('0x'):
                            self.stderrorwrite('Nieznany alias dla Type=%s.\nPunkt o wspolrzednych %s' %
                                               (daneDoZapisu['Type'], daneDoZapisu[tmpData[0]]))
                            daneDoZapisu['Typ'] = '0x0'
                        else:
                            daneDoZapisu['Typ'] = zgdanietyTypPoAliasie.upper()
                else:
                    try:
                        daneDoZapisu['Typ'] = self.tabela_konwersji_typow.type2Alias[daneDoZapisu['Type']][0].upper()
                    except KeyError:
                        self.stderrorwrite('Nieznany alias dla Type=%s. Punkt o wspolrzednych %s' %
                                           (daneDoZapisu['Type'], daneDoZapisu[tmpData[0]]))
                        daneDoZapisu['Typ'] = '0x0'
            else:
                if daneDoZapisu['Typ'].startswith('0x'):
                    pass
                elif daneDoZapisu['Typ'] not in self.tabela_konwersji_typow.alias2Type:
                    self.stderrorwrite('Nieznany typ POI %s, w punkcie %s.' %
                                       (daneDoZapisu['Typ'], daneDoZapisu[tmpData[0]]))
            if 'EndLevel' not in daneDoZapisu:
                daneDoZapisu['EndLevel'] = '0'
            if 'Label' not in daneDoZapisu:
                daneDoZapisu['Label'] = ''
            else:
                daneDoZapisu['Label'] = daneDoZapisu['Label'].replace(',', '°')
            szerokosc, dlugosc = daneDoZapisu[tmpData[0]].lstrip('(').rstrip(')').split(',')
            UlNrTelUrl = self.stworz_ulice_nr_tel_url(daneDoZapisu)
            liniaDoPnt = '  ' + szerokosc + ',  ' + dlugosc + ',  ' + daneDoZapisu['EndLevel'] + ',' + \
                       daneDoZapisu['Label'] + ',' + UlNrTelUrl + ',' + daneDoZapisu['Miasto'] + ',' + \
                       daneDoZapisu['Typ']
            if 'KodPoczt' in daneDoZapisu:
                liniaDoPnt = liniaDoPnt + ',' + daneDoZapisu['KodPoczt'] + '\n'
            else:
                liniaDoPnt += '\n'
            if 'Komentarz' in daneDoZapisu:
                for tmpbbb in daneDoZapisu['Komentarz']:
                    komentarz_w_pliku_pnt.append(tmpbbb + '\n')
            if komentarz_w_pliku_pnt:
                rekord_danych_do_mp = komentarz_w_pliku_pnt + [liniaDoPnt]
            else:
                rekord_danych_do_mp = [liniaDoPnt]
        self.auto_pliki_dla_poi.dodaj_plik_dla_poi(daneDoZapisu)
        self.plikizMp[daneDoZapisu['Plik']] += rekord_danych_do_mp

    def zapiszTXT(self, daneDoZapisu):
        rekord_danych_do_mp = list()
        # workaround dla Floors
        # if 'Floors' in daneDoZapisuKolejnoscKluczy:
        #     daneDoZapisuKolejnoscKluczy.remove('Floors')
        #     for abcd in daneDoZapisuKolejnoscKluczy:
        #         if abcd.find('Data')>=0:
        #             data_index=daneDoZapisuKolejnoscKluczy.index(abcd)
        #             daneDoZapisuKolejnoscKluczy.insert(data_index,'Floors')
        #             break

        # if 'Floors' in daneDoZapisuKolejnoscKluczy:
        #     daneDoZapisuKolejnoscKluczy.remove('Floors')
        #     daneDoZapisuKolejnoscKluczy.append('Floors')

        for klucz_z_dane_do_zapisu in (klucze for klucze in daneDoZapisu if not klucze.startswith('Plik')):
            if klucz_z_dane_do_zapisu in ('Komentarz', 'Dziwne',):
                for wartosc_klucza in daneDoZapisu[klucz_z_dane_do_zapisu]:
                    rekord_danych_do_mp.append(wartosc_klucza + '\n')
                    # self.plikizMp[daneDoZapisu['Plik']].append(wartosc_klucza + '\n')
            elif klucz_z_dane_do_zapisu == 'POIPOLY':
                # self.plikizMp[daneDoZapisu['Plik']].append(daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')
                rekord_danych_do_mp.append(daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')
            elif klucz_z_dane_do_zapisu.startswith('Data'):
                # dla plikow tekstowych mozliwe jest wielokrotne Data0, Data1 itd. Poniewaz przechowuje takie dane
                # w slowniku a tam klucze nie moga sie powtarzac dlatego
                # mamy Data w postaci Data0_0, Data0_1, Data0_2 itd, dla rozroznienia, dlatego przy zapisie do
                # pliku trzeba do _ usunać
                # stad tez mamy tmpaaa.split('_')[0]
                #self.plikizMp[daneDoZapisu['Plik']].append(klucz_z_dane_do_zapisu.split('_')[0] + '=' +
                #                                           daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')
                rekord_danych_do_mp.append(klucz_z_dane_do_zapisu.split('_')[0] + '=' +
                                                           daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')

            elif klucz_z_dane_do_zapisu == 'Miasto':
                # najpierw sprawdz czy lista zawiera jakies elementy, aby wykluczyc grzebanie w pustej
                if self.plikizMp[daneDoZapisu['Plik']]:
                    # w przypadku gdy miasto ma oddzielny plik wtedy na drugim miejscu stoi Miasto=,
                    # (na pierwszym - indeks 0) stoi suma kontrolna danego pliku sprawdz czy
                    # wpisane i to na gorze sa takie same oraz dodatkowo sprawdz czy ktos nie zrobil wpisy w stylu
                    # Miasto=, jesli tak to zignoruj oba przypadki
                    if daneDoZapisu['Miasto'] == '':
                        pass
                    elif daneDoZapisu['Plik'] in self.osobne_pliki_dla_miast \
                            and self.plikizMp[daneDoZapisu['Plik']][1].strip().split('Miasto=')[-1] == \
                            daneDoZapisu['Miasto']:
                        pass
                    else:
                        rekord_danych_do_mp.append(klucz_z_dane_do_zapisu + '='
                                                   + daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')
                else:
                    rekord_danych_do_mp.append(klucz_z_dane_do_zapisu + '='
                                               + daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')
            else:
                rekord_danych_do_mp.append(klucz_z_dane_do_zapisu + '='
                                           + daneDoZapisu[klucz_z_dane_do_zapisu] + '\n')

        rekord_danych_do_mp.append('[END]\n')
        rekord_danych_do_mp.append('\n')
        self.plikizMp[daneDoZapisu['Plik']] += rekord_danych_do_mp
        # return rekord_danych_do_mp

    def stworz_ulice_nr_tel_url(self, daneDoZapisu):
        if 'MiscInfo' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            if 'HouseNumber' not in daneDoZapisu:
                daneDoZapisu['HouseNumber'] = ''
            if 'Phone' not in daneDoZapisu:
                daneDoZapisu['Phone'] = ''
            return daneDoZapisu['StreetDesc'].replace(',', '°') + ';' + \
                         daneDoZapisu['HouseNumber'].replace(',', '°') + ';' + \
                         daneDoZapisu['Phone'].replace(',', '°') + ';' + \
                         daneDoZapisu['MiscInfo'].replace(',', '°')
        elif 'Phone' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            if 'HouseNumber' not in daneDoZapisu:
                daneDoZapisu['HouseNumber'] = ''
            return daneDoZapisu['StreetDesc'].replace(',', '°') + ';' + \
                         daneDoZapisu['HouseNumber'].replace(',', '°') + ';' + \
                         daneDoZapisu['Phone'].replace(',', '°')
        elif 'HouseNumber' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            return daneDoZapisu['StreetDesc'].replace(',', '°') + ';' + \
                         daneDoZapisu['HouseNumber'].replace(',', '°')
        elif 'StreetDesc' in daneDoZapisu:
            return daneDoZapisu['StreetDesc'].replace(',', '°')
        else:
            return ''

    def zbuduj_city_idx_zwroc_format(self, zawartosc_pliku_mp):
        city_idx_miasto = []
        if zawartosc_pliku_mp.find('[END-Cities]') >= 0:
            format_indeksow = '[CITIES]'
            cities, zawartosc_pliku_mp = zawartosc_pliku_mp.split('[END-Cities]')
            self.stdoutwrite('Wczytuję indeksy miast')
            listaCities = cities.split('[Cities]')[1].strip().split('\n')
            for indeks_miasta in range(0, len(listaCities), 2):
                nrCity, nazwaMiastaIdx = listaCities[indeks_miasta].split('=', 1)
                if nazwaMiastaIdx.count('=') > 0:
                    self.stderrorwrite('Bledna nazwa miasta: ' + nazwaMiastaIdx + '. Znak "=" w nazwie.')
                city_idx_miasto.append(nazwaMiastaIdx)
                if city_idx_miasto.index(nazwaMiastaIdx) != (int(nrCity.split('City')[1]) - 1):
                    self.stderrorwrite('Jakis blad w indeksach miast!')

        # print(plikMp.cityIdxMiasto)
        elif zawartosc_pliku_mp.find('CityName=') > 0 and zawartosc_pliku_mp.find('RegionName=') > 0 \
                and zawartosc_pliku_mp.find('CountryName=') > 0:
            format_indeksow = 'CityName'
        else:
            return '', city_idx_miasto, zawartosc_pliku_mp
        return format_indeksow, city_idx_miasto, zawartosc_pliku_mp

    def sprawdz_cyfry_i_hashe_plikow(self, zawartoscPlikuMp, args):
        if zawartoscPlikuMp.find('[CYFRY]') >= 0:
            dokladnosci_hashe_plikow, zawartoscPlikuMp = zawartoscPlikuMp.split('[CYFRY]')[1].split('[END]', 1)
            self.stdoutwrite('Wczytuje dokladnosc pliku i sprawdzam sumy kontrolne.')
            for dokladnosc_i_hash_pliku in dokladnosci_hashe_plikow.strip().split('\n'):
                try:
                    if self.cyfryHash(dokladnosc_i_hash_pliku, args.X):
                        if args.hash:
                            self.stderrorwrite('[...] %s [FALSE].' % dokladnosc_i_hash_pliku.split(';')[0])
                        else:
                            self.stderrorwrite('[...] %s [FALSE].\nSuma kontrolna nie zgadza sie albo jej brak.'
                                               '\nUzyj opcji -nh aby zdemontowac pomimo tego' %
                                               dokladnosc_i_hash_pliku.split(';')[0])
                            return False, zawartoscPlikuMp.strip()
                    else:
                        self.stdoutwrite('[...] %s [OK].' % dokladnosc_i_hash_pliku.split(';')[0])
                except FileNotFoundError:
                    self.stderrorwrite('[...] %s [FALSE].\nPlik nie istnieje w zrodlach. Nie moge kontynuowac.'
                                       % dokladnosc_i_hash_pliku.split(';')[0])
                    return False, zawartoscPlikuMp.strip()
        else:
            self.stderrorwrite('Nie znalazlem informacji na temat zamontowanych plikow, nie moge kontynuowac.')
            return False, zawartoscPlikuMp.strip()
        return True, zawartoscPlikuMp.strip()

    def przeniesc_zawartosc_nowosci_pnt_do_plikow(self):
        # punkty w nowosciach moga miec komentarz, nalezy wiec to uwzglednic
        komentarz_w_nowosci = []
        # tymczasowy plik nowosci, do ktorego bedziemy kopiowac nieznane punkty
        tmp_nowosci = []
        for punkt_z_nowosci_pnt in self.plikizMp['_nowosci.pnt']:
            # najpierw sprawdzmy czy przez przypadek nie ma komentarza, jesli jest skopiuj
            # go do zmiennej i przejdz dalej
            if punkt_z_nowosci_pnt.startswith(';'):
                komentarz_w_nowosci.append(punkt_z_nowosci_pnt)
            else:
                bbb = punkt_z_nowosci_pnt.split(',')
                bbb_len = len(bbb)
                UMP_obszar = self.obszary.zwroc_obszar(float(bbb[0]), float(bbb[1]))
                if bbb_len in (4, 7, 8,):
                    if bbb_len == 4:
                        pnt_typ = 'MIASTO'
                    else:
                        pnt_typ = bbb[6].strip()
                    plik_dla_typu_w_obszarze = self.auto_pliki_dla_poi.zwroc_plik_dla_typu(UMP_obszar, pnt_typ)
                    if UMP_obszar != 'None' and plik_dla_typu_w_obszarze:
                        self.stdoutwrite('%s --> %s' %(punkt_z_nowosci_pnt.strip(), plik_dla_typu_w_obszarze))
                        # najpierw usuwamy i dodajemy komentarze
                        for komentarz in komentarz_w_nowosci:
                            self.plikizMp[plik_dla_typu_w_obszarze].append(komentarz)
                        self.plikizMp[plik_dla_typu_w_obszarze].append(punkt_z_nowosci_pnt)
                        komentarz_w_nowosci = []
                    else:
                        tmp_nowosci += komentarz_w_nowosci
                        tmp_nowosci.append(punkt_z_nowosci_pnt)
                        komentarz_w_nowosci = []
                else:
                    tmp_nowosci.append(punkt_z_nowosci_pnt)
                # kopiujemy tmp_nowosci na oryginalne _nowosci.pnt
                self.plikizMp['_nowosci.pnt'] = tmp_nowosci[:]

    def zwroc_rekord_pliku_mp(self, string_z_rekordem):
        dane_do_zapisu = OrderedDict()
        ostatni_id_dla_data = {'Data0': -1, 'Data1': -1, 'Data2': -1, 'Data3': -1, 'Data4': -1}
        for linia in string_z_rekordem.strip().split('\n'):
            linia = linia.strip()
            if 'POIPOLY' not in dane_do_zapisu:
                if linia.startswith(';'):
                    if len(linia) > 1:
                        if 'Komentarz' in dane_do_zapisu:
                            dane_do_zapisu['Komentarz'].append(linia)
                        else:
                            dane_do_zapisu['Komentarz'] = [linia]
                elif linia == '[POI]' or linia == '[POLYGON]' or linia == '[POLYLINE]':
                    dane_do_zapisu['POIPOLY'] = linia
                else:
                    self.stderrorwrite('Dziwna linia %s w rekordach\n %s.' % (linia, string_z_rekordem))
            else:
                if '=' in linia:
                    klucz, wartosc = linia.split('=', 1)
                    klucz = klucz.strip()
                    if klucz[0:4] == 'Data':
                        ostatni_id_dla_data[klucz] += 1
                        klucz = klucz + '_' + str(ostatni_id_dla_data[klucz])
                    dane_do_zapisu[klucz] = wartosc
                else:
                    self.stderrorwrite('Dziwna linia %s w rekordach\n %s.' % (linia, string_z_rekordem))
                    if 'Dziwne' in dane_do_zapisu:
                        dane_do_zapisu['Dziwne'].append(linia)
                    else:
                        dane_do_zapisu['Dziwne'] = [linia]
        return dane_do_zapisu

    def zaokraglij_klucze_ze_wspolrzednymi(self, dane_do_zapisu):
        dokladnosc = self.plikDokladnosc[dane_do_zapisu['Plik']]
        for klucz in (a for a in dane_do_zapisu if a.startswith('Data') or a.startswith('EntryPoint')):
            dane_do_zapisu[klucz] = self.zaokraglij(dane_do_zapisu[klucz], dokladnosc)
        return dane_do_zapisu

    @staticmethod
    def standaryzuj_otwarte_i_entrypoint(dane_do_zapisu):
        """
        Funkcja standaryzuje wpisy entrypoints in otwarte, tak aby w calym projekcie bylo to ujednolicone
        Robione jest to poprzez korekte komentarza przy demontazu
        Poprawne definicje to: ;;EntryPoint:, ;otwarte:
        dane_do_zapisu['Komentarz'] zawiera komentarze oddzielone \n
        """
        if not 'Komentarz' in dane_do_zapisu:
            return dane_do_zapisu
        tmp_kom = ''.join(dane_do_zapisu['Komentarz'])
        if 'otwarte' not in tmp_kom and 'entrypoint' not in tmp_kom.lower():
            return dane_do_zapisu
        entry_point_defs = [ep for ep in (';;EntryPoint:', ';;EntryPoint=',) if ep in tmp_kom]
        otwarte_defs = [otw for otw in (';otwarte:', ';Otwarte:', ';otwarte=', ';Otwarte=',) if otw in tmp_kom]
        ep_set = set([ep.lstrip(';') for ep in entry_point_defs])
        otw_set = set([otw.lstrip(';') for otw in otwarte_defs])
        # jeśli nie ma ani otwarte ani entrypoint w komentarzu nie idź dalej
        if not ep_set and not otw_set:
            return dane_do_zapisu

        komentarz = list()
        for linia_z_komentarza in dane_do_zapisu['Komentarz']:
            # sprawdźmy co tam właściwie mamy
            znaleziony_element = ''
            elem_end = ''
            entrypoint_czy_otwarte = ''
            for elem in entry_point_defs + otwarte_defs:
                # linia musi się zaczynać dokłądnie jak dany element, czyli z jednym średnikiem albo dwoma
                # w zależności od tego czy to otwarte czy entrypoint. Jak jest więcej średników to znaczy
                # że to komentarz, stąd wyrzucamy ;;otwarte i ;;;Entrypoint, bo to sugueruje że zakomentowano
                # rekord w pliku pnt
                if linia_z_komentarza.startswith(elem) and not linia_z_komentarza.startswith(';' + elem):
                    elem_end = linia_z_komentarza.split(elem, 1)[-1].strip()
                    entrypoint_czy_otwarte = elem
                    break
            if not elem_end or not entrypoint_czy_otwarte:
                komentarz.append(linia_z_komentarza)
            elif entrypoint_czy_otwarte in entry_point_defs:
                komentarz.append(';;EntryPoint: ' + elem_end)
            else:
                komentarz.append(';otwarte: ' + elem_end)

        # komentarz[-1] = komentarz[-1].rstrip()
        dane_do_zapisu['Komentarz'] = komentarz
        return dane_do_zapisu

    @staticmethod
    def przenies_otwarte_i_entrypoint_do_komentarza(dane_do_zapisu):
        przedrostek = {'EntryPoint': ';;EntryPoint: ', 'Otwarte': ';otwarte: '}
        for key in ('EntryPoint', 'Otwarte',):
            if key in dane_do_zapisu:
                if 'Komentarz' in dane_do_zapisu:
                    dane_do_zapisu['Komentarz'].append(przedrostek[key] + dane_do_zapisu[key])
                else:
                    dane_do_zapisu['Komentarz'] = [przedrostek[key] + dane_do_zapisu[key]]
                    dane_do_zapisu.move_to_end('Komentarz', last=False)
                del dane_do_zapisu[key]
        return dane_do_zapisu

    def modyfikuj_plik_dla_rekordu_mp(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] == '[POI]':
            return self.modyfikuj_plik_dla_poi(dane_do_zapisu)
        else:
            return self.modyfikuj_plik_dla_polygon_polyline(dane_do_zapisu)

    def modyfikuj_plik_dla_polygon_polyline(self, dane_do_zapisu):
        # jeśli Plik jest ale kończy się na pnt wtedy zamień wartość na nowosci
        if 'Plik' in dane_do_zapisu:
            dane_do_zapisu['Plik'] = self.plikNormalizacja(dane_do_zapisu['Plik'])
            if dane_do_zapisu['Plik'].endswith('.pnt'):
                self.stderrorwrite('Dla polyline/polygon ustawiono plik %s. Zmieniam na _nowosci.txt'
                                   % dane_do_zapisu['Plik'])
                dane_do_zapisu['Plik'] = self.plik_nowosci_txt
            if self.sprawdz_poprawnosc_sciezki(dane_do_zapisu['Plik']):
                if self.args.autopolypoly:
                    self.stderrorwrite('Niepoprawna sciezka do pliku  \"Plik={!s}\". Probuje zgadnac.'.format(
                        dane_do_zapisu['Plik']))
                    del(dane_do_zapisu['Plik'])
                else:
                    self.stderrorwrite('Niepoprawna sciezka do pliku  \"Plik={!s}\". Ustawiam _nowosci.txt.'.format(
                        dane_do_zapisu['Plik']))
                    dane_do_zapisu['Plik'] = self.plik_nowosci_txt
                    return dane_do_zapisu

        # jesli Plik nie jest obecny w danych do zapisu
        if 'Plik' not in dane_do_zapisu:
            # ponizej dodajemy plik bo i tak to powstanie, a teraz go nie ma
            # tutaj dodac sprawdzanie czy opcja autopoly jest wlaczona
            if self.args.autopolypoly:
                czy_w_jednym_obszarze, obszar_dla_poly, wspolrzedne = \
                    self.obszary.czy_wspolrzedne_w_jednym_obszarze(dane_do_zapisu)
                if czy_w_jednym_obszarze:
                    dane_do_zapisu['Plik'] = self.autoobszary.zwroc_plik_dla_poly(dane_do_zapisu['POIPOLY'],
                                                                                  dane_do_zapisu['Type'],
                                                                                  obszar_dla_poly,
                                                                                  wspolrzedne)
                    if self.plik_nowosci_txt not in dane_do_zapisu['Plik']:
                        self.stdoutwrite(('Przypisuje obiekt do pliku %s' % dane_do_zapisu['Plik']))
                else:
                    dane_do_zapisu['Plik'] = self.plik_nowosci_txt
                    return dane_do_zapisu
            else:
                dane_do_zapisu['Plik'] = self.plik_nowosci_txt
                return dane_do_zapisu

        # jesli jako wartosc plik jest wpisana nieistniejaca w zrodlach pozycja to dodaj go do listy i ustaw mu
        # dokladnosc taka jak dla plikow txt
        if dane_do_zapisu['Plik'] not in self.plikizMp:
            self.plikizMp[dane_do_zapisu['Plik']] = []
            self.plikDokladnosc[dane_do_zapisu['Plik']] = self.plikDokladnosc[self.plik_nowosci_txt]
        return dane_do_zapisu


    def modyfikuj_plik_dla_poi(self, dane_do_zapisu):
        HW = ('0x2000', '0x2001', '0x2100', '0x2101', '0x210f', '0x2110', '0x2111', '0x2200', '0x2201', '0x2202',
              '0x2300', '0x2400', '0x2500', '0x2502', '0x2600', '0x2700',)
        # najpierw sprawdzmy czy plik do zapisu istnieje. Jesli nie to dla punktow autostradowych
        # ustaw plik _nowosci.txt a dla wszystkich inych _nowosci.pnt
        if 'Plik' not in dane_do_zapisu:
            if dane_do_zapisu['Type'] in HW:
                dane_do_zapisu['Plik'] = self.plik_nowosci_txt
            else:
                dane_do_zapisu['Plik'] = self.plik_nowosci_pnt
            return dane_do_zapisu

        # jesli mamy miasto i plik nie jest cities wtedy zamien na nowosci.pnt
        if 'Type' in dane_do_zapisu and dane_do_zapisu['Type'] in City.rozmiar2Type:
            if 'cities-' not in dane_do_zapisu['Plik']:
                dane_do_zapisu['Plik'] = self.plik_nowosci_pnt
                return dane_do_zapisu
        # poi ktore nie sa miastami powinny byc zapisywane w innych plikach niz cities
        try:
            if int(dane_do_zapisu['Type'], 16) > int('0x1100', 16) and 'cities-' in dane_do_zapisu['Plik']:
                dane_do_zapisu['Plik'] = self.plik_nowosci_pnt
                return dane_do_zapisu
        except ValueError:
            # jezeli ktos sie pomylil i zamiast Typ wpisal Type=alias to program sie tutaj wylozy, obslugujemy to.
            self.stderrorwrite('Nieznany Type:%s. Prawdopodobnie literowka Type zamiast Typ.' % dane_do_zapisu['Type'])
            return dane_do_zapisu

        # normalizujemy nazwe pliku, bo moga byc pomieszane duze i male literki
        dane_do_zapisu['Plik'] = self.plikNormalizacja(dane_do_zapisu['Plik'])
        if self.sprawdz_poprawnosc_sciezki(dane_do_zapisu['Plik']):
            if dane_do_zapisu['Type'] in HW:
                self.stderrorwrite(
                    'Niepoprawna sciezka do pliku  \"Plik={!s}\". Zamieniam na _nowosci.txt'.format(
                        dane_do_zapisu['Plik']))
                dane_do_zapisu['Plik'] = self.plik_nowosci_txt
            else:
                self.stderrorwrite(
                    'Niepoprawna sciezka do pliku  \"Plik={!s}\". Zamieniam na _nowosci.pnt'.format(
                        dane_do_zapisu['Plik']))
                dane_do_zapisu['Plik'] = self.plik_nowosci_pnt
            return dane_do_zapisu

        # jesli jako wartosc plik jest wpisana nieistniejaca w zrodlach pozycja to dodaj go do listy i ustaw mu
        # dokladnosc taka jak dla plikow pnt
        if dane_do_zapisu['Plik'] not in self.plikizMp:
            self.plikizMp[dane_do_zapisu['Plik']] = []
            self.plikDokladnosc[dane_do_zapisu['Plik']] = self.plikDokladnosc[self.plik_nowosci_pnt]
        return dane_do_zapisu

    def koreguj_miasto_przy_pomocy_indeksow_miast(self, dane_do_zapisu):
        if 'CityIdx' in dane_do_zapisu:
            dane_do_zapisu['Miasto'] = self.cityIdxMiasto[int(dane_do_zapisu['CityIdx']) - 1]
        elif 'CityName' in dane_do_zapisu:
            dane_do_zapisu['Miasto'] = dane_do_zapisu['CityName']
        # usun zbedne klucze zwiazane z indeksami miast
        for klucz in ('RegionName', 'CountryName', 'DistrictName', 'CityIdx', 'CityName'):
            if klucz in dane_do_zapisu:
                del(dane_do_zapisu[klucz])
        return dane_do_zapisu

    @staticmethod
    def zamien_type_na_orig_type(dane_do_zapisu):
        if 'OrigType' in dane_do_zapisu:
            dane_do_zapisu['Type'] = dane_do_zapisu['OrigType']
            del(dane_do_zapisu['OrigType'])
        return dane_do_zapisu

    def koreguj_wpisy_dla_miast(self, dane_do_zapisu):
         # Miasta < od 1000 dostajš typ 0xe00
        if dane_do_zapisu['Type'] in ('0xf00', '0x1000', '0x1100'):
            dane_do_zapisu['Type'] = '0xe00'
        # miasta > od 1000000 dostaja typ 0x0400
        elif dane_do_zapisu['Type'] in ('0x300', '0x200', '0x100'):
            dane_do_zapisu['Type'] = '0x400'
        if 'Rozmiar' not in dane_do_zapisu:
            dane_do_zapisu['Rozmiar'] = City.type2Rozmiar[dane_do_zapisu['Type']]
        return dane_do_zapisu

    def koreguj_wpisy_dla_poi(self, dane_do_zapisu, dane_do_zapisu_kolejnosc_kluczy):
        tmpData = [dane_do_zapisu[a] for a in dane_do_zapisu if a.startswith['Data']]
        if dane_do_zapisu['POIPOLY'] != '[POI]' or dane_do_zapisu['Type'] in City.rozmiar2Type:
            return dane_do_zapisu, dane_do_zapisu_kolejnosc_kluczy
        if 'Miasto' not in dane_do_zapisu:
            dane_do_zapisu['Miasto'] = ''
        if 'Typ' not in dane_do_zapisu:
            # obslugujemy tworzenie typu po nazwie
            if 'Label' in dane_do_zapisu:
                zgadnietyTypDokladny, zgdanietyTypPoAliasie = \
                    self.tabela_konwersji_typow.zwrocTypPoLabel(dane_do_zapisu['Label'], dane_do_zapisu['Type'])
                if zgadnietyTypDokladny:
                    dane_do_zapisu['Typ'] = zgadnietyTypDokladny
                else:
                    if zgdanietyTypPoAliasie.startswith('0x'):
                        self.stderrorwrite('Nieznany alias dla Type=%s.\nPunkt o wspolrzednych %s' %
                                           (dane_do_zapisu['Type'], dane_do_zapisu[tmpData[0]]))
                        dane_do_zapisu['Typ'] = '0x0'
                    else:
                        dane_do_zapisu['Typ'] = zgdanietyTypPoAliasie.upper()
            else:
                try:
                    dane_do_zapisu['Typ'] = self.tabela_konwersji_typow.type2Alias[dane_do_zapisu['Type']][0].upper()
                except KeyError:
                    self.stderrorwrite('Nieznany alias dla Type=%s. Punkt o wspolrzednych %s' %
                                       (dane_do_zapisu['Type'], dane_do_zapisu[tmpData[0]]))
                    dane_do_zapisu['Typ'] = '0x0'
        else:
            if dane_do_zapisu['Typ'].startswith('0x'):
                pass
            elif dane_do_zapisu['Typ'] not in self.tabela_konwersji_typow.alias2Type:
                self.stderrorwrite('Nieznany typ POI %s, w punkcie %s.' %
                                   (dane_do_zapisu['Typ'], dane_do_zapisu[tmpData[0]]))
        if 'EndLevel' not in dane_do_zapisu:
            dane_do_zapisu['EndLevel'] = '0'
        if len(tmpData) > 1:
            self.stderrorwrite('Wielokrotne DataX= dla POI o wspolrzednych %s' % tmpData[0])
        if 'Label' not in dane_do_zapisu_kolejnosc_kluczy:
            dane_do_zapisu['Label'] = ''
        else:
            dane_do_zapisu['Label'] = dane_do_zapisu['Label'].replace(',', '°')
        return dane_do_zapisu, dane_do_zapisu_kolejnosc_kluczy

    def zamien_przecinki_na_stopnie(self, dane_do_zapisu):
        dane_do_zapisu['Label'] = dane_do_zapisu['Label'].replace(',', '°')
        return dane_do_zapisu

class PlikiDoMontowania(object):
    def __init__(self, katalog_ze_zrodlami, args):
        if not hasattr(args, 'montuj_wedlug_klas'):
            args.montuj_wedlug_klas = 0
        obszary = args.obszary
        self.errOutWriter = errOutWriter(args)
        self.KatalogZeZrodlami = katalog_ze_zrodlami
        self.Obszary = obszary
        self.Pliki = list()
        if not args.trybosmand:
            self.Pliki += ['narzedzia' + os.sep + 'granice.txt']
        for aaa in obszary:
            if os.path.isdir(os.path.join(self.KatalogZeZrodlami, aaa, 'src')):
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.KatalogZeZrodlami, aaa, 'src/*.txt'))]
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.KatalogZeZrodlami, aaa, 'src/*.pnt'))]
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.KatalogZeZrodlami, aaa, 'src/*.adr'))]
            else:
                self.errOutWriter.stderrorwrite('Problem z dostępem do %s.' %
                                                os.path.join(self.KatalogZeZrodlami, aaa, 'src'))
                self.errOutWriter.stderrorwrite('Obszar %s nie istnieje' % aaa)
                raise FileNotFoundError
        # przenosimy zakazy na koniec, aby montowane byly na koncu i aby byly nad drogami a nie pod nimi:
        for plik_z_zakazem in (a for a in self.Pliki if 'zakazy' in a):
            self.Pliki.remove(plik_z_zakazem)
            self.Pliki.append(plik_z_zakazem)

    def Filtruj(self, filtry):
        # montujemy tylko drogi+granice+zakazy, bez radarow
        if filtry.montuj_wedlug_klas:
            highways = [f for f in self.Pliki if f.find('highways') > 0]
            drogi = [f for f in self.Pliki if f.find('drogi') > 0]
            ulice = [f for f in self.Pliki if f.find('ulice') > 0]
            zakazy = [f for f in self.Pliki if f.find('zakazy') > 0]
            self.Pliki = highways + drogi + ulice + zakazy
        elif filtry.tylkodrogi:
            drogi = [f for f in self.Pliki if f.find('drogi') > 0]
            ulice = [f for f in self.Pliki if f.find('ulice') > 0]
            radary = [f for f in self.Pliki if f.find('UMP-radary') >= 0]
            kolej = [f for f in self.Pliki if f.find('kolej.txt') >= 0]
            self.Pliki = drogi + ulice + kolej + radary

        else:
            if not filtry.adrfile:
                self.Pliki = [f for f in self.Pliki if f.find('.adr') < 0]
            if filtry.nocity:
                self.Pliki = [f for f in self.Pliki if f.find('cities') < 0]
            if filtry.nopnt:
                tmp = [f for f in self.Pliki if f.find('cities') > 0]
                self.Pliki = [f for f in self.Pliki if f.find('.pnt') < 0]
                self.Pliki = self.Pliki + tmp
            if filtry.notopo:
                self.Pliki = [f for f in self.Pliki if f.find('topo') < 0]
            if filtry.noszlaki:
                self.Pliki = [f for f in self.Pliki if f.find('szlaki') < 0]
        return

    def ograniczGranice(self, kodowanie):
        with open(os.path.join(self.KatalogZeZrodlami, 'narzedzia' + os.sep + 'granice.txt'),
                  encoding=kodowanie) as granice:
            zawartoscgranice = granice.read().split('[END]\n')
        granicewspolne = []
        for a in self.Obszary:
            for b in zawartoscgranice[:]:
                if b.find(a.split('-')[-1]) > 0:
                    granicewspolne.append(b.strip() + '\n[END]\n\n')
                    zawartoscgranice.remove(b)

        # poniewaz pierwszy element moze zawierac \n na poczatku, to go usuwamy
        # dodatkowo poniewaz dla niektorych obszarow moze nie byc granic, wtedy musimy obsluzyc taka sytuacje
        # dlatego obsluga wyjatku dla takiego przypadku
        try:
            granicewspolne[0] = granicewspolne[0].lstrip()
        except IndexError:
            self.errOutWriter.stderrorwrite('Nie znalazlem zadnych granic dla wybranego obszaru.')
        return granicewspolne


#    Klasa ogólna dla każdego obiektu na mapie, każdy obiekt ma podobne cechy, szczególne będa już w klasach pochodnych
class ObiektNaMapie(object):
    """
    Ogolna klasa dla wszystkich obiektow na mapie:
    dla poi, miast, adresow, polyline, polygone
    """

    def __init__(self, Plik, IndeksyMiast, alias2Type, args):
        self.Komentarz = []
        self.DataX = []
        self.PoiPolyPoly = ''
        self.Plik = Plik
        self.CityIdx = -1
        self.Dane1 = []
        self.alias2Type = alias2Type.alias2Type
        self.args = args
        self.czyDodacCityIdx = args.cityidx
        self.errOutWriter = errOutWriter(args)
        # indeksy miast
        self.IndeksyMiast = IndeksyMiast

    def komentarz_na_entrypoint_i_otwarte(self):
        if not self.Komentarz:
            return 1
        entry_point_defs = [ep for ep in (';;EntryPoint:', ';;EntryPoint=',) if
                            ep in self.Komentarz[0] and ';' + ep not in self.Komentarz[0]]
        otwarte_defs = [otw for otw in (';otwarte:', ';Otwarte:', ';otwarte=', ';Otwarte=',)
                        if otw in self.Komentarz[0] and ';' + otw not in self.Komentarz[0]]
        ep_set = set([ep.lstrip(';') for ep in entry_point_defs])
        otw_set = set([otw.lstrip(';') for otw in otwarte_defs])
        if not ep_set and not otw_set:
            return 1
        if len(ep_set) > 1 or len(otw_set) > 1:
            return 1
        if ep_set and self.Komentarz[0].count(ep_set.pop()) > 1:
            return 1
        if otw_set and self.Komentarz[0].count(otw_set.pop()) > 1:
            return 1
        komentarz = ''
        self.Komentarz[0] = self.Komentarz[0].strip()
        tmp_entry_otwarte = list()
        for abcd in self.Komentarz[0].split('\n'):
            if any(ep for ep in entry_point_defs if abcd.startswith(ep) and not abcd.startswith(';' + ep)):
                entry_point = abcd.lstrip(';')[len('EntryPoint:'):].strip()
                tmp_entry_otwarte.append('EntryPoint=' + entry_point)
            elif any(otw for otw in otwarte_defs if abcd.startswith(otw) and not abcd.startswith(';' + otw)):
                otwarte = abcd.lstrip(';')[len('otwarte:'):].strip()
                tmp_entry_otwarte.append('Otwarte=' + otwarte)
            else:
                komentarz += abcd + '\n'
        self.Dane1 += sorted(tmp_entry_otwarte)
        # po tym zabiegach w komentarzu powinno pozostac tylko to co niezwiazane z otwarte i entrypoint
        if komentarz:
            # jesli tak zapisz nowy komentarz
            self.Dane1[0] = komentarz.strip()
        elif self.Dane1[0][0] == ';':
            # jesli nie to sprawdz czy byl komentarz, jesli byl tzn ze tam byl tylko albo entrypoint albo otwarte
            # W takim przypadku usun go
            del(self.Dane1[0])
        return 0

    def stderrorwrite(self, string):
        self.errOutWriter.stderrorwrite(string)

    def stdoutwrite(self, string):
        self.errOutWriter.stdoutwrite(string)

    def wyczyscRekordy(self):
        self.Komentarz = []
        self.DataX = []
        self.PoiPolyPoly = ''
        self.CityIdx = -1
        self.Dane1 = []

    def ustaw_wartosc_zmiennej_cityidx(self, nazwa_miasta):
        self.CityIdx = self.IndeksyMiast.zwrocIndeksMiasta(nazwa_miasta)
        return 0

    def dodaj_indeksy_miast_do_obiektu(self, nazwa_miasta):
        if self.args.format_indeksow == 'cityidx':
            self.Dane1.append('CityIdx=' + str(self.CityIdx))
        else:
            self.Dane1.append('CityName=' + nazwa_miasta)
            for c_names in self.IndeksyMiast.sekcja_cityname:
                self.Dane1.append(c_names)


class Poi(ObiektNaMapie):
    def __init__(self, Plik, IndeksyMiast, alias2Type, args):
        ObiektNaMapie.__init__(self, Plik, IndeksyMiast, alias2Type, args)
        self.dlugoscRekordowMax = 8
        self.dlugoscRekordowMin = 7
        if hasattr(args, 'entry_otwarte_to_extras'):
            self.entry_otwarte_to_extras = args.entry_otwarte_to_extras
        else:
            self.entry_otwarte_to_extras = False

    def liniaZPliku2Dane(self, LiniaZPliku, orgLinia):
        self.pnt2Dane(LiniaZPliku, orgLinia)

    def dodaj_komentarz_do_dane(self):
        if self.Komentarz:
            for komentarz in self.Komentarz:
                self.Dane1.append(komentarz.rstrip())

    def pnt2Dane(self, LiniaZPliku, orgLinia):
        """Funkcja konwertujaca linijke z pliku pnt na wewnetrznš reprezentacje danego poi"""

        self.dodaj_komentarz_do_dane()
        # 0 Dlugosc, 1 Szerokosc, 2 EndLevel, 3 Label, 4 UlNrTelUrl, 5 Miasto, 6 Type, 7 KodPoczt
        self.PoiPolyPoly = '[POI]'
        self.Dane1.append(self.PoiPolyPoly)
        # Tworzymy Type=
        try:
            self.Dane1.append('Type=' + self.alias2Type[LiniaZPliku[6]])
        except KeyError:
            if LiniaZPliku[6].startswith('0x'):
                self.Dane1.append('Type=' + LiniaZPliku[6])
            else:
                self.stderrorwrite('Nieznany typ %s w pliku %s' % (LiniaZPliku[6], self.Plik))
                self.stderrorwrite(repr(orgLinia))
                self.Dane1.append('Type=0x0')
        # Tworzymy Label=
        if LiniaZPliku[3]:
            self.Dane1.append('Label=' + LiniaZPliku[3].strip().replace('°', ','))
        # Tworzymy EndLevel
        EndLevel = LiniaZPliku[2].lstrip()
        if EndLevel != '0':
            self.Dane1.append('EndLevel=' + LiniaZPliku[2].lstrip())
        # tworzymy HouseNumber=20 StreetDesc=Główna Phone=+48468312519
        StreetDesc, HouseNumber, Phone, Misc = self.rozdzielUlNrTelUrl(LiniaZPliku[4])
        if HouseNumber:
            self.Dane1.append('HouseNumber=' + HouseNumber.replace('°', ','))
        if StreetDesc:
            self.Dane1.append('StreetDesc=' + StreetDesc.replace('°', ','))
        if Phone:
            self.Dane1.append('Phone=' + Phone.replace('°', ','))
        if Misc:
            self.Dane1.append('MiscInfo=' + Misc.replace('°', ','))
        # Tworzymy Data0=(x,x)
        self.Dane1.append('Data0=(' + LiniaZPliku[0].lstrip() + ',' + LiniaZPliku[1].lstrip() + ')')
        # Tworzymy Miasto
        Miasto = LiniaZPliku[5].lstrip()
        if Miasto:
            self.Dane1.append('Miasto=' + Miasto)
            self.ustaw_wartosc_zmiennej_cityidx(Miasto)
            if self.czyDodacCityIdx:
                self.dodaj_indeksy_miast_do_obiektu(Miasto)
        # Tworzymy plik
        self.Dane1.append('Plik=' + self.Plik)
        # tworzymy kod poczt i type
        if len(LiniaZPliku) == 8:
            self.Dane1.append('KodPoczt=' + LiniaZPliku[7])
        self.Dane1.append('Typ=' + LiniaZPliku[6])
        if self.entry_otwarte_to_extras:
            self.komentarz_na_entrypoint_i_otwarte()
        self.Dane1.append('[END]\n')
        return

    def rozdzielUlNrTelUrl(self, UlNrTelUrl):
        """ulica, numer domu, numer telefonu oraz url sa podane w jednej linii.
            Funkcja ta rozdziela je na oddzielne pola
            :return Ulica, NumerDomu, Telefon, Url"""
        if not UlNrTelUrl:
            return '', '', '', ''
        aaa = UlNrTelUrl.split(';', 4)
        len_aaa = len(aaa)
        if len_aaa == 1:
            return aaa[0], '', '', ''
        elif len_aaa == 2:
            return aaa[0], aaa[1], '', ''
        elif len_aaa == 3:
            return aaa[0], aaa[1], aaa[2], ''
        else:
            return aaa[0], aaa[1], aaa[2], aaa[3]


class Adr(Poi):
    def __init__(self, Plik, IndeksyMiast, alias2Type, args):
        Poi.__init__(self, Plik, IndeksyMiast, alias2Type, args)
        self.dlugoscRekordowMax = 8
        self.dlugoscRekordowMin = 7

    def liniaZPliku2Dane(self, LiniaZPliku, orgLinia):
        self.adr2Dane(LiniaZPliku)

    def adr2Dane(self, LiniaZPliku):
        """Funkcja konwertujaca linijke z pliku adr na wewnetrznš reprezentacje danego adr"""
        self.dodaj_komentarz_do_dane()
        # self.dokladnoscWsp=len(LiniaZPliku[0].split('.')[1])
        self.PoiPolyPoly = '[POI]'
        self.Dane1.append(self.PoiPolyPoly)
        # Tworzymy Type=
        if LiniaZPliku[6] == 'ADR' or LiniaZPliku[6] == 'HOUSENUMBER':
            self.Dane1.append('Type=0x2800')
        else:
            self.stderrorwrite('Niepoprawny typ dla punktu adresowego')
            self.stderrorwrite(','.join(LiniaZPliku))
            # print('Niepoprawny typ dla punktu adresowego',file=sys.stderr)
            # print(','.join(LiniaZPliku),file=sys.stderr)
            self.Dane1.append('Type=0x0')

        # Tworzymy Label=
        self.Dane1.append('Label=' + LiniaZPliku[3].strip().replace('°', ','))
        # Tworzymy EndLevel, zakomentowane bo wszystkie adr powinny byc na 0
        # self.Dane1.append('EndLevel='+LiniaZPliku[2].lstrip())
        # tworzymy HouseNumber=20 StreetDesc=Główna Phone=+48468312519
        StreetDesc, HouseNumber, Phone, Misc = self.rozdzielUlNrTelUrl(LiniaZPliku[4])
        if HouseNumber:
            self.Dane1.append('HouseNumber=' + HouseNumber)
        if StreetDesc:
            self.Dane1.append('StreetDesc=' + StreetDesc.replace('°', ','))
        if Phone:
            self.Dane1.append('Phone=' + Phone)
        # Tworzymy Data0=(x,x)
        self.Dane1.append('Data0=(' + LiniaZPliku[0].strip() + ',' + LiniaZPliku[1].strip() + ')')
        # Tworzymy Miasto
        Miasto = LiniaZPliku[5].lstrip()
        if Miasto:
            self.Dane1.append('Miasto=' + Miasto)
            self.ustaw_wartosc_zmiennej_cityidx(Miasto)
            if self.czyDodacCityIdx:
                self.dodaj_indeksy_miast_do_obiektu(Miasto)
        # Tworzymy plik
        self.Dane1.append('Plik=' + self.Plik)
        # tworzymy kod poczt i type
        if len(LiniaZPliku) == 8:
            self.Dane1.append('KodPoczt=' + LiniaZPliku[7])
        self.Dane1.append('Typ=' + LiniaZPliku[6])
        if self.entry_otwarte_to_extras:
            self.komentarz_na_entrypoint_i_otwarte()
        self.Dane1.append('[END]\n')
        return


class City(ObiektNaMapie):
    rozmiar2Type = ['0xe00', '0xd00', '0xc00', '0xb00', '0xa00', '0x900', '0x800', '0x700', '0x600', '0x500', '0x400']
    type2Rozmiar = {'0xe00': '0', '0xd00': '1', '0xc00': '2', '0xb00': '3', '0xa00': '4', '0x900': '5', '0x800': '6',
                    '0x700': '7', '0x600': '8', '0x500': '9', '0x400': '10'}
    typetoEndlevel = [0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4]

    def __init__(self, Plik, IndeksyMiast, alias2Type, args):
        ObiektNaMapie.__init__(self, Plik, IndeksyMiast, alias2Type, args)
        self.dlugoscRekordowMax = 4
        self.dlugoscRekordowMin = 4

    def liniaZPliku2Dane(self, LiniaZPliku, orgLinia):
        self.city2Dane(LiniaZPliku)

    def dodaj_komentarz_do_dane(self):
        if self.Komentarz:
            for komentarz in self.Komentarz:
                self.Dane1.append(komentarz.rstrip())

    def city2Dane(self, LiniaZPliku):
        self.dodaj_komentarz_do_dane()
        self.PoiPolyPoly = '[POI]'
        self.Dane1.append(self.PoiPolyPoly)
        # Tworzymy Type=
        self.Dane1.append('Type=' + self.rozmiar2Type[int(LiniaZPliku[2].lstrip())])
        # Tworzymy Label=
        self.Dane1.append('Label=' + LiniaZPliku[3].strip().replace('°', ','))

        # dodajemy City=Y
        self.Dane1.append('City=Y')
        # Tworzymy EndLevel
        self.Dane1.append('EndLevel=' + str(self.typetoEndlevel[int(LiniaZPliku[2].lstrip())]))
        # Tworzymy Data0=(x,x)
        self.Dane1.append('Data0=(' + LiniaZPliku[0].lstrip() + ',' + LiniaZPliku[1].lstrip() + ')')
        # Tworzymy Miasto
        Miasto = LiniaZPliku[3].lstrip()
        self.Dane1.append('Miasto=' + Miasto)
        self.ustaw_wartosc_zmiennej_cityidx(Miasto)
        if self.czyDodacCityIdx:
            self.dodaj_indeksy_miast_do_obiektu(Miasto)
        # Tworzymy plik
        self.Dane1.append('Plik=' + self.Plik)
        # tworzymy rozmiar
        self.Dane1.append('Rozmiar=' + LiniaZPliku[2].lstrip())
        self.Dane1.append('[END]\n')


class PolylinePolygone(ObiektNaMapie):

    """funkcja parsuje dane z pliku txt/mp i przetwarza na reprezentacje wewnetrzna"""
    def rekord2Dane(self, stringZDanymi, domyslneMiasto):
        Klucze = set()
        self.liniaObszar = string

        for tmpbbb in stringZDanymi.strip().split('\n'):
            tmpbbb = tmpbbb.strip()
            if tmpbbb == '':
                pass
            elif tmpbbb[0] == ';':
                self.Komentarz.append(tmpbbb)
                self.Dane1.append(tmpbbb.rstrip())
            # elif tmpbbb.find('[PO')==0:
            elif tmpbbb.startswith('[PO'):
                self.PoiPolyPoly = tmpbbb
                self.Dane1.append(tmpbbb)
            else:
                try:
                    klucz, wartosc = tmpbbb.split('=', 1)
                except ValueError:
                    print('Nieznana opcja: %s' % tmpbbb, file=sys.stderr)
                    self.Dane1.append(tmpbbb)
                else:
                    if klucz in ('Miasto', 'City',):
                        Klucze.add(klucz)
                        self.Dane1.append(tmpbbb)
                        self.ustaw_wartosc_zmiennej_cityidx(wartosc)
                        if self.czyDodacCityIdx:
                            self.dodaj_indeksy_miast_do_obiektu(wartosc)
                    elif klucz == 'CityIdx':
                        self.CityIdx = wartosc
                    elif klucz == 'Plik':
                        self.Dane1.append(tmpbbb)
                        Klucze.add(klucz)
                    elif klucz.find('Data') >= 0:
                        self.Dane1.append(tmpbbb)
                        # self.dokladnoscWsp=len(wartosc.split(',',1)[0].split('.')[1])
                        self.DataX.append(tmpbbb)
                    elif klucz == 'Type' and self.args.extratypes:
                        if len(wartosc) > 6:
                            self.Dane1.append('Type=0x0')
                            self.Dane1.append('OrigType=' + wartosc)
                        else:
                            self.Dane1.append(tmpbbb)
                    else:
                        self.Dane1.append(tmpbbb)
        if domyslneMiasto and 'Miasto' not in Klucze:
            self.Dane1.append('Miasto=' + domyslneMiasto)
            self.ustaw_wartosc_zmiennej_cityidx(domyslneMiasto)
            if self.czyDodacCityIdx:
                self.dodaj_indeksy_miast_do_obiektu(domyslneMiasto)
        if self.PoiPolyPoly == '':
            self.Dane1.append(';[END]')
        else:
            if 'Plik' not in Klucze:
                self.Dane1.append('Plik=' + self.Plik)
            self.Dane1.append('[END]\n')


class plikTXT(object):
    def __init__(self, NazwaPliku, args, punktzTXT):
        self.domyslneMiasto = ''
        self.sciezkaNazwaPliku = NazwaPliku
        self.Dokladnosc = ''
        self.NazwaPliku = NazwaPliku.split(os.sep)[-1]
        self.sciezkaNazwa = NazwaPliku
        self.errOutWriter = errOutWriter(args)
        self.Dane1 = []
        self.punktzTXT = punktzTXT

    def txt2rekordy(self, zawartoscPliku):
        """funkcja pobiera zawartosc pliku w postaci stringa, dzieli go na liste stringow
        po wystapieniu slowa END, wczytuje domyslne miasto"""

        # w przypadku gdy plik nie zawiera zadnych ulic, nie znajdziemy zadnego '[END]'
        if zawartoscPliku.find('[END]') < 0:
            if zawartoscPliku.lstrip().startswith('Miasto='):
                tmpaaa = zawartoscPliku.strip().split('\n', 1)
                self.domyslneMiasto = tmpaaa[0].split('=', 1)[1]
                # domyslneMiasta2[self.sciezkaNazwa] = self.domyslneMiasto
                if len(tmpaaa) > 1:
                    return [tmpaaa[1]]
                else:
                    return []
            elif zawartoscPliku.strip():
                # return list(zawartoscPliku)
                return []
            else:
                return zawartoscPliku.strip().split('\n')
        zawartoscPlikuPodzielone = zawartoscPliku.strip().split('[END]')
        zawartoscPlikuPodzielone.pop()
        # print(repr(zawartoscPlikuPodzielone[-1]))
        # if zawartoscPlikuPodzielone[0].find('Miasto=')==0:
        if zawartoscPlikuPodzielone[0].startswith('Miasto='):
            self.domyslneMiasto, zawartoscPlikuPodzielone[0] = zawartoscPlikuPodzielone[0].split('\n', 1)
            self.domyslneMiasto = self.domyslneMiasto.split('=', 1)[1]
            if ';' in self.domyslneMiasto:
                self.errOutWriter.stderrorwrite('Uwaga! Srednik w nazwie miasta. Mapa moze sie nie zdemontowac!')
                self.errOutWriter.stderrorwrite('Miasto=%s, plik=%s.' %(self.domyslneMiasto, self.NazwaPliku))
            # domyslneMiasta2[self.sciezkaNazwa] = self.domyslneMiasto
        # zawartoscPlikuPodzielone.replace('\n\n','\n').strip()
        # na koncu pliku jest z reguly jeszcze pusta linia, usuwamy ja
        if not zawartoscPlikuPodzielone[-1]:
            zawartoscPlikuPodzielone.pop()
        return zawartoscPlikuPodzielone

    def zwrocDomyslneMiasto(self):
        return self.sciezkaNazwa, self.domyslneMiasto

    def ustalDokladnosc(self, LiniaZPliku):
        """
        Funkcja ustala dokladnosc pliku pnt
        :param LiniaZPliku: string w postaci linii pliku
        :return: 0 jesli dokladnosc udalo sie ustalic, 1 jesli dokladnosci nie udalo sie ustalic
        """
        if not LiniaZPliku:
            self.Dokladnosc = '-1'
            return 1
        if LiniaZPliku[0].startswith('Data'):
            self.Dokladnosc = '5'
            if len(LiniaZPliku[0].split(',', 1)[0].split('.')[1]) >= 6:
                self.Dokladnosc = '6'
            return 0
        else:
            self.Dokladnosc = '0'
            return 1

    def procesuj(self, zawartoscPlikuTXT):
        if not zawartoscPlikuTXT:
            self.Dokladnosc = '0'
            self.punktzTXT.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % self.NazwaPliku)
            return []
        for tmpaaa in self.txt2rekordy(zawartoscPlikuTXT):
            self.punktzTXT.rekord2Dane(tmpaaa, self.domyslneMiasto)
            if self.Dokladnosc not in ('5', '6') and self.punktzTXT.DataX:
                if self.ustalDokladnosc(self.punktzTXT.DataX):
                    self.punktzTXT.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % self.NazwaPliku)
            self.Dane1.extend(self.punktzTXT.Dane1)
            self.punktzTXT.wyczyscRekordy()
        return self.Dane1


class plikPNT(object):
    def __init__(self, NazwaPliku, args, punktzPntAdrCiti):
        self.sciezkaNazwaPliku = NazwaPliku
        self.Dokladnosc = ''
        self.NazwaPliku = NazwaPliku.split(os.sep)[-1]
        self.sciezkaNazwa = NazwaPliku
        self.punktzPntAdrCiti = punktzPntAdrCiti
        self.errOutWriter = errOutWriter(args)
        self.Dane1 = []

    def usunNaglowek(self, zawartoscPliku):
        """funkcja usuwa naglowek pliku pnt, i zwraca zawartosc pliku po usunieciu naglowka"""
        # pomijaj wszystko od poczštku do wystšpienia pierwszego poprawnego wpisu w pliku: XX.XXXXY, YY.YYYYY
        # przypadek gdy mamy pusty plik
        if len(zawartoscPliku) == 1:
            if zawartoscPliku[0].strip() == 0:
                return zawartoscPliku

        tabIndex = 0
        indeksPierwszegoPoprawnegoElementu = -1
        while tabIndex < len(zawartoscPliku) and indeksPierwszegoPoprawnegoElementu < 0:
            linia = zawartoscPliku[tabIndex].split(',')
            if len(linia) >= 4:
                try:
                    wspSzerokosc = float(linia[0].strip())
                    wspDlugosc = float(linia[1].strip())
                except ValueError:
                    tabIndex += 1
                else:
                    # if wspSzerokosc>=-90 and wspSzerokosc<=90 and wspDlugosc>=-180 and wspDlugosc<=180:
                    if -90 <= wspSzerokosc <= 90 and -180 <= wspDlugosc <= 180:
                        indeksPierwszegoPoprawnegoElementu = tabIndex
                    else:
                        tabIndex += 1
            else:
                tabIndex += 1

        # znalezlismy pierwszy poprawny element, teraz sprawdzmy czy przez przypadek nie ma przed nim komentarza
        if indeksPierwszegoPoprawnegoElementu > 0:
            while indeksPierwszegoPoprawnegoElementu > 0 \
                    and zawartoscPliku[indeksPierwszegoPoprawnegoElementu-1][0] == ';':
                indeksPierwszegoPoprawnegoElementu -= 1
            zawartoscPliku = zawartoscPliku[indeksPierwszegoPoprawnegoElementu:]
            return zawartoscPliku
        else:
            return zawartoscPliku

    def ustalDokladnosc(self, LiniaZPliku):
        """
                Funkcja ustala dokladnosc pliku txt
                :param LiniaZPliku: string w postaci linii pliku
                :return: 0 jesli dokladnosc udalo sie ustalic, 1 jesli dokladnosci nie udalo sie ustalic
        """
        if not LiniaZPliku:
            self.Dokladnosc = '-1'
            return 1
        else:
            wsp1 = LiniaZPliku.split(',')[0]
            if wsp1.find('.') > 0:
                self.Dokladnosc = '5'
                if len(wsp1.split('.')[1]) >= 6:
                    self.Dokladnosc = '6'
                return 0
            else:
                self.Dokladnosc = '0'
                return 1

    def procesuj(self, zawartoscPlikuPNTlubADR):
        komentarz = ''
        for liniaPliku in self.usunNaglowek(zawartoscPlikuPNTlubADR):
            liniaPliku = liniaPliku.strip()
            if not liniaPliku:
                pass
            elif liniaPliku[0] == ';':
                komentarz = komentarz + liniaPliku + '\n'
            else:
                rekordy = liniaPliku.split(',')
                if not self.punktzPntAdrCiti.dlugoscRekordowMin <= len(rekordy) <= self.punktzPntAdrCiti.dlugoscRekordowMax:
                    self.punktzPntAdrCiti.stderrorwrite('Bledna linia w pliku %s' % self.NazwaPliku)
                    self.punktzPntAdrCiti.stderrorwrite(repr(liniaPliku))

                else:
                    # punktzCity=City(pliki,tabKonw,args.cityidx)
                    if komentarz:
                        self.punktzPntAdrCiti.Komentarz.append(komentarz.strip())
                        komentarz = ''
                    self.punktzPntAdrCiti.liniaZPliku2Dane(rekordy, liniaPliku)
                    if not self.Dokladnosc or self.Dokladnosc == '0':
                        if self.ustalDokladnosc(liniaPliku):
                            self.punktzPntAdrCiti.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s'
                                                                % self.NazwaPliku)
                    self.Dane1.extend(self.punktzPntAdrCiti.Dane1)
                    self.punktzPntAdrCiti.wyczyscRekordy()
        return self.Dane1


def zwroc_dane_do_gui(args, listaDiffow, slownikHash):
    if hasattr(args, 'queue'):
        args.queue.put([listaDiffow, slownikHash])
    if hasattr(args, 'buttonqueue'):
        args.buttonqueue.put('Koniec')
    return listaDiffow, slownikHash


def update_progress(progress, args):
    barLength = 20
    status = ''
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\n"
    if progress >= 1:
        progress = 1
        status = "Zrobione...\n"
    block = int(round(barLength*progress))
    text = "\rProcent: [{0}] {1}% {2}".format("#" * block + "-" * (barLength-block), int(progress*100), status)
    if hasattr(args, 'stdoutqueue'):
        args.stdoutqueue.put(text)
    else:
        sys.stdout.write(text)
        sys.stdout.flush()


def zapiszkonfiguracje(args):
    print('Zapisuje konfiguracje w pliku konfiguracyjnym .mont-demont-py.config \nw katalogu domowym uzytkownika.')
    print('Podaj sciezki bezwzgledne. Tylda (~) oznacza katalog domowy uzytkownia.\n')
    UMPHOME = ''
    while UMPHOME == '':
        UMPHOME = input('Katalog ze zrodlami UMP: ')
        if UMPHOME.startswith('~'):
            UMPHOME = os.path.expanduser('~') + UMPHOME.lstrip('~')
        if not os.path.isdir(UMPHOME):
            print('Katalog ze zrodlami UMP %s nie istnieje. Utworz go najpierw' % UMPHOME)
            UMPHOME = ''
        if not (UMPHOME.endswith('\\') or UMPHOME.endswith('/')):
            UMPHOME = UMPHOME.strip() + '/\n'

    KATALOGROBOCZY = ''
    while KATALOGROBOCZY == '':
        KATALOGROBOCZY = input('Katalog roboczy: ')
        if KATALOGROBOCZY.startswith('~'):
            KATALOGROBOCZY = os.path.expanduser('~') + KATALOGROBOCZY.lstrip('~')
        if not os.path.isdir(KATALOGROBOCZY):
            print('Katalog roboczy %s nie istnieje. Utworz go najpierw' % KATALOGROBOCZY)
            KATALOGROBOCZY = ''
        if not (KATALOGROBOCZY.endswith('\\') or KATALOGROBOCZY.endswith('/')):
            KATALOGROBOCZY = KATALOGROBOCZY.strip()+'/\n'

    print('\nZapisuje plik konfiguracyjny .mont-demont-py.config \nw katalogu domowym uzytkownika: %s'
          % os.path.expanduser('~'), file=sys.stdout)
    with open(os.path.expanduser('~') + '/.mont-demont-py.config', 'w') as configfile:
        configfile.write('UMPHOME=' + UMPHOME)
        configfile.write('\n')
        configfile.write('KATALOGROBOCZY=' + KATALOGROBOCZY)


def listujobszary(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)
    try:
        listaobszarow = [a for a in os.listdir(Zmienne.KatalogzUMP)
                         if (a.startswith('UMP-') and os.path.isdir(os.path.join(Zmienne.KatalogzUMP, a)))]
        listaobszarow.sort()
        print('\n'.join(listaobszarow), file=sys.stdout)
    except FileNotFoundError:
        print('Bledna konfiguracja, nie znalazlem zadnych obszarow.', file=sys.stderr)
        return []
    else:
        return listaobszarow


def testuj_poprawnosc_danych(tester_poprawnosci_danych, dane_do_zapisu):
    if dane_do_zapisu['POIPOLY'] == '[POI]':
        tester_poprawnosci_danych.testy_poprawnosci_danych_poi(dane_do_zapisu)
    else:
        tester_poprawnosci_danych.testy_poprawnosci_danych_txt(dane_do_zapisu)


def montujpliki(args):
    stderr_stdout_writer = errOutWriter(args)
    Zmienne = UstawieniaPoczatkowe(args.plikmp)
    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.obszary:
        if args.obszary[0] == 'pwd':
            if os.getcwd().find('UMP') >= 0:
                args.obszary[0] = 'UMP' + os.getcwd().split('UMP')[1]
                Zmienne.KatalogRoboczy = os.getcwd()
            else:
                stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
                return 0
    else:
        stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
        return 0

    # gdy wybierzemy do montowania same radary, wtedy nalezy zamontowac cala polske - tylko drogi i radary.
    if args.obszary[0] == 'UMP-radary' and len(args.obszary) == 1:
        for a in listujobszary(args):
            if a.find('UMP-PL') >= 0:
                args.obszary.append(a)
        args.tylkodrogi = 1
    else:
        args.tylkodrogi = 0

    try:
        plikidomont = PlikiDoMontowania(Zmienne.KatalogzUMP, args)
    except (IOError, FileNotFoundError):
        return 0

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob
    plikidomont.Filtruj(args)

    # uklon w strone arta, montowanie tylko granic obszarow
    if hasattr(args, 'graniceczesciowe') and not args.tylkodrogi and not args.trybosmand:
        if args.graniceczesciowe:
            agranice = plikidomont.ograniczGranice(Zmienne.Kodowanie)
            with open(os.path.join(Zmienne.KatalogRoboczy, 'granice-czesciowe.txt'), 'w', encoding=Zmienne.Kodowanie,
                      errors=Zmienne.WriteErrors) as f:
                for a in agranice:
                    f.write(a)
            plikidomont.Pliki[0] = os.path.join(Zmienne.KatalogRoboczy, 'granice-czesciowe.txt')

    tabKonw = tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    try:
        os.remove(os.path.join(Zmienne.KatalogRoboczy, Zmienne.OutputFile))
    except FileNotFoundError:
        pass

    plikMP = tempfile.NamedTemporaryFile('w', encoding=Zmienne.Kodowanie, dir=Zmienne.KatalogRoboczy, delete=False)
    globalneIndeksy = IndeksyMiast()
    zawartoscPlikuMp = plikMP1(Zmienne, args, tabKonw)
    # ListaObiektowDoMontowania=[]
    for pliki in plikidomont.Pliki:
        try:
            if pliki.find('granice-czesciowe.txt') > 0:
                # print('granice czesciowe')
                plikPNTTXT = open(pliki, encoding=Zmienne.Kodowanie, errors=Zmienne.ReadErrors)
            else:
                plikPNTTXT = open(os.path.join(Zmienne.KatalogzUMP, pliki), encoding=Zmienne.Kodowanie,
                                  errors=Zmienne.ReadErrors)
        except IOError:
            stderr_stdout_writer.stderrorwrite('Nie moge otworzyć pliku %s' % os.path.join(Zmienne.KatalogzUMP, pliki))
        else:
            zawartoscPlikuMp.dodajplik(pliki)
            if args.hash:
                zawartoscPlikuMp.plikHash[pliki] = ''
            else:
                if pliki.find('granice-czesciowe.txt') > 0:
                    zawartoscPlikuMp.plikHash[pliki] = hashlib.md5(open(pliki, 'rb').read()).hexdigest()
                else:
                    zawartoscPlikuMp.plikHash[pliki] = hashlib.md5(open(os.path.join(Zmienne.KatalogzUMP, pliki),
                                                                      'rb').read()).hexdigest()

            # print('Udalo sie otworzyc pliku %s'%(pliki))

            ############################################################################################################
            # montowanie plikow cities
            if pliki.find('cities') > 0:
                punktzCity = City(pliki, globalneIndeksy, tabKonw, args)
                punktzCity.stdoutwrite(('....[CITY] %s' % pliki))
                przetwarzanyPlik = plikPNT(pliki, args, punktzCity)
                # komentarz=''
                zawartoscPlikuCITY = plikPNTTXT.readlines()
                if not zawartoscPlikuCITY:
                    punktzCity.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % pliki)
                    zawartoscPlikuMp.ustawDokladnosc(pliki, '-1')
                else:
                    zawartoscPlikuMp.dodaj(przetwarzanyPlik.procesuj(zawartoscPlikuCITY))
                    zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                del przetwarzanyPlik
                del punktzCity

            #########################################################################################################
            # montowanie plików pnt
            elif pliki.find('.pnt') > 0 and pliki.find('cities') < 0:
                punktzPnt = Poi(pliki, globalneIndeksy, tabKonw, args)
                punktzPnt.stdoutwrite('....[POI] %s' % pliki)
                przetwarzanyPlik = plikPNT(pliki, args, punktzPnt)
                # komentarz=''
                zawartoscPlikuPNT = plikPNTTXT.readlines()
                if not zawartoscPlikuPNT:
                    punktzPnt.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % pliki)
                    zawartoscPlikuMp.ustawDokladnosc(pliki, '-1')
                else:
                    zawartoscPlikuMp.dodaj(przetwarzanyPlik.procesuj(zawartoscPlikuPNT))
                    zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                del przetwarzanyPlik
                del punktzPnt

            ###########################################################################################################
            # montowanie plikow txt
            elif pliki.find('txt') > 0:
                punktzTXT = PolylinePolygone(pliki, globalneIndeksy, tabKonw, args)
                punktzTXT.stdoutwrite('....[TXT] %s' % pliki)
                przetwarzanyPlik = plikTXT(pliki, args, punktzTXT)
                tmpaaabbb = przetwarzanyPlik.procesuj(plikPNTTXT.read())
                zawartoscPlikuMp.dodaj(tmpaaabbb)
                zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                _nazwapliku, _miasto = przetwarzanyPlik.zwrocDomyslneMiasto()
                if _miasto:
                    zawartoscPlikuMp.domyslneMiasta2[_nazwapliku] = _miasto
                del przetwarzanyPlik
                del punktzTXT

            ############################################################################################################
            # montowanie plikow adr
            elif pliki.find('adr') > 0:
                punktzAdr = Adr(pliki, globalneIndeksy, tabKonw, args)
                punktzAdr.stdoutwrite('....[ADR] %s' % pliki)
                przetwarzanyPlik = plikPNT(pliki, args, punktzAdr)
                # komentarz=''
                zawartoscPlikuADR = plikPNTTXT.readlines()
                if not zawartoscPlikuADR:
                    punktzAdr.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % pliki)
                    zawartoscPlikuMp.ustawDokladnosc(pliki, '-1')
                else:
                    zawartoscPlikuMp.dodaj(przetwarzanyPlik.procesuj(zawartoscPlikuADR))
                    zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                del przetwarzanyPlik
                del punktzAdr
            plikPNTTXT.close()

    # zapisujemy naglowek
    stderr_stdout_writer.stdoutwrite('zapisuje naglowek')
    plikMP.write(zawartoscPlikuMp.naglowek)

    # zapisujemy indeksy miast
    if args.cityidx and args.format_indeksow == 'cityidx':
        stderr_stdout_writer.stdoutwrite('zapisuje cityidx')
        if hasattr(args, 'savememory') and args.savememory:
            print('oszczedzam pamiec')
            plikMP.writelines("{}\n".format(x) for x in globalneIndeksy.sekcja_cityidx)
        else:
            plikMP.write('\n'.join(globalneIndeksy.sekcja_cityidx))
        plikMP.write('\n[END-Cities]\n\n')

    if not args.trybosmand:
        # zapisujemy dokladnosc
        stderr_stdout_writer.stdoutwrite('zapisuje pliki, domyslne miasta i dokladnosc plikow')
        plikMP.write('[CYFRY]\n')
        for abc in zawartoscPlikuMp.plikDokladnosc:
            abcd = ''
            if abc in zawartoscPlikuMp.domyslneMiasta2:
                abcd = zawartoscPlikuMp.domyslneMiasta2[abc]
            plikMP.write(abc + ';' + zawartoscPlikuMp.plikDokladnosc[abc] + ';' + abcd + '\n')
        plikMP.write('[END]\n\n')

    stderr_stdout_writer.stdoutwrite('zapisuje plik mp --> %s'
                                     % os.path.join(Zmienne.KatalogRoboczy, Zmienne.OutputFile))
    if hasattr(args, 'savememory') and args.savememory:
        plikMP.writelines("{}\n".format(x) for x in zawartoscPlikuMp.zawartosc)
    else:
        plikMP.write('\n'.join(zawartoscPlikuMp.zawartosc))

    plikMP.close()
    shutil.copy(plikMP.name, os.path.join(Zmienne.KatalogRoboczy, Zmienne.OutputFile))
    os.remove(plikMP.name)
    del zawartoscPlikuMp
    del globalneIndeksy
    stderr_stdout_writer.stdoutwrite('Gotowe!')
    return 0


###############################################################################
# Demontaz
###############################################################################
def demontuj(args):
    if hasattr(args, 'buttonqueue'):
        args.buttonqueue.put('Pracuje')
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = errOutWriter(args)

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if args.plikmp:
        Zmienne.KatalogRoboczy = os.getcwd()
    # print(Zmienne.KatalogRoboczy)
    tabKonw = tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = plikMP1(Zmienne, args, tabKonw, 0)

    # obszarTypPlik_thread = threading.Thread(target=uruchom_obszary_dla_poi, args=(auto_poi_kolejka_wejsciowa,
    #                                                                               auto_poi_kolejka_wyjsciowa))
    # obszarTypPlik_thread.start()
    stderr_stdout_writer.stdoutwrite('Wczytuje %s' % os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile))

    try:
        zawartoscPlikuMp = open(os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile), encoding=Zmienne.Kodowanie,
                              errors=Zmienne.ReadErrors).read()
    except FileNotFoundError:
        stderr_stdout_writer.stderrorwrite('Nie odnalazlem pliku %s.'
                                           % os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile))
        return zwroc_dane_do_gui(args, [], {})

    # zmienna przechowujaca format indeksow w pliku mp, mozliwe sa dwie wartosci: [CITIES], albo CityName w zaleznosci
    # od ustawienia mapedit
    formatIndeksow = ''
    # najpierw powinna byc sekcja dotyczaca indeksu miast. Szukam go
    if args.cityidx:
        formatIndeksow, plikMp.cityIdxMiasto, zawartoscPlikuMp = plikMp.zbuduj_city_idx_zwroc_format(zawartoscPlikuMp)
        if not formatIndeksow:
            stderr_stdout_writer.stderrorwrite('Nie znalazlem danych do indeksu miast, pomijam.')
            args.cityidx = None

    #############################################################
    # sprawdzamy cyfry i hashe
    #############################################################
    poprawne_sumy_hash, zawartoscPlikuMp = plikMp.sprawdz_cyfry_i_hashe_plikow(zawartoscPlikuMp, args)
    if not poprawne_sumy_hash:
        return zwroc_dane_do_gui(args, [], {})

    # wczytałem juz sekcje dotyczaca plikow, moge teraz ustawic liste zamontowanych obszarow
    plikMp.ustawObszary()
    plikMp.zwaliduj_sciezki_do_plikow()

    # mamy liste plikow, teraz dla autopoly nalezy wczytac wspolrzedne z plikow ktore lapia sie na autopoly
    if args.autopolypoly:
        plikMp.autoobszary.wypelnijObszarPlikWspolrzedne(plikMp.plikizMp)

    # jezeli string konczy sie na [END] to split zwroci liste w ktorej ostatnia pozycja jest rowna
    # '' dlatego [0:-1]. Dodatkowo na koncu pliku zamontowane sa warstwy ktorych tez nie potrzebujemy
    rekordy_mp = zawartoscPlikuMp.split('\n[END]')[0:-1]
    ilosc_rekordow = len(rekordy_mp)

    # iterujemy po kolejnych rekordach w pliku mp. Rekordy to dane pomiedzy [END]
    update_progress(0 / 100, args)
    tester_poprawnosci_danych = TestyPoprawnosciDanych(args)
    for numer_aktualnego_rekordu, rekord_z_pliku_mp in enumerate(rekordy_mp):
        if (numer_aktualnego_rekordu + 1) % int(ilosc_rekordow/100) == 0:
            update_progress(round((numer_aktualnego_rekordu + 1) / int(ilosc_rekordow), 2), args)
        dane_do_zapisu = plikMp.zwroc_rekord_pliku_mp(rekord_z_pliku_mp.strip())
        # tester_queue.put(dane_do_zapisu)
        plikMp.procesuj_rekordy_mp(dane_do_zapisu)
        testuj_poprawnosc_danych(tester_poprawnosci_danych, dane_do_zapisu)
    # wylaczam proces odpowiedzialny za testowanie danych
    # tester_queue.put([])

    ########################################################
    # Przerzucam zawartosc nowosci.pnt do odpowiednich plikow
    ########################################################
    if plikMp.plikizMp['_nowosci.pnt'] and args.autopoi:
        stderr_stdout_writer.stdoutwrite('Przenosze zawartosc _nowosci.pnt do odpowiednich plikow.')
        plikMp.przeniesc_zawartosc_nowosci_pnt_do_plikow()

    ###############################
    # Plik mp przetworzony, generowanie diffow
    ###############################
    stderr_stdout_writer.stdoutwrite('Generuje pliki diff.')
    wszystkie_diffy_razem = []

    # na potrzeby gui tworzymy sobie slownik: klucz: nazwa pliku, wartosc nazwa latki, w przypadku gdy mamy nowy plik
    # jako wartosc bedzie ustawione ''
    listaDiffow = []
    slownikHash = {}
    for nazwa_pliku in plikMp.plikizMp:
        # usuwamy pierwsza linijke z pliku ktora to zawiera hash do pliku.
        if not nazwa_pliku.startswith('_nowosci.'):
            if len(plikMp.plikizMp[nazwa_pliku]) > 0 and plikMp.plikizMp[nazwa_pliku][0].startswith('MD5HASH='):
                slownikHash[nazwa_pliku] = plikMp.plikizMp[nazwa_pliku].pop(0).split('=')[1].strip()
            else:
                slownikHash[nazwa_pliku] = 'MD5HASH=NOWY_PLIK'

        # dodajemy naglowek do pliku pnt i adr
        if nazwa_pliku[-4:] == '.pnt' or nazwa_pliku[-4:] == '.adr':
            naglowek = ['OziExplorer Point File Version 1.0\n', 'WGS 84\n', 'Reserved 1\n', 'Reserved 2\n']
            if nazwa_pliku.find('cities-') >= 0:
                naglowek.append('255,65535,3,8,0,0,CITY ' + nazwa_pliku.split('cities-')[1].split('.')[0] + '\n')
            else:
                naglowek.append('255,65535,3,8,0,0,' + nazwa_pliku.split(os.sep)[-1] + '\n')
            plikMp.plikizMp[nazwa_pliku] = naglowek + plikMp.plikizMp[nazwa_pliku]

        if nazwa_pliku in ('_nowosci.txt', '_nowosci.pnt',):
            # plik _nowosci.txt musi miec jakakolwiek zawartosc, a plik _nowosci.pnt musi byc dluzszy niz naglowek
            if (nazwa_pliku == '_nowosci.txt' and plikMp.plikizMp[nazwa_pliku]) \
                    or (nazwa_pliku == '_nowosci.pnt' and len(plikMp.plikizMp[nazwa_pliku]) > 5):
                stderr_stdout_writer.stdoutwrite('Uwaga. Powstal plik %s.' % nazwa_pliku)
                listaDiffow.append(nazwa_pliku)
                with open(os.path.join(Zmienne.KatalogRoboczy, nazwa_pliku), 'w', encoding=Zmienne.Kodowanie,
                          errors=Zmienne.WriteErrors) as f:
                    f.writelines(plikMp.plikizMp[nazwa_pliku])
        else:
            try:
                if nazwa_pliku.find('granice-czesciowe.txt') > 0:
                    orgPlikZawartosc = open(nazwa_pliku, encoding=Zmienne.Kodowanie, errors=Zmienne.ReadErrors).readlines()
                else:
                    orgPlikZawartosc = open(os.path.join(Zmienne.KatalogzUMP, nazwa_pliku), encoding=Zmienne.Kodowanie,
                                            errors=Zmienne.ReadErrors).readlines()
                if orgPlikZawartosc:
                    if orgPlikZawartosc[-1][-1] != '\n':
                        orgPlikZawartosc[-1] += '\\ No new line at the end of file\n'
                else:
                    orgPlikZawartosc.append('\\ No new line at the end of file\n')
            except FileNotFoundError:
                stderr_stdout_writer.stdoutwrite('Powstal nowy plik %s. Zarejestruj go w cvs.' %
                                                 nazwa_pliku.replace(os.sep, '-'))
                listaDiffow.append(nazwa_pliku)
                with open(os.path.join(Zmienne.KatalogRoboczy, nazwa_pliku.replace(os.sep, '-')), 'w',
                          encoding=Zmienne.Kodowanie, errors=Zmienne.WriteErrors) as f:
                    f.writelines(plikMp.plikizMp[nazwa_pliku])
            else:
                plikDiff = []
                if not plikMp.plikizMp[nazwa_pliku]:
                    plikMp.plikizMp[nazwa_pliku].append('\\ No new line at the end of file\n')
                elif plikMp.plikizMp[nazwa_pliku][-1][-1] != '\n':
                    plikMp.plikizMp[nazwa_pliku][-1][-1] += '\\ No new line at the end of file\n'
                if 'granice-czesciowe.txt' not in nazwa_pliku:
                    tofile = nazwa_pliku.replace('UMP', 'UMP_Nowe').replace('narzedzia', 'narzedzia_Nowe')
                else:
                    tofile = os.path.join(os.path.dirname(nazwa_pliku) + '_Nowe', os.path.basename(nazwa_pliku))
                for line in difflib.unified_diff(orgPlikZawartosc, plikMp.plikizMp[nazwa_pliku], fromfile=nazwa_pliku,
                                                 tofile=tofile):
                    # sys.stdout.write(line)
                    if line.endswith('\\ No new line at the end of file\n'):
                        a, b = line.split('\\')
                        plikDiff.append(a + '\n')
                        plikDiff.append('\\' + b)
                        wszystkie_diffy_razem.append(a + '\n')
                        wszystkie_diffy_razem.append('\\' + b)
                    else:
                        plikDiff.append(line)
                        wszystkie_diffy_razem.append(line)
                if plikDiff:
                    stderr_stdout_writer.stdoutwrite('Powstala latka dla pliku %s.' % nazwa_pliku)
                    if nazwa_pliku.find('granice-czesciowe.txt') > 0:
                        plikdootwarcia = nazwa_pliku
                    else:
                        plikdootwarcia = os.path.join(Zmienne.KatalogRoboczy, nazwa_pliku.replace(os.sep, '-'))
                    # zapisujemy plik oryginalny
                    if nazwa_pliku.find('granice-czesciowe.txt') < 0:
                        with open(plikdootwarcia, 'w', encoding=Zmienne.Kodowanie, errors=Zmienne.WriteErrors) as f:
                            f.writelines(plikMp.plikizMp[nazwa_pliku])

                    # bawimy sie z latkami. Jesli montowane byly granice czesciowe sprobujmy je przerobic na ogolne
                    if nazwa_pliku.find('granice-czesciowe.txt') > 0:
                        graniceczesciowe = PaczerGranicCzesciowych(Zmienne)
                        if graniceczesciowe.konwertujLatke(plikDiff):
                            listaDiffow.append('narzedzia' + os.sep + 'granice.txt')
                            slownikHash['narzedzia' + os.sep + 'granice.txt'] = graniceczesciowe.granice_txt_hash
                        else:
                            stderr_stdout_writer.stderrorwrite('Nie udalo sie skonwertowac granic lokalnych na narzedzia' + os.sep + 'granice.txt.\nMusisz nalozyc latki recznie.')
                            listaDiffow.append(os.path.join(os.path.basename(nazwa_pliku)))
                            slownikHash['granice-czesciowe.txt'] = 'NOWY_PLIK'
                            with open(plikdootwarcia + '.diff', 'w', encoding=Zmienne.Kodowanie,
                                      errors=Zmienne.WriteErrors) as f:
                                f.writelines(plikDiff)
                    # zapisujemy plik diff
                    else:
                        with open(plikdootwarcia + '.diff', 'w', encoding=Zmienne.Kodowanie,
                                  errors=Zmienne.WriteErrors) as f:
                            f.writelines(plikDiff)
                        listaDiffow.append(nazwa_pliku)
                    plikDiff = []

    if wszystkie_diffy_razem:
        stderr_stdout_writer.stdoutwrite('Plik wszystko.diff - zbiorczy plik dla wszystkich latek.')
        with open(os.path.join(Zmienne.KatalogRoboczy, 'wszystko.diff'), 'w',
                  encoding=Zmienne.Kodowanie, errors=Zmienne.WriteErrors) as f:
            f.writelines(wszystkie_diffy_razem)
    stderr_stdout_writer.stdoutwrite('Gotowe!')
    del plikMp
    return zwroc_dane_do_gui(args, listaDiffow, slownikHash)


def edytuj(args):
    wine_exe = None
    if hasattr(args, 'InputFile'):
        Zmienne = UstawieniaPoczatkowe(args.InputFile)
    else:
        Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = errOutWriter(args)

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphone)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if args.plikmp:
        Zmienne.KatalogRoboczy = os.getcwd()

    # sprawdzmy ktory wine jest dostepny w przypadku linuksa
    if sys.platform.startswith('linux'):
        if shutil.which('wine64'):
            wine_exe = 'wine64'
        elif shutil.which('wine'):
            wine_exe = 'wine'
        else:
            stderr_stdout_writer.stderrorwrite('Nie znalazlem pliku wykonywalnego wine.\nNie moge kontynuowac.')
            return 1

    if args.mapedit2:
        if os.path.isfile(Zmienne.MapEdit2Exe):
            if sys.platform.startswith('linux'):
                process = subprocess.call([wine_exe, Zmienne.MapEdit2Exe, os.path.join(Zmienne.KatalogRoboczy,
                                                                                       Zmienne.InputFile)])
            else:
                process = subprocess.call([Zmienne.MapEdit2Exe, os.path.join(Zmienne.KatalogRoboczy,
                                                                             Zmienne.InputFile)])
        else:
            stderr_stdout_writer.stderrorwrite('Nieprawidlowa sciezka do pliku wykonywalnego mapedit.exe.\nNie moge kontynuowac.')
        return 1
    else:
        if os.path.isfile(Zmienne.MapEditExe):
            if sys.platform.startswith('linux'):
                process = subprocess.call([wine_exe, Zmienne.MapEditExe, os.path.join(Zmienne.KatalogRoboczy,
                                                                                      Zmienne.InputFile)])
            else:
                process = subprocess.call([Zmienne.MapEditExe, os.path.join(Zmienne.KatalogRoboczy,
                                                                            Zmienne.InputFile)])
        else:
            stderr_stdout_writer.stderrorwrite('Nieprawidlowa sciezka do pliku wykonywalnego mapedit.exe.\nNie moge kontynuowac.')
        return 1


def sprawdz_numeracje(args):
    stderr_stdout_writer = errOutWriter(args)
    Zmienne = UstawieniaPoczatkowe('wynik.mp')

    if not hasattr(args, 'mode'):
        stderr_stdout_writer.stdoutwrite('Sprawdzam numeracje i zakazy!')
        args.mode = None
    else:
        stderr_stdout_writer.stdoutwrite('Ciaglosc siatki routingowej!')

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if args.plikmp:
        Zmienne.KatalogRoboczy = os.getcwd()+'/'
    znajdz_bledy_numeracji.main(os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile),
                                stderr_stdout_writer, args.mode)
    if not args.mode:
        stderr_stdout_writer.stdoutwrite('Sprawdzanie numeracji i zakazow gotowe!')
    else:
        stderr_stdout_writer.stdoutwrite('Sprawdzanie ciaglowsci siatki routingowej gotowe!')


def sprawdz(args):
    stderr_stdout_writer = errOutWriter(args)
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    if hasattr(args, 'sprawdzbuttonqueue'):
        args.sprawdzbuttonqueue.put('Pracuje')

    stderr_stdout_writer.stdoutwrite('Uruchamiam netgen!')

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if args.plikmp:
        Zmienne.KatalogRoboczy = os.getcwd()

    bledy = {'slepy': [], 'przeciecie': [], 'blad routingu': [], 'za bliskie': [], 'zygzak': [],
             'zapetlona numeracja': [], 'nieuzywany slepy': [], 'nieuzywany przeciecie': []}
    NetgenConfFile = os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'netgen.cfg'))
    process = subprocess.Popen([Zmienne.NetGen, '-cbxj', '-a60', '-e0', '-r0.00007', '-s0.0003',
                                '-N', '-T' + NetgenConfFile, os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    line, err = process.communicate()
    line = line.decode(Zmienne.Kodowanie, errors=Zmienne.ReadErrors)
    err = err.decode(Zmienne.Kodowanie, errors=Zmienne.ReadErrors)

    poprzedni = ''
    for a in err.split('\n'):
        a.strip()
        if a.startswith("Warning: Road with \'Numbers\' parameter cut"):
            numer_linii_pliku = int(poprzedni.split('@')[-1].strip().rstrip(')'))
            with open(os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile), encoding=Zmienne.Kodowanie,
                      errors=Zmienne.WriteErrors) as f:
                linijki_pliku = f.readlines()
            while 1:
                if linijki_pliku[numer_linii_pliku].startswith('Data'):
                    x, y = linijki_pliku[numer_linii_pliku].split('=')[-1].split('),(')[0].lstrip('(').split(',')
                    bledy['zapetlona numeracja'].append('-1,zapetlona numeracja,' + x + ',' + y + ',,0,1,3,255,65535,,,0,0,0,6,0,19')
                    break
                else:
                    numer_linii_pliku -= 1
        poprzedni = a

    for a in line.split('\n'):
        a = a.strip()
        if a.startswith('-1,BE') or a.startswith('-1,BX') or a.startswith('-1,NE') or a.startswith('-1,NX'):
            bledy['blad routingu'].append(a)
        elif a.startswith('-1,B'):
            bledy['slepy'].append(a)
        elif a.startswith('-1,I'):
            bledy['przeciecie'].append(a)
        elif a.startswith('-1,A'):
            bledy['zygzak'].append(a)
        elif a.startswith('-1,BC') or a.startswith('-1,NC'):
            bledy['za bliskie'].append(a)
        elif a.startswith('-1,UI'):
            bledy['nieuzywany przeciecie'].append(a)
        elif a.startswith('-1,UB'):
            bledy['nieuzywany slepy'].append(a)
        else:
            pass

    for typBledu in bledy:
        if bledy[typBledu]:
            for b in bledy[typBledu]:
                errorcoord = b.rstrip().split(',')[2:4]
                error = typBledu + ' ' + errorcoord[0] + ',' + errorcoord[1]
                if typBledu not in ('nieuzywany slepy', 'nieuzywany przeciecie'):
                    stderr_stdout_writer.stderrorwrite(error)
            with open(os.path.join(Zmienne.KatalogRoboczy, typBledu.replace(' ', '-') + '.wpt'), 'w',
                      encoding=Zmienne.Kodowanie, errors=Zmienne.WriteErrors) as f:
                f.write('OziExplorer Waypoint File Version 1.1\n')
                f.write('WGS 84\n')
                f.write('Reserved 2\n')
                f.write('Reserved 3\n')
                f.writelines([abc+'\n' for abc in bledy[typBledu]])
            stderr_stdout_writer.stdoutwrite(typBledu + '-->' + Zmienne.KatalogRoboczy + typBledu.replace(' ', '-') +
                                             '.wpt\n')

    stderr_stdout_writer.stdoutwrite('Sprawdzanie Netgenem zakonczone!')
    if hasattr(args, 'sprawdzbuttonqueue'):
        args.sprawdzbuttonqueue.put('Koniec')


def cvsup(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = errOutWriter(args)

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if len(args.obszary) > 0:
        if args.obszary[0] == 'pwd':
            if os.getcwd().find('UMP') >= 0:
                args.obszary[0] = 'src'
                Zmienne.KatalogRoboczy = os.getcwd()
            else:
                stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
                return 0

    else:
        stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
        return 0

    CVSROOT = '-d:pserver:' + Zmienne.CvsUserName + '@cvs.ump.waw.pl:/home/cvsroot'
    os.chdir(Zmienne.KatalogzUMP)
    for a in args.obszary:
        process = subprocess.Popen(['cvs.exe', CVSROOT, 'up', a], stdout=subprocess.PIPE)
        for line in process.stdout.readlines():
            if hasattr(args, 'cvsoutputqueue'):
                args.cvsoutputqueue.put(line.decode(Zmienne.Kodowanie))
            else:
                print(line)
    if hasattr(args, 'cvsoutputqueue'):
        args.cvsoutputqueue.put('Gotowe\n')
    else:
        print('Gotowe\n')


def czysc(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = errOutWriter(args)
    zawartoscKatRob = os.listdir(Zmienne.KatalogRoboczy)
    plikiDoUsuniecia = []

    # jezeli wywolamy bez argumentu usun tylko wynik.mp
    if args.wszystko or args.oryg or args.bledy or args.diff:
        if args.wszystko:
            args.bledy = 1
            args.diff = 1
            args.oryg = 1
            for a in zawartoscKatRob:
                if a.endswith('wynik.mp') or a.endswith('wynik-klasy.mp') or a.endswith('granice-czesciowe.txt') or \
                        a.endswith('_nowosci.txt') or a.endswith('_nowosci.pnt'):
                    plikiDoUsuniecia.append(a)

        if args.oryg:
            for a in zawartoscKatRob:
                if a.endswith('.diff'):
                    plikiDoUsuniecia.append(a.split('.diff', 1)[0])
        if args.bledy:
            for a in zawartoscKatRob:
                if a.endswith('blad-routingu.wpt'):
                    plikiDoUsuniecia.append(a)
                elif a.endswith('slepy.wpt'):
                    plikiDoUsuniecia.append(a)
                elif a.endswith('przeciecie.wpt'):
                    plikiDoUsuniecia.append(a)
                elif a.endswith('zygzak.wpt'):
                    plikiDoUsuniecia.append(a)
                elif a.endswith('za-bliskie.wpt'):
                    plikiDoUsuniecia.append(a)
                elif a.endswith('zapetlona-numeracja.wpt'):
                    plikiDoUsuniecia.append(a)
        if args.diff:
            for a in zawartoscKatRob:
                if a.endswith('.diff'):
                    plikiDoUsuniecia.append(a)
    else:
        for a in zawartoscKatRob:
            if a.endswith('wynik.mp') or a.endswith('wynik-klasy.mp') or a.endswith('granice-czesciowe.txt'):
                plikiDoUsuniecia.append(a)

    for a in plikiDoUsuniecia:
        try:
            os.remove(os.path.join(Zmienne.KatalogRoboczy, a))
        except FileNotFoundError:
            pass


def rozdziel_na_klasy(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = errOutWriter(args)
    if len(args.obszary) > 0:
        if args.obszary[0] == 'pwd':
            if os.getcwd().find('UMP') >= 0:
                args.obszary[0] = 'UMP' + os.getcwd().split('UMP')[1]
                Zmienne.KatalogRoboczy = os.getcwd()
            else:
                stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
                return 0
    else:
        stderr_stdout_writer.stderrorwrite('Nie wybrano zadnych obszarow.\nNie moge kontynuowac!')
        return 0
    args.cityidx = 0
    args.adrfile = 0
    args.notopo = 1
    args.noszlaki = 1
    args.nocity = 1
    args.nopnt = 1
    args.plikmp = 'wynik.mp'
    args.hash = 1
    args.extratypes = 0
    args.graniceczesciowe = 0
    args.trybosmand = 0
    args.montuj_wedlug_klas = 1

    montujpliki(args)
    stderr_stdout_writer.stdoutwrite('Dodaje do pliku dane routingowe przy pomocy netgena')
    NetgenConfFile = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'netgen.cfg')
    print(NetgenConfFile)
    process = subprocess.Popen([Zmienne.NetGen, '-e0', '-j', '-k',
                                '-T' + NetgenConfFile, os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    plik_mp_z_klasami, err = process.communicate()
    stderr_stdout_writer.stdoutwrite('Dziele drogi na klasy')
    plik_mp_z_klasami = plik_mp_z_klasami.decode(Zmienne.Kodowanie)
    err = err.decode(Zmienne.Kodowanie)
    with open(os.path.join(Zmienne.KatalogRoboczy, 'wynik-klasy.mp'), 'w', encoding=Zmienne.Kodowanie,
              errors=Zmienne.WriteErrors) as f:
        for a in plik_mp_z_klasami.split('\n'):
            if a.startswith('EndLevel'):
                pass
            else:
                if a.startswith('Routeparam'):
                    klasa = a.split('=')[-1].split(',')[1]
                    f.write('EndLevel=' + klasa + '\n')
                f.write(a.strip() + '\n')
    stderr_stdout_writer.stdoutwrite('Utworzony plik z klasami: ' +
                                     os.path.join(Zmienne.KatalogRoboczy, 'wynik-klasy.mp'))
    # jesli wywolany z mdm bedzie mial w argumentach kolejke do aktywacji guzika zobacz
    if hasattr(args, 'zobaczbuttonqueue'):
        args.zobaczbuttonqueue.put('Koniec')


def patch(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        patchExe = 'patch'
    else:
        patchExe = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'patch.exe')
    stderr_stdout_writer = errOutWriter(args)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    stderr_stdout_writer.stdoutwrite('Nakladam plik z latami:\n')
    os.chdir(Zmienne.KatalogzUMP)
    returncode = None
    for plik in args.pliki_diff:
        stderr_stdout_writer.stdoutwrite('Plik: ' + str(plik))
        process = subprocess.Popen([patchExe, '-Np0', '-t', '-i', os.path.join(Zmienne.KatalogRoboczy, plik)],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = process.communicate()
        stderr_stdout_writer.stdoutwrite(out.decode(Zmienne.Kodowanie))
        returncode = process.returncode
    return returncode


def dodaj_dane_routingowe(args):
    stderr_stdout_writer = errOutWriter(args)
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer.stdoutwrite('Dodaje do pliku dane routingowe przy pomocy netgena')
    NetgenConfFile = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'snetgen.cfg')
    stderr_stdout_writer.stdoutwrite('Uruchamiam netgena na pliku wejściowym')
    process = subprocess.Popen([Zmienne.NetGen, '-e0', '-j', '-k',
                                '-T' + NetgenConfFile, os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    plik_mp_z_klasami, err = process.communicate()
    stderr_stdout_writer.stdoutwrite('Zapisuje plik wyjsciowy %s z danymi routingowymi' % args.output_filename[0])
    with open(os.path.join(Zmienne.KatalogRoboczy, args.output_filename[0]), 'w') as file_name:
        file_name.writelines(plik_mp_z_klasami.decode(Zmienne.Kodowanie))

def main(argumenty):

    # glowny parser:
    parser = argparse.ArgumentParser(description="montowanie i demontowanie plikow w projekcie ump")
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='wyswietlaj dokladnie co robisz')
    parser.add_argument('-uh', '--ump-home', dest='umphome', help='katalog ze zrodlami ump')
    parser.add_argument('-kr', '--katalog-roboczy', dest='katrob', help='ustaw katalog roboczy')
    parser.add_argument('-sm', '--save-memory', action='store_true', dest='savememory',
                        help='postaraj sie oszczedzac pamiec kosztem szybkosci, na razie nie dziala')

    # tworzymy subparsery do polecen mont demont list
    subparsers = parser.add_subparsers()

    # parser dla komendy montuj/mont
    parser_montuj = subparsers.add_parser('mont', help="montowanie obszarow do pliku mp")
    parser_montuj.add_argument('obszary', nargs="*", default=['pwd'])
    parser_montuj.add_argument('-idx', '--city-idx', action="store_true", dest='cityidx', help="tworzy indeks miast")
    parser_montuj.add_argument('-if', '--format-indeksow', action='store', help='Format indeksów', default='cityidx',
                               choices=['cityidx', 'cityname'])
    parser_montuj.add_argument('-adr', '--adr-files', action='store_true', dest='adrfile', help="montuj pliki adresowe")
    parser_montuj.add_argument('-nt', '--no-topo', action='store_true', dest='notopo', help='nie montuj plikow topo')
    parser_montuj.add_argument('-ns', '--no-szlaki', action='store_true', dest='noszlaki', help='nie montuj szlakow')
    parser_montuj.add_argument('-nc', '--no-city', action='store_true', dest='nocity', help='nie montuj plikow miast')
    parser_montuj.add_argument('-np', '--no-pnt', action='store_true', dest='nopnt', help='nie montuj plikow pnt')
    parser_montuj.add_argument('-o', '--output-file', dest='plikmp', default='wynik.mp',
                               help='nazwa pliku wynikowego. Domyslnie wynik.mp')
    parser_montuj.add_argument('-nh', '--no-hash', dest='hash', action='store_true',
                               help='nie generuj sum kontrolnych dla montowanych plikow')
    parser_montuj.add_argument('-et', '--extra-types', dest='extratypes', action='store_true',
                               help='specjalne traktowanie typow')
    parser_montuj.add_argument('-gc', '--granice-czesciowe', dest='graniceczesciowe', action='store_true',
                               help='dolacz tylko granice montowanych obszarow')
    parser_montuj.add_argument('-toa', '--tryb-osmand', dest='trybosmand', action='store_true',
                               help='ogranicza ilosc montowanych danych dla konwersji do OSMAnd')
    parser_montuj.add_argument('--entry-otwarte-to-extras', action='store_true', default=False,
                               help='Przenosi otarte i entrypoints z komentarza do extras. Uwaga, używać '
                                    'ostrożnie')
    parser_montuj.set_defaults(func=montujpliki)

    # parser dla komendy demontuj/demont
    parser_demontuj = subparsers.add_parser('demont', help='demontaz pliku mp')
    parser_demontuj.add_argument('-i', '--input-file', dest='plikmp',
                                 help='nazwa pliku do demontazu, domyslnie wynik.mp')
    parser_demontuj.add_argument('-idx', '--city-idx', action="store_true", dest='cityidx',
                                 help="nadpisuj Miasto= wartoscia indeksu miast")
    parser_demontuj.add_argument('-nh', '--no-hash', action='store_true', dest='hash',
                                 help='ignoruj sumy kontrolne plikow z cvs')
    parser_demontuj.add_argument('-r', '--round', dest='X', default='0', choices=['5', '6'],
                                 help='zaokraglij wspolrzedne do X cyfr znaczacych. Dozwolone wartosci 5 i 6')
    parser_demontuj.add_argument('-ap', '--auto-poi', action='store_true', dest='autopoi',
                                 help='automatycznie przenos poi z _nowosci.pnt do odpowiednich plikow')
    parser_demontuj.add_argument('-aol', '--auto-obszary-linie', action='store_true', dest='autopolypoly',
                                 help='automatycznie przenos z _nowosci.txt do odpowiednich plikow')
    parser_demontuj.add_argument('-et', '--extra-types', dest='extratypes', action='store_true',
                                 help='specjalne traktowanie typow')
    parser_demontuj.add_argument('-sk', '--standaryzuj-komentarz', action='store_true', help='Standaryzuj otwawrte '
                                                                                             'i EntryPoints')
    parser_demontuj.set_defaults(func=demontuj)

    # parser dla komendy listuj
    parsers_listuj = subparsers.add_parser('list', help='listuj obszary do montowania')
    parsers_listuj.set_defaults(func=listujobszary)

    # parser dla komendy zapiszkonf
    parsers_zapiszkonf = subparsers.add_parser('zapiszkonf', help='tworzy plik konfiguracyjny z katalogiem domowym ump i katalogiem roboczym')
    parsers_zapiszkonf.set_defaults(func=zapiszkonfiguracje)

    # parser dla komendy edytuj - uruchamianie mapedit
    parsers_edytuj = subparsers.add_parser('edytuj', help='uruchom mapedit')
    parsers_edytuj.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do demontazu, domyslnie wynik.mp')
    parsers_edytuj.add_argument('-me2', '--mapedit-2', action='store_true', dest='mapedit2',
                                help='alternatywna wersja mapedit, zdefiniowana w konfiguracji')
    parsers_edytuj.set_defaults(func=edytuj)

    # parser dla komendy sprawdz - sprawdza negenem
    parsers_sprawdz = subparsers.add_parser('sprawdz', help='sprawdza siatke drog netgenem')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, domyslnie wynik.mp')
    parsers_sprawdz.set_defaults(func=sprawdz)

    # parser dla komendy sprawdz_numeracje
    parsers_sprawdz = subparsers.add_parser('sprawdz_numeracje', help='sprawdza numeracje')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, domyslnie wynik.mp')
    parsers_sprawdz.set_defaults(func=sprawdz_numeracje)

    # parser dla komendy sprawdz_siatke_routingowa
    parsers_sprawdz = subparsers.add_parser('sprawdz_siatke_routingowa', help='sprawdz ciaglosc siatki routingowej')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, domyslnie wynik.mp')
    parsers_sprawdz.add_argument('-m', '--mode', dest='mode', default='sprawdz_siatke_dwukierunkowa',
                                 choices=['sprawdz_siatke_dwukierunkowa', 'sprawdz_siatke_jednokierunkowa'],
                                 help='sprawdz siatke routingowa dwukierunkowa i jednokierunkowa')
    parsers_sprawdz.set_defaults(func=sprawdz_numeracje)

    # parser dla komendy cvsup -
    parsers_cvsup = subparsers.add_parser('cvsup', help='uaktualnia zrodla')
    parsers_cvsup.add_argument('obszary', nargs="*", default=['pwd'])
    parsers_cvsup.set_defaults(func=cvsup)

    # parser dla komendu czysc
    parsers_czysc = subparsers.add_parser('czysc', help='usuwa wynik.mp (domyslnie), granice-czesciowe.txt (domyslnie) oraz czysci katalog roboczy z plikow diff, plikow oryginalnych, plikow bledow')
    parsers_czysc.add_argument('-w', '--wszystko', dest='wszystko', action='store_true',
                               help='usuwa pliki diff, pliki oryginalne, pliki bledow oraz wynik.mp')
    parsers_czysc.add_argument('-d', '--diff', dest='diff', action='store_true', help='usuwa tylko pliki diff')
    parsers_czysc.add_argument('-b', '--bledy', dest='bledy', action='store_true', help='usuwa tylko pliki bledow')
    parsers_czysc.add_argument('-o', '--oryg', dest='oryg', action='store_true',
                               help='usuwa pliki oryginalne do ktorych istnieja pliki diff')
    parsers_czysc.set_defaults(func=czysc)

    # parser dla komendy rozdziel na klasy
    parser_rozdziel_na_klasy = subparsers.add_parser('rozdziel-na-klasy',
                                                     help='montuje wynik.mp, dodaje dane routingowe netgenem, a potem rozklada na klasy')
    parser_rozdziel_na_klasy.add_argument('obszary', nargs="*", default=['pwd'])
    parser_rozdziel_na_klasy.set_defaults(func=rozdziel_na_klasy)

    # parser dla komendy patch
    parser_patch = subparsers.add_parser('patch', help='naklada latki przy pomocy komendy patch/patch.exe')
    parser_patch.add_argument('pliki_diff', nargs='+')
    parser_patch.set_defaults(func=patch)

    # parser dla komendy dodaj dane routingowe
    parser_dodaj_dane_routingowe = subparsers.add_parser('dodaj-dane-routingowe', help="dodaje dane routingowe przy "
                                                                                       " pomocy netgena")
    parser_dodaj_dane_routingowe.add_argument('-o', '--output-filename', help='Nazwa pliku mp z danymi routingowymi, '
                                                                          'domyślnie wynik.mp',
                                              action='store', default=['wynik.mp'], nargs=1)
    parser_dodaj_dane_routingowe.set_defaults(func=dodaj_dane_routingowe)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main(sys.argv)
