#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Szukanie rozbieznosci pomiedzy adresacja punktowa (POI Type=0x2800) a adresacja liniowa (NumbersX= drog).

Dla kazdego punktu adresowego z numerem bez indeksu literowego szukamy odcinkow numeracji liniowej tej samej
ulicy w tym samym miescie (z tym samym kodem pocztowym, o ile jest podany), ktore obejmuja dany numer, interpolujemy polozenie numeru wzdluz drogi i liczymy
odleglosc od punktu adresowego. Gdy najblizszy zinterpolowany punkt jest dalej niz limit - zglaszamy blad."""

import sys
import os.path
import re
import math
from collections import defaultdict, namedtuple

TYPY_ROUTINGOWE = {'0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7', '0x8', '0x9', '0xa', '0xb',
                   '0xc', '0x16', '0xd', '0xe', '0xf', '0x1a', '0x117'}
TYP_PUNKTU_ADRESOWEGO = '0x2800'
WZORZEC_NUMERU = re.compile(r'^\d+$')
PROMIEN_ZIEMI = 6371000.0

PunktAdresowy = namedtuple('PunktAdresowy', 'miasto ulica numer kod wspolrzedne')
OdcinekNumeracji = namedtuple('OdcinekNumeracji', 'start koniec parzystosc kod punkty')


def normalizuj_nazwe(nazwa):
    """Usuwa prefiksy ~[0x..] i {...} (tak jak mont_demont.sprawdz_label_dla_drogi_z_numerami), zbedne spacje
    i wielkosc liter, aby nazwy ulic i miast z POI i z drog mozna bylo porownywac."""
    nazwa = nazwa.strip()
    if nazwa.startswith('~'):
        nazwa = nazwa.split(' ', 1)[-1] if ' ' in nazwa else ''
    if nazwa.startswith('{'):
        nazwa = nazwa.split('}', 1)[-1]
    return ' '.join(nazwa.split()).lower()


def normalizuj_kod(kod):
    """Usuwa spacje z kodu pocztowego, brak kodu (pusty, -1) zwraca jako ''."""
    kod = ''.join(kod.split())
    return '' if kod == '-1' else kod


def kody_zgodne(kod1, kod2):
    """Kody pocztowe uznajemy za zgodne, gdy sa rowne albo gdy ktoregos brakuje - w przeciwnym razie
    drogi bez kodu nie pasowalyby do zadnego punktu adresowego."""
    return not kod1 or not kod2 or kod1 == kod2


def numer_bez_litery(numer):
    """Zwraca numer jako int, albo None gdy numer ma indeks literowy, jest lamany itp."""
    numer = numer.strip()
    if WZORZEC_NUMERU.match(numer):
        return int(numer)
    return None


def wspolrzedne_z_data(data):
    """'(52.1,21.1),(52.2,21.2)' -> [(52.1, 21.1), (52.2, 21.2)]"""
    wynik = []
    for para in data.strip().lstrip('(').rstrip(')').split('),('):
        szerokosc, dlugosc = para.split(',')
        wynik.append((float(szerokosc), float(dlugosc)))
    return wynik


def odleglosc_m(punkt1, punkt2):
    """Odleglosc w metrach w przyblizeniu rownoprostokatnym - dla odleglosci rzedu kilometrow wystarczy."""
    sr_szerokosc = math.radians((punkt1[0] + punkt2[0]) / 2)
    d_szer = math.radians(punkt2[0] - punkt1[0])
    d_dl = math.radians(punkt2[1] - punkt1[1]) * math.cos(sr_szerokosc)
    return PROMIEN_ZIEMI * math.hypot(d_szer, d_dl)


def interpoluj_punkt(punkty, t):
    """Zwraca punkt lezacy na lamanej punkty w odleglosci t * dlugosc_lamanej od jej poczatku."""
    dlugosci = [odleglosc_m(a, b) for a, b in zip(punkty, punkty[1:])]
    cel = t * sum(dlugosci)
    for (a, b), dlugosc in zip(zip(punkty, punkty[1:]), dlugosci):
        if cel <= dlugosc and dlugosc > 0:
            u = cel / dlugosc
            return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        cel -= dlugosc
    return punkty[-1]


def wartosc_t_dla_numeru(numer, odcinek):
    """Zwraca polozenie numeru w zakresie odcinka (0..1) albo None gdy odcinek numeru nie obejmuje."""
    if not min(odcinek.start, odcinek.koniec) <= numer <= max(odcinek.start, odcinek.koniec):
        return None
    if odcinek.parzystosc == 'O' and numer % 2 != 1:
        return None
    if odcinek.parzystosc == 'E' and numer % 2 != 0:
        return None
    if odcinek.start == odcinek.koniec:
        return 0.5
    return (numer - odcinek.start) / (odcinek.koniec - odcinek.start)


def odcinki_numeracji(punkty_drogi, numeracje, miasto, kod_pocztowy=''):
    """Dzieli droge na odcinki numeracji. numeracje to lista wartosci kluczy NumbersX, czyli
    idx,LTyp,LStart,LEnd,RTyp,RStart,REnd[,LZip,RZip,LCity,LRegion,LCountry,RCity,RRegion,RCountry].
    Miasto i kod pocztowy strony biora sie z Numbers, a gdy ich tam nie ma - z Miasto= i KodPoczt= drogi.
    Zwraca liste par (miasto, OdcinekNumeracji)."""
    pola_numeracji = sorted((numeracja.split(',') for numeracja in numeracje), key=lambda pola: int(pola[0]))
    wynik = []
    for pola, nastepne_pola in zip(pola_numeracji, pola_numeracji[1:] + [None]):
        idx_poczatku = int(pola[0])
        idx_konca = int(nastepne_pola[0]) if nastepne_pola is not None else len(punkty_drogi) - 1
        punkty = punkty_drogi[idx_poczatku:idx_konca + 1]
        if len(punkty) < 2:
            continue
        for pozycja_typu, pozycja_kodu, pozycja_miasta in ((1, 7, 9), (4, 8, 12)):
            parzystosc = pola[pozycja_typu].strip().upper()
            if parzystosc not in ('O', 'E', 'B'):
                continue
            start, koniec = int(pola[pozycja_typu + 1]), int(pola[pozycja_typu + 2])
            if start <= 0 or koniec <= 0:
                continue
            miasto_strony = miasto
            if len(pola) > pozycja_miasta and pola[pozycja_miasta].strip() not in ('', '-1'):
                miasto_strony = pola[pozycja_miasta]
            kod_strony = normalizuj_kod(pola[pozycja_kodu]) if len(pola) > pozycja_kodu else ''
            if not kod_strony:
                kod_strony = normalizuj_kod(kod_pocztowy)
            wynik.append((normalizuj_nazwe(miasto_strony),
                          OdcinekNumeracji(start, koniec, parzystosc, kod_strony, punkty)))
    return wynik


def zwroc_rekordy_pliku_mp(zawartosc_pliku):
    """Zwraca rekordy POI adresowych oraz drog routingowych z numeracja jako slowniki klucz: wartosc."""
    punkty_adresowe, drogi = [], []
    sekcja = ''
    rekord = {}
    for tmp_linia in zawartosc_pliku:
        linia = tmp_linia.strip()
        if linia in ('[POI]', '[POLYLINE]', '[POLYGON]'):
            sekcja = linia
            rekord = {}
            continue
        if linia == '[END]':
            if sekcja == '[POI]' and rekord.get('Type') == TYP_PUNKTU_ADRESOWEGO:
                punkty_adresowe.append(rekord)
            elif sekcja == '[POLYLINE]' and rekord.get('Type') in TYPY_ROUTINGOWE and rekord.get('Numbers'):
                drogi.append(rekord)
            sekcja = ''
            rekord = {}
            continue
        if not sekcja or linia.startswith(';') or '=' not in linia:
            continue
        klucz, wartosc = linia.split('=', 1)
        if klucz.startswith('Numbers') and not klucz.startswith('NumbersExt'):
            rekord.setdefault('Numbers', []).append(wartosc)
        elif klucz.startswith('Data'):
            # bierzemy pierwsze Data - kolejne to ta sama geometria dla innych poziomow
            rekord.setdefault('Data', wartosc)
        else:
            rekord[klucz] = wartosc
    return punkty_adresowe, drogi


class SprawdzanieAdresacji(object):
    def __init__(self, punkty_adresowe, drogi):
        self.punkty_adresowe = []
        self.pominiete_z_litera = 0
        for rekord in punkty_adresowe:
            numer = numer_bez_litery(rekord.get('HouseNumber') or rekord.get('Label', ''))
            if numer is None or 'Data' not in rekord:
                self.pominiete_z_litera += 1
                continue
            self.punkty_adresowe.append(PunktAdresowy(rekord.get('Miasto', ''), rekord.get('StreetDesc', ''), numer,
                                                      normalizuj_kod(rekord.get('KodPoczt', '')),
                                                      wspolrzedne_z_data(rekord['Data'])[0]))
        # klucz (miasto, ulica) po normalizacji, wartosc - lista odcinkow numeracji
        self.odcinki = defaultdict(list)
        for rekord in drogi:
            ulica = normalizuj_nazwe(rekord.get('adrLabel') or rekord.get('Label', ''))
            if not ulica or 'Data' not in rekord:
                continue
            for miasto, odcinek in odcinki_numeracji(wspolrzedne_z_data(rekord['Data']), rekord['Numbers'],
                                                    rekord.get('Miasto', ''), rekord.get('KodPoczt', '')):
                self.odcinki[(miasto, ulica)].append(odcinek)

    def odcinki_ulicy(self, punkt_adresowy):
        """Zwraca wszystkie odcinki numeracji ulicy punktu adresowego w jego miescie, bez wzgledu na kod pocztowy."""
        klucz = (normalizuj_nazwe(punkt_adresowy.miasto), normalizuj_nazwe(punkt_adresowy.ulica))
        return self.odcinki.get(klucz, [])

    @staticmethod
    def najblizszy_punkt_numeracji(punkt_adresowy, odcinki_ulicy):
        """Zwraca (odleglosc, zinterpolowany punkt, kod pocztowy odcinka) dla najblizszego odcinka obejmujacego
        numer albo None."""
        najblizszy = None
        for odcinek in odcinki_ulicy:
            t = wartosc_t_dla_numeru(punkt_adresowy.numer, odcinek)
            if t is None:
                continue
            punkt = interpoluj_punkt(odcinek.punkty, t)
            odleglosc = odleglosc_m(punkt_adresowy.wspolrzedne, punkt)
            if najblizszy is None or odleglosc < najblizszy[0]:
                najblizszy = (odleglosc, punkt, odcinek.kod)
        return najblizszy

    def sprawdz(self, limit):
        """Zwraca slownik z listami: za_daleko, inny_kod, brak_numeru, brak_ulicy.

        Najpierw szukamy numeracji ze zgodnym kodem pocztowym. Gdy jej nie ma albo jest dalej niz limit,
        szukamy najblizszej numeracji tej ulicy z dowolnym kodem - jesli miesci sie w limicie, to adres
        jest na miejscu, a nie zgadza sie tylko kod pocztowy; jesli nie, raportujemy najblizsza z nich."""
        wyniki = {'za_daleko': [], 'inny_kod': [], 'brak_numeru': [], 'brak_ulicy': []}
        for punkt_adresowy in self.punkty_adresowe:
            odcinki_ulicy = self.odcinki_ulicy(punkt_adresowy)
            if not odcinki_ulicy:
                wyniki['brak_ulicy'].append(punkt_adresowy)
                continue
            odcinki_zgodne = [odcinek for odcinek in odcinki_ulicy if kody_zgodne(punkt_adresowy.kod, odcinek.kod)]
            najblizszy = self.najblizszy_punkt_numeracji(punkt_adresowy, odcinki_zgodne)
            if najblizszy is not None and najblizszy[0] <= limit:
                continue
            najblizszy = self.najblizszy_punkt_numeracji(punkt_adresowy, odcinki_ulicy)
            if najblizszy is None:
                wyniki['brak_numeru'].append(punkt_adresowy)
            elif najblizszy[0] <= limit:
                wyniki['inny_kod'].append((punkt_adresowy,) + najblizszy)
            else:
                wyniki['za_daleko'].append((punkt_adresowy,) + najblizszy)
        return wyniki


def opis_punktu(punkt_adresowy):
    miasto = ' '.join(a for a in (punkt_adresowy.kod, punkt_adresowy.miasto) if a)
    return '%s %s, %s (%.5f,%.5f)' % (punkt_adresowy.ulica, punkt_adresowy.numer, miasto,
                                      punkt_adresowy.wspolrzedne[0], punkt_adresowy.wspolrzedne[1])


def main(nazwapliku, stderr_stdout_writer, limit):
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        encoding = 'latin2'
    else:
        encoding = 'cp1250'
    try:
        with open(nazwapliku, encoding=encoding, errors='ignore') as f:
            punkty_adresowe, drogi = zwroc_rekordy_pliku_mp(f)
    except FileNotFoundError:
        stderr_stdout_writer.stderrorwrite('Nie mogę znaleźć pliku %s!' % nazwapliku)
        return
    except PermissionError:
        stderr_stdout_writer.stderrorwrite('ME zapisuje plik. Uruchom sprawdzanie jeszcze raz!')
        return

    sprawdzanie = SprawdzanieAdresacji(punkty_adresowe, drogi)
    wyniki = sprawdzanie.sprawdz(limit)

    linie_raportu = []
    for punkt_adresowy, odleglosc, punkt, kod in wyniki['za_daleko']:
        linie_raportu.append('Adres-za daleko: %s - %d m od najbliższej numeracji liniowej (%.5f,%.5f), kod: %s'
                             % (opis_punktu(punkt_adresowy), odleglosc, punkt[0], punkt[1], kod or 'brak'))
    for punkt_adresowy, odleglosc, punkt, kod in wyniki['inny_kod']:
        linie_raportu.append('Adres-inny kod pocztowy: %s - numeracja liniowa %d m dalej (%.5f,%.5f) ma kod: %s'
                             % (opis_punktu(punkt_adresowy), odleglosc, punkt[0], punkt[1], kod))
    for punkt_adresowy in wyniki['brak_numeru']:
        linie_raportu.append('Adres-brak numeracji liniowej: %s' % opis_punktu(punkt_adresowy))
    for linia in linie_raportu:
        stderr_stdout_writer.stderrorwrite(linia)
    # ulic bez numeracji liniowej moze byc bardzo duzo, wiec trafiaja tylko do pliku
    for punkt_adresowy in wyniki['brak_ulicy']:
        linie_raportu.append('Adres-ulica bez numeracji liniowej: %s' % opis_punktu(punkt_adresowy))

    nazwa_pliku_raportu = os.path.splitext(nazwapliku)[0] + '_bledy_adresacji.txt'
    with open(nazwa_pliku_raportu, 'w', encoding=encoding, errors='replace') as plik_raportu:
        for linia in linie_raportu:
            plik_raportu.write(linia + '\n')

    stderr_stdout_writer.stdoutwrite('Punkty adresowe: %s, pominięte (z literą lub inne): %s, sprawdzone: %s'
                                     % (len(punkty_adresowe), sprawdzanie.pominiete_z_litera,
                                        len(sprawdzanie.punkty_adresowe)))
    stderr_stdout_writer.stdoutwrite('Za daleko (> %s m): %s, inny kod pocztowy: %s, brak numeru w numeracji '
                                     'liniowej: %s, ulica bez numeracji liniowej: %s'
                                     % (limit, len(wyniki['za_daleko']), len(wyniki['inny_kod']),
                                        len(wyniki['brak_numeru']), len(wyniki['brak_ulicy'])))
    stderr_stdout_writer.stdoutwrite('Utworzono plik %s.' % nazwa_pliku_raportu)


if __name__ == "__main__":
    print('Używaj z mont_demont.py')
