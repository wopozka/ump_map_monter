#!/usr/bin/env python3
# -*- coding: cp1250 -*-

import sys
import os
import argparse
from collections import defaultdict


class PolygonyObszarow:
    # klasa przechowujaca wspolrzedne obszaru ograniczajacego
    # oraz zawierająca funkcje sprawdzające czy punkt w obszarze
    
    # konstruktor klasy. 
    # argumenty: nazwa obszaru - nazwa obszaru z pliku obszary.txt np.
    # ; Przemysl uproszczony PL -> Przemysl, ; Wroclaw PL -> Wroclaw itd
    #            umphome - katalog ze zrodlami do ump, np u mnie: c:\ump\
    #
    def __init__(self, umphome, test_mode=False):
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            self.Kodowanie = 'latin2'
        else:
            self.Kodowanie = 'cp1250'
        self.umphome = umphome
        self.test_mode = test_mode
        # self.clockwise = 1
        # wspolrzedne obszaru w postaci par string: NS,EW
        self.wspolrzedne = defaultdict(lambda: [])
        self.liniaGraniczna_constXvariableY = defaultdict(lambda: {})
        self.liniaGraniczna_constYvariableX = defaultdict(lambda: {})
        self.wczytajobszarytxt()
        self.nazwa_obszaru = None

        # aby sprawdzanie dzialalo poprawnie obszar musi byc zgodny z ruchem wskazowek zegara jesli nie
        # to zamieniamy wspolrzedne
        for obszar in self.wspolrzedne:
            if not self.clockwisecheck(obszar):
                # print('dlugosc przed odwroceniem',aaabbb+1)
                self.wspolrzedne[obszar].reverse()
                tymczasowy_x = self.wspolrzedne[obszar][0::2]
                tymczasowy_y = self.wspolrzedne[obszar][1::2]
                del self.wspolrzedne[obszar][:]
                for aa in range(len(tymczasowy_x)-1):
                    self.wspolrzedne[obszar].append(tymczasowy_y[aa])
                    self.wspolrzedne[obszar].append(tymczasowy_x[aa])

            # print('odwrocilem wsp num',self.clockwisecheck(self.wspolrzednenumeryczne),self.clockwise)
            # print('dlugosc po odwroceniu',len(self.wspolrzednenumeryczne))
            # self.porzadkujwspolrzedne(a5)
    
    def clockwisecheck(self, obszar):
        """funkcja sprawdzajaca czy obszar prawo czy lewoskretny"""
        # https://www.geeksforgeeks.org/orientation-3-ordered-points/
        p = self.wspolrzedne[obszar]
        count = 0
        n = int(len(p) / 2 - 1)
        for i in range(n):
            x1 = p[i]
            y1 = p[i + 1]
            x2 = p[i + 2]
            y2 = p[i + 3]
            x3 = p[i + 4]
            y3 = p[i + 5]
            z = (y2-y1)*(x3-x2)-(y3-y2)*(x2-x1)
            if z < 0:
                count -= 1
            elif z > 0:
                count += 1
        if count > 0:
            # sys.stderr.write('Obszar lewoskretny, odwracam.')
            return False
        elif count < 0:
            # print('Obszar prawoskretny, pozostawiam jak jest.')
            return True

    # funkcja wczytuje dany obszar z pliku narzedzia/obszary.txt
    def wczytajobszarytxt(self):
        koniecpliku = 0
        czyznalazlemobszar = 0
        if self.test_mode:
            plik_obszarow_txt = self.umphome
        else:
            plik_obszarow_txt = os.path.join(os.path.join(self.umphome, 'narzedzia'), 'obszary.txt')
        plik_obszary = open(plik_obszarow_txt, encoding=self.Kodowanie, errors='ignore')
        linia = plik_obszary.readline()
        while linia:
            if linia.startswith('; '):
                nazwa_obszaru = linia.split('; ', 1)[-1].strip()
                # czyznalazlemobszar = 1
                while not linia.startswith('Data0='):
                    linia = plik_obszary.readline()
                linia = linia.split('=')[-1].strip()

                # tworzymy liste wspolrzednych w formacie [x,y],[x1,y1],[x2,y2]
                lista_wspolrzednych = linia.lstrip('(').rstrip(')').split('),(')
                if lista_wspolrzednych[-1] != lista_wspolrzednych[0]:
                    lista_wspolrzednych.append(lista_wspolrzednych[0])
                for aa in lista_wspolrzednych:
                    xxx, yyy = aa.split(',')
                    x = float(xxx)
                    y = float(yyy)
                    if self.wspolrzedne[nazwa_obszaru]:
                        if x == self.wspolrzedne[nazwa_obszaru][-2]:
                            if x not in self.liniaGraniczna_constXvariableY[nazwa_obszaru]:
                                self.liniaGraniczna_constXvariableY[nazwa_obszaru][x] = \
                                    [(min(y, self.wspolrzedne[nazwa_obszaru][-1]),
                                      max(y, self.wspolrzedne[nazwa_obszaru][-1]),)]
                            else:
                                _min = min(y, self.wspolrzedne[nazwa_obszaru][-1])
                                _max = max(y, self.wspolrzedne[nazwa_obszaru][-1])
                                self.liniaGraniczna_constXvariableY[nazwa_obszaru][x].append((_min, _max,))
                        if y == self.wspolrzedne[nazwa_obszaru][-1]:
                            if y not in self.liniaGraniczna_constYvariableX[nazwa_obszaru]:
                                self.liniaGraniczna_constYvariableX[nazwa_obszaru][y] = \
                                    [(min(x, self.wspolrzedne[nazwa_obszaru][-2]),
                                      max(x, self.wspolrzedne[nazwa_obszaru][-2]),)]
                            else:
                                _min = min(x, self.wspolrzedne[nazwa_obszaru][-2])
                                _max = max(x, self.wspolrzedne[nazwa_obszaru][-2])
                                self.liniaGraniczna_constYvariableX[nazwa_obszaru][y].append((_min, _max,))
                    self.wspolrzedne[nazwa_obszaru].append(x)
                    self.wspolrzedne[nazwa_obszaru].append(y)
                # print(self.wspolrzedne, file=sys.stderr)
            linia = plik_obszary.readline()
        plik_obszary.close()
        return 1

    # funkcja sprawdzajaca czy dany punkt jest polozony wewnatrz wielokata obszaru
    def is_inside(self, x, y, nazwaobszaru=None):
        # najpierw znajdz obszar
        # print('aaa', self.nazwa_obszaru, nazwaobszaru)
        if self.nazwa_obszaru is None or nazwaobszaru not in self.nazwa_obszaru:
            for obszar in self.wspolrzedne:
                if nazwaobszaru in obszar:
                    szukany_obszar = obszar
                    self.nazwa_obszaru = obszar
                    # print(obszar, szukany_obszar)
                    break
            else:
                return None
        else:
            szukany_obszar = self.nazwa_obszaru

        # najpierw sprawdzmy czy dany punkt nie lezy przypadkiem na linii granicznej

        if x in self.liniaGraniczna_constXvariableY[szukany_obszar]:
            for iterator in self.liniaGraniczna_constXvariableY[szukany_obszar][x]:
                if iterator[0] <= y <= iterator[1]:
                    return True
        if y in self.liniaGraniczna_constYvariableX[szukany_obszar]:
            for iterator in self.liniaGraniczna_constYvariableX[szukany_obszar][y]:
                if iterator[0] <= x <= iterator[1]:
                    return True

        polyx = self.wspolrzedne[szukany_obszar][0::2]
        polyy = self.wspolrzedne[szukany_obszar][1::2]
        n = len(polyx)
        inside = False

        p1x = polyx[0]
        p1y = polyy[0]
        for i in range(1, n+1):
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

    def zwroc_obszar_dla_wsp(self, x, y):
        for obszar in self.wspolrzedne:
            if self.is_inside(x, y, obszar):
                return obszar
        print('Nic nie znalazlem dla %s, %s' % (x, y))
        return ''

