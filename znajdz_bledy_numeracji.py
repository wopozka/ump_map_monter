#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import timeit
from collections import defaultdict, deque, namedtuple
import os.path


class ZbioryRozlaczne(object):
    """Union-Find (DSU) z kompresja sciezek i laczeniem po rozmiarze.

    znajdz() na elemencie, ktory nigdy nie bral udzialu w polacz/polacz_wszystkie,
    zwraca go bez zadnych efektow ubocznych (nie rejestruje go) - dzieki temu
    mozna bezpiecznie sprawdzic, czy dwa wezly naleza juz do tego samego zbioru,
    bez ryzyka przypadkowego zarejestrowania jednego z nich jako nowy,
    sztuczny zbior jednoelementowy."""

    def __init__(self):
        self.rodzic = {}
        self.rozmiar = {}

    def znajdz(self, x):
        if x not in self.rodzic:
            return x
        korzen = x
        while self.rodzic[korzen] != korzen:
            korzen = self.rodzic[korzen]
        while self.rodzic[x] != korzen:
            self.rodzic[x], x = korzen, self.rodzic[x]
        return korzen

    def polacz(self, x, y):
        self.rodzic.setdefault(x, x)
        self.rodzic.setdefault(y, y)
        rx, ry = self.znajdz(x), self.znajdz(y)
        if rx == ry:
            return
        if self.rozmiar.get(rx, 1) < self.rozmiar.get(ry, 1):
            rx, ry = ry, rx
        self.rodzic[ry] = rx
        self.rozmiar[rx] = self.rozmiar.get(rx, 1) + self.rozmiar.get(ry, 1)

    def polacz_wszystkie(self, elementy):
        elementy = list(elementy)
        if not elementy:
            return
        pierwszy = elementy[0]
        self.rodzic.setdefault(pierwszy, pierwszy)
        for element in elementy[1:]:
            self.polacz(pierwszy, element)

    def grupy(self):
        wynik = defaultdict(set)
        for element in self.rodzic:
            wynik[self.znajdz(element)].add(element)
        return wynik


def wierzcholki_nieosiagalne(wierzcholki, sasiedzi):
    """Dla kazdego wierzcholka-zrodla zwraca pary (skad, dokad), do ktorych nie
    da sie dojechac zgodnie z kierunkiem krawedzi. Zwykly BFS (O(V+E) na
    zrodlo) - krawedzie maja jednostkowa wage, wiec liczenie najkrotszych
    sciezek Bellmanem-Fordem (O(V*E) na zrodlo) nie jest tu potrzebne."""
    nieosiagalne = []
    for src in wierzcholki:
        odwiedzone = {src}
        kolejka = deque([src])
        while kolejka:
            aktualny = kolejka.popleft()
            for sasiad in sasiedzi.get(aktualny, ()):
                if sasiad not in odwiedzone:
                    odwiedzone.add(sasiad)
                    kolejka.append(sasiad)
        for dokad in wierzcholki:
            if dokad not in odwiedzone:
                nieosiagalne.append((src, dokad))
    return nieosiagalne


