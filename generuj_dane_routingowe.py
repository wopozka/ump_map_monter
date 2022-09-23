from collections import OrderedDict

class NodDrogi(object):
    def __init__(self, wspolrzedne, roadid):
        self.wspolrzedne = wspolrzedne
        self.nod_skrajny = False
        self.roadid_drog = [roadid]
w

class ObiektMapy(object):
    def __init__(rekord_danych):
        self.dane_obiektu = rekord_danych
        self.punkty_drogi = list()
        self.type = None
        self.multiple_data = False
        data0_odczytane = False
        self.data0 = list()
        self.road_id = None
        for a in rekord_danych:
            if a.startswith('[POLYLINE]'):
                self.typ_obiektu = 'polyline'
            elif a.startswith('[POI]'):
                self.typ_obiektu = 'poi'
            elif a.startswith('[POLYGONE]'):
                self.typ_obiektu = 'polygone'
            elif a.startswith('Type=') and polyline:
                self.type = a.split('=', 1)[1]
            elif a.startswith('Data0') and not data0_odczytane:
                self.data0 = a.split('=')[1].lstrip('(').rstrip(')').split('),(')
                data0_odczytane = True
            elif a.startswith('Data0') and data0_odczytane:
                self.multiple_data = True
                break

    def ustaw_roadid(self, roadid):
        self.road_id = roadid



class Restrykcja(object):
    def __init__(self, data0):
        self.typ_restrykcji = None # mozliwe wartosci restr sign
        self.from_road_id = None
        self.via_rod_id = None
        self.to_road_id = None
        self.punkty_restrykcji = data0.lstrip('(').rstrip(')').split('),(')

    def policz_from_via_to(self):
        pass

class MapaMP(object):
    def __init__(self, netgen_cfg):
        self.pierwsze_wolne_road_id = 1
        self.parametry_routingu = dict()
        self.typy_routingowe = ('0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7', '0x8', '0x9', '0xa', )
        self.typy_zakazow = None
        self.typy_sing = None
        self.typy_graniczne = ('0x4b',)
        self.naglowek_mapy = []
        self.poi_drogi_poly = list()
        self.restrykcje_znaki = list()
        self.poi_do_usuniecia = list()
        self.poi_dla_slepych = list()
        self.nody_graniczne = set()
        self.wczytaj_konfiguracje(netgen_cfg)

    def wczytaj_konfiguracje(self, netgen_cfg):
        with open(netgen_cfg, 'r') as netgen_conf_plik:
            zawartosc_netgen_cfg = netgen_conf_plik.readlines()
        for linijka in zawartosc_netgen_cfg:
            if linijka.startswith('Type'):
                typ, param = linijka.split('=', 1)
                self.typy_routingowe.append(typ[3:])
                parametry = param.split(',')
                self.parametry_routingu[typ[3:]] = {'predkosc': parametry[0], 'klasa': parametry[1]}
            elif linijka.startswith('Restriction'):
                self.typy_zakazow = linijka.split('=',1)[1]
            elif linijka_startswith('RoadSign'):
                self.typy_sign = linijka.split('=', 1)[1]
            elif linijka.startswith('Removed') or linijka.startswith('RoadEnd'):
                start, end = linijka.split('=', 1)[1].split('-', 1)
                for a in range(int(start, 0), int(end, 0)):
                    self.poi_do_usuniecia.append(hex(a))


    def dodaj_obiekt_mapy(self, obiekt_mapy):
        if obiekt_mapy.typ_obiektu == 'poi':
            if obiekt_mapy.type not in self.poi_do_usuniecia:
                self.poi_drogi_poly.append(obiekt_mapy)
        elif obiekt_mapy.typ_obiektu == 'polygone':
            self.poi_drogi_poly.append(obiekt_mapy)
        else:
            if obiekt_mapy.type in self.typy_graniczne:
                self.dodaj_nody_do_nodow_granicznych(obiekt_mapy.data0)
            else:
                if obiekt_mapy.type in self.typy_routingowe:
                    for tmp_obj in self.zwroc_obiekt_niezapetlony(obiekt_na_mapie):
                        tmp_obj.ustaw_roadid(self.pierwsze_wolne_road_id)
                        self.pierwsze_wolne_road_id += 1
                elif obiekt_mapy.type in self.typy_zakazow:
                    pass
                elif obiekt_mapy.type in self.typy_sign:
                    pass
                self.poi_drogi_poly.append(obiekt_mapy)

    def dodaj_nody_do_nodow_granicznych(self, nody_graniczne):
        for nod_graniczny in nody_graniczne:
            self.nody_graniczne.add(nod_graniczny)

    def zwroc_obiekt_niezapetlony(self, obiekt_na_mapie):
        if obiekt_na_mapie.czy_jestem_zapetlony():
            tmp_obiekt = []
            for nowe_wspolrzedne in obiekt_na_mapie.odpetlone_wspolrzedne():
                tmp_obiekt.append(obiekt_na_mapie.ustaw_odpetlone_wsp(nowe_wspolrzedne))
            return tmp_obiekt
        return [obiekt_na_mapie]


def dodaj_dane_routingowe(nazwa_pliku):
    # wczytujemy mape
    with open(nazwa_pliku, 'r') as plik:
        zawartosc_pliku_mp = plik.readlines()
    dane_mapy = MapaMp()
    # najpierw wczytajmy naglowek, potem zajmiemy sie reszta
    for linia, numer in enumerate(zawartosc_pliku_mp):
        dane_mapy.naglowek_mapy.append(linia)
        if linia.startswith('[END-IMG ID]'):
            break
    rekord_danych = list()
    for linia in zawartosc_pliku_mp[numer:]:
        rekord_danych.append(linia)
        if linia.startswith('[END]'):
            dane_mapy.dodaj_obiekt_mapy(ObiektMapy(rekord_danych))
            rekord_danych = []



