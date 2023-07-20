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
import json
import subprocess
import tempfile
import shutil
import kdtree
import znajdz_bledy_numeracji
from collections import OrderedDict
from collections import defaultdict
from datetime import date
from datetime import datetime


class Mkgmap(object):
    def __init__(self, args, zmienne):
        self.args = args
        if hasattr(args, 'mkgmap_path') and args.mkgmap_path:
            self.mkg_map = args.mkgmap_path
        else:
            self.mkg_map = zmienne.mkgmap_jar_path
        self.zmienne = zmienne

    def java_call_general(self):
        java_call_args = ['java'] + ['-Xmx' + self.args.maksymalna_pamiec] + ['-jar', self.mkg_map, '--lower-case']
        if self.args.code_page == 'cp1250':
            java_call_args.append('--code-page=1250')
        java_call_args.append('--family-id=' + self.args.family_id)
        java_call_args.append('--output-dir=' + self.zmienne.KatalogRoboczy)
        return java_call_args

    def java_call_typ(self):
        return self.java_call_general()

    def java_call_mkgmap(self):
        mapset_name = []
        java_call_args = self.java_call_general()
        if self.args.dodaj_routing:
            java_call_args += ['--route', '--drive-on=detect,right']
        if self.args.format_mapy == 'gmapsupp':
            java_call_args.append('--gmapsupp')
            mapset_name = ['--description=UMP pcPL']
        else:
            java_call_args.append('--gmapi')
        if self.args.index:
            java_call_args += ['--index', '--split-name-index']
        try:
            int(self.args.max_jobs)
        except ValueError:
            pass
        else:
            if int(self.args.max_jobs):
                java_call_args += ['--max-jobs=' + self.args.max_jobs]
        nazwa_map = 'UMP mkgmap ' + date.today().strftime('%d%b%y')
        java_call_args += ['--family-name=' + nazwa_map, '--series-name=' + nazwa_map]
        plik_licencji = os.path.join(os.path.join(self.zmienne.KatalogzUMP, 'narzedzia'), 'UMP_mkgmap_licencja.txt')
        java_call_args += ['--overview-mapname=' + 'UMP_mkgmap']
        java_call_args += ['--license-file=' + plik_licencji]
        java_call_args += ['--area-name=' + 'UMP to']
        return java_call_args, mapset_name, nazwa_map


class ErrOutWriter(object):
    def __init__(self, args):
        self.stderrqueue = None
        self.stdoutqueue = None
        if hasattr(args, 'stderrqueue'):
            self.stderrqueue = args.stderrqueue
        if hasattr(args, 'stdoutqueue'):
            self.stdoutqueue = args.stdoutqueue

    def stderrorwrite(self, string_to_print):
        if self.stderrqueue is not None:
            self.stderrqueue.put(self.modyfikuj_komunikat(string_to_print))
        else:
            print(string_to_print, file=sys.stderr)

    def stdoutwrite(self, string_to_print):
        if self.stdoutqueue is not None:
            self.stdoutqueue.put(self.modyfikuj_komunikat(string_to_print))
        else:
            print(string_to_print, file=sys.stdout)

    @staticmethod
    def modyfikuj_komunikat(komunikat):
        if not komunikat.endswith('\n'):
            komunikat += '\n'
        if komunikat.startswith('\n'):
            komunikat = komunikat.lstrip()
        return komunikat