class Mapa(object):
    def __init__(self, nazwapliku, stderr_stdout_writer, mode):
        typyRoutingowe = ('0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7', '0x8', '0x9', '0xa', '0xb',
                          '0xc', '0x16', '0x19', '0xd', '0xe', '0xf', '0x2f', '0x1a', '0x117')
        typLiniiGranicznej = ('0x4b',)
        typy_zakazow = ('0x19', '0x2f')
        typy_nieroutingowe_dla_jednokierunkowych = ('0x16', '0xd')
        self.roadid_nieroutingowe_dla_jednokierunkowych = set()
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            encoding = 'latin2'
        else:
            encoding = 'cp1250'
        self.WszystkieNody = defaultdict(lambda: Node())
        self.nazwaplikudlaoutput = os.path.splitext(nazwapliku)[0] + 'ciaglosc_routingu.txt'
        self.NodyDoSprawdzenia = []
        self.NodyDrogi = []
        self.WezlyDoSprawdzenia = []
        self.WezlyDoOdrzucenia = []
        self.stderr_stdout_writer = stderr_stdout_writer
        self.mode = mode
        self.RoadId = -1
        self.Zakazy = defaultdict(lambda: Zakaz(self.stderr_stdout_writer))
        self.Drogi = dict()
        self.DrogiJednokierunkowe = []
        # poniższe pomaga wyszukiwać dróg jednokierunkowych bez wjazdu albo bez wyjazdu
        self.SkrajneNodyDrogJednokierunkowych = list()
        # lista nodow granicznych, potrzebne do określenia czy jednokierunkowa ślepa czy nie
        self.NodyGraniczne = list()

        try:
            with open(nazwapliku, encoding=encoding, errors='ignore') as f:
                zawartoscpliku = f.read()
        except FileNotFoundError:
            self.stderr_stdout_writer.stderrorwrite('Nie mogę znaleźć pliku!')
        except PermissionError:
            self.stderr_stdout_writer.stderrorwrite('ME zapisuje plik. Uruchom sprawdzanie jeszcze raz!')
        else:
            # iteruję po rekordach pliku mp.
            for rekord_pliku_mp in zawartoscpliku.split('[END]\n'):
                if '[POLYLINE]' not in rekord_pliku_mp:
                    continue
                # usuwamy POLYLINE
                rekord_pliku_mp = rekord_pliku_mp.strip().split('[POLYLINE]')[1]
                my_type = rekord_pliku_mp.split('Type=')[-1].split('\n', 1)[0].strip()
                if my_type in typyRoutingowe:
                    # my_type = a.split('Type=')[-1].split('\n', 1)[0].strip(P)
                    del self.WezlyDoSprawdzenia[:]
                    del self.NodyDrogi[:]
                    del self.WezlyDoOdrzucenia[:]
                    uwzglednij_numeracje = 1
                    # self.RoadId += 1
                    # sprawdzamy czy mamy znacznik drogi jednokierunkowej
                    DirIndicator = 0
                    if rekord_pliku_mp.find('DirIndicator=1') >= 0:
                        DirIndicator = 1
                    # wydzielamy Data0
                    rekord_pliku_mp = rekord_pliku_mp.split('Data0=')[-1]
                    try:
                        Data0, rekord_pliku_mp = rekord_pliku_mp.split('\n', 1)
                    except ValueError:
                        # w przypadku gdy jest to koniec pliku i po Data nie ma już nic,
                        # droga nieprzypisana do pliku
                        Data0 = rekord_pliku_mp
                    # nody_tmp = Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),(')

                    # jesli to zakaz to nie sprawdzaj zapetlenia
                    if my_type not in typy_zakazow:
                        nody_tmp = self.sprawdzzapetlenie(
                            Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),('))
                        # gdy droga zapętlona nie sprawdzaj numeracji, robi to netgen i raportuje odpowiednio
                        if len(nody_tmp) > 1:
                            uwzglednij_numeracje = 0
                    else:
                        nody_tmp = [Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),(')]

                    # poniewaz droga moze byc zapetlona, wtedy po rozpetleniu mamy dwa Data0 dla danej drogi
                    # z tego powodu iterujemy po liscie nodytmp
                    for punkty_drogi in nody_tmp:
                        self.RoadId += 1
                        # jeśli droga jednokierunkowa dodaj ja do listy drog do sprawdzenia. roadid bedzie nam
                        # potrzebne, dlatego dodajemy slownik
                        if DirIndicator and my_type not in typy_zakazow:
                            self.SkrajneNodyDrogJednokierunkowych.append({'roadid': self.RoadId,
                                                                          'poczatek': punkty_drogi[0],
                                                                          'koniec': punkty_drogi[-1]
                                                                          }
                                                                         )
                        # kolejnyNrNoda = 0
                        nodyskrajne = (punkty_drogi[0], punkty_drogi[-1])
                        for kolejnyNrNoda, para_wspolrzednych in enumerate(punkty_drogi):
                            if my_type in typy_zakazow:
                                self.Zakazy[self.RoadId].Nody.append(para_wspolrzednych)
                                continue
                            # jednokierunkowe nie powinny sie zaczynac ani konczyc na sciezkach i drogach
                            # rowerowych, robimy wiec liste roadid dla sciezek i drog rowerowych aby sprawdzic
                            # pozniej czy takie skrzyzowanie wystepuje
                            if my_type in typy_nieroutingowe_dla_jednokierunkowych:
                                self.roadid_nieroutingowe_dla_jednokierunkowych.add(self.RoadId)
                            self.WszystkieNody[para_wspolrzednych].dodaj_node(self.RoadId, kolejnyNrNoda, DirIndicator)
                            self.NodyDrogi.append(para_wspolrzednych)
                            if para_wspolrzednych in nodyskrajne:
                                self.WszystkieNody[para_wspolrzednych].wezelRoutingowy += 1
                        if my_type not in typy_zakazow:
                            self.Drogi[self.RoadId] = self.NodyDrogi[:]
                            if DirIndicator:
                                self.DrogiJednokierunkowe.append(self.RoadId)

                        # teraz czas sprawdzic czy droga nie byla zapetlona, jesli tak to dzialamy
                        # zapetlenie = (self.sprawdzzapetlenie(self.NodyDrogi))
                        # if len(zapetlenie)>1:
                        #   print('zapetlenie:',zapetlenie)

                    for tmpbbb in rekord_pliku_mp.split('\n'):
                        if tmpbbb.startswith('Numbers') and not tmpbbb.startswith('NumbersExt') and \
                                uwzglednij_numeracje and not self.mode:
                            # print(tmpbbb)
                            Numery = tmpbbb.split('=')[-1].split(',')
                            # print(Numery)
                            # zapisujemy numery wezlow aby pozniej sprawdzic czy routingowe
                            if Numery[1] == 'N' and Numery[4] == 'N':
                                self.WezlyDoOdrzucenia.append(int(Numery[0]))
                            self.WezlyDoSprawdzenia.append(int(Numery[0]))
                            # sprawdzamy poprawnosc danych
                            parzystosc = self.sprawdzParzystosc(tuple(Numery))
                            if parzystosc:
                                for error_msg in parzystosc:
                                    self.stderr_stdout_writer.stderrorwrite(
                                        '%s przy %s' % (error_msg, self.NodyDrogi[int(Numery[0])]))
                            del Numery[:]

                    # przypadek gdy ostatni segment jest ponumerowany, wtedy ostatni węzeł nie dostaje nic. Trzeba
                    # wtedy sprawdzić co jest pomiędzy. Taki przypadek będzie gdy ostatni węzeł z numerami będzie
                    # będzie zawierał coś innego niż -1,-1 czyli będzie na liście węzłów do sprawdzenia, ale
                    # nie będzie na liście węzłów do wyrzucenia

                    if self.WezlyDoSprawdzenia and self.WezlyDoSprawdzenia[-1] not in self.WezlyDoOdrzucenia:
                        self.WezlyDoSprawdzenia.append(len(self.NodyDrogi)-1)

                    for current, my_next in zip(self.WezlyDoSprawdzenia, self.WezlyDoSprawdzenia[1:]):
                        if current + 1 == my_next:
                            pass
                        elif current in self.WezlyDoOdrzucenia:
                            pass
                        else:
                            # print(current)
                            punkty_drogi = current + 1
                            while punkty_drogi < my_next:
                                # if tmpccc not in self.WezlyDoOdrzucenia:
                                # print(punkty_drogi, len(self.NodyDrogi), my_type)
                                self.NodyDoSprawdzenia.append(self.NodyDrogi[punkty_drogi])
                                # print(self.NodyDoSprawdzenia)
                                punkty_drogi += 1

                    # no i czyścimy liste wezłów do sprawdzenia dla danej drogi, oraz nody drogi
                elif my_type in typLiniiGranicznej:
                    rekord_pliku_mp = rekord_pliku_mp.split('Data0=')[-1]
                    try:
                        Data0, rekord_pliku_mp = rekord_pliku_mp.split('\n', 1)
                    except ValueError:
                        # w przypadku gdy jest to koniec pliku i po Data nie ma już nic,
                        # droga nieprzypisana do pliku
                        Data0 = rekord_pliku_mp
                    for para_wspolrzednych in Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),('):
                        self.NodyGraniczne.append(para_wspolrzednych)
                        # dodajemy też z dokładnością 6 cyfr, bo Wrocław tak ma
                        dlugosc, szerokosc = para_wspolrzednych.split(',')
                        self.NodyGraniczne.append(dlugosc + '0' + ',' + szerokosc + '0')

            # obrabiamy zakazy iterujemy po RoadID zakazow
            if not self.mode:
                self.ustaw_wezly_zakazow_jako_routingowe()
                self.ustaw_from_via_to_dla_zakazow()
                self.sprawdzCzyRoutingowe()

            # obrabiamy ślepe jednokierunkowe
            if not self.mode:
                self.sprawdz_jednokierunkowe_slepe()

            if self.mode:
                if self.mode == 'sprawdz_siatke_dwukierunkowa':
                    self.sprawdzNieciaglosciSiatkiRoutingowej()
                elif self.mode == 'sprawdz_siatke_jednokierunkowa':
                    self.sprawdzNieciaglosciSiatkiRoutingowejUwzglednijJednokierunkowosc()

    @staticmethod
    def zwroc_rekordy_pliku_mp(zawartosc_pliku):
        typy_routingowe = {'0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7', '0x8', '0x9', '0xa', '0xb',
                           '0xc', '0x16', '0xd', '0xe', '0xf', '0x1a', '0x117'}
        typ_linii_granicznej = {'0x4b'}
        typy_zakazow_drogowskazow = {'0x19', '0x2f'}
        drogi, zakazy, granice = [], [], []
        token = ''
        num_rekordu = 0
        rekord_pliku_mp = dict()
        for tmp_linia in zawartosc_pliku:
            linia = tmp_linia.strip()
            if linia == '[POLYLINE]':
                # gdy nie zamknelismy POLYLINE slowem kluczowy END, wtedy olej wszystko co do tej pory zapisales
                if token:
                    rekord_pliku_mp.clear()
                token = 'in polyline'
                continue
            elif linia in ('[POLYGONE]', '[POI]'):
                # gdy nie zamknelismy POLYLINE slowem kluczowy END, wtedy olej wszystko co do tej pory zapisales
                if token:
                    rekord_pliku_mp.clear()
                token = ''
                continue
            elif token and linia == '[END]':
                if rekord_pliku_mp and 'Type' in rekord_pliku_mp:
                    if rekord_pliku_mp['Type'] in typy_routingowe:
                        drogi.append(rekord_pliku_mp)
                    elif rekord_pliku_mp['Type'] in typy_zakazow_drogowskazow:
                        zakazy.append(rekord_pliku_mp)
                    elif rekord_pliku_mp['Type'] in typ_linii_granicznej:
                        granice.append(rekord_pliku_mp)
                rekord_pliku_mp = dict()
                token = ''
                continue
            if token:
                if '=' not in linia:
                    continue
                klucz, wartosc = linia.split('=', 1)
                if klucz.startswith('Type'):
                    rekord_pliku_mp[klucz] = wartosc
                elif klucz.startswith('Numbers') and not klucz.startswith('NumbersExt'):
                    rekord_pliku_mp[klucz] = wartosc
                elif klucz.startswith('Data0'):
                    rekord_pliku_mp[klucz] = wartosc
                else:
                    continue
        return drogi, zakazy, granice


    def ustaw_wezly_zakazow_jako_routingowe(self):
        for zakaz_id in self.Zakazy:
            for tmpbbb in self.Zakazy[zakaz_id].Nody:
                if self.Zakazy[zakaz_id] is None:
                    continue
                if tmpbbb in self.WszystkieNody:
                    self.WszystkieNody[tmpbbb].wezelRoutingowy += 1
                    self.Zakazy[zakaz_id].Nodes.append(self.WszystkieNody[tmpbbb])
                else:
                    self.stderr_stdout_writer.stderrorwrite('Błąd zakazu! Węzeł bez drogi ' + tmpbbb)
                    self.Zakazy[zakaz_id].Nodes.append(None)
                    # ten zakaz już ma wyświetlony błąd, nie sprawdzaj go ponownie
                    self.Zakazy[zakaz_id] = None

    def ustaw_from_via_to_dla_zakazow(self):
        for zakaz_id in self.Zakazy:
            if self.Zakazy[zakaz_id] is None:
                continue
            elif not 3 <= len(self.Zakazy[zakaz_id].Nody) <= 4:
                self.stderr_stdout_writer.stderrorwrite('Błąd zakazu!\nZakaz może mieć tylko 3 lub 4 węzły a ma '
                                                        '%s : %s %s' % (len(self.Zakazy[zakaz_id].Nody),
                                                                        self.Zakazy[zakaz_id].Nody[0],
                                                                        self.Zakazy[zakaz_id].Nody[1]))
                continue
            else:
                self.Zakazy[zakaz_id].ustawFromViaTo1(self.WszystkieNody, self.Drogi)

    def sprawdz_jednokierunkowe_slepe(self):
        for droga in self.SkrajneNodyDrogJednokierunkowych:
            for para_wspolrzednych in (droga['poczatek'], droga['koniec']):
                if para_wspolrzednych in self.NodyGraniczne:
                    continue
                if droga['roadid'] in self.roadid_nieroutingowe_dla_jednokierunkowych:
                    if len(self.WszystkieNody[para_wspolrzednych].RoadIds) < 2:
                        self.stderr_stdout_writer.stderrorwrite('Jednokierunkowa ślepa: ' + para_wspolrzednych)
                else:
                    if len([_id_ for _id_ in self.WszystkieNody[para_wspolrzednych].RoadIds
                            if _id_ not in self.roadid_nieroutingowe_dla_jednokierunkowych]) < 2:
                        self.stderr_stdout_writer.stderrorwrite('Jednokierunkowa ślepa: ' + para_wspolrzednych)


    def sprawdzNieciaglosciSiatkiRoutingowej(self):
        # laczymy w DSU wezly routingowe kazdej drogi - drogi dzielace wspolny
        # wezel routingowy trafiaja do tego samego zbioru (skladowej spojnej)
        dsu = ZbioryRozlaczne()
        nodyGranicznetmp = set(a for a in self.NodyGraniczne if a in self.WszystkieNody)
        dsu.polacz_wszystkie(nodyGranicznetmp)
        for tmpaaa in self.Drogi:
            dsu.polacz_wszystkie(c for c in self.Drogi[tmpaaa] if self.WszystkieNody[c].wezelRoutingowy)
        print('analizuje %s drog' % (len(self.Drogi) + 1))

        timer_start = timeit.default_timer()
        grupy = dsu.grupy()
        # wezly graniczne wyznaczaja "glowna" siatke - jej nie raportujemy jako
        # oddzielny/rozlaczny graf; gdy w pliku nie ma wezlow granicznych, za
        # glowna przyjmujemy najwieksza ze znalezionych skladowych
        if nodyGranicznetmp:
            glowna_grupa = dsu.znajdz(next(iter(nodyGranicznetmp)))
        elif grupy:
            glowna_grupa = max(grupy, key=lambda korzen: len(grupy[korzen]))
        else:
            glowna_grupa = None
        oddzielnegrafy = ([grupy[glowna_grupa]] if glowna_grupa is not None else []) + \
            [zbior for korzen, zbior in grupy.items() if korzen != glowna_grupa]

        print()
        print('czas wykonania %s' % (timeit.default_timer() - timer_start))
        if len(oddzielnegrafy) > 1:
            for a in range(1, len(oddzielnegrafy)):
                print(str(oddzielnegrafy[a]))

    def sprawdzNieciaglosciSiatkiRoutingowejUwzglednijJednokierunkowosc(self):
        # 2-kierunkowe drogi (i samo-zapetlone jednokierunkowe) laczymy w DSU -
        # dajac skladowe spojne, do ktorych da sie dojechac i wyjechac w obie strony
        dsu = ZbioryRozlaczne()
        nodyGranicznetmp = set(a for a in self.NodyGraniczne if a in self.WszystkieNody)
        dsu.polacz_wszystkie(nodyGranicznetmp)

        drogi_kierunkowe = []
        for tmpaaa in self.Drogi:
            nody_routingowe = [c for c in self.Drogi[tmpaaa] if self.WszystkieNody[c].wezelRoutingowy]
            if tmpaaa in self.DrogiJednokierunkowe and nody_routingowe and nody_routingowe[0] != nody_routingowe[-1]:
                drogi_kierunkowe.append(nody_routingowe)
            else:
                dsu.polacz_wszystkie(nody_routingowe)

        # jednokierunkowa zaczynajaca i konczaca sie w tym samym, juz polaczonym
        # zbiorze jest z nim osiagalna w obie strony (dojedziemy do jej poczatku,
        # a z konca da sie do niego wrocic) - dolaczamy jej wezly do tego zbioru,
        # zamiast opisywac ja jako oddzielna krawedz skierowana
        pozostale_drogi_kierunkowe = []
        for droga in drogi_kierunkowe:
            if dsu.znajdz(droga[0]) == dsu.znajdz(droga[-1]):
                dsu.polacz_wszystkie(droga)
            else:
                pozostale_drogi_kierunkowe.append(droga)
        drogi_kierunkowe = pozostale_drogi_kierunkowe

        grupy = dsu.grupy()
        korzenie = list(grupy.keys())
        oddzielnegrafy = [grupy[korzen] for korzen in korzenie]
        korzen_do_indeksu = {korzen: i for i, korzen in enumerate(korzenie)}
        print('analizuje %s drog' % len(oddzielnegrafy))

        def indeks_komponentu(node):
            korzen = dsu.znajdz(node)
            if korzen in korzen_do_indeksu:
                return str(korzen_do_indeksu[korzen])
            return node

        print('Redukuje drogi jednokierunkowe')
        print(len(drogi_kierunkowe))

        # laczymy skierowane odcinki miedzy skladowymi (albo pojedynczymi wezlami
        # poza siatka dwukierunkowa) w krawedzie grafu skierowanego. Osiagalnosc
        # miedzy skladowymi/wezlami - w tym w obie strony, gdy istnieja krawedzie
        # A->B i B->A - sprawdza pozniej wieloskokowy BFS w wierzcholki_nieosiagalne(),
        # wiec scalanie wzajemnie polaczonych par w jeden wezel nie zmienia wyniku
        # i nie jest tu potrzebne
        paryJednokierunkoweBezGrafu = set()
        polaczeniaPomiedzyGrafami = set()
        print('sprawdzam polaczenia jednokierunkowe miedzy grafami')
        timer_start = timeit.default_timer()
        for aaa in drogi_kierunkowe:
            for bbb in range(0, len(aaa) - 1):
                n = indeks_komponentu(aaa[bbb])
                n_plus_1 = indeks_komponentu(aaa[bbb + 1])
                if n == n_plus_1:
                    continue
                elif n.isdigit() and n_plus_1.isdigit():
                    polaczeniaPomiedzyGrafami.add((n, n_plus_1))
                else:
                    paryJednokierunkoweBezGrafu.add((n, n_plus_1))

        polaczeniaPomiedzyGrafami = sorted(polaczeniaPomiedzyGrafami)
        paryJednokierunkoweBezGrafu = sorted(paryJednokierunkoweBezGrafu)
        print(polaczeniaPomiedzyGrafami)
        print(paryJednokierunkoweBezGrafu)
        print(len(polaczeniaPomiedzyGrafami))
        print(len(paryJednokierunkoweBezGrafu))

        print()
        print('czas wykonania %s' % (timeit.default_timer() - timer_start))

        wierzcholkiGrafu = []
        print('Buduje wierzcholki grafu')
        for tmpaaa in range(0, len(oddzielnegrafy)):
            if oddzielnegrafy[tmpaaa]:
                wierzcholkiGrafu.append(str(tmpaaa))
        for tmpaaa in polaczeniaPomiedzyGrafami:
            if tmpaaa[0] not in wierzcholkiGrafu:
                wierzcholkiGrafu.append(tmpaaa[0])
            if tmpaaa[1] not in wierzcholkiGrafu:
                wierzcholkiGrafu.append(tmpaaa[1])
        for tmpaaa in paryJednokierunkoweBezGrafu:
            if tmpaaa[0] not in wierzcholkiGrafu:
                wierzcholkiGrafu.append(tmpaaa[0])
            if tmpaaa[1] not in wierzcholkiGrafu:
                wierzcholkiGrafu.append(tmpaaa[1])
        print(wierzcholkiGrafu)

        sasiedzi = defaultdict(list)
        for tmpaaa in polaczeniaPomiedzyGrafami:
            sasiedzi[tmpaaa[0]].append(tmpaaa[1])
        for tmpaaa in paryJednokierunkoweBezGrafu:
            sasiedzi[tmpaaa[0]].append(tmpaaa[1])

        print('spradzam polaczenia')
        timer_start = timeit.default_timer()

        def opisz_wierzcholek(nazwa):
            if not nazwa.isdigit():
                return nazwa
            indeks = int(nazwa)
            if indeks >= len(oddzielnegrafy) or not oddzielnegrafy[indeks]:
                return nazwa
            return nazwa + '(' + next(iter(oddzielnegrafy[indeks])) + ')'

        with open(self.nazwaplikudlaoutput, 'w') as file:
            for skad, dokad in wierzcholki_nieosiagalne(wierzcholkiGrafu, sasiedzi):
                linia = opisz_wierzcholek(skad) + '->' + opisz_wierzcholek(dokad) + ' brak polaczenia'
                print(linia)
                file.write(linia + '\n')

        print('czas wykonania %s' % (timeit.default_timer() - timer_start))
        print('Utworzono plik %s.' % self.nazwaplikudlaoutput)

    def sprawdzzapetlenie(self, nodydrogi):
        """ funkcja sprawdza czy droga nie jest ze sobą zapętlona, jeśli jest, to wtedy dzieli ją na pół aż rozpętli"""
        # nodydrogi to zmienna przechowująca pary współrzędnych danej drogi np.:
        # '51.79507,19.45560', '51.79538,19.45566', '51.79529,19.45543'
        # wyszukujemy nody podwojne
        nodypodwojne = [a for a in nodydrogi if nodydrogi.count(a) > 1]
        # print('nodypodwojne',  nodypodwojne)
        for a in nodypodwojne:
            if a == nodydrogi[(nodydrogi.index(a)+1)]:
                self.stderr_stdout_writer.stderrorwrite("Zdublowane punkty drogi " + a + "\npomijam sprawdzanie.")
                return [nodydrogi]
            
        # print(nodypodwojne)
        if not nodypodwojne:
            return [nodydrogi]
        else:
            # no to mamy zapętlenie, trzeba obsłużyć, zakładam że nikt nie będzie plątał w nieskończoność
            # idea jest taka. Dzielimy na pół, sprawdzamy czy nadal zapętlone, jeśli tak to ten z zapętleniem
            # dzielimy dalej na pół itd
            a = self.sprawdzzapetlenie(nodydrogi[:len(nodydrogi) // 2 + 1])
            if len(a) > 1:
                c = [a[0], a[1]]
            else:
                c = [a[0]]
            # print(c)
            b = self.sprawdzzapetlenie(nodydrogi[len(nodydrogi) // 2:])
            if len(b) > 1:
                c.append(b[0])
                c.append(b[1])
            else:
                c.append(b[0])
            # print(c)
            return c

    def sprawdzCzyRoutingowe(self):
        for a in self.NodyDoSprawdzenia:
            if self.WszystkieNody[a].wezelRoutingowy:
                # print('Brakujący węzeł w %s'%a)
                self.stderr_stdout_writer.stderrorwrite('Numeracja-brakujący węzeł w %s' % a)

    @staticmethod
    def sprawdzParzystosc(Numery):
        # sprawdzamy czy sa poprawnie zefiniowane konce numeraji oraz czy jest poprawna parzystosc liczb, tzn
        # dla O start i koniec powinien byc nieparzysty, dla E start i koniec powinien byc parzysty
        returnVal = []
        for kol_num in (1, 4):
            # jesli nie ma zdefiniowanej numeracji to idz do nastepnego rekordu
            if Numery[kol_num] == 'N':
                continue
            liczba1 = int(Numery[kol_num + 1])
            liczba2 = int(Numery[kol_num + 2])
            if liczba1 <= 0 or liczba2 <= 0:
                returnVal.append('Numeracja-niezdefiniowany koniec (' + Numery[kol_num] + ',' + (Numery[kol_num + 1]) +
                                 ',' + (Numery[kol_num + 2]) + ')')
            # jesli numeracja jest both nie sprawdzaj parzystosci tylko kontynuuj
            if Numery[kol_num] == 'B':
                continue
            parzystosc = 1 if Numery[kol_num] == 'O' else 0
            if liczba1 % 2 != parzystosc or liczba2 % 2 != parzystosc:
                returnVal.append('Numeracja-nieprawidłowa parzystość (' + (Numery[kol_num]) + ',' +
                                 (Numery[kol_num + 1]) + ',' + (Numery[kol_num + 2]) + ')')
        return returnVal


# nazwa klasy mylaca ale niech bedzie
class Node(object):
    def __init__(self):
        # poniewaz node jest tworzone w defaultdict, a dodaj_node podbija o jeden, trzeba ustawic wartosc -1
        # aby nody nierutingowe mialy wartosc 0.
        self.wezelRoutingowy = -1
        # id drogi. Jesli takie samo oznacza to ze wezly naleza do jednej linii
        self.RoadIds = list()
        # kolejny nr wezla dla danej drogi - slownik gdzie kluczem jest roadid, a wartoscia to tupla nr wezla
        # kierunkowosc (0 brak, 1 jednokierunkowa). jesli bedzie kilka drog to bedzie tez kilka numerow id
        # self.numerParyWspDlaDanejDrogi = {RoadId: (kolejny_nr_noda, dirindicator)}
        self.no_wsplrzednej_kierunkowosc_w_data0 = dict()

    def dodaj_node(self, RoadId, kolejny_nr_noda, dir_indicator):
        self.wezelRoutingowy += 1
        self.RoadIds.append(RoadId)
        self.no_wsplrzednej_kierunkowosc_w_data0[RoadId] = (kolejny_nr_noda, dir_indicator)
        return

    def czy_jednokierunkowa(self, road_id):
        return self.no_wsplrzednej_kierunkowosc_w_data0[road_id][1]

    def num_wsp_w_data(self, road_id):
        return self.no_wsplrzednej_kierunkowosc_w_data0[road_id][0]


class Zakaz(object):
    def __init__(self, stderr_stdout_writer):
        self.stderr_stdout_writer = stderr_stdout_writer
        # zmienna zawierajaca Nody zakazu w postaci pary wspolrzednych
        self.Nody = []
        self.FromRoadId = []
        self.ViaRoadId = []
        self.ToRoadId = []
        self.Nodes = []

    def sprawdz_czy_pomiedzy_sa_wezly_routingowe(self, Drogi, WszystkieNody, lRoadId, lNody):
        # WszystkieNody to slownik: klucz to para wsp, wartosc to obiekt typu Node
        # Drogi to slownik roadid jako klucz a wartosc to wszystkie nody danej drogi
        # lRoadID lista RoadID dla danego wezla - moze byc tam kilka drog 
        # lNody 2 nody okreslajace czesc zakazu, moze to byc from moze to byc via moze to byc to
        indeksA = Drogi[lRoadId].index(lNody[0])
        indeksB = Drogi[lRoadId].index(lNody[1])
        # probujemy to samo tylko lekko inaczej, kazdy obiekt Node zawiera w sobie informacje
        # o drogach ktorych czescia jest oraz o ktorym z kolei wezelem tej drogi jest
        # moze uda sie wiec pozbyc Drogi
        # tmpIndeksA = WszystkieNody[lNody[0]].numerParyWspDlaDanejDrogi[lRoadId][0]
        # tmpIndeksB = WszystkieNody[lNody[1]].numerParyWspDlaDanejDrogi[lRoadId][0]

        step = 1 if indeksA < indeksB else -1
        for abcde in range(indeksA + step, indeksB, step):
            wspolrzedna = Drogi[lRoadId][abcde]
            if WszystkieNody[wspolrzedna].wezelRoutingowy:
                self.stderr_stdout_writer.stderrorwrite('Błąd zakazu. Pomiędzy węzłami %s, %s\n' % (lNody[0], lNody[1]))
                self.stderr_stdout_writer.stderrorwrite('istnieje węzeł routingowy %s.' % wspolrzedna)

    def ustawFromViaTo1(self, wszystkie_nody, drogi):
        # WszystkieNody to slownik: klucz to para wsp, wartosc to obiekt typu Node
        # Drogi to slownik roadid jako klucz a wartosc to wszystkie nody danej drogi
        from_via_to = {'FromRoadId': [], 'ViaRoadId': [], 'ToRoadId': []}
        elementy_zakazu = ('FromRoadId', 'ViaRoadId', 'ToRoadId') if len(self.Nody) == 4 else ('FromRoadId', 'ToRoadId')

        for numer, from_via_to_item in enumerate(elementy_zakazu):
            if self.Nody[numer] in wszystkie_nody and self.Nody[numer + 1] in wszystkie_nody:
                for abcd in wszystkie_nody[self.Nody[numer]].RoadIds:
                    from_via_to[from_via_to_item].append(abcd)
                for abcd in wszystkie_nody[self.Nody[numer + 1]].RoadIds:
                    from_via_to[from_via_to_item].append(abcd)
                from_via_to[from_via_to_item] = list(set(a for a in from_via_to[from_via_to_item] if
                                                         from_via_to[from_via_to_item].count(a) > 1))
                # gdy nie ma chociaz 1 drogi laczacej dwa wezly zakazu wtedy self.FromRoadId bedzie puste
                if from_via_to[from_via_to_item]:
                    # sprawdzamy czy nody drogi From nie są rozdzielone wezłem routingowym
                    self.sprawdz_czy_pomiedzy_sa_wezly_routingowe(drogi, wszystkie_nody,
                                                                  from_via_to[from_via_to_item][0],
                                                                  self.Nody[numer:numer + 2])

        self.FromRoadId, self.ViaRoadId, self.ToRoadId = from_via_to['FromRoadId'], from_via_to['ViaRoadId'], \
                                                         from_via_to['ToRoadId']
        self.sprawdz_zakaz1()

    def sprawdz_zakaz1(self):
        # zakaz musi mieć przynajmniej 3 a maksymalnie 4 punkty, pozostale przypadki do blad
        from_via_to = (self.FromRoadId, self.ViaRoadId, self.ToRoadId) if len(self.Nody) == 4 else \
            (self.FromRoadId, self.ToRoadId)
        for numer, from_via_to_item in enumerate(from_via_to):
            a = len(from_via_to_item)
            if a == 0:
                self.stderr_stdout_writer.stderrorwrite(
                    'Błąd zakazu!\nBrak pojedynczej drogi łączącej węzły: %s %s ' %
                    (self.Nody[numer], self.Nody[numer + 1]))
            elif a > 1:
                self.stderr_stdout_writer.stderrorwrite(
                    'Błąd zakazu! %s drogi łączą węzły: %s %s ' % (a, self.Nody[numer], self.Nody[numer + 1]))
            else:
                if self.Nodes[numer].czy_jednokierunkowa(from_via_to_item[0]):
                    if self.Nodes[numer].num_wsp_w_data(from_via_to_item[0]) > \
                            self.Nodes[numer + 1].num_wsp_w_data(from_via_to_item[0]):
                        self.stderr_stdout_writer.stderrorwrite(
                            'Błąd zakazu! Zakaz dodany pod prąd: %s %s ' % (self.Nody[numer], self.Nody[numer + 1]))


def main(argumenty, stderr_stdout_writer, mode):
    mapa = Mapa(argumenty, stderr_stdout_writer, mode)


if __name__ == "__main__":
    print('Używaj z mont_demont.py')
