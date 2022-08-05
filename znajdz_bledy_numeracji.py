#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import timeit
from collections import defaultdict
from multiprocessing import Pool
from multiprocessing import Queue
from multiprocessing import cpu_count
import time

def update_progress(progress):
    barLength=20
    status=''
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
    text = "\rProcent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), int(progress*100), status)
    sys.stdout.write(text)
    sys.stdout.flush()

#Class to represent a graph
class Graph(object):

    def __init__(self,vertices):
        self.vertices = vertices
        self.V= len(vertices) #No. of vertices
        self.graph = [] # default dictionary to store graph
        self.infinity = float('Inf')


    # function to add an edge to graph
    def addEdge(self,u,v,w):
        self.graph.append([u, v, w])

    # utility function used to print the solution
    def printArr(self, dist):
        print("Vertex   Distance from Source")
        wynik = []
        # for i in range(self.V):
        for i in self.vertices:
            print("%s \t\t %s" % (i, str(dist[i])))
            wynik.append((i, str(dist[i])))
        return wynik

    def BellmanFord(self, src):
        # Step 1: Initialize distances from src to all other vertices
        # as INFINITE
        #dist = [float("Inf")] * self.V
        # dist = dict()
        # for a in self.vertices:
        #     dist[a] = self.infinity
        dist = {a:self.infinity for a in self.vertices}
        dist[src] = 0

        # Step 2: Relax all edges |V| - 1 times. A simple shortest
        # path from src to any other vertex can have at-most |V| - 1
        # edges
        for i in range(self.V-1):
            # Update dist value and parent index of the adjacent vertices of
            # the picked vertex. Consider only those vertices which are still in
            # queue
            for u, v, w in self.graph:
                # if dist[u] != float("Inf") and dist[u] + w < dist[v]:
                if dist[u] != self.infinity and dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w

        # Step 3: check for negative-weight cycles.  The above step
        # guarantees shortest distances if graph doesn't contain
        # negative weight cycle.  If we get a shorter path, then there
        # is a cycle.

        # for u, v, w in self.graph:
        #         if dist[u] != float("Inf") and dist[u] + w < dist[v]:
        #                 print("Graph contains negative weight cycle")
        #                 return

        # print all distance
        # self.printArr(dist)
        wynik = []
        # for i in range(self.V):
        for i in self.vertices:
            #print("%s \t\t %s" % (i, str(dist[i])))
            if dist[i] == self.infinity:
                wynik.append((str(src)+'->'+str(i), str(dist[i])))
        #queue.put(wynik)
        return wynik

        #return
        