class TestyPoprawnosciDanych(object):
    DOZWOLONE_ZNAKI_CP1250 = 'óąćęłńśźżáäéëíöüčšâýăěňőřžçôúĺűß'
    DOZWOLONE_KLUCZE = {'adrLabel',
                        'City', 'CityIdx', 'Czas',
                        'dekLabel', 'DirIndicator', 'DontDisplayAdr', 'DontFind',
                        'EndLevel',
                        'Floors', 'ForceClass', 'ForceSpeed', 'FullLabel',
                        'HouseNumber', 'Height_f', 'Height_m', 'Highway',
                        'KodPoczt', 'Komentarz',
                        'Label', 'Label2', 'Label3', 'Lanes',
                        'MaxWeight', 'MiscInfo',
                        'Typ', 'Type',
                        'MaxHeight', 'MaxWidth', 'Miasto', 'Moto',
                        'LA', 'lokalLabel',
                        'Oplata', 'Oplata:moto', 'Oplata:rower', 'OvernightParking',
                        'Phone', 'Plik', 'POIPOLY',
                        'Rodzaj', 'RouteParam',
                        'Sign', 'SignAngle', 'SignLabel', 'SignParam', 'SignPos', 'Speed', 'StreetDesc',
                        'TLanes', 'Transit',
                        'RestrParam', 'Rozmiar',
                        'WebPage',
                        'Zip'
                        }
    DOZWOLONE_KLUCZE_PRZESTARZALE = {'Rampa'}
    # ponizsze klucze pojawiaja sie wielokrotnie w rekordzie, dlatego monter dodaje numery na koncu, aby je
    # rozroznic. Z tego powodu sa traktowane inaczej
    DOZWOLONE_KLUCZE_Z_NUMEREM = {'Numbers', 'Data0', 'Data1', 'Data2', 'Data3', 'HLevel', 'Exit'}

    def __init__(self, error_out_writer):
        # Typ dla roznych drog, ktore powinny posiadac wpis Miasto=
        self.error_out_writer = error_out_writer
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
            '0xd',  # droga dla rowerow
            '0xe',  # tunel
            '0xf',  # 4x4
            '0x16',  # walkway]
            # '0x1a',  # ferry
            # '0x1b'  # water or rail ferry
        ]
        typy_szlaki_piesze = ['0x010e00', '0x010e01', '0x010e02', '0x010e03', '0x010e04', '0x010e07']
        typy_szlaki_rowerowe = ['0x010e08', '0x010e09', '0x010e0a', '0x010e0b', '0x010e0c', '0x010e0d']
        typy_szlaki_inne = ['0x010e0f']
        self.typy_data_0_only = self.typy_label_z_miastem + ['0x14', '0x10e10', '0x10e14', '0x10e15'] + \
                                typy_szlaki_piesze + typy_szlaki_rowerowe + typy_szlaki_inne
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
        self.dozwolone_klucze = TestyPoprawnosciDanych.DOZWOLONE_KLUCZE
        self.dozwolone_klucze_przestarzale = TestyPoprawnosciDanych.DOZWOLONE_KLUCZE_PRZESTARZALE
        self.dozwolone_klucze_z_numerem = TestyPoprawnosciDanych.DOZWOLONE_KLUCZE_Z_NUMEREM
        self.dozwolone_wart_kluczy_funkcje = {'EndLevel': self.dozwolona_wartosc_dla_EndLevel,
                                              'Sign': self.dozwolona_wartosc_dla_Sign,
                                              'SignPos': self.dozwolona_wartosc_dla_SignPos,
                                              'SignAngle': self.dozwolona_wartosc_dla_SignAngle,
                                              'ForceSpeed': self.dozwolona_wartosc_dla_ForceSpeed,
                                              'ForceClass': self.dozwolona_wartosc_dla_ForceClass,
                                              'MaxWeight': self.dozwolona_wartosc_dla_MaxWeight
                                              }
        self.dozwolone_wartosci_dla_sign = {'BRAK', 'NAKAZ_BRAK', 'brak',  # brak zakazu
                                            'B-1', 'B1', 'ZAKAZ', 'RESTRYKCJA',  # inna restrykcja
                                            'B-2', 'B2', 'ZAKAZ_PROSTO', 'Z_PROSTO',  # zakaz na wprost
                                            'B-21', 'B21', 'ZAKAZ_LEWO', 'Z_LEWO',  # zakaz w lewo
                                            'B-22', 'B22', 'ZAKAZ_PRAWO', 'Z_PRAWO',  # zakaz w prawo
                                            'B-23', 'B23', 'ZAKAZ_ZAWRACANIA', 'Z_ZAWRACANIA', 'NO_UTURN',  # zakaz zawracania
                                            'C-2', 'C2', 'NAKAZ_PRAWO', 'N_PRAWO',  # nakaz w prawo
                                            'C-4', 'C4', 'NAKAZ_LEWO', 'N_LEWO',  # nakaz w lewo
                                            'C-5', 'C5', 'NAKAZ_PROSTO', 'N_PROSTO',  # nakaz prosto
                                            'C-6', 'C6', 'NAKAZ_PRAWO_PROSTO', 'N_PRAWO_PROSTO', 'NAKAZ_PROSTO_PRAWO',
                                            'N_PROSTO_PRAWO',  # nakaz prosto lub w prawo
                                            'C-7', 'C7', 'NAKAZ_LEWO_PROSTO', 'N_LEWO_PROSTO', 'NAKAZ_PROSTO_LEWO',
                                            'N_PROSTO_LEWO',  # nakaz prosto lub w lewo
                                            'C-8', 'C8', 'NAKAZ_LEWO_PRAWO', 'N_LEWO_PRAWO', 'NAKAZ_PRAWO_LEWO',
                                            'N_PRAWO_LEWO'  # nakaz prawo lub w lewo
                                            }
        self.dozwolone_wartosci_dla_ForceSpeed = {'0', '1', '2', '3', '4', '5', '6', '7', 'faster', 'slower'}
        self.dozwolone_wartosci_dla_ForceClass = {'0', '1', '2', '3', '4'}
        self.dozwolone_wartosci_dla_EndLevel = {'0', '1', '2', '3', '4', '5'}
        self.typy_bez_forceclass = {'0x1',  # motorway
                                    '0x2',  # principal highway
                                    '0x8',  # highway ramp, low-speed
                                    '0x9',  # highway ramp, high-speed
                                    '0xb',  # highway connector
                                    '0xc',  # roundabout
                                    '0xe',  # tunnel
                                    '0x1a',  # ferry
                                    }
        self.wspolrzedne_obiektu = ''
        self.dozwolone_znaki_cp1250 = set(TestyPoprawnosciDanych.DOZWOLONE_ZNAKI_CP1250 +
                                      TestyPoprawnosciDanych.DOZWOLONE_ZNAKI_CP1250[:-1].upper() +
                                      string.printable[:-5] + '°')

    def sprawdz_czy_forceclass_zabronione(self, dane_do_zapisu):
        if 'ForceClass' not in dane_do_zapisu or dane_do_zapisu['POIPOLY'] != '[POLYLINE]' \
                or dane_do_zapisu['Type'] not in self.typy_bez_forceclass:
            return ''
        coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
        self.error_out_writer.stderrorwrite('Niepotrzebne ForceClass dla drogi %s' % coords)
        return 'ForceClass'

    def sprawdz_czy_endlevel_wieksze_od_data(self, dane_do_zapisu):
        if 'EndLevel' not in dane_do_zapisu:
            return ''
        end_level = int(dane_do_zapisu['EndLevel'])
        if end_level == 0:
            return ''
        data_levels = set(int(a.split('_')[0].split('Data')[1]) for a in dane_do_zapisu if a.startswith('Data'))
        min_data = min(data_levels)
        # jesli max_data == 0, wtedy mamy data0 tylko. W takim przypadku nie sprawdzaj EndLevel
        kom_bledu = ''
        # EndLevel nie powinien byc rowny jakiemukolwiek DataX danym rekordzie, jesli jest to jest blad
        if end_level in data_levels:
            kom_bledu = 'EndLevel=%s dla Data%s' % (end_level, end_level)
        # jesli EndLevel jest mniejszy od najniższego DataX to jest blad
        elif end_level < min_data:
            kom_bledu = 'EndLevel=%s mniejsze niz Data%s' % (end_level, min_data)
        # EndLevel moze byc wiekszy tylko od min_data, nie może być większy od dwóch, bo wtedy nie wiadomo co generowac
        # na przykład mamy Data0, Data1 i Data3, a EndLevel=2, co by znaczylo ze zarowno Data0 jak i Data1 powinny byc
        # podniesione do poziomu 2
        elif len([a for a in data_levels if a < end_level]) > 1:
            kom_bledu = 'EndLevel=%s dla wielokrotnego ' % end_level
            for tmp_ in (a for a in data_levels if a < end_level):
                kom_bledu += 'Data%s, ' % tmp_
            kom_bledu = kom_bledu.rstrip(', ')
        if kom_bledu:
            coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
            wspolrzedne = ' %s' % coords
            self.error_out_writer.stderrorwrite(kom_bledu + wspolrzedne)
            return 'error'
        return ''

    def sprawdz_poprawnosc_klucza(self, dane_do_zapisu):
        for klucz in dane_do_zapisu:
            if klucz not in self.dozwolone_klucze:
                klucz_z_numerem_znaleziony = False
                for klucz_z_numerem in self.dozwolone_klucze_z_numerem:
                    if klucz.startswith(klucz_z_numerem):
                        klucz_z_numerem_znaleziony = True
                        break
                if not klucz_z_numerem_znaleziony:
                    coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                    if klucz in self.dozwolone_klucze_przestarzale:
                        self.error_out_writer.stderrorwrite('Nieużywany klucz %s %s, można usunąć.' % (klucz, coords))
                    else:
                        self.error_out_writer.stderrorwrite('Nieznany klucz: %s %s' % (klucz, coords))
        return ''

    def sprawdz_poprawnosc_wartosci_klucza(self, dane_do_zapisu, klucze_do_sprawdzenia=None):
        if klucze_do_sprawdzenia is None:
            klucze = self.dozwolone_wart_kluczy_funkcje.keys()
        else:
            klucze = klucze_do_sprawdzenia
        coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
        for klucz in klucze:
            if klucz in dane_do_zapisu:
                czy_ok, info_blad = self.dozwolone_wart_kluczy_funkcje[klucz](dane_do_zapisu[klucz])
                if not czy_ok:
                    self.error_out_writer.stderrorwrite('Bledna wartosc dla %s: %s %s'
                                                        % (klucz, dane_do_zapisu[klucz], coords))
                    self.error_out_writer.stderrorwrite('Dozwolone wartosci: %s' % info_blad)
        return ''

    def dozwolona_wartosc_dla_ForceSpeed(self, wartosc):
        return wartosc in self.dozwolone_wartosci_dla_ForceSpeed, ", ".join(self.dozwolone_wartosci_dla_ForceSpeed)

    def dozwolona_wartosc_dla_ForceClass(self, wartosc):
        return wartosc in self.dozwolone_wartosci_dla_ForceClass, ", ".join(self.dozwolone_wartosci_dla_ForceClass)

    def dozwolona_wartosc_dla_EndLevel(self, wartosc):
        return wartosc in self.dozwolone_wartosci_dla_EndLevel, ", ".join(self.dozwolone_wartosci_dla_EndLevel)

    @staticmethod
    def dozwolona_wartosc_dla_SignAngle(wartosc):
        try:
            wartosc_int = int(wartosc)
        except ValueError:
            return False, 'dozwolone wartosci: -360 do 360'
        return -360 <= wartosc_int <= 360, 'dozwolone wartosci: -360 do 360'

    @staticmethod
    def dozwolona_wartosc_dla_SignPos(wartosc):
        if not (wartosc.startswith('(') and wartosc.endswith(')')):
            return False, '(XX.XXXXX,YY.YYYYY)'
        if ',' not in wartosc:
            return False, '(XX.XXXXX,YY.YYYYY)'
        try:
            for val in wartosc[1:-1].split(',', 1):
                float(val)
        except ValueError:
            return False, '(XX.XXXXX,YY.YYYYY)'
        return True, '(XX.XXXXX,YY.YYYYY)'

    def dozwolona_wartosc_dla_Sign(self, wartosc):
        return wartosc in self.dozwolone_wartosci_dla_sign, 'sprawdz na wiki: http://ump.fuw.edu.pl/wiki/Restrykcje'

    @staticmethod
    def dozwolona_wartosc_dla_MaxWeight(wartosc):
        try:
            maks_masa = float(wartosc)
        except ValueError:
            return False, 'dozwolone tylko liczby w zakresie 0-100'
        return 0 < maks_masa < 100, 'dozwolone tylko liczby w zakresie 0-100'

    def zwroc_wspolrzedne_do_szukania(self, dane_do_zapisu):
        if self.wspolrzedne_obiektu:
            return self.wspolrzedne_obiektu
        for tmpkey in dane_do_zapisu:
            if tmpkey.startswith('Data'):
                if '),(' in dane_do_zapisu[tmpkey]:
                    self.wspolrzedne_obiektu = dane_do_zapisu[tmpkey].split('),(', 1)[0] + ')'
                else:
                    self.wspolrzedne_obiektu = dane_do_zapisu[tmpkey]
                return self.wspolrzedne_obiektu
        return '()'

    def resetuj_wspolrzedne(self):
        self.wspolrzedne_obiektu = ''

    def sprawdz_label_dla_drogi_z_numerami(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] in ('[POLYGON]', '[POI]'):
            return ''
        for tmp_label in ('adrLabel', 'Label'):
            if tmp_label in dane_do_zapisu and dane_do_zapisu[tmp_label]:
                if dane_do_zapisu[tmp_label].startswith('~'):
                    if ' ' in dane_do_zapisu[tmp_label]:
                        dane_do_zapisu[tmp_label] = dane_do_zapisu[tmp_label].split(' ', 1)[-1].strip()
                    else:
                        continue
                if dane_do_zapisu[tmp_label].startswith('{'):
                    dane_do_zapisu[tmp_label] = dane_do_zapisu[tmp_label].split('}', 1)[-1].strip()
                if dane_do_zapisu[tmp_label]:
                    return ''
        if any(a.startswith('Numbers') for a in dane_do_zapisu):
            data = dane_do_zapisu[[a for a in dane_do_zapisu if a.startswith('Data')][0]][1:-1].split('),(')
            # teraz trzeba policzyc przy ktorych wezlach mamy problem
            no_wezlow = [int(dane_do_zapisu[a].split('=', 1)[-1].split(',', 1)[0]) for a in dane_do_zapisu
                         if a.startswith('Numbers')]
            self.error_out_writer.stderrorwrite('Numeracja drogi bez Label: %s' % ', '.join(data[a] for a in no_wezlow))
            return 'brak_label_przy_numeracji'
        return ''

    def sprawdz_join_zamiast_merge(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] == '[POLYLINE]' and dane_do_zapisu['Type'] in self.typy_data_0_only:
            data = [a for a in dane_do_zapisu if a.startswith('Data0')]
            if len(data) > 1:
                self.error_out_writer.stderrorwrite('Uzyte join zamiast merge dla drogi %s' % dane_do_zapisu[data[0]])
                return 'Data1'
        return ''

    def sprawdzData0Only(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] == '[POLYGON]':
            return ''
        data = [a for a in dane_do_zapisu if a.startswith('Data') and not a.startswith('Data0')]
        if not data:
            return ''
        if dane_do_zapisu['POIPOLY'] == '[POI]':
            self.error_out_writer.stderrorwrite('Data 1 albo wyzej dla POI %s' % dane_do_zapisu[data[0]])
            return 'Data1_POI'
        elif dane_do_zapisu['Type'] in self.typy_data_0_only:
            self.error_out_writer.stderrorwrite('Data 1 albo wyzej dla drogi/kolei %s' % dane_do_zapisu[data[0]])
            return 'Data1_POLY'
        else:
            return ''

    def sprawdz_label_dla_poi(self, dane_do_zapisu):
        if 0x2900 <= int(dane_do_zapisu['Type'], 16) <= 0x3008:
            if 'Label' not in dane_do_zapisu or ('Label' in dane_do_zapisu and not dane_do_zapisu['Label']):
                coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                self.error_out_writer.stderrorwrite(
                    '\nBrak Label dla punktu o wspolrzednych %s.\nWyszukiwanie nie będzie działać.' % coords)
                return 'brak_label'
            elif 'Miasto' not in dane_do_zapisu or ('Miasto' in dane_do_zapisu and not dane_do_zapisu['Miasto']):
                coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                self.error_out_writer.stderrorwrite(
                    '\nBrak Miasto dla punktu o wspolrzednych %s.\nWyszukiwanie nie będzie działać.' % coords)
                return 'brak_miasto'
            return ''
        elif dane_do_zapisu['Type'] in City.rozmiar2Type:
            if 'Label' not in dane_do_zapisu or ('Label' in dane_do_zapisu and not dane_do_zapisu['Label']):
                coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                self.error_out_writer.stderrorwrite(
                    '\nBrak nazwy Miasta dla punktu o wspolrzednych %s.' % coords)
                return 'brak_nazwy_miasta'
            return ''

    def sprawdz_label_dla_poly(self, dane_do_zapisu):
        if 'Label' not in dane_do_zapisu:
            return ''
        if 'Miasto' in dane_do_zapisu:
            return ''
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
                    coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                    self.error_out_writer.stderrorwrite(('Brak Miasto= dla {!s} {!s}'.format(dane_do_zapisu['Label'],
                                                                                             coords)))
                    return 'miasto potrzebne'
            # w przypadku gdyby nazwa zaczynala sie mala litera
            else:
                coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                self.error_out_writer.stderrorwrite(('Brak Miasto= dla {!s} {!s}'.format(dane_do_zapisu['Label'],
                                                                                         coords)))
                return 'miasto potrzebne'
        else:
            return ''

    def sprawdz_krotkie_remonty(self, dane_do_zapisu):
        if dane_do_zapisu['POIPOLY'] != '[POLYLINE]':
            return ''
        if 'Komentarz' not in dane_do_zapisu:
            return ''
        for komentarz in dane_do_zapisu['Komentarz']:
            komentarz = komentarz.strip()
            if komentarz.startswith(';Termin:') or komentarz.startswith(';termin:') or \
                    komentarz.startswith(';;Termin:') or komentarz.startswith(';;termin:'):
                if komentarz.count(':') < 2:
                    self.error_out_writer.stderrorwrite('Nieppprawny format krotkiego terminu: %s %s.'
                                                        % (komentarz,
                                                           self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)))
                    self.error_out_writer.stderrorwrite('Poprawny format: Termin:data:komentarz')
                    return 'blad_krotkich_remontow'
                _, data_string, opis = komentarz.split(':', 2)
                data_string = data_string.strip()
                if len(data_string) != 8:
                    self.error_out_writer.stderrorwrite('Niepoprawny format daty dla krotkiego terminu: %s %s.'
                                                        % (data_string,
                                                           self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)))
                    self.error_out_writer.stderrorwrite('Poprawny format daty: YYYYMMDD.')
                    return 'blad_krotkich_remontow'
                try:
                    date_time_obj = datetime.strptime(data_string, '%Y%m%d')
                except ValueError:
                    self.error_out_writer.stderrorwrite('Niepoprawna data dla krotkiego remontu: %s %s'
                                                        % (data_string,
                                                           self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)))
                    return 'blad_krotkich_remontow'
                if (date_time_obj - datetime.today()).days < 0:
                    self.error_out_writer.stderrorwrite('Krotki remont zakonczony: %s %s' % (data_string,
                                                        self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)))
                    return 'blad_krotkich_remontow'
        return ''

    @staticmethod
    def clockwisecheck(wspolrzedne):
        """
        Sprawdzanie w ktora strone kreci sie wielokat
        :param wspolrzedne: wspolrzedne wielokata (ronda) w postaci stringa (XX.XXXXX,YY.YYYYY),(XX.XXXXX,YY.YYYYY)
        :return: -1: wielokat (rondo) kreci sie w lewo, 1: wielokat (rondo) kreci sie w prawo, 0: nie wiadomo
        """
        pole_wielokata = 0
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
            pole_wielokata = pole_wielokata + (x1 * y2 - x2 * y1)
        if pole_wielokata > 0:
            return 1
        elif pole_wielokata < 0:
            return -1
        elif pole_wielokata == 0:
            return 0

    def sprawdzKierunekRonda(self, dane_do_zapisu):
        Data = dane_do_zapisu[[b for b in dane_do_zapisu if b.startswith('Data')][0]]
        coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
        if 'DirIndicator' not in dane_do_zapisu:
            self.error_out_writer.stderrorwrite(('Brak ustawionej kierunkowosci dla ronda {!s}'.format(coords)))
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
            self.error_out_writer.stderrorwrite(
                'Nie moge okreslic kierunku ronda {!s}.\nZbyt malo punktow.'.format(coords))
            return 'NIE_WIEM'
        else:
            self.error_out_writer.stderrorwrite('Rondo z odwrotnym kierunkiem {!s}'.format(coords))
            return 'ODWROTNE'

    def sprawdz_czy_tylko_znaki_cp1250(self, dane_do_zapisu):
        for klucz in ('adrLabel', 'Label', 'Label2', 'Label3', 'Miasto', 'StreetName', 'Komentarz'):
            if klucz in dane_do_zapisu:
                if klucz == 'Komentarz':
                    literki_set = set()
                    for kom in dane_do_zapisu['Komentarz']:
                        literki_set = literki_set.union(set(kom))
                else:
                    literki_set = set(dane_do_zapisu[klucz])
                if not literki_set.issubset(self.dozwolone_znaki_cp1250):
                    nl = ''.join(literki_set.difference(self.dozwolone_znaki_cp1250))
                    coords = self.zwroc_wspolrzedne_do_szukania(dane_do_zapisu)
                    self.error_out_writer.stderrorwrite('Literka spoza zakresu cp1250: %s %s' % (nl, coords))
                    return 'cp1250_nie_ok'
        return 'cp1250_ok'


    def testy_poprawnosci_danych_poi(self, dane_do_zapisu):
        self.sprawdzData0Only(dane_do_zapisu)
        self.sprawdz_label_dla_poi(dane_do_zapisu)
        self.sprawdz_poprawnosc_klucza(dane_do_zapisu)
        self.sprawdz_poprawnosc_wartosci_klucza(dane_do_zapisu, klucze_do_sprawdzenia=('EndLevel',))
        self.sprawdz_czy_endlevel_wieksze_od_data(dane_do_zapisu)
        # self.sprawdz_czy_tylko_znaki_cp1250(dane_do_zapisu)
        self.resetuj_wspolrzedne()

    def testy_poprawnosci_danych_txt(self, dane_do_zapisu):
        wyniki_testow = list()
        wyniki_testow.append(self.testuj_kierunkowosc_ronda(dane_do_zapisu))
        wyniki_testow.append(self.sprawdzData0Only(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_join_zamiast_merge(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_label_dla_poly(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_label_dla_drogi_z_numerami(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_poprawnosc_klucza(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_czy_endlevel_wieksze_od_data(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_poprawnosc_wartosci_klucza(dane_do_zapisu, klucze_do_sprawdzenia=None))
        wyniki_testow.append(self.sprawdz_czy_forceclass_zabronione(dane_do_zapisu))
        wyniki_testow.append(self.sprawdz_krotkie_remonty(dane_do_zapisu))
        # wyniki_testow.append(self.sprawdz_czy_tylko_znaki_cp1250(dane_do_zapisu))
        self.resetuj_wspolrzedne()
        if wyniki_testow:
            return ','.join(a for a in wyniki_testow if a)
        return ''

    def testuj_kierunkowosc_ronda(self, dane_do_zapisu):
        # poniewaz testy leca dla wszystkich polyline, nieronda trzeba od razu odrzucic
        if dane_do_zapisu['Type'] == '0xc' and dane_do_zapisu['POIPOLY'] == '[POLYLINE]':
            return self.sprawdzKierunekRonda(dane_do_zapisu)
        else:
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
        :param plik_z_granicami_do_testow: plik z granicami, uzywany do testow jednostkowych
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

    @staticmethod
    def zamien_komentarz_na_malpki(granice_czesciowe_diff):
        index_ostatniego_elem_listy = len(granice_czesciowe_diff) - 1
        for num, linijka in enumerate(granice_czesciowe_diff):
            if linijka.startswith(' ; granica routingu'):
                if num < index_ostatniego_elem_listy:
                    if not granice_czesciowe_diff[num + 1].startswith('@@'):
                        granice_czesciowe_diff[num] = '@@\n'
        return granice_czesciowe_diff

    @staticmethod
    def podziel_diff_granic_czesciowych_na_rekordy(granice_czesciowe_diff):
        """
        Funkcja dzieli diff granic czesciowych na pojedyncze rekordy
        :param granice_czesciowe_diff: plik diff granic czesciowych
        :return: lista list zawierajaca rekordy granic czesciowych
        """
        granice_czesciowe_rekordy = []
        rekord_granic_czesciowych = []
        # bo numerowanie list zaczyna sie od zera, dlatego zakladamy ze dl_diff jest o 1 mnijesza, latwiej bedzie
        # pozniej porownywac
        granice_czesciowe_diff = PaczerGranicCzesciowych.zamien_komentarz_na_malpki(granice_czesciowe_diff)
        for a in granice_czesciowe_diff:
            if a.startswith('+++') or a.startswith('---'):
                pass
            # jesli mamy @@ oznacza to ze zaczyna sie nowy oddzielny rekord
            elif a.startswith('@@'):
                # jesli sa juz jakies dane w rekordzie granic czesciowych dolacz go to granicy_czesciowe i
                # zacznij od nowa, przypisujac mu wartosc z @@
                if rekord_granic_czesciowych:
                    granice_czesciowe_rekordy.append(rekord_granic_czesciowych)
                rekord_granic_czesciowych = [a]
            else:
                rekord_granic_czesciowych.append(a)
        granice_czesciowe_rekordy.append(rekord_granic_czesciowych)
        return granice_czesciowe_rekordy

    def konwertujLatke(self, granice_czesciowe_diff):
        """
        konwersja latki ktora jest stworzona dla granicy czesciowej na latki stworzona dla pliku granice z narzedzi.
        :param granice_czesciowe_diff:
        :return: list() nowy diff w przypadku sukcesu, pusta liste w przypadku porazki
        """
        for pojedyncza_granica in self.podziel_diff_granic_czesciowych_na_rekordy(granice_czesciowe_diff):
            zamien_co = []
            zamien_co_kontekst = []
            zamien_na_co = []
            zamien_na_co_kontekst = []
            for linijka_granicy in pojedyncza_granica:
                # @ jest czescia latki, wiec to nalezy zignorowac
                if linijka_granicy.startswith('@'):
                    pass
                # od srednika zaczyna sie komentarz, komentarz ktory sie lapie to niestety nie ten z poczatku ale ten
                # z konca rekordu. Trzeba to zignorowac, ale z drugiej strony trzeba miec pewnosc ze wystepuje on na
                # koncu rekordu. Dlatego mamy a[-1] == b, w srodku rekordu moze byc i nie stanowi to zadnego problemu
                elif linijka_granicy.startswith(' ;') and pojedyncza_granica[-1] == linijka_granicy:
                    pass
                elif linijka_granicy.startswith(' '):
                    linia_tmp = linijka_granicy.replace(' ', '', 1)
                    zamien_co.append(linia_tmp)
                    zamien_co_kontekst.append('kontekst')
                    zamien_na_co.append(linia_tmp)
                    zamien_na_co_kontekst.append('kontekst')
                elif linijka_granicy.startswith('-'):
                    zamien_co.append(linijka_granicy.replace('-', '', 1))
                    zamien_co_kontekst.append('-')
                elif linijka_granicy.startswith('+'):
                    zamien_na_co.append(linijka_granicy.replace('+', '', 1))
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
            for b in zamien_co:
                if b.find('Data') >= 0:
                    DataX = b
                    DataX_index = zamien_co.index(DataX)
                    break
            if DataX_index == -1:
                return []
            przesuniecie = self.granice_txt.index(DataX) - DataX_index
            for b in range(len(zamien_co)):
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
        if isinstance(plikmp, list):
            self.OutputFile = plikmp[0]
            self.InputFile = plikmp[0]
        else:
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
        self.mkgmap_jar_path = 'c:\\ump\\mkgmap-r4905\\mkgmap.jar'
        self.wczytajKonfiguracje()

    def ustaw_katalog_home(self, katalog_home):
        self.KatalogzUMP = katalog_home
        self.uaktualnij_zalezne_home()

    def uaktualnij_zalezne_home(self):
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
                    self.uaktualnij_zalezne_home()
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
                if 'MKGMAPJARPATH' in konf:
                    self.mkgmap_jar_path = konf['MKGMAPJARPATH']
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
                    self.uaktualnij_zalezne_home()
                else:
                    print('Nie moge zgadnac konfiguracji', file=sys.stderr)


class tabelaKonwersjiTypow(object):
    def __init__(self, Zmienne, stderr_stdout_writer, wlasny_alias2type=None):
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
        self.wlasny_alias2type = {}
        if wlasny_alias2type is not None:
            self.wlasny_alias2type = wlasny_alias2type

    @staticmethod
    def create_type2Alias():
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
            '0x1805': ["signstat"],
            '0x1806': ["stawa_r"],
            '0x1807': ["stawa_by", "stawa_pn"],
            '0x1808': ["prawa_b"],
            '0x1809': ["lewa_b"],
            '0x180a': ["stawa_brb", "stawa_nieb"],
            '0x180b': ["boja"],
            '0x180d': ["w_prawo"],
            '0x180c': ["kard_n"],
            '0x1905': ["tablica"],
            '0x1906': ["stawa_g"],
            '0x1907': ["stawa_yb", "stawa_pd"],
            '0x1908': ["stawa_rgr"],
            '0x1909': ["stawa_grg"],
            '0x190a': ["stawa_rwr"],
            '0x190b': ["dalba"],
            '0x190c': ["kard_s"],
            '0x190d': ["w_lewo"],
            '0x1a06': ["stawa_y"],
            '0x1a07': ["stawa_byb", "stawa_ws"],
            '0x1a08': ["stawa_rw"],
            '0x1a09': ["stawa_gw"],
            '0x1a0a': ["stawa_bw"],
            '0x1a0c': ["kard_e"],
            '0x1a0d': ["w_lewo_b"],
            '0x1b06': ["stawa_w"],
            '0x1b07': ["stawa_yby", "stawa_za"],
            '0x1b08': ["stawa_wr"],
            '0x1b09': ["stawa_wg"],
            '0x1b0a': ["stawa_wb"],
            '0x1b0b': ["stawa_b"],
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
            '0x2f11': ["fabryka"],
            '0x2f12': ["wifi", "hotspot"],
            '0x2f13': ["serwis", "repair", "naprawa"],
            '0x2f14': ["pralnia", "social"],
            '0x2f15': ["budynek", "building"],
            '0x2f16': ["truck_stop"],
            '0x2f17': ["turystyka"],  # ","biuro","turystyczne,","transit_services
            '0x2f18': ["biletomat"],
            '0x2f1b': ["business", "firma"],
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

    @staticmethod
    def create_name2Alias():
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
            'Rossmann': 'SPECIAL',
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
        if Type not in self.type2Alias:
            return '', Type
        if Label in self.name2Alias:
            return self.name2Alias[Label], '0x0'
        if len(set(a.lower() for a in self.type2Alias[Type])) == 1:
            return self.type2Alias[Type][-1].upper(), '0x0'
        else:
            pasujace_typy = [a for a in Label.strip().split(' ') if a.lower() in self.type2Alias[Type]]
            if pasujace_typy:
                if len(pasujace_typy) > 1:
                    self.stderr_stdout_writer.stderrorwrite('Nie moge jednoznacznie dopasowac Type po Label.'
                                                            '\nUzywam pierwszej wartosci z listy: %s'
                                                            % pasujace_typy[0])
                return '', pasujace_typy[0].upper()
            self.stderr_stdout_writer.stderrorwrite('Nie moge jednoznacznie dopasowac Type po Label.'
                                                    '\nUzywam pierwszej wartosci z listy: %s'
                                                    % self.type2Alias[Type][0])
            return '', self.type2Alias[Type][0].upper()

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
        plik_pnt2poi = os.path.join('narzedzia', 'pnt2poi.txt')
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
            for nr_linii, a in enumerate(zawartosc_pliku_pnt2poi):
                a = a.strip()
                # po strip powstaja nieraz puste linie wiec takich nie ma co przeszukiwac stad ten if
                if a:
                    if a.startswith('[DEF-POI]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii))
                        sekcja = '[DEF-POI]'
                    elif a.startswith('[DEF-LINE]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii))
                        sekcja = '[DEF-LINE]'
                    elif a.startswith('[DEF-REVPOI]'):
                        if sekcja:
                            self.stderr_stdout_writer.stderrorwrite('Niepoprawne zakonczenie sekcji w pliku ' +
                                                                    plik_pnt2poi)
                            self.stderr_stdout_writer.stderrorwrite('brak [END] w linii %s' % str(nr_linii))
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
                                alias, type_ = a.split('=')
                                type_ = type_.split('#')[0].strip()
                                alias = alias.strip()
                                if alias in self.alias2TypeFromFile:
                                    self.stderr_stdout_writer.stderrorwrite('Uwaga! Podwojna definicja aliasu %s w pliku ' +
                                    plik_pnt2poi + '.' % alias)
                                self.alias2TypeFromFile[alias] = type_
            # print(self.alias2TypeFromFile)
            return 0

    def zwroc_type_prefix_suffix_dla_aliasu(self, alias):
        if alias in self.wlasny_alias2type:
            return self.wlasny_alias2type[alias]['Type'], self.wlasny_alias2type[alias]['Prefix'], \
                   self.wlasny_alias2type[alias]['Suffix']
        elif alias in self.alias2Type:
            return self.alias2Type[alias], '', ''
        elif alias.startswith('0x'):
            return alias, '', ''
        else:
            return '0x0', '', ''


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

    @staticmethod
    def point_inside_polygon(x, y, polyx, polyy):
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


class AutoPlikDlaPoi(object):
    def __init__(self):
        self.obszar_typ_plik = defaultdict(lambda: defaultdict(lambda: ''))
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
        """
        podczas demontazu tworzymy ranking plikow dla danego Typu, tak aby pozniej wykorzystać najbardziej popularny
        plik dla danego typu, zamiast pierwszy jako zostal znaleziony jak bylo we wczesnijeszej wersji
        :param dane_do_zapisu:
        :return:
        """
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
 

class AutoPlikDlaPolylinePolygone(object):
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

    def wypelnij_obszar_plik_wspolrzedne(self, pliki):
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

    def zwroc_plik_dla_poly(self, typobiektu, poly_type, obszar, wspolrzedne):
        try:
            if typobiektu == '[POLYGON]':
                auto_obszary_typy = self.TypPolygon2Plik[poly_type]
            else:
                auto_obszary_typy = self.TypPolyline2Plik[poly_type]
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

    def zwroc_indeks_miasta(self, nazwa_miasta):
        if nazwa_miasta not in self.globalCityIdx:
            self.actCityIdx += 1
            self.globalCityIdx[nazwa_miasta] = self.actCityIdx
            self.sekcja_cityidx.append('City' + str(self.actCityIdx) + '=' + nazwa_miasta)
            self.sekcja_cityidx.append('RegionIdx' + str(self.actCityIdx) + '=1')
        return self.globalCityIdx[nazwa_miasta]


class PlikMP1(object):
    """przechowuje zawartosc pliku mp do zapisu"""
    def __init__(self, Zmienne, args, tabela_konwersji_typow, stderr_stdout_writer, Montuj=1, naglowek_mapy=''):

        # zawartosc nowo tworzonego pliku mp, zawartosc z plikow skladowych do montazu
        self.zawartosc = []
        self.plik_nowosci_txt = '_nowosci.txt'
        self.plik_nowosci_pnt = '_nowosci.pnt'
        self.Zmienne = Zmienne
        self.args = args
        self.tabela_konwersji_typow = tabela_konwersji_typow
        self.domyslneMiasta2 = {}
        self.cityIdxMiasto = []
        self.errOutWriter = stderr_stdout_writer
        self.sciezka_zwalidowana = set()
        self.auto_pliki_dla_poi = AutoPlikDlaPoi()
        self.dozwolone_obszary_dla_plikow = None

        # przechowywanie hashy dla danego pliku w postaci slownika: nazwapliku:wartosc hash
        self.plikHash = {}
        if Montuj:
            self.plikDokladnosc = {}
            if not naglowek_mapy:
                plik_naglowka_nazwa = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'header.txt')
                try:
                    with open(plik_naglowka_nazwa, encoding=Zmienne.Kodowanie, errors=Zmienne.ReadErrors) as plik_naglowka:
                        self.naglowek = plik_naglowka.read()
                # self.zawartosc.append(self.naglowek.rstrip()+'\n')
                except FileNotFoundError:
                    self.stderrorwrite('nie moge zaladowac pliku naglowka: ' + plik_naglowka_nazwa)
                else:
                    self.stdoutwrite('Wczytalem naglowek mapy z pliku :' + plik_naglowka_nazwa)
            else:
                self.naglowek = naglowek_mapy
        else:
            self.plikDokladnosc = {self.plik_nowosci_txt: '5', self.plik_nowosci_pnt: '5'}
            self.plikizMp = {self.plik_nowosci_txt: [], self.plik_nowosci_pnt: []}
            self.osobne_pliki_dla_miast = list()

            # Zmienna z obszarami ktore sa zamontowane, wykorzystywana do autorozkladu linii i polygonow do
            # odpowiednich plikow, na poczatku ustawione jako None,
            # zmienia sie po pierwszym wywolaniu zapiszTXT poprzez funkcje ustawObszary
            self.obszary = None
            self.autoobszary = AutoPlikDlaPolylinePolygone(self.Zmienne, self.plik_nowosci_txt)

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
        dozw_obsz_dla_UMP = set()
        dozw_obsz_dla_granic = set()
        for nazwa_pliku in (a for a in self.plikizMp if a not in (self.plik_nowosci_txt, self.plik_nowosci_pnt)):
            if nazwa_pliku.startswith('UMP-'):
                dozw_obsz_dla_UMP.add(os.path.split(os.path.split(nazwa_pliku)[0])[0])
            else:
                dozw_obsz_dla_granic.add(nazwa_pliku)
        self.dozwolone_obszary_dla_plikow = tuple(sorted(dozw_obsz_dla_UMP) + sorted(dozw_obsz_dla_granic))
        print(self.dozwolone_obszary_dla_plikow)

    def czy_nazwa_obszar_dla_pliku_jest_dozwolony(self, nazwa_pliku):
        if nazwa_pliku.startswith('UMP'):
            return any(nazwa_pliku.startswith(a) for a in self.dozwolone_obszary_dla_plikow)
        return nazwa_pliku in self.dozwolone_obszary_dla_plikow

    def zwaliduj_sciezki_do_plikow(self):
        if self.dozwolone_obszary_dla_plikow is None:
            self.zbuduj_dozwolone_obszary_dla_plikow()
        for plik in self.plikizMp:
            if not self.sprawdz_poprawnosc_sciezki(plik):
                self.sciezka_zwalidowana.add(plik)

    def cyfry_hash(self, linia_z_cyfram_i_hashem, zaokraglij):
        """
        Wczytuje dokladnosc danego pliku oraz hash tego pliku zapisany w pliku mp. Nastepnie otwiera plik z dysku.
        Jesli oba hashe sa sobie rowne wtedy zwraca 0, w przeciwnym wypadku 1. Gdy nie ma hasha - jest pusty zwraca 2
        """
        plik, dokladnosc, wartosc_hash, Miasto = linia_z_cyfram_i_hashem.strip().split(';', 4)
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
            if self.args.usun_puste_numery:
                dane_do_zapisu = self.usun_pusta_numeracje(dane_do_zapisu)
            self.zapiszTXT(dane_do_zapisu)
        elif dane_do_zapisu['POIPOLY'] == '[POI]':
            if dane_do_zapisu['Type'] in City.rozmiar2Type:
                dane_do_zapisu = self.koreguj_wpisy_dla_miast(dane_do_zapisu)
            dane_do_zapisu = self.modyfikuj_plik_dla_poi(dane_do_zapisu)
            dane_do_zapisu = self.zaokraglij_klucze_ze_wspolrzednymi(dane_do_zapisu)
            dane_do_zapisu = self.przywroc_data0_i_entrypointy_z_origdata0(dane_do_zapisu)
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
                            daneDoZapisu['Typ'] = zgdanietyTypPoAliasie
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
            if klucz_z_dane_do_zapisu in ('Komentarz', 'Dziwne'):
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
                # self.plikizMp[daneDoZapisu['Plik']].append(klucz_z_dane_do_zapisu.split('_')[0] + '=' +
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

    @staticmethod
    def stworz_ulice_nr_tel_url(daneDoZapisu):
        for klucz in ('StreetDesc', 'HouseNumber', 'Phone', 'MiscInfo'):
            if klucz in daneDoZapisu:
                daneDoZapisu[klucz] = daneDoZapisu[klucz].replace(',', '°')
        if 'MiscInfo' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            if 'HouseNumber' not in daneDoZapisu:
                daneDoZapisu['HouseNumber'] = ''
            if 'Phone' not in daneDoZapisu:
                daneDoZapisu['Phone'] = ''
            return daneDoZapisu['StreetDesc'] + ';' + daneDoZapisu['HouseNumber'] + ';' + daneDoZapisu['Phone'] + ';' \
                   + daneDoZapisu['MiscInfo']
        elif 'Phone' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            if 'HouseNumber' not in daneDoZapisu:
                daneDoZapisu['HouseNumber'] = ''
            return daneDoZapisu['StreetDesc'] + ';' + daneDoZapisu['HouseNumber'] + ';' + daneDoZapisu['Phone']
        elif 'HouseNumber' in daneDoZapisu:
            if 'StreetDesc' not in daneDoZapisu:
                daneDoZapisu['StreetDesc'] = ''
            return daneDoZapisu['StreetDesc'] + ';' + daneDoZapisu['HouseNumber']
        elif 'StreetDesc' in daneDoZapisu:
            return daneDoZapisu['StreetDesc']
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
                    if self.cyfry_hash(dokladnosc_i_hash_pliku, args.X):
                        if args.demonthash:
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
                if bbb_len in (4, 7, 8):
                    if bbb_len == 4:
                        pnt_typ = 'MIASTO'
                    else:
                        pnt_typ = bbb[6].strip()
                    plik_dla_typu_w_obszarze = self.auto_pliki_dla_poi.zwroc_plik_dla_typu(UMP_obszar, pnt_typ)
                    if UMP_obszar != 'None' and plik_dla_typu_w_obszarze:
                        self.stdoutwrite('%s --> %s' % (punkt_z_nowosci_pnt.strip(), plik_dla_typu_w_obszarze))
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
        ostatni_id_dla_data = defaultdict(lambda: -1)
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
        for klucz in (a for a in dane_do_zapisu if a.startswith('Data') or a.startswith('EntryPoint') or
                                                   a.startswith('OrigData0')):
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
        if 'Komentarz' not in dane_do_zapisu:
            return dane_do_zapisu
        tmp_kom = ''.join(dane_do_zapisu['Komentarz'])
        if 'otwarte' not in tmp_kom and 'entrypoint' not in tmp_kom.lower():
            return dane_do_zapisu
        entry_point_defs = [ep for ep in (';;EntryPoint:', ';;EntryPoint=') if ep in tmp_kom]
        otwarte_defs = [otw for otw in (';otwarte:', ';Otwarte:', ';otwarte=', ';Otwarte=') if otw in tmp_kom]
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
                # linia musi się zaczynać dokładnie jak dany element, czyli z jednym średnikiem albo dwoma
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
        for key in ('EntryPoint', 'Otwarte'):
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

    @staticmethod
    def koreguj_wpisy_dla_miast(dane_do_zapisu):
        # Miasta < od 1000 dostajš typ 0xe00
        if dane_do_zapisu['Type'] in ('0xf00', '0x1000', '0x1100'):
            dane_do_zapisu['Type'] = '0xe00'
        # miasta > od 1000000 dostaja typ 0x0400
        elif dane_do_zapisu['Type'] in ('0x300', '0x200', '0x100'):
            dane_do_zapisu['Type'] = '0x400'
        if 'Rozmiar' not in dane_do_zapisu:
            dane_do_zapisu['Rozmiar'] = City.type2Rozmiar[dane_do_zapisu['Type']]
        return dane_do_zapisu

    @staticmethod
    def zamien_przecinki_na_stopnie(dane_do_zapisu):
        dane_do_zapisu['Label'] = dane_do_zapisu['Label'].replace(',', '°')
        return dane_do_zapisu

    @staticmethod
    def usun_pusta_numeracje(dane_do_zapisu):
        wszystkie_numeracje = [a for a in dane_do_zapisu if a.startswith('Numbers')]
        numeracja_do_usuniecia = [a for a in wszystkie_numeracje if 'N,-1,-1,N,-1,-1' in dane_do_zapisu[a]]
        if numeracja_do_usuniecia and len(numeracja_do_usuniecia) == len(wszystkie_numeracje):
            for numeracja in wszystkie_numeracje:
                del(dane_do_zapisu[numeracja])
        return dane_do_zapisu

    @staticmethod
    def przywroc_data0_i_entrypointy_z_origdata0(dane_do_zapisu):
        Data0 = list(a for a in dane_do_zapisu if a.startswith('Data0'))[0]
        if 'OrigData0' in dane_do_zapisu and Data0:
            if dane_do_zapisu['OrigData0'] != dane_do_zapisu[Data0]:
                dane_do_zapisu['EntryPoint'] = dane_do_zapisu[Data0]
                dane_do_zapisu[Data0] = dane_do_zapisu['OrigData0']
            del dane_do_zapisu['OrigData0']
        return dane_do_zapisu


class PlikiDoMontowania(object):
    def __init__(self, zmienne, args, stderr_stdout_writer):
        if not hasattr(args, 'montuj_wedlug_klas'):
            args.montuj_wedlug_klas = 0
        obszary = args.obszary
        self.errOutWriter = stderr_stdout_writer
        self.zmienne = zmienne
        self.Obszary = obszary
        self.Pliki = list()
        if not args.trybosmand:
            self.Pliki += ['narzedzia' + os.sep + 'granice.txt']
        for aaa in obszary:
            if os.path.isdir(os.path.join(self.zmienne.KatalogzUMP, aaa, 'src')):
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.zmienne.KatalogzUMP, aaa, 'src/*.txt'))]
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.zmienne.KatalogzUMP, aaa, 'src/*.pnt'))]
                self.Pliki += [os.path.join(aaa, 'src', os.path.split(a)[1])
                               for a in glob.glob(os.path.join(self.zmienne.KatalogzUMP, aaa, 'src/*.adr'))]
            else:
                self.errOutWriter.stderrorwrite('Problem z dostępem do %s.' %
                                                os.path.join(self.zmienne.KatalogzUMP, aaa, 'src'))
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
            if filtry.no_osm:
                self.Pliki = [f for f in self.Pliki if f.find('osm.woda.txt') < 0]
        return

    def ogranicz_granice_lub_obszary(self, plik_do_ograniczenia):
        with open(os.path.join(os.path.join(self.zmienne.KatalogzUMP, 'narzedzia'), plik_do_ograniczenia),
                  encoding=self.zmienne.Kodowanie) as plik_do_ogr:
            zaw_pliku_do_ogr = plik_do_ogr.read().split('[END]\n')
        tylko_wybrany_obszar = []
        for a in self.Obszary:
            for b in tuple(zaw_pliku_do_ogr):
                if b.find(a.split('-')[-1]) > 0:
                    tylko_wybrany_obszar.append(b.strip() + '\n[END]\n\n')
                    zaw_pliku_do_ogr.remove(b)

        # poniewaz pierwszy element moze zawierac \n na poczatku, to go usuwamy
        # dodatkowo poniewaz dla niektorych obszarow moze nie byc granic, wtedy musimy obsluzyc taka sytuacje
        # dlatego obsluga wyjatku dla takiego przypadku
        try:
            tylko_wybrany_obszar[0] = tylko_wybrany_obszar[0].lstrip()
        except IndexError:
            self.errOutWriter.stderrorwrite('Nie znalazlem zadnych granic dla wybranego obszaru.')
        return tylko_wybrany_obszar

    def zwroc_granice_czesciowe(self):
        return self.ogranicz_granice_lub_obszary('granice.txt')

    def zwroc_obszary_txt(self):
        return self.ogranicz_granice_lub_obszary('obszary.txt')

    def zamien_granice_na_granice_czesciowe(self):
        gr_czesciowe = tempfile.NamedTemporaryFile(mode='w', encoding=self.zmienne.Kodowanie,
                                                   dir=self.zmienne.KatalogRoboczy, delete=False,
                                                   suffix='_granice-czesciowe.txt')
        for a in self.zwroc_granice_czesciowe():
            gr_czesciowe.write(a)
        gr_czesciowe.close()
        self.Pliki[0] = os.path.join(self.zmienne.KatalogRoboczy, gr_czesciowe.name)

    def usun_plik_z_granicami(self):
        if 'granice' in self.Pliki[0]:
            self.Pliki = self.Pliki[1:]


class ObiektNaMapie(object):
    """
    Ogolna klasa dla wszystkich obiektow na mapie:
    dla poi, miast, adresow, polyline, polygone
    """

    def __init__(self, Plik, IndeksyMiast, tab_konw_typow, args, stderr_stdout_writer, rekordy_max_min=(0, 0)):
        self.Komentarz = []
        self.DataX = []
        self.PoiPolyPoly = ''
        self.Plik = Plik
        self.CityIdx = -1
        self.Dane1 = []
        self.tab_konw_typow = tab_konw_typow
        self.args = args
        self.czyDodacCityIdx = args.cityidx
        self.errOutWriter = stderr_stdout_writer
        # indeksy miast
        self.IndeksyMiast = IndeksyMiast
        self.tryb_mkgmap = False
        if hasattr(args, 'tryb_mkgmap') and args.tryb_mkgmap:
            self.tryb_mkgmap = True
        self.dlugoscRekordowMax = rekordy_max_min[0]
        self.dlugoscRekordowMin = rekordy_max_min[1]

    def dodaj_komentarz_do_dane(self):
        if self.Komentarz:
            for komentarz in self.Komentarz:
                self.Dane1.append(komentarz.rstrip())

    def komentarz_na_entrypoint_i_otwarte(self):
        if not self.Komentarz:
            return 1
        entry_point_defs = [ep for ep in (';;EntryPoint:', ';;EntryPoint=') if
                            ep in self.Komentarz[0] and ';' + ep not in self.Komentarz[0]]
        otwarte_defs = [otw for otw in (';otwarte:', ';Otwarte:', ';otwarte=', ';Otwarte=')
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

    def stderrorwrite(self, komunikat):
        self.errOutWriter.stderrorwrite(komunikat)

    def stdoutwrite(self, komunikat):
        self.errOutWriter.stdoutwrite(komunikat)

    def wyczyscRekordy(self):
        self.Komentarz = []
        self.DataX = []
        self.PoiPolyPoly = ''
        self.CityIdx = -1
        self.Dane1 = []

    def ustaw_wartosc_zmiennej_cityidx(self, nazwa_miasta):
        self.CityIdx = self.IndeksyMiast.zwroc_indeks_miasta(nazwa_miasta)
        return 0

    def dodaj_indeksy_miast_do_obiektu(self, nazwa_miasta):
        if self.args.format_indeksow == 'cityidx':
            self.Dane1.append('CityIdx=' + str(self.CityIdx))
        else:
            self.Dane1.append('CityName=' + nazwa_miasta)
            if not self.tryb_mkgmap:
                for c_names in self.IndeksyMiast.sekcja_cityname:
                    self.Dane1.append(c_names)


class Poi(ObiektNaMapie):
    def __init__(self, Plik, IndeksyMiast, tab_konw_typow, args, stderr_stdout_writer, typ_obj='pnt'):
        ObiektNaMapie.__init__(self, Plik, IndeksyMiast, tab_konw_typow, args, stderr_stdout_writer,
                               rekordy_max_min=(8, 7))
        self.entry_otwarte_do_extras = False
        if hasattr(args, 'entry_otwarte_do_extras'):
            self.entry_otwarte_do_extras = args.entry_otwarte_do_extras
        self.sprytne_entrypoints = False
        if hasattr(args, 'sprytne_entrypoints'):
            self.sprytne_entrypoints = args.sprytne_entrypoints
        self.typ_obj = typ_obj

    def liniaZPliku2Dane(self, LiniaZPliku, orgLinia):
        self.pnt2Dane(LiniaZPliku, orgLinia)

    @staticmethod
    def czy_poi_moze_z_entrypoint(poi_type):
        try:
            type_val = int(poi_type, 16)
        except ValueError:
            return False
        return True if type_val > int('0x2700', 16) else False

    def dodaj_sprytne_entrypoints(self, poi_type):
        if not self.czy_poi_moze_z_entrypoint(poi_type):
            return
        entrypoint = ''
        entrypointpos = -1
        origdata = ''
        origdatapos = -1
        for no, linia in enumerate(self.Dane1):
            if linia.startswith('EntryPoint'):
                entrypoint = linia.split('=', 1)[-1]
                entrypointpos = no
            if linia.startswith('Data'):
                origdata = linia.split('=', 1)[-1]
                origdatapos = no
            if entrypoint and origdata:
                break
        # print(entrypoint, origdata)
        self.Dane1[origdatapos] = 'OrigData0=' + origdata
        if entrypointpos > -1:
            self.Dane1[entrypointpos] = 'Data0=' + entrypoint
        else:
            self.Dane1.append('Data0=' + origdata)

    def pnt2Dane(self, LiniaZPliku, orgLinia):
        """Funkcja konwertujaca linijke z pliku pnt na wewnetrzna reprezentacje danego poi"""
        self.dodaj_komentarz_do_dane()
        # 0 Dlugosc, 1 Szerokosc, 2 EndLevel, 3 Label, 4 UlNrTelUrl, 5 Miasto, 6 Typ, 7 KodPoczt
        self.PoiPolyPoly = '[POI]'
        self.Dane1.append(self.PoiPolyPoly)
        poi_type, label_prefix, label_suffix = self.tab_konw_typow.zwroc_type_prefix_suffix_dla_aliasu(LiniaZPliku[6])
        if self.typ_obj == 'pnt':
            if poi_type == '0x0':
                self.stderrorwrite('Nieznany typ %s w pliku %s' % (LiniaZPliku[6], self.Plik))
                self.stderrorwrite(repr(orgLinia))
            self.Dane1.append('Type=' + poi_type)
        else:
            if LiniaZPliku[6] == 'ADR' or LiniaZPliku[6] == 'HOUSENUMBER':
                self.Dane1.append('Type=' + poi_type)
            else:
                self.stderrorwrite('Niepoprawny typ dla punktu adresowego')
                self.stderrorwrite(','.join(LiniaZPliku))
                self.Dane1.append('Type=0x0')
        # Tworzymy Label=
        if LiniaZPliku[3]:
            self.Dane1.append('Label=' + label_prefix + LiniaZPliku[3].strip().replace('°', ',') + label_suffix)
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
        if self.entry_otwarte_do_extras:
            self.komentarz_na_entrypoint_i_otwarte()
        if self.sprytne_entrypoints:
            self.dodaj_sprytne_entrypoints(poi_type)
        self.Dane1.append('[END]\n')
        return

    @staticmethod
    def rozdzielUlNrTelUrl(UlNrTelUrl):
        """ulica, numer domu, numer telefonu oraz url sa podane w jednej linii.
            Funkcja ta rozdziela je na oddzielne pola
            :return Ulica, NumerDomu, Telefon, Url"""
        if not UlNrTelUrl:
            return '', '', '', ''
        return_val = ['', '', '', '']
        for licznik, aaa in enumerate(UlNrTelUrl.split(';', 3)):
            return_val[licznik] = aaa
        return return_val


class City(ObiektNaMapie):
    rozmiar2Type = ('0xe00', '0xd00', '0xc00', '0xb00', '0xa00', '0x900', '0x800', '0x700', '0x600', '0x500', '0x400')
    type2Rozmiar = {'0xe00': '0', '0xd00': '1', '0xc00': '2', '0xb00': '3', '0xa00': '4', '0x900': '5', '0x800': '6',
                    '0x700': '7', '0x600': '8', '0x500': '9', '0x400': '10'}
    typetoEndlevel = ('0', '1', '1', '2', '2', '3', '3', '3', '4', '4', '4')

    def __init__(self, Plik, IndeksyMiast, tab_konw_typow, args, stderr_stdout_writer):
        ObiektNaMapie.__init__(self, Plik, IndeksyMiast, tab_konw_typow, args, stderr_stdout_writer,
                               rekordy_max_min=(4, 4))

    def liniaZPliku2Dane(self, LiniaZPliku, orgLinia):
        self.city2Dane(LiniaZPliku)

    def city2Dane(self, LiniaZPliku):
        self.dodaj_komentarz_do_dane()
        self.PoiPolyPoly = '[POI]'
        self.Dane1.append(self.PoiPolyPoly)
        # Tworzymy Type=
        self.Dane1.append('Type=' + City.rozmiar2Type[int(LiniaZPliku[2].lstrip())])
        # Tworzymy Label=
        self.Dane1.append('Label=' + LiniaZPliku[3].strip().replace('°', ','))

        # dodajemy City=Y
        self.Dane1.append('City=Y')
        # Tworzymy EndLevel
        self.Dane1.append('EndLevel=' + City.typetoEndlevel[int(LiniaZPliku[2].lstrip())])
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
                    if klucz in ('Miasto', 'City'):
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
    def __init__(self, NazwaPliku, punktzTXT, stderr_stdout_writer):
        self.domyslneMiasto = ''
        self.Dokladnosc = ''
        self.NazwaPliku = os.path.basename(NazwaPliku)
        self.sciezkaNazwa = NazwaPliku
        self.errOutWriter = stderr_stdout_writer
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
                self.errOutWriter.stderrorwrite('Miasto=%s, plik=%s.' % (self.domyslneMiasto, self.NazwaPliku))
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
        Funkcja ustala dokladnosc pliku txt
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
            self.errOutWriter.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % self.NazwaPliku)
            return []
        for tmpaaa in self.txt2rekordy(zawartoscPlikuTXT):
            self.punktzTXT.rekord2Dane(tmpaaa, self.domyslneMiasto)
            if self.Dokladnosc not in ('5', '6') and self.punktzTXT.DataX:
                if self.ustalDokladnosc(self.punktzTXT.DataX):
                    self.errOutWriter.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % self.NazwaPliku)
            self.Dane1.extend(self.punktzTXT.Dane1)
            self.punktzTXT.wyczyscRekordy()
        return self.Dane1