class wspolrzedne:
    # klasa przechowuje liste wszystkich wspolrzednych w postaci tablicy
    def __init__(self):
        # lista wszystkich wspolrzednych w postaci tablicy, wspolrzedne nie są grupowane parami, ale jedna za druga
        # czyli mamy: szerokosc, dlugosc, szerokosc1, dlugosc1, szerokosc2, dlugosc2
        # wspolrzedne jako float
        self.listawspolrzednych = []
        # tak na wszelki wypadek przechowujemy tez pare wspolrzednych w postaci stringa czyli: szerokosc,dlugosc
        self.listawspolrzednychstring = []
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            self.Kodowanie = 'latin2'
        else:
            self.Kodowanie = 'cp1250'
        self.lista_plikow = []

    # funkcja wczytuje wspolrzedne z danego pliku. W zaleznosci czy pnt, adr czy txt
    def wczytajobiekt(self, nazwapliku):
        koniecpliku = 0
        a = open(nazwapliku, encoding=self.Kodowanie, errors='ignore')
        if nazwapliku.endswith('.pnt') or nazwapliku.endswith('.adr'):
            while not koniecpliku:
                linia = a.readline()
                if linia.startswith('  '):
                    linia = linia.strip()
                    bbb_tmp = linia.split(',')
                    szerokosc = bbb_tmp[0]
                    dlugosc = bbb_tmp[1]
                    self.listawspolrzednychstring.append(szerokosc + ',' + dlugosc)
                    self.listawspolrzednych.append(float(szerokosc))
                    self.listawspolrzednych.append(float(dlugosc))
                    self.lista_plikow.append(nazwapliku)
                    # print(szerokosc,':',dlugosc)
                elif linia == '':
                    koniecpliku = 1

        else:
            while not koniecpliku:
                linia = a.readline()
                if linia.startswith('Data'):
                    linia = linia.split('=')[-1].strip()
                    # print(linia)
                    for aaa_tmp in linia.split('),('):
                        aaa_tmp = aaa_tmp.lstrip('(').rstrip(')')
                        self.listawspolrzednychstring.append(aaa_tmp)
                        self.lista_plikow.append(nazwapliku)
                        # print(aaa_tmp)
                        dlugosc, szerokosc = aaa_tmp.split(',')
                        self.listawspolrzednych.append(float(dlugosc))
                        self.listawspolrzednych.append(float(szerokosc))
                elif linia == '':
                    koniecpliku = 1