class Mapa(object):
    def __init__(self, nazwapliku, stderr_stdout_writer, mode):
        typyRoutingowe = ('0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7', '0x8', '0x9', '0xa', '0xb',
                          '0xc', '0x16', '0x19', '0xd', '0xe', '0xf', '0x2f', '0x1a', '0x117')
        typLiniiGranicznej = ('0x4b',)
        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            encoding = 'latin2'
        else:
            encoding = 'cp1250'
        self.WszystkieNody = {}
        self.nazwaplikudlaoutput = nazwapliku.rstrip('.mp') + 'ciaglosc_routingu.txt'
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
                    if my_type not in ('0x19', '0x2f'):
                        nody_tmp = self.sprawdzzapetlenie(
                            Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),('))
                        # gdy droga zapętlona nie sprawdzaj numeracji, robi to netgen i raportuje odpowiednio
                        if len(nody_tmp) > 1:
                            uwzglednij_numeracje = 0
                    else:
                        nody_tmp = [Data0.strip().split('=')[-1].lstrip('(').rstrip(')').split('),(')]

                    # jeśli droga jednokierunkowa dodaj skrajne nody do listy nodow jednokierunkowych
                    # zrob to tylko w przypadku gdy droga nie jest zapętlona, bo w takim przypadku na pewno
                    # nie będzie ślepa
                    if DirIndicator and nody_tmp[0][0] != nody_tmp[0][-1] and my_type not in ('0x19', '0x2f'):
                        self.SkrajneNodyDrogJednokierunkowych.append(nody_tmp[0][0])
                        self.SkrajneNodyDrogJednokierunkowych.append(nody_tmp[0][-1])
                    # nod pierwszy i ostatni mają być routingowe, więc dodaję je osobno
                    # zapisujemy więc je w osobnym setcie
                    # nody_tmp moze byc listą list z racji tego ze dzielimy zapetlone linie, dlatego
                    for punkty_drogi in nody_tmp:
                        self.RoadId += 1
                        kolejnyNrNoda = 0
                        nodyskrajne = (punkty_drogi[0], punkty_drogi[-1])
                        for para_wspolrzednych in punkty_drogi:
                            if my_type not in ('0x19', '0x2f'):
                                if para_wspolrzednych in self.WszystkieNody:
                                    self.WszystkieNody[para_wspolrzednych].wezelRoutingowy += 1
                                    self.WszystkieNody[para_wspolrzednych].RoadIds.append(self.RoadId)
                                    self.WszystkieNody[para_wspolrzednych].numerParyWspDlaDanejDrogi[self.RoadId] \
                                        = (kolejnyNrNoda, DirIndicator)
                                    self.NodyDrogi.append(para_wspolrzednych)
                                else:
                                    self.WszystkieNody[para_wspolrzednych] = Node(para_wspolrzednych, self.RoadId,
                                                                                  (kolejnyNrNoda, DirIndicator), 1)
                                    self.NodyDrogi.append(para_wspolrzednych)
                                #nody skrajne powinny być z definicji routingowe
                                if para_wspolrzednych in nodyskrajne:
                                    self.WszystkieNody[para_wspolrzednych].wezelRoutingowy += 1

                            else:
                                self.Zakazy[self.RoadId].Nody.append(para_wspolrzednych)
                            kolejnyNrNoda += 1
                        if my_type not in ('0x19', '0x2f'):
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
                                # print(tmpccc)
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
                self.przetwarzanie_zakazow()
                self.sprawdzCzyRoutingowe()

            # obrabiamy ślepe jednokierunkowe
            if not self.mode:
                self.sprawdz_jednokierunkowe_slepe()

            if self.mode:
                if self.mode == 'sprawdz_siatke_dwukierunkowa':
                    self.sprawdzNieciaglosciSiatkiRoutingowej()
                elif self.mode == 'sprawdz_siatke_jednokierunkowa':
                    self.sprawdzNieciaglosciSiatkiRoutingowejUwzglednijJednokierunkowosc()

    def przetwarzanie_zakazow(self):
        for para_wspolrzednych in self.Zakazy:
            for tmpbbb in self.Zakazy[para_wspolrzednych].Nody:
                if tmpbbb in self.WszystkieNody:
                    self.WszystkieNody[tmpbbb].wezelRoutingowy = +1
                    self.Zakazy[para_wspolrzednych].Nodes.append(self.WszystkieNody[tmpbbb])
                else:
                    self.stderr_stdout_writer.stderrorwrite('Błąd zakazu! Węzeł bez drogi ' + tmpbbb)
                    self.Zakazy[para_wspolrzednych].Nodes.append(None)
            # self.Zakazy[para_wspolrzednych].ustawFromViaTo(self.WszystkieNody, self.Drogi)
            self.Zakazy[para_wspolrzednych].ustawFromViaTo1(self.WszystkieNody, self.Drogi)

    def sprawdz_jednokierunkowe_slepe(self):
        for para_wspolrzednych in self.SkrajneNodyDrogJednokierunkowych:
            if len(self.WszystkieNody[para_wspolrzednych].RoadIds) < 2 and para_wspolrzednych not in self.NodyGraniczne:
                self.stderr_stdout_writer.stderrorwrite('Jednokierunkowa ślepa: ' + para_wspolrzednych)

    def redukuj_ilosc_zbiorow_routingowych(self, nodyRoutingoweDrog):
        iloscdrog = len(nodyRoutingoweDrog)
        iloscdrogdlaprogress = iloscdrog
        iloscNone = 0
        procent = 0
        timer_start = timeit.default_timer()
        update_progress(0)
        tmpccc = -1
        while tmpccc:
            if tmpccc == -1:
                tmpccc = 0
            # for tmpccc in range(0, iloscdrog-1):
            if nodyRoutingoweDrog[tmpccc]:
                udalosiezredukowac = 1
                while udalosiezredukowac:
                    udalosiezredukowac = 0
                    numery_nodow_do_usuniecia = []
                    for tmpbbb in range(tmpccc + 1, iloscdrog):

                        if nodyRoutingoweDrog[tmpbbb]:
                            for zzz in nodyRoutingoweDrog[tmpbbb]:
                                if zzz in nodyRoutingoweDrog[tmpccc]:
                                    setwsp = nodyRoutingoweDrog[tmpccc].union(nodyRoutingoweDrog[tmpbbb])
                                    nodyRoutingoweDrog[tmpccc] = setwsp
                                    nodyRoutingoweDrog[tmpbbb] = None
                                    numery_nodow_do_usuniecia.append(tmpbbb)
                                    iloscdrog -= 1
                                    iloscNone += 1
                                    udalosiezredukowac = 1
                                    break
                        aktprocent = round(iloscNone / iloscdrogdlaprogress, 2)
                        if aktprocent * 100 > procent + 1:
                            procent = aktprocent * 100
                            update_progress(aktprocent)
                    # usun elementy:
                    iter = 0
                    for zzz in numery_nodow_do_usuniecia:
                        if nodyRoutingoweDrog[zzz - iter]:
                            print('Uwaga nie usuwam None')
                        del nodyRoutingoweDrog[zzz - iter]
                        iter += 1

            ##noweNody = [a for a in nodyRoutingoweDrog if a]
            ##nodyRoutingoweDrog = noweNody
            if nodyRoutingoweDrog[-1]:
                nodyRoutingoweDrog.append(None)
                iloscdrog += 1
            if nodyRoutingoweDrog[tmpccc + 1]:
                tmpccc += 1
            else:
                tmpccc = None
            print(iloscdrog, nodyRoutingoweDrog[iloscdrog - 1])
        return nodyRoutingoweDrog

    def sprawdzNieciaglosciSiatkiRoutingowej(self):
        # najpierw tworzymy dla każdej drogi jej węzły tylko w postaci węzłów routingowych
        nodyRoutingoweDrog = []
        #timer_start = timeit.default_timer()
        nodyGranicznetmp = set((a for a in self.NodyGraniczne if a in self.WszystkieNody))
        #print('czas wykonania %s' %(timeit.default_timer() - timer_start))
        nodyRoutingoweDrog.append(nodyGranicznetmp)
        for tmpaaa in self.Drogi:
            nodyRoutingoweDrog.append(set((c for c in self.Drogi[tmpaaa] if self.WszystkieNody[c].wezelRoutingowy)))
        # dodajemy nody graniczne do pierwszej pozycji, inaczej bedzie pokazywal slepe na granicy
        # iloscdrog = len(nodyRoutingoweDrog)
        # iloscdrogdlaprogress = iloscdrog
        # iloscNone = 0
        # teraz trzeba czary mary ze zbiorami tak aby to wszysto jakos polaczyc
        print('analizuje %s drog' %(len(nodyRoutingoweDrog)))

        timer_start = timeit.default_timer()
        oddzielnegrafy = [a for a in self.redukuj_ilosc_zbiorow_routingowych(nodyRoutingoweDrog) if a]

        print()
        print('czas wykonania %s' %(timeit.default_timer() - timer_start))
        if len(oddzielnegrafy)>1:
            for a in range(1, len(oddzielnegrafy)):
                print(str(oddzielnegrafy[a]))

    def sprawdzNieciaglosciSiatkiRoutingowejUwzglednijJednokierunkowosc(self):
            # najpierw tworzymy dla każdej drogi jej węzły tylko w postaci węzłów routingowych
            nodyRoutingoweDrog = []
            nodyRoutingoweDrogJednokierunkowych = []
            #timer_start = timeit.default_timer()
            nodyGranicznetmp = set((a for a in self.NodyGraniczne if a in self.WszystkieNody))
            #print('czas wykonania %s' %(timeit.default_timer() - timer_start))
            # dodajemy nody graniczne do pierwszej pozycji, inaczej bedzie pokazywal slepe na granicy
            nodyRoutingoweDrog.append(nodyGranicznetmp)
            procent = 0
            for tmpaaa in self.Drogi:
                #if self.WszystkieNody[self.Drogi[tmpaaa][0]].numerParyWspDlaDanejDrogi[self.Drogi[tmpaaa][0]][1]:
                if tmpaaa in self.DrogiJednokierunkowe:
                    njedn = [c for c in self.Drogi[tmpaaa] if self.WszystkieNody[c].wezelRoutingowy]
                    if njedn[0] == njedn[-1]:
                        #print('droga zapetlona', self.Drogi[tmpaaa])
                        nodyRoutingoweDrog.append(set(njedn))
                    else:
                        nodyRoutingoweDrogJednokierunkowych.append(njedn)
                else:
                    nodyRoutingoweDrog.append(set((c for c in self.Drogi[tmpaaa] if self.WszystkieNody[c].wezelRoutingowy)))

            # obrabiamy drogi jednokierunkowe, jeśli kończy się i zaczyna w tym samym segmencie to można dodać bez patrzenia
            # do danego segmentu
            self.polacz_jednokierunkowe_o_tym_samym_poczatku_i_koncu()
            # for tmpaaa in range(0, len(nodyRoutingoweDrogJednokierunkowych)):
            #     for tmpbbb in range(0, len(nodyRoutingoweDrog)):
            #         if (nodyRoutingoweDrogJednokierunkowych[tmpaaa][0] in nodyRoutingoweDrog[tmpbbb]) and \
            #                 (nodyRoutingoweDrogJednokierunkowych[tmpaaa][-1] in nodyRoutingoweDrog[tmpbbb]):
            #             nodyRoutingoweDrog[tmpbbb] = \
            #                 nodyRoutingoweDrog[tmpbbb].union(nodyRoutingoweDrogJednokierunkowych[tmpaaa])
            #             #print('Jednokierunkowa z poczatkiem i koncem w grafie', nodyRoutingoweDrogJednokierunkowych[tmpaaa] )
            #             #print('Jednokierunkowa z poczatkiem i koncem w grafie', nodyRoutingoweDrog[tmpbbb] )
            #             nodyRoutingoweDrogJednokierunkowych[tmpaaa] = None
            #             break

            iloscdrog = len(nodyRoutingoweDrog)
            iloscdrogdlaprogress = iloscdrog
            iloscNone = 0
            # teraz trzeba czary mary ze zbiorami tak aby to wszysto jakos polaczyc
            print('analizuje %s drog' %(iloscdrog))
            timer_start = timeit.default_timer()
            update_progress(0)
            tmpccc = -1
            while tmpccc:
                if tmpccc == -1:
                    tmpccc = 0
            #for tmpccc in range(0, iloscdrog-1):
                if nodyRoutingoweDrog[tmpccc]:
                    udalosiezredukowac = 1
                    while udalosiezredukowac:
                        udalosiezredukowac = 0
                        numery_nodow_do_usuniecia = []
                        for tmpbbb in range(tmpccc+1, iloscdrog):

                            if nodyRoutingoweDrog[tmpbbb]:
                                for zzz in nodyRoutingoweDrog[tmpbbb]:
                                    if zzz in nodyRoutingoweDrog[tmpccc]:
                                        setwsp = nodyRoutingoweDrog[tmpccc].union(nodyRoutingoweDrog[tmpbbb])
                                        nodyRoutingoweDrog[tmpccc] = setwsp
                                        nodyRoutingoweDrog[tmpbbb] = None
                                        numery_nodow_do_usuniecia.append(tmpbbb)
                                        # uaktualniamy dane do paska postepu
                                        iloscdrog -= 1
                                        iloscNone += 1
                                        udalosiezredukowac = 1
                                        break
                            aktprocent = round(iloscNone/iloscdrogdlaprogress,2)
                            if aktprocent*100>procent+1:
                                procent = aktprocent*100
                                update_progress(aktprocent)
                        #usun elementy:
                        # iter = 0
                        numery_nodow_do_usuniecia.reverse()
                        for zzz in numery_nodow_do_usuniecia:
                            if nodyRoutingoweDrog[zzz]:
                                print('Uwaga nie usuwam None')
                            del nodyRoutingoweDrog[zzz]
                            # if nodyRoutingoweDrog[zzz-iter]:
                            #     print('Uwaga nie usuwam None')
                            # del nodyRoutingoweDrog[zzz-iter]
                            # iter += 1


                ##noweNody = [a for a in nodyRoutingoweDrog if a]
                ##nodyRoutingoweDrog = noweNody
                if nodyRoutingoweDrog[-1]:
                    nodyRoutingoweDrog.append(None)
                    iloscdrog += 1
                if nodyRoutingoweDrog[tmpccc+1]:
                    tmpccc += 1
                else:
                    tmpccc = None
                print(iloscdrog, nodyRoutingoweDrog[iloscdrog-1])
            oddzielnegrafy = [a for a in nodyRoutingoweDrog if a]
            # print('oddzielne grafy')
            # for a in range(len(oddzielnegrafy)):
            #     print(a, oddzielnegrafy[a])

            print(len(oddzielnegrafy))
            print('czas wykonania %s' %(timeit.default_timer() - timer_start))
            #if len(oddzielnegrafy)>1:
            #    for a in range(1, len(oddzielnegrafy)):
            #        print(str(oddzielnegrafy[a]))

            timer_start = timeit.default_timer()
            print('Redukuje drogi jednokierunkowe')
            print(len(nodyRoutingoweDrogJednokierunkowych))
            for aaa in range(0, len(oddzielnegrafy)):
                for bbb in range(0, len(nodyRoutingoweDrogJednokierunkowych)):
                    if nodyRoutingoweDrogJednokierunkowych[bbb]:
                        inside = 1
                        for ccc in nodyRoutingoweDrogJednokierunkowych[bbb]:
                            if ccc not in oddzielnegrafy[aaa]:
                                inside = 0
                                break
                        if inside:
                            nodyRoutingoweDrogJednokierunkowych[bbb] = None

            print('czas wykonania %s' % (timeit.default_timer() - timer_start))
            paryJednokierunkoweBezGrafu = []
            polaczeniaPomiedzyGrafami = []
            print('sprawdzam polaczenia jednokierunkowe miedzy grafami')
            timer_start = timeit.default_timer()
            for aaa in (a for a in nodyRoutingoweDrogJednokierunkowych if a):
                for bbb in range(0, len(aaa)-1):
                    n = aaa[bbb]
                    n_plus_1 = aaa[bbb+1]
                    for ccc in range(0, len(oddzielnegrafy)):
                        if aaa[bbb] in oddzielnegrafy[ccc]:
                            n = str(ccc)
                            break
                    for ccc in range(0, len(oddzielnegrafy)):
                        if aaa[bbb+1] in oddzielnegrafy[ccc]:
                            n_plus_1 = str(ccc)
                            break
                    if n == n_plus_1:
                        pass
                    elif n.isdigit() and n_plus_1.isdigit():
                        if ((n, n_plus_1)) not in polaczeniaPomiedzyGrafami:
                            polaczeniaPomiedzyGrafami.append((n, n_plus_1))
                    else:
                        if ((n, n_plus_1)) not in paryJednokierunkoweBezGrafu:
                            paryJednokierunkoweBezGrafu.append((n, n_plus_1))

            polaczeniaPomiedzyGrafami.sort()
            print(polaczeniaPomiedzyGrafami)
            print((paryJednokierunkoweBezGrafu))
            print(len(polaczeniaPomiedzyGrafami))
            print(len(paryJednokierunkoweBezGrafu))

            print()
            print('czas wykonania %s' % (timeit.default_timer() - timer_start))
            #print(len([a for a in nodyRoutingoweDrogJednokierunkowych if a]))
            print('Redukuje ilosc osobnych grafow')
            slownikRedukcji = {}

            # Redukujemy ilość osobnych grafów. Trzeba to zrobić kilkakrotnie, ponieważ przy zamianie elementy które
            # już raz zamieniliśmy mogą ponownie ulce zamianie. Poza tym powstają elementy typu (0,0) które należy
            # zamienić na none.

            iloscNonePomiedzyGrafami = len([a for a in polaczeniaPomiedzyGrafami if a])
            iloscNonePomiedzyGrafami_poprzedni = -1

            while iloscNonePomiedzyGrafami > iloscNonePomiedzyGrafami_poprzedni:
                iloscNonePomiedzyGrafami_poprzedni = iloscNonePomiedzyGrafami
                for aaa in range(0, len(polaczeniaPomiedzyGrafami)):
                    print(aaa)
                    if polaczeniaPomiedzyGrafami[aaa]:
                        pOdwr = (polaczeniaPomiedzyGrafami[aaa][1],polaczeniaPomiedzyGrafami[aaa][0])
                        print('polaczenia', polaczeniaPomiedzyGrafami[aaa], pOdwr)
                        if pOdwr in polaczeniaPomiedzyGrafami:
                            print('odwrotne w polaczeniach')
                            indeks = polaczeniaPomiedzyGrafami.index(pOdwr)
                            min_ = str(min(int(polaczeniaPomiedzyGrafami[aaa][0]),int(polaczeniaPomiedzyGrafami[aaa][1])))
                            max_ = str(max(int(polaczeniaPomiedzyGrafami[aaa][0]),int(polaczeniaPomiedzyGrafami[aaa][1])))
                            if min_ in slownikRedukcji:
                                if min_ != max_:
                                    slownikRedukcji[min_].append(max_)
                            else:
                                slownikRedukcji[min_]=[max_]
                            polaczeniaPomiedzyGrafami[aaa] = None
                            polaczeniaPomiedzyGrafami[indeks] = None
                            # teraz wiemy, że dana para jest tozszama (0,100) i (100,0). Czyli 100 laduje w tym przypadku
                            # calkowicie w 0. W tym przypadku nalezy wszystkie
                            # 100 w pozostałych elementach pozamieniac na 0. Dlatego iterujemy po wszystkich elementach i dokonujemy
                            # stosownych korekt. Bo de facto ten element (100) znika już wiec dobrze go zastapic nowym.
                            for bbb in range(0, len(polaczeniaPomiedzyGrafami)):
                                if polaczeniaPomiedzyGrafami[bbb]:
                                    a, b = polaczeniaPomiedzyGrafami[bbb]
                                    if a == max_:
                                        a = min_
                                        print('zamieniam pierwszy element ' + str(polaczeniaPomiedzyGrafami[bbb]) + '->' + a)
                                    if b == max_:
                                        b = min_
                                        print('zamieniam drugi element ' + str(polaczeniaPomiedzyGrafami[bbb]) + '->' + b)
                                    if a == b:
                                        polaczeniaPomiedzyGrafami[bbb] = None
                                    else:
                                        polaczeniaPomiedzyGrafami[bbb] = (a,b)
                                    # print(polaczeniaPomiedzyGrafami[bbb])
                    iloscNonePomiedzyGrafami = len([a for a in polaczeniaPomiedzyGrafami if a])

            print(polaczeniaPomiedzyGrafami)
            polaczeniaPomiedzyGrafami = [a for a in polaczeniaPomiedzyGrafami if a]
            print(len(polaczeniaPomiedzyGrafami))

            # musze uporzadkowac slownik redukcji, bo z racji wieloprzebiegowosci poprzedniej czesci niektore elementy
            # nie sa calkowicie zastapione i moga sie dublowac. np
            # 1: 10,12,45 i 10: 77, trzeba uporzadkowac tak 1: 10.12.45.77
            print('slownik redukcji', slownikRedukcji)
            kluczeRedukcji = sorted([int(a) for a in slownikRedukcji])
            kluczeRedukcji = [str(a) for a in kluczeRedukcji]
            kluczeRedukcjiOdwrotne = kluczeRedukcji
            kluczeRedukcjiOdwrotne.reverse()

            for tmpaaa in kluczeRedukcji:
                if slownikRedukcji[tmpaaa]:
                    for tmpbbb in kluczeRedukcjiOdwrotne:
                        if tmpbbb == tmpaaa:
                            break
                        else:
                            if slownikRedukcji[tmpbbb] and tmpbbb in slownikRedukcji[tmpaaa]:
                                slownikRedukcji[tmpaaa] = slownikRedukcji[tmpaaa] + slownikRedukcji[tmpbbb]
                                slownikRedukcji[tmpbbb] = None
            slownikRedukcji = {a: slownikRedukcji[a] for a in slownikRedukcji if slownikRedukcji[a]}
            print('slownik redukcji', slownikRedukcji)
            #mapujemy co na co zamienić
            slownikSubstytucji = dict()
            print('oddzielne grafy przed', oddzielnegrafy)
            for aaa in slownikRedukcji:
                for bbb in slownikRedukcji[aaa]:
                    slownikSubstytucji[bbb] = aaa
                    oddzielnegrafy[int(bbb)] = None
            print('oddzielne grafy po', oddzielnegrafy)

            print('slownik substytucji ', slownikSubstytucji)
            for aaa in oddzielnegrafy:
                print(aaa)

            print('redukuje pary jednokierunkowe bez grafu')
            for aaa in range(0, len(paryJednokierunkoweBezGrafu)):
                if paryJednokierunkoweBezGrafu[aaa][0] in slownikSubstytucji:
                    print('lewe znalezione ', paryJednokierunkoweBezGrafu[aaa])
                    bbb = (slownikSubstytucji[paryJednokierunkoweBezGrafu[aaa][0]], paryJednokierunkoweBezGrafu[aaa][1])
                    paryJednokierunkoweBezGrafu[aaa] = bbb
                    print('lewe zamieenione ',bbb)
                if paryJednokierunkoweBezGrafu[aaa][1] in slownikSubstytucji:
                    print('prawe znalezione ',paryJednokierunkoweBezGrafu[aaa])
                    bbb = (paryJednokierunkoweBezGrafu[aaa][0], slownikSubstytucji[paryJednokierunkoweBezGrafu[aaa][1]])
                    paryJednokierunkoweBezGrafu[aaa] = bbb
                    print('prawe znalezione ', bbb)

            print('polaczenia pomiedzy grafami przed', polaczeniaPomiedzyGrafami)
            for aaa in range(0, len(polaczeniaPomiedzyGrafami)):
                if polaczeniaPomiedzyGrafami[aaa]:
                    if polaczeniaPomiedzyGrafami[aaa][0] in slownikSubstytucji:
                        bbb = (slownikSubstytucji[polaczeniaPomiedzyGrafami[aaa][0]], polaczeniaPomiedzyGrafami[aaa][1])
                        polaczeniaPomiedzyGrafami[aaa] = bbb
                    if polaczeniaPomiedzyGrafami[aaa][1] in slownikSubstytucji:
                        bbb = (polaczeniaPomiedzyGrafami[aaa][0], slownikSubstytucji[polaczeniaPomiedzyGrafami[aaa][1]])
                        polaczeniaPomiedzyGrafami[aaa] = bbb

            polaczeniaPomiedzyGrafami = list(set(polaczeniaPomiedzyGrafami))
            print('polaczenia pomiedzy grafami po ', polaczeniaPomiedzyGrafami)
            paryJednokierunkoweBezGrafu = list(set(paryJednokierunkoweBezGrafu))
            print(len(paryJednokierunkoweBezGrafu))


            wierzcholkiGrafu = []
            print('Buduje wierzcholki grafu')
            for tmpaaa in range(0, len(oddzielnegrafy)):
                print(tmpaaa, oddzielnegrafy[tmpaaa])
                if oddzielnegrafy[tmpaaa]:
                    wierzcholkiGrafu.append(str(tmpaaa))
            print(wierzcholkiGrafu)
            for tmpaaa in polaczeniaPomiedzyGrafami:
                if tmpaaa:
                    print(tmpaaa)
                    if tmpaaa[0] not in wierzcholkiGrafu:
                        wierzcholkiGrafu.append(tmpaaa[0])
                    if tmpaaa[1] not in wierzcholkiGrafu:
                        wierzcholkiGrafu.append(tmpaaa[1])
            for tmpaaa in paryJednokierunkoweBezGrafu:
                print(tmpaaa)
                if tmpaaa[0] not in wierzcholkiGrafu:
                    wierzcholkiGrafu.append(tmpaaa[0])
                if tmpaaa[1] not in wierzcholkiGrafu:
                    wierzcholkiGrafu.append(tmpaaa[1])

            
            graf = Graph(wierzcholkiGrafu)
            for tmpaaa in polaczeniaPomiedzyGrafami:
                graf.addEdge(tmpaaa[0], tmpaaa[1], 1)
            for tmpaaa in paryJednokierunkoweBezGrafu:
                graf.addEdge(tmpaaa[0], tmpaaa[1], 1)

            print('spradzam polaczenia')


            pool = Pool(cpu_count())
            # ponizsze to jakis artefakt, chyba nie rzumiem o co chodzi
            #wierzcholkiGrafu = [a for a in wierzcholkiGrafu]
            # rs = pool.map_async(graf.BellmanFord, wierzcholkiGrafu)

            rs = []
            for wierzch in wierzcholkiGrafu:
                rs.append(pool.apply_async(graf.BellmanFord, [wierzch]))

            progress100 = len(wierzcholkiGrafu)
            time_of_break = 1
            timer_start = timeit.default_timer()
            incomplete_count_previous = 0
            incomplete_count = 0
            while (1):
                incomplete_count_previous = incomplete_count
                incomplete_count = sum(1 for x in rs if not x.ready())
                if incomplete_count == 0:
                    print('Skończone')
                    break
                if incomplete_count_previous and incomplete_count_previous == incomplete_count:
                    time_of_break += 1
                    #print(time_of_break)
                else:
                    time_of_running_in_seconds = round(timeit.default_timer() - timer_start)
                    if incomplete_count < progress100:
                        ETA_int = round(incomplete_count/((progress100-incomplete_count)/time_of_running_in_seconds))
                        if ETA_int <= 120:
                            ETA = str(ETA_int) + ' s'
                        else:
                            ETA = str(round(ETA_int/60,1))+' min'
                        print('Pozostało ' + str(incomplete_count) + ' wierzchołków do sprawdzenia. ETA: ' + ETA)


                time.sleep(time_of_break)

            file = open(self.nazwaplikudlaoutput, 'w')
            for wynikAnalizy in rs:
                # wyninkAnalizy ma postac [('53.27990,16.45933->53.32999,16.02584', 'inf')]
                if wynikAnalizy.get(timeout=1):
                    for tmpbbb in wynikAnalizy.get(timeout=1):
                        print(tmpbbb)
                        skaddokad,infinity = tmpbbb
                        skad,dokad = skaddokad.split('->')
                        try:
                            # poniewaz oddzielnegrafy to set wiec aby wyciagnac jeden element z niego musze zrobic liste
                            skad = skad + '(' + list(oddzielnegrafy[int(skad)])[0] + ')'
                        except ValueError:
                            pass
                        try:
                            # poniewaz oddzielnegrafy to set wiec aby wyciagnac jeden element z niego musze zrobic liste
                            dokad = dokad + '(' + list(oddzielnegrafy[int(dokad)])[0] + ')'
                        except ValueError:
                            pass
                        print(skad + '->' + dokad + ' brak polaczenia')
                        file.write(skad + '->' + dokad + ' brak polaczenia\n')

            file.close()
            print('Utworzono plik %s.' %(self.nazwaplikudlaoutput))

    def polacz_jednokierunkowe_o_tym_samym_poczatku_i_koncu(self):
        # jeśli jednokierunkowa zaczya się i kończy w tym samym zbiorze, to znaczy, że z każdego dowolnego
        # punktu tej jednokierunkowej można dojechać do tego zbioru. Można więc spokojnie połączyć te dwa zbiory

        for tmpaaa in range(0, len(nodyRoutingoweDrogJednokierunkowych)):
            for tmpbbb in range(0, len(nodyRoutingoweDrog)):
                if (nodyRoutingoweDrogJednokierunkowych[tmpaaa][0] in nodyRoutingoweDrog[tmpbbb]) and \
                        (nodyRoutingoweDrogJednokierunkowych[tmpaaa][-1] in nodyRoutingoweDrog[tmpbbb]):
                    nodyRoutingoweDrog[tmpbbb] = \
                        nodyRoutingoweDrog[tmpbbb].union(nodyRoutingoweDrogJednokierunkowych[tmpaaa])
                    # print('Jednokierunkowa z poczatkiem i koncem w grafie', nodyRoutingoweDrogJednokierunkowych[tmpaaa] )
                    # print('Jednokierunkowa z poczatkiem i koncem w grafie', nodyRoutingoweDrog[tmpbbb] )
                    nodyRoutingoweDrogJednokierunkowych[tmpaaa] = None
                    break

    def sprawdzzapetlenie(self, nodydrogi):
        ''' funkcja sprawdza czy droga nie jest ze sobą zapętlona, jeśli jest, to wtedy dzieli ją na pół aż rozpętli'''
        # nodydrogi to zmienna przechowująca pary współrzędnych danej drogi np.:
        # '51.79507,19.45560', '51.79538,19.45566', '51.79529,19.45543'
        # wyszukujemy nody podwojne
        nodypodwojne = [a for a in nodydrogi if nodydrogi.count(a)>1]
        # print('nodypodwojne',  nodypodwojne)
        for a in nodypodwojne:
            if a == nodydrogi[(nodydrogi.index(a)+1)]:
                self.stderr_stdout_writer.stderrorwrite("Zdublowane punkty drogi " + a + "\npomijam sprawdzanie.")
                return [nodydrogi]
            
        #print(nodypodwojne)
        if not nodypodwojne:
            return [nodydrogi]
        else:
            # no to mamy zapętlenie, trzeba obsłużyć, zakładam że nikt nie będzie plątał w nieskończoność
            # idea jest taka. Dzielimy na pół, sprawdzamy czy nadal zapętlone, jeśli tak to ten z zapętleniem
            # dzielimy dalej na pół itd
            a = self.sprawdzzapetlenie(nodydrogi[:len(nodydrogi) // 2 + 1])
            if len(a)>1:
                c = [a[0],a[1]]
            else:
                c = [a[0]]
            # print(c)
            b = self.sprawdzzapetlenie(nodydrogi[len(nodydrogi) // 2:])
            if len(b)>1:
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
        returnVal = []
        for kol_num in (1, 4):
            if Numery[kol_num] in ('N', 'B'):
                continue
            liczba1 = int(Numery[kol_num + 1])
            liczba2 = int(Numery[kol_num + 2])
            if liczba1 <= 0 or liczba2 <= 0:
                returnVal.append('Numeracja-niezdefiniowany koniec (' + Numery[kol_num] + ',' + (Numery[kol_num + 1]) +
                                 ',' + (Numery[kol_num + 2]) + ')')
            parzystosc = 1 if Numery[kol_num] == 'O' else 0
            if liczba1 % 2 != parzystosc or liczba2 % 2 != parzystosc:
                returnVal.append('Numeracja-nieprawidłowa parzystość (' + (Numery[kol_num]) + ',' +
                                 (Numery[kol_num + 1]) + ',' + (Numery[kol_num + 2]) + ')')
        return returnVal


# nazwa klasy mylaca ale niech bedzie
class Node(object):
    def __init__(self, paraWsp, RoadId, nrwsp , skrajna=0):

        # mowi samo za siebie
        self.wspolrzedne = paraWsp
        # czy dana współrzędna jest skrajna
        self.wspolrzednaSkrajna = skrajna
        # gdy = 0 wtedy dany węzeł nie jest węzłem routingowym
        self.wezelRoutingowy = 0
        # id drogi. Jesli takie samo oznacza to ze wezly naleza do jednej linii
        self.RoadIds = [RoadId]
        # kolejny nr wezla dla danej drogi - slownik gdzie kluczem jest roadid, a wartoscia to tupla nr wezla
        # kierunkowosc (0 brak, 1 jednokierunkowa). jesli bedzie kilka drog to bedzie tez kilka numerow id
        self.numerParyWspDlaDanejDrogi = {RoadId: nrwsp}
        #print(self.numerParyWspDlaDanejDrogi[RoadId])


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
        #tmpIndeksA = WszystkieNody[lNody[0]].numerParyWspDlaDanejDrogi[lRoadId][0]
        #tmpIndeksB = WszystkieNody[lNody[1]].numerParyWspDlaDanejDrogi[lRoadId][0]

        if indeksA < indeksB:
            step = 1
        else:
            step = -1
        for abcde in range(indeksA + step, indeksB, step):
            wspolrzedna = Drogi[lRoadId][abcde]
            if WszystkieNody[wspolrzedna].wezelRoutingowy:
                self.stderr_stdout_writer.stderrorwrite('Błąd zakazu. Pomiędzy węzłami %s, %s\n'%(lNody[0], lNody[1]))
                self.stderr_stdout_writer.stderrorwrite('istnieje węzeł routingowy %s.'%wspolrzedna)

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

    def ustawFromViaTo(self, WszystkieNody, Drogi):
        # WszystkieNody to slownik: klucz to para wsp, wartosc to obiekt typu Node
        # Drogi to slownik roadid jako klucz a wartosc to wszystkie nody danej drogi

        # przetwarzamy From
        if self.Nody[0] in WszystkieNody and self.Nody[0] and WszystkieNody:
            for abcd in WszystkieNody[self.Nody[0]].RoadIds:
                self.FromRoadId.append(abcd)
            for abcd in WszystkieNody[self.Nody[1]].RoadIds:
                self.FromRoadId.append(abcd)
            self.FromRoadId = [a for a in self.FromRoadId if self.FromRoadId.count(a) > 1]
            self.FromRoadId = list(set(self.FromRoadId))
            # gdy nie ma chociaz 1 drogi laczacej dwa wezly zakazu wtedy self.FromRoadId bedzie puste
            if self.FromRoadId:
                # sprawdzamy czy nody drogi From nie są rozdzielone wezłem routingowym
                self.sprawdz_czy_pomiedzy_sa_wezly_routingowe(Drogi, WszystkieNody, self.FromRoadId[0], self.Nody[0:2])

        # przetwarzamy Via o ile istnieje
        if len(self.Nody) == 4:
            if self.Nody[1] in WszystkieNody and self.Nody[2] and WszystkieNody:
                for abcd in WszystkieNody[self.Nody[1]].RoadIds:
                    self.ViaRoadId.append(abcd)
                for abcd in WszystkieNody[self.Nody[2]].RoadIds:
                    self.ViaRoadId.append(abcd)
                self.ViaRoadId = [a for a in self.ViaRoadId if self.ViaRoadId.count(a) > 1]
                self.ViaRoadId = list(set(self.ViaRoadId))
                # gdy nie ma chociaz 1 drogi laczacej dwa wezly zakazu wtedy self.FromRoadId bedzie puste
                if self.ViaRoadId:
                    self.sprawdz_czy_pomiedzy_sa_wezly_routingowe(Drogi, WszystkieNody, self.ViaRoadId[0], self.Nody[1:3])

        # przetwarzamy To
        if self.Nody[-2] in WszystkieNody and self.Nody[-1] and WszystkieNody:
            for abcd in WszystkieNody[self.Nody[-2]].RoadIds:
                self.ToRoadId.append(abcd)
            for abcd in WszystkieNody[self.Nody[-1]].RoadIds:
                self.ToRoadId.append(abcd)
            self.ToRoadId = [a for a in self.ToRoadId if self.ToRoadId.count(a) > 1]
            self.ToRoadId = list(set(self.ToRoadId))
            if self.ToRoadId:
                self.sprawdz_czy_pomiedzy_sa_wezly_routingowe(Drogi, WszystkieNody, self.ToRoadId[0], self.Nody[-2:])
            # gdy nie ma pojedynczej drogi laczacej dwa wezly zakazu generowany jest wyjatek albo KeyError albo IndexError
            # przechwycamy go i obslugujemy taki blad pozniej

        self.sprawdz_zakaz()

    def sprawdz_zakaz1(self):
        # zakaz musi mieć przynajmniej 3 a maksymalnie 4 punkty, pozostale przypadki do blad
        if not 3 <= len(self.Nody) <= 4:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu!\nZakaz może mieć tylko 3 lub 4 węzły a ma %s : %s %s' % (
                len(self.Nody), self.Nody[0], self.Nody[1]))

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
                if self.Nodes[numer].numerParyWspDlaDanejDrogi[from_via_to_item[0]][1]:
                    if self.Nodes[numer].numerParyWspDlaDanejDrogi[from_via_to_item[0]][0] > \
                            self.Nodes[numer + 1].numerParyWspDlaDanejDrogi[from_via_to_item[0]][0]:
                        self.stderr_stdout_writer.stderrorwrite(
                            'Błąd zakazu! Zakaz dodany pod prąd: %s %s ' % (self.Nody[numer], self.Nody[numer + 1]))

    def sprawdz_zakaz(self):
        # zakaz musi mieć przynajmniej 3 a maksymalnie 4 punkty, pozostale przypadki do blad
        if not 3 <= len(self.Nody) <= 4:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu!\nZakaz może mieć tylko 3 lub 4 węzły a ma %s : %s %s' % (len(self.Nody), self.Nody[0], self.Nody[1]))
                
        # sekcja analizujaca from
        a = len(self.FromRoadId)
        if a == 0:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu!\nBrak pojedynczej drogi łączącej węzły: %s %s ' % (self.Nody[0], self.Nody[1]))
        elif a > 1:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu! %s drogi łączą węzły: %s %s ' % (a, self.Nody[0], self.Nody[1]))
        else:
            if self.Nodes[0].numerParyWspDlaDanejDrogi[self.FromRoadId[0]][1]:
                if self.Nodes[0].numerParyWspDlaDanejDrogi[self.FromRoadId[0]][0] > self.Nodes[1].numerParyWspDlaDanejDrogi[self.FromRoadId[0]][0]:
                    self.stderr_stdout_writer.stderrorwrite(
                        'Błąd zakazu! Zakaz dodany pod prąd: %s %s ' % (self.Nody[0], self.Nody[1]))

        # analiza via, tylko w przypadku gdy występuje 4 nodowy zakaz
        if len(self.Nody) == 4:
            a = len(self.ViaRoadId)
            if a == 0:
                self.stderr_stdout_writer.stderrorwrite(
                    'Błąd zakazu!\nBrak pojedynczej drogi łączącej węzły: %s %s ' % (self.Nody[1], self.Nody[2]))
            elif a > 1:
                self.stderr_stdout_writer.stderrorwrite(
                    'Błąd zakazu! %s drogi łączą węzły: %s %s' % (a, self.Nody[1], self.Nody[2]))
            else:
                if self.Nodes[1].numerParyWspDlaDanejDrogi[self.ViaRoadId[0]][1]:
                    if self.Nodes[1].numerParyWspDlaDanejDrogi[self.ViaRoadId[0]][0] > self.Nodes[2].numerParyWspDlaDanejDrogi[self.ViaRoadId[0]][0]:
                        self.stderr_stdout_writer.stderrorwrite(
                            'Błąd zakazu! Zakaz dodany pod prąd: %s %s ' % (self.Nody[1], self.Nody[2]))
        # sekcja analizujaca to
        a = len(self.ToRoadId)
        if a == 0:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu!\nBrak pojedynczej drogi łączącej węzły: %s %s ' % (self.Nody[-2], self.Nody[-1]))
        elif a > 1:
            self.stderr_stdout_writer.stderrorwrite(
                'Błąd zakazu! %s drogi łączą węzły: %s %s' % (a, self.Nody[-2], self.Nody[-1]))
        else:
            if self.Nodes[-2].numerParyWspDlaDanejDrogi[self.ToRoadId[0]][1]:
                if self.Nodes[-2].numerParyWspDlaDanejDrogi[self.ToRoadId[0]][0] > self.Nodes[-1].numerParyWspDlaDanejDrogi[self.ToRoadId[0]][0]:
                    self.stderr_stdout_writer.stderrorwrite(
                        'Błąd zakazu! Zakaz dodany pod prąd: %s %s ' % (self.Nody[-2], self.Nody[-1]))


def main(argumenty, stderr_stdout_writer, mode):
    mapa = Mapa(argumenty, stderr_stdout_writer, mode)


if __name__ == "__main__":
    print('Używaj z mont_demont.py')