class plikPNT(object):
    def __init__(self, NazwaPliku, stderr_stdout_writer, punktzPntAdrCiti):
        self.Dokladnosc = ''
        self.NazwaPliku = os.path.basename(NazwaPliku)
        self.sciezkaNazwa = NazwaPliku
        self.punktzPntAdrCiti = punktzPntAdrCiti
        self.errOutWriter = stderr_stdout_writer
        self.Dane1 = []

    @staticmethod
    def usunNaglowek(zawartoscPliku):
        """funkcja usuwa naglowek pliku pnt, i zwraca zawartosc pliku po usunieciu naglowka"""
        # pomijaj wszystko od poczatku do wystapienia pierwszego poprawnego wpisu w pliku: XX.XXXXY, YY.YYYYY
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
            return []

    def ustalDokladnosc(self, LiniaZPliku):
        """
                Funkcja ustala dokladnosc pliku txtupper
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
                    self.errOutWriter.stderrorwrite('Bledna linia w pliku %s' % self.NazwaPliku)
                    self.errOutWriter.stderrorwrite(repr(liniaPliku))

                else:
                    # punktzCity=City(pliki,tabKonw,args.cityidx)
                    if komentarz:
                        self.punktzPntAdrCiti.Komentarz.append(komentarz.strip())
                        komentarz = ''
                    self.punktzPntAdrCiti.liniaZPliku2Dane(rekordy, liniaPliku)
                    if not self.Dokladnosc or self.Dokladnosc == '0':
                        if self.ustalDokladnosc(liniaPliku):
                            self.errOutWriter.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s'
                                                            % self.NazwaPliku)
                    self.Dane1.extend(self.punktzPntAdrCiti.Dane1)
                    self.punktzPntAdrCiti.wyczyscRekordy()
        return self.Dane1


def cp1250_to_ascii(cp1250_string):
    zamien_co = 'óąćęłńśźżáäéëíöüčšâýăěňőřžçôúĺű'
    zamien_na_co = 'oacelnszzaaeeioucsayaenoržcoulu'
    tabela_konwersji = str.maketrans(zamien_co + str.upper(zamien_co) + 'ß',
                                      zamien_na_co + str.upper(zamien_na_co) + 's')
    ascii_string = cp1250_string.translate(tabela_konwersji)


def wczytaj_json_i_zwroc_wlasne_definicje_aliasow(plik_z_definicjami_typow, err_out_writer):
    """
    funkcja wczytuje zawartosc pliku. Rozdzielenie czytania pliku i jego procesingu ulatwia unitesty i istnieje tylko
    z tego powodu
    :param plik_z_definicjami_typow: string nazwa pliku z definicjami ze sciezka
    :param err_out_writer: referencja do klasy obslugujacej wypisywanie informacja na konsole albo do okienek
    :return: wczytany plik w postaci listy
    """
    # rozdzielamy czytanie pliku i przetwarzanie danych aby moc latwo zbudowac unitesty do tego
    plik_ze_sciezka = os.path.join(os.getcwd(), plik_z_definicjami_typow)
    err_out_writer.stdoutwrite('Wczytuje definicje aliasow z pliku %s' % plik_ze_sciezka)
    try:
        with open(plik_ze_sciezka) as plik_aliasow:
            definicje_aliasow_z_pliku = plik_aliasow.readlines()
    except FileNotFoundError:
        err_out_writer.stderrorwrite('Nie moge znalezc pliku: %s. Ignoruje definicje.' % plik_ze_sciezka)
        return {}
    except PermissionError:
        err_out_writer.stderrorwrite('Nie moge otworzyc pliku: %s. Brak dostepu. Ignoruje definicje.' % plik_ze_sciezka)
        return {}
    except IOError:
        err_out_writer.stderrorwrite('Nie moge otworzyc pliku: %s. I/O Error. Ignoruje definicje.' % plik_ze_sciezka)
        return {}
    if definicje_aliasow_z_pliku:
        return zwroc_wlasne_definicje_aliasow(definicje_aliasow_z_pliku, err_out_writer)
    return {}


def zwroc_wlasne_definicje_aliasow(definicje_aliasow_z_pliku, err_out_writer):
    """
    funkcja tworzy slownik słowników z definicjami aliasu w postaci 'Alias': {'Type': 'XXX', 'Prefix': 'XXX',
    'Suffix": 'XXX}
    :param definicje_aliasow_z_pliku: (list) lista linijek z pliku z definicjami
    :param err_out_writer: referencja do klasy z wlasna obsluga drukowania na ekranie albo w okienkach
    :return: {'Alias': {'Type': 'XXX', 'Prefix': 'XXX', 'Suffix': 'XXX'}}
    """
    wlasne_definicje_typow = {}
    dozwolone_klucze = {'Alias', 'Type', 'Prefix', 'Suffix'}
    for definicja_aliasu in definicje_aliasow_z_pliku:
        definicja_aliasu = definicja_aliasu.strip()
        if not definicja_aliasu or definicja_aliasu.startswith('#'):
            continue
        try:
            def_aliasu = json.loads(definicja_aliasu)
        except json.decoder.JSONDecodeError:
            err_out_writer.stderrorwrite('Niepoprawna linia w pliku z aliasami:')
            err_out_writer.stderrorwrite(str(definicja_aliasu))
            continue
        if dozwolone_klucze.difference(a for a in def_aliasu):
            err_out_writer.stderrorwrite('Niepoprawna definicja w pliku z aliasami, ignoruje')
            err_out_writer.stderrorwrite(str(definicja_aliasu))
            continue
        alias = def_aliasu['Alias']
        err_out_writer.stdoutwrite('Alias dla %s wczytany.' % alias)
        def_aliasu.pop('Alias')
        wlasne_definicje_typow[alias] = def_aliasu
    return wlasne_definicje_typow


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


def listujobszary(args, wydrukuj_obszary=True):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)
    try:
        listaobszarow = [a for a in os.listdir(Zmienne.KatalogzUMP)
                         if (a.startswith('UMP-') and os.path.isdir(os.path.join(Zmienne.KatalogzUMP, a)))]
        listaobszarow.sort()
    except FileNotFoundError:
        print('Bledna konfiguracja, nie znalazlem zadnych obszarow.', file=sys.stderr)
        return []
    else:
        if wydrukuj_obszary:
            print('\n'.join(listaobszarow), file=sys.stdout)
        return listaobszarow


def testuj_poprawnosc_danych(tester_poprawnosci_danych, dane_do_zapisu):
    if dane_do_zapisu['POIPOLY'] == '[POI]':
        tester_poprawnosci_danych.testy_poprawnosci_danych_poi(dane_do_zapisu)
    else:
        tester_poprawnosci_danych.testy_poprawnosci_danych_txt(dane_do_zapisu)


def zwroc_typ_komentarz(nazwa_pliku):
    # kolejnosc ifow odzwierciedla ilosc plikow danego typu w projekcie. Daje to bardzo malutkie przyspieszenie
    # przy czym cities trzeba szukac najpierw, bo tez sie konczy na pnt
    if nazwa_pliku.endswith('.txt'):
        return 'txt', '....[TXT] %s'
    if nazwa_pliku.endswith('.adr'):
        return 'adr', '....[ADR] %s'
    if nazwa_pliku.endswith('.pnt'):
        if 'cities' in nazwa_pliku:
            return 'cities', '....[CITY] %s'
        else:
            return 'pnt', '....[PNT] %s'
    return '', ''


def montujpliki(args, naglowek_mapy=''):
    stderr_stdout_writer = ErrOutWriter(args)
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
        for a in listujobszary(args, wydruku_obszary=False):
            if a.find('UMP-PL') >= 0:
                args.obszary.append(a)
        args.tylkodrogi = 1
    else:
        args.tylkodrogi = 0
    try:
        plikidomont = PlikiDoMontowania(Zmienne, args, stderr_stdout_writer)
    except (IOError, FileNotFoundError):
        return 0

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob
    plikidomont.Filtruj(args)

    # uklon w strone arta, montowanie tylko granic obszarow
    if hasattr(args, 'graniceczesciowe') and not args.tylkodrogi and not args.trybosmand:
        if args.graniceczesciowe:
            plikidomont.zamien_granice_na_granice_czesciowe()
    # jesli montujemy mape dla mkgmap i jest ona bez routingu nie montuj plikow granic bo wtedy kompilacja sie wylozy
    if hasattr(args, 'tryb_mkgmap') and args.tryb_mkgmap and hasattr(args, 'dodaj_routing') and not args.dodaj_routing:
        plikidomont.usun_plik_z_granicami()

    # sprytne entrypoints
    if hasattr(args, 'sprytne_entrypoints') and args.sprytne_entrypoints:
        args.entry_otwarte_do_extras = True
    # wlasnorecznie zdefiniowane aliasy
    wlasne_aliasy = {}
    if hasattr(args, 'wlasne_typy') and args.wlasne_typy:
        wlasne_aliasy = wczytaj_json_i_zwroc_wlasne_definicje_aliasow(args.wlasne_typy, stderr_stdout_writer)
    tabKonw = tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer, wlasny_alias2type=wlasne_aliasy)
    try:
        os.remove(os.path.join(Zmienne.KatalogRoboczy, Zmienne.OutputFile))
    except FileNotFoundError:
        pass

    globalneIndeksy = IndeksyMiast()
    zawartoscPlikuMp = PlikMP1(Zmienne, args, tabKonw, stderr_stdout_writer, Montuj=1, naglowek_mapy=naglowek_mapy)
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
            if args.monthash:
                zawartoscPlikuMp.plikHash[pliki] = ''
            else:
                if pliki.find('granice-czesciowe.txt') > 0:
                    zawartoscPlikuMp.plikHash[pliki] = hashlib.md5(open(pliki, 'rb').read()).hexdigest()
                else:
                    zawartoscPlikuMp.plikHash[pliki] = hashlib.md5(open(os.path.join(Zmienne.KatalogzUMP, pliki),
                                                                        'rb').read()).hexdigest()

            # print('Udalo sie otworzyc pliku %s'%(pliki))

            ############################################################################################################
            typ_pliku, informacja = zwroc_typ_komentarz(pliki)
            # montowanie plikow cities
            if typ_pliku in ('pnt', 'adr', 'cities'):
                if typ_pliku == 'cities':
                    punktzpnt = City(pliki, globalneIndeksy, tabKonw, args, stderr_stdout_writer)
                else:
                    punktzpnt = Poi(pliki, globalneIndeksy, tabKonw, args, stderr_stdout_writer, typ_obj=typ_pliku)
                punktzpnt.stdoutwrite((informacja % pliki))
                przetwarzanyPlik = plikPNT(pliki, stderr_stdout_writer, punktzpnt)
                # komentarz=''
                zawartosc_pliku_pnt = plikPNTTXT.readlines()
                if not zawartosc_pliku_pnt:
                    punktzpnt.stderrorwrite('Nie moge ustalic dokladnosci dla pliku %s' % pliki)
                    zawartoscPlikuMp.ustawDokladnosc(pliki, '-1')
                else:
                    zawartoscPlikuMp.dodaj(przetwarzanyPlik.procesuj(zawartosc_pliku_pnt))
                    zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                del przetwarzanyPlik
                del punktzpnt

            ###########################################################################################################
            # montowanie plikow txt
            elif typ_pliku == 'txt':
                punktzTXT = PolylinePolygone(pliki, globalneIndeksy, tabKonw, args, stderr_stdout_writer)
                punktzTXT.stdoutwrite(informacja % pliki)
                przetwarzanyPlik = plikTXT(pliki, punktzTXT,  stderr_stdout_writer)
                zawartosc_pliku_txt = plikPNTTXT.read()
                zawartoscPlikuMp.dodaj(przetwarzanyPlik.procesuj(zawartosc_pliku_txt))
                zawartoscPlikuMp.ustawDokladnosc(pliki, przetwarzanyPlik.Dokladnosc)
                _nazwapliku, _miasto = przetwarzanyPlik.zwrocDomyslneMiasto()
                if _miasto:
                    zawartoscPlikuMp.domyslneMiasta2[_nazwapliku] = _miasto
                del przetwarzanyPlik
                del punktzTXT

            else:
                print('nieznany typ pliku %s' % pliki)
                continue
            plikPNTTXT.close()

    # zapisujemy naglowek
    stderr_stdout_writer.stdoutwrite('zapisuje naglowek')
    plikMP = tempfile.NamedTemporaryFile('w', encoding=Zmienne.Kodowanie, dir=Zmienne.KatalogRoboczy, delete=False)
    plikMP.write(zawartoscPlikuMp.naglowek)

    # zapisujemy indeksy miast
    if args.cityidx and args.format_indeksow == 'cityidx':
        stderr_stdout_writer.stdoutwrite('zapisuje cityidx')
        if hasattr(args, 'savememory') and args.savememory:
            plikMP.writelines("{}\n".format(x) for x in globalneIndeksy.sekcja_cityidx)
        else:
            plikMP.write('\n'.join(globalneIndeksy.sekcja_cityidx))
        plikMP.write('\n[END-Cities]\n\n')

    if not args.trybosmand and not hasattr(args, 'tryb_mkgmap'):
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

    # jesli montujemy obszar aby skompilowac go mkgmapem, potrzebujemy też polygona obszarow pod spodem
    if hasattr(args, 'tryb_mkgmap') and args.tryb_mkgmap:
        plikMP.write('\n')
        plikMP.write('\n'.join(plikidomont.zwroc_obszary_txt()))
    plikMP.close()
    shutil.copy(plikMP.name, os.path.join(Zmienne.KatalogRoboczy, Zmienne.OutputFile))
    os.remove(plikMP.name)
    del zawartoscPlikuMp
    del globalneIndeksy
    stderr_stdout_writer.stdoutwrite('Gotowe!')
    return 0

###############################################################################
# montaz dla mkgmap
###############################################################################
def montuj_mkgmap(args):
    stderr_stdout_writer = ErrOutWriter(args)
    if not args.obszary:
        stderr_stdout_writer.stderrorwrite('Wybierz przynajmniej jeden obszar!')
        return
    # wczytaj liste map
    zmienne = UstawieniaPoczatkowe('wynik.mp')
    n_pliku = os.path.join(os.path.join(os.path.join(zmienne.KatalogzUMP, 'narzedzia'), 'widzimisie'), 'lista-map.txt')
    with open(n_pliku, 'r') as plik_lista_map:
        miasto_img_id = {a.split('=')[0].split('-')[-1]: a.split('=')[1].split('.')[0]
                         for a in plik_lista_map.readlines() if a.strip()}

    naglowek = OrderedDict({'ID': '', 'FamilyID': '4800', 'Name': '', 'Datum': 'W84', 'TreSize': '3096',
                            'RgnLimit': '1024', 'Levels': '6', 'Level0': '24', 'Level1': '22', 'Level2': '20',
                            'Level3': '18', 'Level4': '16', 'Level5': '15', 'POIIndex': 'Y', 'MG': 'Y',
                            'Numbering': 'Y', 'POINumberFirst': 'N', 'POIZipFirst': 'Y', 'Routing': 'Y',
                            'DrawPriority': '23', 'Copyright': 'ump.waw.pl debest', 'Elevation': 'm',
                            'DefaultRegionCountry': '', 'LBLcoding': '9', 'Codepage': '1250', 'LeftSideTraffic': 'N'
                            })
    # lewostronni: Brytania * 3, Irlandia, Cypr, Malta
    ruch_lewostronny = (str(a) for a in (44100001, 44130001, 44280001, 35300001, 35700001, 35600001))

    args.verbose = False
    args.umphome = ''
    args.katrob = ''
    args.savememory = False
    args.cityidx = True
    args.format_indeksow = 'cityname'
    if args.dodaj_adresy:
        args.adrfile = True
    else:
        args.adrfile = False
    args.notopo = False
    args.noszlaki = False
    args.nocity = False
    args.nopnt = False
    args.monthash = False
    args.graniceczesciowe = True
    args.extratypes = False
    args.trybosmand = False
    args.tryb_mkgmap = True
    args.entry_otwarte_do_extras = False
    args.no_osm = True
    obszary = tuple(args.obszary)
    dostepne_obszary = listujobszary(args, wydrukuj_obszary=False)
    for obszar in obszary:
        naglowek_mapy = '[IMG ID]\n'
        if obszar not in dostepne_obszary:
            stderr_stdout_writer.stderrorwrite('Nie moge odnalezc obszaru %s' % obszar)
            continue
        miasto = obszar.split('-')[-1].strip()
        args.obszary = [obszar]
        args.plikmp = miasto + '_' + miasto_img_id[miasto] + '_mkgmap.mp'
        naglowek['ID'] = miasto_img_id[miasto]
        naglowek['DefaultRegionCountry'] = miasto
        if naglowek['ID'] in ruch_lewostronny:
            naglowek['LeftSideTraffic'] = 'Y'
        data_kompilacji = date.today()
        naglowek['Name'] = 'UMP-' + miasto + '-' + data_kompilacji.strftime('%d') + data_kompilacji.strftime('%B')[0:3]
        for elem_naglowka in naglowek:
            naglowek_mapy += elem_naglowka + '=' + naglowek[elem_naglowka] + '\n'
        naglowek_mapy += '[END-IMG ID]\n\n'
        stderr_stdout_writer.stdoutwrite('montuje mape')
        montujpliki(args, naglowek_mapy=naglowek_mapy)
        # zamieniam KodPoczt na Zip
        stderr_stdout_writer.stdoutwrite('Zamieniam KodPoczt na ZipCode, zamienam {} na ()')
        with open(os.path.join(zmienne.KatalogRoboczy, args.plikmp), 'r', encoding=zmienne.Kodowanie) as plik_mp_do_czyt:
            plik_do_konwersji = plik_mp_do_czyt.readlines()
        for num, linia in enumerate(plik_do_konwersji):
            if linia.startswith('KodPoczt='):
                plik_do_konwersji[num] = linia.replace('KodPoczt=', 'ZipCode=', 1)
            elif linia.startswith('Label='):
                plik_do_konwersji[num] = linia.replace('{', '(').replace('}', ')')
            elif linia.startswith('CityName'):
                plik_do_konwersji[num] = linia.replace('@', ';')
        with open(os.path.join(zmienne.KatalogRoboczy, args.plikmp), 'w', encoding=zmienne.Kodowanie) as plik_mp_do_zap:
            plik_mp_do_zap.writelines(plik_do_konwersji)
        if args.podnies_poziom:
            args.output_filename = args.plikmp
            stderr_stdout_writer.stdoutwrite('Dostosowuje predkosci przy pomocy podnies-poziom.pl')
            ustaw_force_speed(args)
        if args.uruchom_wojka:
            args.output_filename = args.plikmp
            stderr_stdout_writer.stdoutwrite('dodaje dane wojkiem')
            wojkuj(args)
        if args.dodaj_routing:
            args.output_filename = args.plikmp
            stderr_stdout_writer.stdoutwrite('dodaje dane routingowe')
            args.input_file = args.plikmp
            dodaj_dane_routingowe(args)


###############################################################################
# Demontaz
###############################################################################
def demontuj(args):
    if hasattr(args, 'buttonqueue'):
        args.buttonqueue.put('Pracuje')
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = ErrOutWriter(args)

    if args.umphome:
        Zmienne.ustaw_katalog_home(args.umphome)

    if args.katrob:
        Zmienne.KatalogRoboczy = args.katrob

    if args.plikmp:
        Zmienne.KatalogRoboczy = os.getcwd()
    # print(Zmienne.KatalogRoboczy)
    tabKonw = tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = PlikMP1(Zmienne, args, tabKonw, stderr_stdout_writer, Montuj=0, naglowek_mapy='')

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
        plikMp.autoobszary.wypelnij_obszar_plik_wspolrzedne(plikMp.plikizMp)

    # jezeli string konczy sie na [END] to split zwroci liste w ktorej ostatnia pozycja jest rowna
    # '' dlatego [0:-1]. Dodatkowo na koncu pliku zamontowane sa warstwy ktorych tez nie potrzebujemy
    rekordy_mp = zawartoscPlikuMp.split('\n[END]')[0:-1]
    ilosc_rekordow = len(rekordy_mp)

    # iterujemy po kolejnych rekordach w pliku mp. Rekordy to dane pomiedzy [END]
    update_progress(0 / 100, args)
    tester_poprawnosci_danych = TestyPoprawnosciDanych(stderr_stdout_writer)
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

        if nazwa_pliku in ('_nowosci.txt', '_nowosci.pnt'):
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
                    orgPlikZawartosc = open(nazwa_pliku, encoding=Zmienne.Kodowanie,
                                            errors=Zmienne.ReadErrors).readlines()
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
    stderr_stdout_writer = ErrOutWriter(args)

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
    stderr_stdout_writer = ErrOutWriter(args)
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
    stderr_stdout_writer = ErrOutWriter(args)
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
    process = subprocess.Popen([Zmienne.NetGen, '-cbxj', '-a60', '-e0', '-r0.0000315', '-s0.0003',
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
                f.writelines(('OziExplorer Waypoint File Version 1.1\n', 'WGS 84\n', 'Reserved 2\n', 'Reserved 3\n'))
                f.writelines([abc + '\n' for abc in bledy[typBledu]])
            stderr_stdout_writer.stdoutwrite(typBledu + '-->' + os.path.join(Zmienne.KatalogRoboczy,
                                                                             typBledu.replace(' ', '-') + '.wpt\n'))

    stderr_stdout_writer.stdoutwrite('Sprawdzanie Netgenem zakonczone!')
    if hasattr(args, 'sprawdzbuttonqueue'):
        args.sprawdzbuttonqueue.put('Koniec')


def cvsup(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = ErrOutWriter(args)

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
    stderr_stdout_writer = ErrOutWriter(args)
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
    stderr_stdout_writer = ErrOutWriter(args)
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
    args.monthash = 1
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
    wynik_klasy_mp = os.path.join(Zmienne.KatalogRoboczy, 'wynik-klasy.mp')
    with open(os.path.join(wynik_klasy_mp), 'w', encoding=Zmienne.Kodowanie, errors=Zmienne.WriteErrors) as f:
        for a in plik_mp_z_klasami.split('\n'):
            if a.startswith('EndLevel'):
                pass
            else:
                if a.startswith('Routeparam') or a.startswith('RouteParam'):
                    klasa = a.split('=')[-1].split(',')[1]
                    f.write('EndLevel=' + klasa + '\n')
                f.write(a.strip() + '\n')
    stderr_stdout_writer.stdoutwrite('Utworzony plik z klasami: ' + wynik_klasy_mp)
    # jesli wywolany z mdm bedzie mial w argumentach kolejke do aktywacji guzika zobacz
    if hasattr(args, 'zobaczbuttonqueue'):
        args.zobaczbuttonqueue.put('Koniec')


def patch(args):
    Zmienne = UstawieniaPoczatkowe('wynik.mp')
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        patchExe = 'patch'
    else:
        patchExe = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'patch.exe')
    stderr_stdout_writer = ErrOutWriter(args)

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
    stderr_stdout_writer = ErrOutWriter(args)
    if isinstance(args.output_filename, list):
        plik_wyjsciowy = args.output_filename[0]
    else:
        plik_wyjsciowy = args.output_filename
    Zmienne = UstawieniaPoczatkowe(args.plikmp)
    stderr_stdout_writer.stdoutwrite('Dodaje do pliku dane routingowe przy pomocy netgena')
    NetgenConfFile = os.path.join(Zmienne.KatalogzUMP, 'narzedzia' + os.sep + 'netgen.cfg')
    stderr_stdout_writer.stdoutwrite('Uruchamiam netgena na pliku wejściowym: %s' % Zmienne.InputFile)
    netgen_call = [Zmienne.NetGen, '-b', '-R', '-e0.00002', '-j', '-k', '-T' + NetgenConfFile,
                   os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)]
    process = subprocess.Popen(netgen_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    plik_mp_z_klasami, err = process.communicate()
    stderr_stdout_writer.stderrorwrite(err.decode(Zmienne.Kodowanie))
    stderr_stdout_writer.stdoutwrite('Zapisuje plik wyjsciowy %s z danymi routingowymi' % plik_wyjsciowy)
    plik_mp_do_zapisu = []
    for linia in plik_mp_z_klasami.decode(Zmienne.Kodowanie).split('\n'):
        plik_mp_do_zapisu.append(linia.strip().replace('Routeparam', 'RouteParam') + '\n')
    with open(os.path.join(Zmienne.KatalogRoboczy, plik_wyjsciowy), 'w', encoding=Zmienne.Kodowanie) as file_name:
        file_name.writelines(plik_mp_do_zapisu)


def wojkuj(args):
    stderr_stdout_writer = ErrOutWriter(args)
    Zmienne = UstawieniaPoczatkowe(args.plikmp)
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        wojek_exe =  os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia'), 'wojek')
    else:
        wojek_exe = os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia'), 'wojek.exe')
    wojek_slownik_txt = os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia'), 'wojek-slownik-mkgmap.txt')
    wynik_mp = os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)
    mapa_woj_mp = os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia'), 'mapka_woj.mp')
    wynik_mp_wojek = tempfile.NamedTemporaryFile('w', encoding=Zmienne.Kodowanie, dir=Zmienne.KatalogRoboczy,
                                                 delete=False)
    wynik_mp_wojek.close()
    wojek_call = [wojek_exe, '-s', wojek_slownik_txt, '-k', mapa_woj_mp, '-f', wynik_mp, '-F', wynik_mp_wojek.name]
    print(' '.join(wojek_call))
    process = subprocess.Popen(wojek_call)
    process.wait()
    os.remove(wynik_mp)
    shutil.copy(wynik_mp_wojek.name, wynik_mp)
    os.remove(wynik_mp_wojek.name)

def kompiluj_mape(args):

    stderr_stdout_writer = ErrOutWriter(args)
    zmienne = UstawieniaPoczatkowe('wynik.mp')
    pliki_do_kompilacji = list()
    # dwuliterowe kody pastw za https://pl.wikipedia.org/wiki/ISO_3166-1https://pl.wikipedia.org/wiki/ISO_3166-1
    # w formacie numer kierunkowy: skrot, kolejnosc wedlug pliku lista.map
    dwuliterowy_skrot_panstw = {'355': 'AL', '213': 'DZ', '376': 'AD', '43': 'AT', '32': 'BE', '387': 'BA', '359': 'BG',
                                '385': 'HR', '357': 'CY', '382': 'ME', '420': 'CZ', '45': 'DK', '49': 'DE', '372': 'EE',
                                '20': 'EG', '34': 'ES', '358': 'FI', '33': 'FR', '44': 'GB', '30': 'GR', '353': 'IE',
                                '354': 'IS', '39': 'IT', '53': 'CU', '423': 'LI', '370': 'LT', '371': 'LV', '352': 'LU',
                                '389': 'MK', '356': 'MT', '212': 'MA', '373': 'MD', '31': 'NL', '47': 'NO', '48': 'PL',
                                '351': 'PT', '40': 'RO', '7': 'RU', '46': 'SE', '381': 'RS', '421': 'SK', '386': 'SI',
                                '41': 'CH', '216': 'TN', '90': 'TR', '380': 'UA', '36': 'HU', '298': 'FO', '238': 'CV'
                                # karaiby, kosowo, nepal, pomijam
                                }
    # mapset_name = []
    nazwa_sciezka_pliku_typ = ''
    print(args.nazwa_typ)
    if args.nazwa_typ != 'brak':
        nazwa_sciezka_pliku_typ = stworz_plik_typ(args)
    for plik_do_k in glob.glob(os.path.join(zmienne.KatalogRoboczy, '*mkgmap.mp')):
        opis, kod_kraju, _mkgmap = os.path.basename(plik_do_k).split('_')
        pliki_do_kompilacji.append('--description=' + opis + '_' + date.today().strftime('%d%b%y'))
        skrot_kraju = ''
        for ii in (2, 1):
            if kod_kraju[0:ii] in dwuliterowy_skrot_panstw:
                skrot_kraju = dwuliterowy_skrot_panstw[kod_kraju[0:ii]]
                break
        if not skrot_kraju:
            stderr_stdout_writer.stderrorwrite('Nie moge ustalic skrotu kraju dla: %s' % plik_do_k)
        else:
            pliki_do_kompilacji.append('--country-abbr=' + skrot_kraju)
        pliki_do_kompilacji.append(plik_do_k)
    if not pliki_do_kompilacji:
        stderr_stdout_writer.stderrorwrite('Brak plikow do kompilacji w katalogu roboczym: *mkgmap.img')
        return

    java_call_args, mapset_name, nazwa_map = Mkgmap(args, zmienne).java_call_mkgmap()
    java_call_args += pliki_do_kompilacji
    if nazwa_sciezka_pliku_typ:
        java_call_args += [nazwa_sciezka_pliku_typ]
    java_call_args += mapset_name
    stderr_stdout_writer.stdoutwrite('Kompiluje mape przy pomocy mkgmap')
    stderr_stdout_writer.stdoutwrite(' '.join(java_call_args))
    gmapsupp_img_path = os.path.join(zmienne.KatalogRoboczy, 'gmapsupp.img')
    gmapi_folder_path =os.path.join(zmienne.KatalogRoboczy, nazwa_map + '.gmap')
    if args.format_mapy == 'gmapsupp':
        if os.path.exists(gmapsupp_img_path):
            os.remove(gmapsupp_img_path)
    else:
        if os.path.exists(gmapi_folder_path):
            shutil.rmtree(gmapi_folder_path)
    process = subprocess.Popen(java_call_args)
    process.wait()
    if args.format_mapy == 'gmapsupp':
        if os.path.exists(gmapsupp_img_path):
            stderr_stdout_writer.stdoutwrite('Kompilacja zakonczona sukcesem. Powstal plik %s' % gmapsupp_img_path)
        else:
            stderr_stdout_writer.stderrorwrite('Kompilacja nieudana. Nie powstal plik %s. Sprawdz konsole!' %
                                               gmapsupp_img_path)

    else:
        if os.path.exists(gmapi_folder_path):
            stderr_stdout_writer.stdoutwrite('Kompilacja zakonczona sukcesem. Powstal katalog %s' % gmapi_folder_path)
        else:
            stderr_stdout_writer.stdoutwrite('Kompilacja nieudana. Nie powstal katalog %s. Sprawdz konsole!' %
                                             gmapi_folder_path)
    return


def ustaw_force_speed(args):
    stderr_stdout_writer = ErrOutWriter(args)
    Zmienne = UstawieniaPoczatkowe(args.plikmp)
    podnies_poziom = os.path.join(os.path.join(Zmienne.KatalogzUMP, 'narzedzia'), 'podnies-poziom.pl')
    wynik_mp = os.path.join(Zmienne.KatalogRoboczy, Zmienne.InputFile)
    wynik_mp_podnies_poziom = tempfile.NamedTemporaryFile('w', encoding=Zmienne.Kodowanie, dir=Zmienne.KatalogRoboczy,
                                                          delete=False)
    wynik_mp_podnies_poziom.close()
    podnies_poziom_call = ['perl', podnies_poziom, '--speed', '--city', '--inpfile', wynik_mp, '--outfile',
                           wynik_mp_podnies_poziom.name]
    stderr_stdout_writer.stdoutwrite(' '.join(podnies_poziom_call))
    process = subprocess.Popen(podnies_poziom_call)
    process.wait()
    os.remove(wynik_mp)
    shutil.copy(wynik_mp_podnies_poziom.name, wynik_mp)
    os.remove(wynik_mp_podnies_poziom.name)


def stworz_plik_typ(args):
    """
    funkcja tworzy plik typ z plikow czastkowych obecnych w
    Parameters
    ----------
    args: argumenty wywołania

    Returns: nazwa_pliku sukces, '' blad
    -------
    """
    # z gui przekazywane to jest jako string, dlatego trzeba tak obchodzic.
    stderr_stdout_writer = ErrOutWriter(args)
    if isinstance(args.nazwa_typ, list):
        nazwa_typ = args.nazwa_typ[0]
    else:
        nazwa_typ = args.nazwa_typ
    zmienne = UstawieniaPoczatkowe(args)
    katalog_narzedzia = os.path.join(zmienne.KatalogzUMP, 'narzedzia')
    katalog_ikonki = os.path.join(katalog_narzedzia, 'ikonki')
    plik_typ_zawartosc = ['[_id]\n', 'ProductCode=1\n', 'FID=' + args.family_id + '\n']
    if not args.code_page == 'cp1250':
        plik_typ_zawartosc += ['CodePage=1250\n']
    plik_typ_zawartosc += ['[end]\n\n', '']
    with open(os.path.join(katalog_ikonki, 'header.txt'), 'r', encoding=zmienne.Kodowanie) as header_file:
        plik_typ_zawartosc += header_file.readlines()

    if nazwa_typ in ('rzuq', 'olowos'):
        n_pliku = 'point-rzuq003.txt' if nazwa_typ == 'rzuq' else 'point-olowos.txt'
        with open(os.path.join(katalog_ikonki, n_pliku), encoding=zmienne.Kodowanie) as plik_do_czyt:
            plik_typ_zawartosc += plik_do_czyt.readlines()
    else:
        for plik_ikonki_nazwa in glob.glob(os.path.join(katalog_ikonki, 'punkty', '*day*.xpm')):
            font = ''
            fontc = ''
            try:
                mp_typ, nazwa_pl, nazwa_en, tryb = \
                    os.path.splitext(os.path.basename(plik_ikonki_nazwa))[0].split('_', 3)
            except ValueError:
                stderr_stdout_writer.stdoutwrite('Bledna nazwa dla pliku ikonki %s. Poprawny format nazwy to: '
                                                 'typ_nazwaPl_nazwaEn_day.xpm lub night. Ignoruje ikonke')
                continue

            if '_' in tryb:
                tryb, font = tryb.split('_', 1)
            if '_' in font:
                font, fontc = font.split('_', 1)
            if len(mp_typ) == 4:
                mp_type = mp_typ[0:2]
                mp_subtype = mp_typ[2:5]
                mp_specialny = ''
            else:
                mp_type = mp_typ[2:4]
                mp_subtype = mp_typ[4:6]
                # mp_specialny = 'Marine=Y\n'
                mp_specialny = ''
            plik_typ_zawartosc += ['\n', '[_point]\n']
            plik_typ_zawartosc.append('Type=0x' + mp_type + '\n')
            plik_typ_zawartosc.append('SubType=0x' + mp_subtype + '\n')
            if mp_specialny:
                plik_typ_zawartosc.append(mp_specialny)
            plik_typ_zawartosc.append('string1=0x04,' + nazwa_en + '\n')
            plik_typ_zawartosc.append('string2=0x15,' + nazwa_pl + '\n')
            # if font:
            #     plik_typ_zawartosc.append('Font=' + font + '\n')
            if fontc:
                if tryb == 'day':
                    plik_typ_zawartosc.append('DayFontColor=0x' + fontc + '\n')
                elif tryb == 'night':
                    plik_typ_zawartosc.append('NightFontColor=0x' + fontc + '\n')
            with open(plik_ikonki_nazwa, 'r', encoding=zmienne.Kodowanie) as plik_ikonki:
                ikonka = plik_ikonki.readlines()
            plik_typ_zawartosc.append(tryb + 'xpm=' + ikonka[2].replace('.', ''))
            plik_typ_zawartosc += ikonka[3:]
            plik_typ_zawartosc += ['[end]', '\n']

    nazwa_typu_plik = {'reczniak': ['polygon-outdoor.txt', 'line-outdoor_mkgmap.txt'],
                       'rzuq': ['polygon-rzuq003.txt', 'line-rzuq003.txt'],
                       'olowos': ['polygon-olowos.txt', 'line-olowos.txt'],
                       'domyslny': ['polygon.txt', 'line_mkgmap.txt']}

    for plik in nazwa_typu_plik[nazwa_typ]:
        with open(os.path.join(katalog_ikonki, plik), 'r', encoding=zmienne.Kodowanie) as pl:
            definicje = pl.readlines()
        if not args.uwzglednij_warstwice and 'polygon' in plik:
            plik_typ_zawartosc += [a.replace('# c #AAAA00', '# c none') for a in definicje]
        else:
            plik_typ_zawartosc += definicje

    plik_typ_txt = os.path.join(zmienne.KatalogRoboczy, 'ump_typ_' + nazwa_typ + '.txt')
    with open(plik_typ_txt, 'w', encoding=zmienne.Kodowanie) as typ_file:
        typ_file.writelines(plik_typ_zawartosc)
    if os.path.isfile(plik_typ_txt):
        stderr_stdout_writer.stdoutwrite('Zapisalem plik typ: %s' % plik_typ_txt)
    else:
        stderr_stdout_writer.stdoutwrite('Nie udalo sie zapisac pliku typ: %s. Nie moge kontynuowac' %plik_typ_txt)
        return ''
    java_call_args = Mkgmap(args, zmienne).java_call_typ()
    stderr_stdout_writer.stdoutwrite('Kompiluje plik typ: ' + ' '.join(java_call_args) + ' ' + plik_typ_txt)
    process = subprocess.Popen(java_call_args + [plik_typ_txt])
    process.wait()
    plik_typ = plik_typ_txt.replace('.txt', '.typ')
    if not os.path.isfile(plik_typ):
        stderr_stdout_writer.stdoutwrite('Skompilowanie pliku typ nie powiodlo sie.')
        return ''
    else:
        stderr_stdout_writer.stdoutwrite('Kompilacja zakonczona sukcesem. Stworzylem plik %s' % plik_typ)
    return plik_typ


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
    parser_montuj.add_argument('-fi', '--format-indeksow', action='store', help='Format indeksów', default='cityidx',
                               choices=['cityidx', 'cityname'])
    parser_montuj.add_argument('-adr', '--adr-files', action='store_true', dest='adrfile', help="montuj pliki adresowe")
    parser_montuj.add_argument('-nt', '--no-topo', action='store_true', dest='notopo', help='nie montuj plikow topo')
    parser_montuj.add_argument('-ns', '--no-szlaki', action='store_true', dest='noszlaki', help='nie montuj szlakow')
    parser_montuj.add_argument('-nc', '--no-city', action='store_true', dest='nocity', help='nie montuj plikow miast')
    parser_montuj.add_argument('-np', '--no-pnt', action='store_true', dest='nopnt', help='nie montuj plikow pnt')
    parser_montuj.add_argument('-no', '--no-osm', action='store_true', help='nie montuj plikow z osm: *osm.woda.txt')
    parser_montuj.add_argument('-o', '--output-file', dest='plikmp', default='wynik.mp',
                               help='nazwa pliku wynikowego. Domyslnie wynik.mp')
    parser_montuj.add_argument('-nh', '--no-hash', dest='monthash', action='store_true',
                               help='nie generuj sum kontrolnych dla montowanych plikow')
    parser_montuj.add_argument('-et', '--extra-types', dest='extratypes', action='store_true',
                               help='specjalne traktowanie typow')
    parser_montuj.add_argument('-gc', '--granice-czesciowe', dest='graniceczesciowe', action='store_true',
                               help='dolacz tylko granice montowanych obszarow')
    parser_montuj.add_argument('-toa', '--tryb-osmand', dest='trybosmand', action='store_true',
                               help='ogranicza ilosc montowanych danych dla konwersji do OSMAnd')
    parser_montuj.add_argument('-eoe', '--entry-otwarte-do-extras', action='store_true', default=False,
                               help='Przenosi otarte i entrypoints z komentarza do extras. Uwaga, używać '
                                    'ostrożnie')
    parser_montuj.add_argument('-sep', '--sprytne-entrypoints', action='store_true', default=False,
                               help='Ustaw EntryPoints jako Data0, dzięki czemu łatwiej się dodaje EP dla punktó?')
    parser_montuj.set_defaults(func=montujpliki)

    # parser dla komendy montuj_mkgmap
    parser_montuj_mkgmap = subparsers.add_parser('montuj-mkgmap', help="Montowanie mapy dla mkgmap")
    parser_montuj_mkgmap.add_argument('obszary', nargs="*", default=[])
    parser_montuj_mkgmap.add_argument('-a', '--dodaj-adresy', action='store_true', help="Dodaj punkty adresowe",
                                      default=False)
    parser_montuj_mkgmap.add_argument('-r', '--dodaj-routing', help="Dodaj dane routingowe do zamontowanej mapy",
                                      action='store_true', default=False)
    parser_montuj_mkgmap.add_argument('-w', '--uruchom-wojka', help="Dodaj dane przy pomocy wojka do zamontowanej mapy",
                                      action='store_true', default=False)
    parser_montuj_mkgmap.add_argument('-p', '--podnies-poziom', help='Uruchom skrypt podnies-poziom.pl na pliku mp',
                                      action='store_true', default=False)
    parser_montuj_mkgmap.add_argument('-wt', '--wlasne-typy', default='',
                                      help='Plik zawierajacy wlasne defnicje typow dla konwersji Typ->Type, oraz '
                                           'reguly zmiany Label')
    parser_montuj_mkgmap.set_defaults(func=montuj_mkgmap)

    # parser dla komendy demontuj/demont
    parser_demontuj = subparsers.add_parser('demont', help='demontaz pliku mp')
    parser_demontuj.add_argument('-i', '--input-file', dest='plikmp',
                                 help='nazwa pliku do demontazu, domyslnie wynik.mp')
    parser_demontuj.add_argument('-idx', '--city-idx', action="store_true", dest='cityidx',
                                 help="nadpisuj Miasto= wartoscia indeksu miast")
    parser_demontuj.add_argument('-nh', '--no-hash', action='store_true', dest='demonthash',
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
    parser_demontuj.add_argument('-upn', '--usun-puste-numery', action='store_true', help='Usun pusta numeracje')
    parser_demontuj.set_defaults(func=demontuj)

    # parser dla komendy listuj
    parsers_listuj = subparsers.add_parser('list', help='listuj obszary do montowania')
    parsers_listuj.set_defaults(func=listujobszary)

    # parser dla komendy zapiszkonf
    parsers_zapiszkonf = subparsers.add_parser('zapiszkonf', help='tworzy plik konfiguracyjny z katalogiem domowym ump '
                                                                  'i katalogiem roboczym')
    parsers_zapiszkonf.set_defaults(func=zapiszkonfiguracje)

    # parser dla komendy edytuj - uruchamianie mapedit
    parsers_edytuj = subparsers.add_parser('edytuj', help='uruchom mapedit')
    parsers_edytuj.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do demontazu, '
                                                                          'domyslnie wynik.mp')
    parsers_edytuj.add_argument('-me2', '--mapedit-2', action='store_true', dest='mapedit2',
                                help='alternatywna wersja mapedit, zdefiniowana w konfiguracji')
    parsers_edytuj.set_defaults(func=edytuj)

    # parser dla komendy sprawdz - sprawdza negenem
    parsers_sprawdz = subparsers.add_parser('sprawdz', help='sprawdza siatke drog netgenem')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, '
                                                                           'domyslnie wynik.mp')
    parsers_sprawdz.set_defaults(func=sprawdz)

    # parser dla komendy sprawdz_numeracje
    parsers_sprawdz = subparsers.add_parser('sprawdz_numeracje', help='sprawdza numeracje')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, '
                                                                           'domyslnie wynik.mp')
    parsers_sprawdz.set_defaults(func=sprawdz_numeracje)

    # parser dla komendy sprawdz_siatke_routingowa
    parsers_sprawdz = subparsers.add_parser('sprawdz_siatke_routingowa', help='sprawdz ciaglosc siatki routingowej')
    parsers_sprawdz.add_argument('-i', '--input-file', dest='plikmp', help='nazwa pliku do sprawdzenia, '
                                                                           'domyslnie wynik.mp')
    parsers_sprawdz.add_argument('-m', '--mode', dest='mode', default='sprawdz_siatke_dwukierunkowa',
                                 choices=['sprawdz_siatke_dwukierunkowa', 'sprawdz_siatke_jednokierunkowa'],
                                 help='sprawdz siatke routingowa dwukierunkowa i jednokierunkowa')
    parsers_sprawdz.set_defaults(func=sprawdz_numeracje)

    # parser dla komendy cvsup -
    parsers_cvsup = subparsers.add_parser('cvsup', help='uaktualnia zrodla')
    parsers_cvsup.add_argument('obszary', nargs="*", default=['pwd'])
    parsers_cvsup.set_defaults(func=cvsup)

    # parser dla komendu czysc
    parsers_czysc = subparsers.add_parser('czysc', help='usuwa wynik.mp (domyslnie), granice-czesciowe.txt (domyslnie) '
                                                        'oraz czysci katalog roboczy z plikow diff, '
                                                        'plikow oryginalnych, plikow bledow')
    parsers_czysc.add_argument('-w', '--wszystko', dest='wszystko', action='store_true',
                               help='usuwa pliki diff, pliki oryginalne, pliki bledow oraz wynik.mp')
    parsers_czysc.add_argument('-d', '--diff', dest='diff', action='store_true', help='usuwa tylko pliki diff')
    parsers_czysc.add_argument('-b', '--bledy', dest='bledy', action='store_true', help='usuwa tylko pliki bledow')
    parsers_czysc.add_argument('-o', '--oryg', dest='oryg', action='store_true',
                               help='usuwa pliki oryginalne do ktorych istnieja pliki diff')
    parsers_czysc.set_defaults(func=czysc)

    # parser dla komendy rozdziel na klasy
    parser_rozdziel_na_klasy = subparsers.add_parser('rozdziel-na-klasy',
                                                     help='montuje wynik.mp, dodaje dane routingowe netgenem, '
                                                          'a potem rozklada na klasy')
    parser_rozdziel_na_klasy.add_argument('obszary', nargs="*", default=['pwd'])
    parser_rozdziel_na_klasy.set_defaults(func=rozdziel_na_klasy)

    # parser dla komendy patch
    parser_patch = subparsers.add_parser('patch', help='naklada latki przy pomocy komendy patch/patch.exe')
    parser_patch.add_argument('pliki_diff', nargs='+')
    parser_patch.set_defaults(func=patch)

    # parser dla komendy dodaj dane routingowe
    parser_dodaj_dane_routingowe = subparsers.add_parser('dodaj-dane-routingowe', help="dodaje dane routingowe przy "
                                                                                       " pomocy netgena")
    parser_dodaj_dane_routingowe.add_argument('-i', '--input-file', dest='plikmp', default=['wynik.mp'], nargs=1,
                                              help='Nazwa pliku do przetworzenia. Domyslnie wynik.mp')
    parser_dodaj_dane_routingowe.add_argument('-o', '--output-filename', help='Nazwa pliku mp z danymi routingowymi, '
                                                                              'domyślnie wynik.mp',
                                              action='store', default=['wynik.mp'], nargs=1)
    parser_dodaj_dane_routingowe.set_defaults(func=dodaj_dane_routingowe)

    # parser dla komendy wojkuj
    parser_wojkuj_mape = subparsers.add_parser('wojkuj', help="Dodaj dane przy pomocy wojka")
    parser_wojkuj_mape.add_argument('-i', '--input-file', dest='plikmp', default=['wynik.mp'], nargs=1,
                                    help='Nazwa pliku do przetworzenia. Domyslnie wynik.mp')
    parser_wojkuj_mape.set_defaults(func=wojkuj)

    # parser dla komendy kompiluj mape
    parser_kompiluj_mape = subparsers.add_parser('kompiluj-mape', help="Kompiluj mapę przy pomocy mkgmap")
    parser_kompiluj_mape.add_argument('-m', '--mkgmap-path', default='', help='Sciezka do programu mkgmap')
    parser_kompiluj_mape.add_argument('-fi', '--family-id', default='6324', help='family id mapy, domyslnie 6324')
    parser_kompiluj_mape.add_argument('-cp', '--code-page', default='cp1250', choices=['cp1250', 'ascii'],
                                      help='kodowanie pliku: cp1250 - z polskimi literkami, ascii - bez '
                                           'polskich literek')
    parser_kompiluj_mape.add_argument('-nt', '--nazwa-typ', default='domyslny',
                                      choices=['brak', 'domyslny', 'rzuq', 'olowos', 'reczniak'],
                                      help='wybierz plik typ dla mapy - domyslny jest uzywany standardowo')
    parser_kompiluj_mape.add_argument('-uw', '--uwzglednij-warstwice', default=False, action='store_true',
                                      help='Dodaj warstwice do pliku mapy')
    parser_kompiluj_mape.add_argument('-fm', '--format-mapy', default='gmapsupp', choices=['gmapsupp', 'gmapi'],
                                      help="Generuj mape w formacie gmapsupp.img albo gmapii. "
                                           "Gmapsupp wgrywasz do odbiornika, gmapi wgrywasz do mapsource/basecamp.")
    parser_kompiluj_mape.add_argument('-r', '--dodaj-routing', action='store_true', default=False,
                                      help="Generuj mape z routingiem")
    parser_kompiluj_mape.add_argument('-i', '--index', action='store_true', default=False,
                                      help="Generuj index do wyszukiwania adresow")
    parser_kompiluj_mape.add_argument('-Xmx', '--maksymalna-pamiec', default='1G',
                                      help='Maksymalna pamięc dla srodowiska java, np -Xmx 2G gdzie g, G, m, M,')
    parser_kompiluj_mape.add_argument('-mj', '--max-jobs', default='0',
                                      help='Maksymalna ilosc watkow do kompilacji (domyslnie auto)')
    parser_kompiluj_mape.set_defaults(func=kompiluj_mape)

    # parser dla komendy skompiluj_typ
    parser_kompiluj_typ = subparsers.add_parser('kompiluj-typ', help='stworzenie i kmpilacja pliku typ')
    parser_kompiluj_typ.add_argument('nazwa_typ', default='domyslny',
                                     choices=['domyslny', 'rzuq', 'olowos', 'reczniak'],
                                     help='rodzaj pliku typ do wyboru')
    parser_kompiluj_typ.add_argument('-m', '--mkgmap-path', default='', help='Sciezka do programu mkgmap')
    parser_kompiluj_typ.add_argument('-Xmx', '--maksymalna-pamiec', default='1G',
                                      help='Maksymalna pamięc dla srodowiska java, np -Xmx 2G gdzie g, G, m, M,')
    parser_kompiluj_typ.add_argument('-f', '--family-id', default='6324', help='Family ID dla pliku typ '
                                                                               '(domyslnie 6324)')
    parser_kompiluj_typ.add_argument('-w', '--uwzglednij-warstwice', default=False, action='store_true',
                                     help='Dodaj warstwice do pliku typ')
    parser_kompiluj_typ.add_argument('-cp', '--code-page', default='cp1250', choices=['cp1250', 'ascii'],
                                     help='kodowanie pliku: cp1250 - z polskimi literkami,'
                                          ' ascii - bez polskich literek')
    parser_kompiluj_typ.set_defaults(func=stworz_plik_typ)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main(sys.argv)