def update_progress(progress):
    # zwykly progressbar zeby widac bylo postep przeszukiwania
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
    text = "\rProcent: [{0}] {1}% {2}".format("#"*block + "-"*(barLength-block), int(progress*100), status)
    sys.stderr.write(text)
    sys.stderr.flush()

def main(argumenty):
    # argumenty to tablica z dwoma zmiennymi:
    # argumenty[0] - zawiera nazwę obszaru w formacie mdm-py, czyli np. UMP-PL-Lodz, UMP-PL-Radom, UMP-PL-Wroclaw
    # argumenty[1] - katalog domowy z UMP, u mnie w win: c:\ump\
    
    # zmienna z lista wystajacych poza obszar punktow
    lista_wystajacych = []
    sys.stderr.write('Wczytuje granice obszaru: ' + argumenty[0] + '\n')
    
    # zmienna aaa jest instancja klasy polygonObszaru, wywolujemy z dwoma argumentami
    # argument[0].split... - wycina z UMP-PL-Lodz samo Lodz, z UMP-PL-Wroclaw samo Wrocal,
    # bo w obszary.txt jest sam ten drugi czlon
    # argument[1] to katalog domowy ump
    obszar_do_zbadania = argumenty[0].split('-')[-1]
    aaa = PolygonyObszarow(argumenty[1])

    sys.stderr.write('\nWczytuje wspolrzedne punktow dla '+argumenty[0]+'\n')

    # zmienna przechowujaca wszystkie wspolrzedne
    bbb = wspolrzedne()
    
    # dla kazdego pliku w katalogu z obszarem wczytaj wspolrzedne
    # listujemy kazdy plik w katalogu umphome\obszar\src\
    katalog_do_przeszukania = os.path.join(argumenty[1], os.path.join(argumenty[0], 'src'))
    for arg in [f for f in os.listdir(katalog_do_przeszukania)]:
        # jeśli dany plik nie jest katalogiem
        if not os.path.isdir(os.path.join(katalog_do_przeszukania, arg)):
            # poniewaz nie chce wczytywac plikow adr, to je ignoruje wczytujac tylko pliki txt i pnt.
            # dzieki temu sa rowniez ignorowane pliki konfliktow cvs konczace sie numerem rewizji
            if arg.endswith('.txt') or arg.endswith('.pnt'):
                # wczytaj wszystkie wspolrzedne z danego pliku. Obsluguje zarowno txt, pnt jak i adr
                bbb.wczytajobiekt(os.path.join(katalog_do_przeszukania, arg))

    ilosc_punktow_do_sprawdzenia = len(bbb.listawspolrzednych)
    print('Wspolrzedne {} punktow wczytane, sprawdzam'.format(int(ilosc_punktow_do_sprawdzenia/2)))

    # ustawiamy progressbar na 100
    update_progress(0/100)
    progres_previous = 0
    
    # iterujemy po kazdej drugiej wspolrzednej. Musimy powiedzlic przez 2 bo lista zawiera ciag, szer, dl, szer, dl itd.
    obszary_z_wystajacymi = set()
    for a in range(int(ilosc_punktow_do_sprawdzenia / 2)):
        # ponieważ progressbar ma przeskakiwać tylko co pełny procent robimy mały trick przed uaktualnieniem
        # i sprawdzamy czy zmieniło się o 1%.
        if (a*100//(ilosc_punktow_do_sprawdzenia/2)) > progres_previous:
            progres_previous = a*100//(ilosc_punktow_do_sprawdzenia/2)
            update_progress(progres_previous / 100)

        # print(a, bbb.listawspolrzednych[2 * a ], bbb.listawspolrzednych[2 * a +1])
        # sprawdzamy czy punkt w srodku
        wsp_x = bbb.listawspolrzednych[2 * a]
        wsp_y = bbb.listawspolrzednych[2 * a + 1]
        if not aaa.is_inside(wsp_x, wsp_y, nazwaobszaru=obszar_do_zbadania):
            # print('nie w srodku')
            # sprawdzamy czy punkt nie lezy przypadkiem na granicy obszaru
            # najpierw sprawdz czy dany punkt nie ma swojego odpowiednika we wspolrzednych obszaru, niby tylko kilkanascie punktow
            # ale po co je sprawdzac jesli nie trzeba. Sprawdzamy czy dany string x,y jest we wspolrzednych obszaru -> x,y
            if not (bbb.listawspolrzednychstring[a] in aaa.wspolrzedne):
                print(bbb.listawspolrzednychstring[a], bbb.lista_plikow[a])
                _obszar = aaa.zwroc_obszar_dla_wsp(wsp_x, wsp_y)
                obszary_z_wystajacymi.add(_obszar)
                lista_wystajacych.append((str(bbb.listawspolrzednych[2 * a]) + ',' +
                                         str(bbb.listawspolrzednych[2 * a + 1]),
                                         'w obszarze: ' + _obszar,))

    update_progress(100 / 100)

    if lista_wystajacych:
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            Kodowanie = 'latin2'
        else:
            Kodowanie = 'cp1250'
        
        plik = open(os.path.join(argumenty[2], 'wystajace.wpt'), 'w', encoding=Kodowanie, errors='ignore')
        plik.write("OziExplorer Waypoint File Version 1.1\n")
        plik.write("WGS 84\n")
        plik.write("Reserved 2\n")
        plik.write("Reserved 3\n")
        for tmp_aaa in lista_wystajacych:
            plik.write("-1,wystaje,")
            plik.write(tmp_aaa[0])
            print(' '.join(tmp_aaa))
            plik.write(",,0,1,3,255,65535,,,0,0,0,6,0,19\n")
        plik.close()
        print(', '.join(obszary_z_wystajacymi))
        sys.stderr.write('zapisuje plik z wystajacymi ' + os.path.join(argumenty[2], 'wystajace.wpt'))
    sys.stderr.write('\nKoniec\n')
    sys.stderr.flush()
    

def parsuj_args(args):
    parser = argparse.ArgumentParser(description="szukanie wystajacych poza obszar punktow na danym obszarze mapy")
    parser.add_argument('-r', '--region', dest='umpregion', required=True,
                        help='region do przeszukania w formacie UMP-XX-ZZZZ, UMP-PL-Lodz, UMP-PL-Gdansk itd.')
    parser.add_argument('-kz', '--katalog-ze-zrodlami', dest='katalog_zrodel', required=True,
                        help='katalog ze zrodlami, np c:\\ump\\')
    
    args = parser.parse_args()
    # args.func(args)
    main([args.umpregion, args.katalog_zrodel, os.path.join(args.katalog_zrodel, args.umpregion)])
    

if __name__ == "__main__":
    parsuj_args(sys.argv)
