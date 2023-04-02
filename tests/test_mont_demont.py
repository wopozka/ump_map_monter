import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mont_demont
from collections import OrderedDict

class Args(object):
    def __init__(self):
        pass

TEST_ZWROC_REKORD_PLIKU_MP = (
    (
        ';dekomunizacja: J. Krasickiego -> Ignacego Krasickiego\n;Uchwala nr 0007.XXVIII.241.2017 Rady Miejskiej w Zmigrodzie z dnia 7 czerwca 2017 r.\n[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\n',
         ({
            'Komentarz': [';dekomunizacja: J. Krasickiego -> Ignacego Krasickiego', ';Uchwala nr 0007.XXVIII.241.2017 Rady Miejskiej w Zmigrodzie z dnia 7 czerwca 2017 r.'],
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt'
         }),
    ),
    (
        ';\n[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\n',
         ({
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt'
         }),
    ),
    (';;Gmina=Rozdrazew\n[POI]\nType=0x2800\nLabel=1\nHouseNumber=1\nStreetDesc=Wygoda\nData0=(51.78184,17.44398)\nMiasto=Wygoda\nPlik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr\nKodPoczt=63-708\nTyp=ADR\n',
     ({
        'Komentarz': [';;Gmina=Rozdrazew'],
        'POIPOLY': '[POI]',
        'Type': '0x2800',
        'Label': '1',
        'HouseNumber': '1',
        'StreetDesc': 'Wygoda',
        'Data0_0': '(51.78184,17.44398)',
        'Miasto': 'Wygoda',
        'Plik': 'UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
        'KodPoczt': '63-708',
        'Typ': 'ADR',
     })
    ),
    (
        '[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\n',
         ({
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data0_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt'
         }),
    ),
(
        '[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData10=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData11=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\n',
         ({
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data0_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data10_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data11_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt'
         }),
    ),
    (
        '[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\nTutaj dziwna linia\nTutaj dziwna linia2\n',
         ({
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data0_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt',
            'Dziwne': ['Tutaj dziwna linia', 'Tutaj dziwna linia2']
         }),
    ),
(
        '[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nData1=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\nTutaj dziwna linia=\nTutaj dziwna linia2=\n',
         ({
            'POIPOLY': '[POLYLINE]',
            'Type': '0x6',
            'Label': 'Krasickiego',
            'EndLevel': '1',
            'DirIndicator': '1',
            'Data0_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data0_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_0': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Data1_1': '(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)',
            'Numbers1': '0,E,14,14,O,9,3',
            'Numbers2': '1,N,-1,-1,O,1,1',
            'Miasto': 'Zmigrod',
            'Plik': 'UMP-PL-Leszno/src/ZMIGROD.ulice.txt',
            'Tutaj dziwna linia': '',
            'Tutaj dziwna linia2': ''
         }),
    ),
)

@pytest.mark.parametrize('target, answer', TEST_ZWROC_REKORD_PLIKU_MP)
def test_zwroc_rekord_pliku_mp(target, answer):
    zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    args = Args()
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabela_konwersji_typow = mont_demont.tabelaKonwersjiTypow(zmienne, stderr_stdout_writer)
    assert mont_demont.plikMP1(zmienne, args, tabela_konwersji_typow, Montuj=0).zwroc_rekord_pliku_mp(target) == answer


TEST_ADR_TO_MP = (
    (
        [';;Gmina=Rozdrazew',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
         '51.77569,  17.45854,  0,2,Debowiec;2,Debowiec,ADR,63-708',
        ],
        [';;Gmina=Rozdrazew', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', '[END]\n', '[POI]', 'Type=0x2800', 'Label=2', 'HouseNumber=2',
         'StreetDesc=Debowiec', 'Data0=(51.77569,17.45854)', 'Miasto=Debowiec',
         'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr', 'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
    (
        [';;Gmina=Rozdrazew',
         ';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00',
         ';EntryPoint:(51.77364,17.46213)',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        [';;Gmina=Rozdrazew\n;;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00\n;EntryPoint:(51.77364,17.46213)',
         '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec', 'Data0=(51.77364,17.46213)',
         'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr', 'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
    (
        [';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        [';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1',
         'StreetDesc=Debowiec', 'Data0=(51.77364,17.46213)', 'Miasto=Debowiec',
         'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr', 'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
    (
        [
         ';Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        ['[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00', '[END]\n'
        ]
    ),
    (
        [
         ';;EntryPoint:(51.77364,17.46213)',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        ['[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'EntryPoint=(51.77364,17.46213)', '[END]\n'
        ]
    ),
    (
        [
         ';EntryPoint:(51.77364,17.46213)',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        [';EntryPoint:(51.77364,17.46213)', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
    (
        [
         ';;EntryPoint:(51.77364,17.46213)',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        ['[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'EntryPoint=(51.77364,17.46213)', '[END]\n'
        ]
    ),
    (
        [
         ';;;EntryPoint:(51.77364,17.46213)',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        [';;;EntryPoint:(51.77364,17.46213)', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
    (
        [';3', ';2', ';1',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        [';3\n;2\n;1', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', '[END]\n'
        ]
    ),
)

@pytest.mark.parametrize('target, answer', TEST_ADR_TO_MP)
def test_plik_pnt_procesuj(target, answer):
    args = Args()
    args.cityidx = False
    args.entry_otwarte_do_extras = True
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    globalneIndeksy = mont_demont.IndeksyMiast()
    punkt_z_adr = mont_demont.Poi('UMP-PL-Leszno/src/gRozdrazew_2017i.adr', globalneIndeksy, tabKonw, args)
    przetwarzanyPlik = mont_demont.plikPNT('UMP-PL-Leszno/src/gRozdrazew_2017i.adr', args, punkt_z_adr)
    zawartoscPlikuADR = target
    assert przetwarzanyPlik.procesuj(zawartoscPlikuADR) == answer

TEST_ENTRYPOINT_OTWARTE_NA_KOMENTARZ = (
    ({'EntryPoint': '(51.77364,17.46213)', 'Otwarte': 'Mo-Sa 6:00-24:00; Su 7:00-24:00'}, {'Komentarz': [';;EntryPoint: (51.77364,17.46213)', ';otwarte: Mo-Sa 6:00-24:00; Su 7:00-24:00']}),
    ({'Komentarz': ['la la la'], 'EntryPoint': '(51.77364,17.46213)', 'Otwarte': 'Mo-Sa 6:00-24:00; Su 7:00-24:00'}, {'Komentarz': ['la la la', ';;EntryPoint: (51.77364,17.46213)', ';otwarte: Mo-Sa 6:00-24:00; Su 7:00-24:00']}),

)

@pytest.mark.parametrize('target, answer', TEST_ENTRYPOINT_OTWARTE_NA_KOMENTARZ)
def test_entrypoint_otwarte_na_komentarz(target, answer):
    assert mont_demont.plikMP1.przenies_otwarte_i_entrypoint_do_komentarza(OrderedDict(target)) == OrderedDict(answer)

TEST_MODYFIKUJ_PLIK_DLA_POI = (
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Plik': 'UMP-PL-Lodz/crs/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Plik': 'UMP-PL-Lodz/crs/POI-Lodz.bankomaty.pnt', 'Type': '0x2000'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '_nowosci.txt', 'Type': '0x2000'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '', 'Type': '0x2000'},{'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '_nowosci.txt', 'Type': '0x2000'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '', 'Type': '0x2f06'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Type': '0x2f06'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Type': '0x2f06', 'Plik': '_nowosci.pnt'}),
    ({'POIPOLY': '[POI]', 'Label': 'label', 'Type': '0x2000'}, {'POIPOLY': '[POI]', 'Label': 'label', 'Type': '0x2000', 'Plik': '_nowosci.txt'}),
    ({'POIPOLY': '[POI]', 'Label': 'Miasto', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0xd00'}, {'POIPOLY': '[POI]', 'Label': 'Miasto', 'Plik': '_nowosci.pnt', 'Type': '0xd00'}),
    ({'POIPOLY': '[POI]', 'Label': 'ATM', 'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0x2f06'}, {'POIPOLY': '[POI]', 'Label': 'ATM', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
    ({'POIPOLY': '[POI]', 'Label': 'Miasto Miasto', 'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0xe00'}, {'POIPOLY': '[POI]', 'Label': 'Miasto Miasto', 'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0xe00'}),
)
@pytest.mark.parametrize('target, answer', TEST_MODYFIKUJ_PLIK_DLA_POI)
def test_modyfikuj_plik_dla_poi(target, answer):
    args = Args()
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    plikMp.plikizMp = {'UMP-PL-Lodz/src/LODZ.bankomaty.pnt': [], 'UMP-PL-Lodz/src/cities-Lodz.pnt': []}
    plikMp.zwaliduj_sciezki_do_plikow()
    assert plikMp.modyfikuj_plik_dla_rekordu_mp(OrderedDict(target)) == OrderedDict(answer)

TEST_MODYFIKUJ_PLIK_DLA_POLY = (
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel' :'1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.txt'}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel' :'1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.pnt'}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'XXX'}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': ''}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)'}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)'}, True,), {'POIPOLY': '[POLYLINE]', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/LODZ.budynki.txt'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.pnt'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': ''}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': ''}, False,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYLINE]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Leszno/src/inne_drogi.drogi.pnt'}, False,), {'POIPOLY': '[POLYLINE]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': '_nowosci.txt'}),
)
@pytest.mark.parametrize('target, answer', TEST_MODYFIKUJ_PLIK_DLA_POLY)
def test_modyfikuj_plik_dla_polygon_polyline(target, answer):
    args = Args()
    args.autopolypoly = target[1]
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    plikMp.obszary = mont_demont.Obszary(['Lodz'], Zmienne)
    plikMp.plikizMp = {'UMP-PL-Lodz/src/LODZ.obszary.txt': [], 'UMP-PL-Lodz/src/LODZ.budynki.txt': [],
                       'UMP-PL-Lodz/src/LODZ.kolej.txt': [], 'UMP-PL-Lodz/src/LODZ.zakazy.txt': []}
    plikMp.zwaliduj_sciezki_do_plikow()
    plikMp.autoobszary.wypelnijObszarPlikWspolrzedne(['UMP-PL-Lodz/src/LODZ.obszary.txt',
                                                      'UMP-PL-Lodz/src/LODZ.budynki.txt',
                                                      'UMP-PL-Lodz/src/LODZ.kolej.txt',
                                                      'UMP-PL-Lodz/src/LODZ.zakazy.txt'
                                                      ])
    assert plikMp.modyfikuj_plik_dla_rekordu_mp(OrderedDict(target[0])) == answer

TEST_STWORZ_MISC_INFO = (
    ({'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}),
    ({'Plik': 'POI-Lodz.bankomaty.txt', 'Type': '0x2f06', 'Komentarz': ['lalala']}, {'Plik': 'POI-Lodz.bankomaty.txt', 'Type': '0x2f06', 'Komentarz': ['lalala']}),
    ({'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0xe00', 'Komentarz': ['lalala']}, {'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0xe00', 'Komentarz': ['lalala']}),
    ({'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'Komentarz': [';wys=123']}, {'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'StreetDesc': '123'}),
    ({'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'Komentarz': ['kom1', ';wys=123', 'kom2']}, {'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'Komentarz': ['kom1', 'kom2'], 'StreetDesc': '123'}),
    ({'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'Komentarz': ['kom1', ';wys=123', ';wys=124','kom2']}, {'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x6616', 'Komentarz': ['kom1', 'kom2'], 'StreetDesc': '124'}),
    ({'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}),
    ({'Komentarz': ['aaa', ';http://bbb.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'url=http://bbb.pl'}),
    ({'Komentarz': ['aaa', ';https://bbb.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'url=https://bbb.pl'}),
    ({'Komentarz': ['aaa', ';http://aaa.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'url=http://bbb.pl'}, {'Komentarz': ['aaa', ';http://aaa.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'url=http://bbb.pl'}),
    ({'Komentarz': ['aaa', ';fb:bbb.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'fb=bbb.pl'}),
    ({'Komentarz': ['aaa', ';fb://bbb.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'fb=bbb.pl'}),
    ({'Komentarz': ['aaa', ';wiki://bbb.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'wiki=bbb.pl'}),
    ({'Komentarz': ['aaa', ';wiki://bbb.pl', ';http://aaa.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Komentarz': ['aaa', ';http://aaa.pl'], 'Plik': 'POI-Lodz.bankomaty.pnt', 'Type': '0x2f06', 'MiscInfo': 'wiki=bbb.pl'}),
)
@pytest.mark.parametrize('target, answer', TEST_STWORZ_MISC_INFO)
def test_stworz_misc_info(target, answer):
    args = Args()
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    assert plikMp.stworz_misc_info(OrderedDict(target)) == answer

TEST_AUTO_PLIK_POI_WYKLUCZENIE = (
    ('OLSZTYN.BP.paliwo.pnt', True),
    ('OLSZTYN.paczkom.pnt', False),
)
@pytest.mark.parametrize('target, answer', TEST_AUTO_PLIK_POI_WYKLUCZENIE)
def test_czy_plik_jest_wykluczony(target, answer):
    assert mont_demont.autoPlikDlaPoi().czy_plik_jest_wykluczony(target) == answer

TEST_PLIK_TYP_DANE = (
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty1.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Lodz/src/POI-Belchatow.bankomaty.pnt', 'Typ': 'ATMBANK', 'Type': '0x2f06'},
    {'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0xe00'},
    {'Plik': 'UMP-PL-Lodz/src/cities-Belchatow.pnt', 'Type': '0xe00'},
)

TEST_AUTO_PLIK_POI_WYKLUCZENIE = (
    # (('Lodz', 'ATMBANK',), 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt'),
    # (('Leszno', 'ATMBANK',), 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt'),
    (('Lodz', 'MIASTO',), 'UMP-PL-Lodz/src/cities-Lodz.pnt'),
    # (('Leszno', 'MIASTO',), 'UMP-PL-Leszno/src/cities-Leszno.pnt'),
)
@pytest.mark.parametrize('target, answer', TEST_AUTO_PLIK_POI_WYKLUCZENIE)
def test_zwroc_plik_dla_typu(target, answer):
    auto_plik = mont_demont.autoPlikDlaPoi()
    for dane_do_zapisu in TEST_PLIK_TYP_DANE:
        auto_plik.dodaj_plik_dla_poi(dane_do_zapisu)
    assert auto_plik.zwroc_plik_dla_typu(target[0], target[1]) == answer

TEST_POPRAWNOSC_DANYCH_LABEL_POI = (
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': 'Bank Spoldzielczy', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Miasto': 'Wyki',
    'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, ''),
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Miasto': 'Wyki',
    'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'brak_label'),
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': '', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Miasto': 'Wyki',
    'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'brak_label'),
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': 'ATM', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Miasto': '',
    'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'brak_miasto'),
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': 'ATM', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
      'Data0': '(51.82457,17.57944)',
      'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'brak_miasto'),
    ({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': '', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
      'Data0': '(51.82457,17.57944)',
      'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'brak_label'),
    ({'POIPOLY': '[POI]', 'Type': '0xe00', 'Label': 'Golkowo', 'City': 'Y', 'Data0': '(51.60143,17.51641)',
      'Miasto': 'Golkowo', 'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Rozmiar': '0'}, ''),
    ({'POIPOLY': '[POI]', 'Type': '0xe00', 'Label': '', 'City': 'Y', 'Data0': '(51.60143,17.51641)',
      'Miasto': 'Golkowo', 'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Rozmiar': '0'}, 'brak_nazwy_miasta'),
    ({'POIPOLY': '[POI]', 'Type': '0xe00', 'City': 'Y', 'Data0': '(51.60143,17.51641)',
      'Miasto': 'Golkowo', 'Plik': 'UMP-PL-Leszno/src/cities-Leszno.pnt', 'Rozmiar': '0'}, 'brak_nazwy_miasta'),
)
@pytest.mark.parametrize('target, answer', TEST_POPRAWNOSC_DANYCH_LABEL_POI)
def test_testy_poprawnosci_danych_label_poi(target, answer):
    args = Args()
    tester_poprawnosci_danych = mont_demont.TestyPoprawnosciDanych(args)
    assert tester_poprawnosci_danych.sprawdz_label_dla_poi(target) == answer

TEST_POPRAWNOSCI_DANYCH_MIASTO_LABEL_POLY = (
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'miasto potrzebne',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': '{rondo Solidarnosci}', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, '',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': '~XXX rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'miasto potrzebne',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': '~XXX {rondo Solidarnosci}', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, '',),
)
@pytest.mark.parametrize('target, answer', TEST_POPRAWNOSCI_DANYCH_MIASTO_LABEL_POLY)
def test_testy_poprawnosci_danych_label_miasto(target, answer):
    args = Args()
    tester_poprawnosci_danych = mont_demont.TestyPoprawnosciDanych(args)
    assert tester_poprawnosci_danych.sprawdz_label_dla_poly(target) == answer

TEST_POPRAWNOSC_DANYCH_DATA_0_ONLY = (
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Data1': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'Data1_POLY',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data1': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'Data1_POLY',),
    ({'POIPOLY': '[POLYGON]', 'Type': '0x14', 'EndLevel': '2',
      'Data0': '(51.38958,19.39735),(51.38938,19.39714),(51.38924,19.39739),(51.38725,19.39673),(51.38714,19.39623),(51.38715,19.39556),(51.38725,19.39513),(51.38730,19.39456),(51.38735,19.39364),(51.38893,19.39361),(51.38906,19.39422),(51.38799,19.39428),(51.38799,19.39512),(51.38938,19.39531),(51.38991,19.39733)',
      'Data1': '(51.38851,19.39563),(51.38838,19.39544),(51.38810,19.39537),(51.38797,19.39557),(51.38810,19.39585),(51.38836,19.39585)',
      'Data2': '(51.38768,19.39593),(51.38768,19.39580),(51.38756,19.39583),(51.38743,19.39570),(51.38726,19.39573),(51.38717,19.39603),(51.38719,19.39632),(51.38725,19.39656),(51.38751,19.39660),(51.38757,19.39622),(51.38760,19.39598)',
      'Plik': 'UMP-PL-Lodz/src/BELCHATOW.zielone.txt'}, '',),
    ({'POIPOLY': '[POI]', 'Type': '0x2800', 'Label': '43', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Data1': '(51.82457,17.57944)', 'Miasto': 'Wyki',
    'Plik': 'UMP-PL-Leszno/src/gRozdrazew_2017i.adr', 'KodPoczt': '63-708', 'Typ': 'ADR'}, 'Data1_POI'),
)
@pytest.mark.parametrize('target, answer', TEST_POPRAWNOSC_DANYCH_DATA_0_ONLY)
def test_testy_poprawnosci_danych_tylko_data0_dla_drog(target, answer):
    args = Args()
    tester_poprawnosci_danych = mont_demont.TestyPoprawnosciDanych(args)
    assert tester_poprawnosci_danych.sprawdzData0Only(target) == answer

# testujemy poprawne rondo
TEST_POPRAWNOSC_DANYCH_RONDO = (
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2',
      'DirIndicator': '1', 'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)', 'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, '',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'brak_DirIndicator',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-GB-Leszno/src/LESZNO.ulice.txt'}, 'ODWROTNE',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2',
      'DirIndicator': '1', 'Data0': '(51.84588,16.58070),(51.84595,16.58066)', 'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'NIE_WIEM',),
)
@pytest.mark.parametrize('target, answer', TEST_POPRAWNOSC_DANYCH_RONDO)
def test_testy_poprawnosci_danych_kierukowosc_ronda(target, answer):
    args = Args()
    tester_poprawnosci_danych = mont_demont.TestyPoprawnosciDanych(args)
    assert tester_poprawnosci_danych.testuj_kierunkowosc_ronda(target) == answer


TEST_DATA_0_ONLY = (
({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': 'ATM', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
      'Data0': '(51.82457,17.57944)',
      'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, ''),
({'POIPOLY': '[POI]', 'Type': '0x2f06', 'Label': 'ATM', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
      'Data0_1': '(51.82457,17.57944)', 'Data0_2': '(51.82457,17.57944)',
      'Plik': 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt', 'KodPoczt': '63-708', 'Typ': 'ATMBANK'}, 'Data1'),
)
@pytest.mark.parametrize('target, answer', TEST_DATA_0_ONLY)
def test_testuj_wielokrotne_data(target, answer):
    args = Args()
    testy_poprawnosci_danych = mont_demont.TestyPoprawnosciDanych(args)
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    assert plikMp.testuj_wielokrotne_data(target, testy_poprawnosci_danych) == answer

TEST_ZAOKRAGLIJ = (
    (('(51.55555,29.55555)', '5',), '(51.55555,29.55555)'),
    (('(51.555555,29.555555)', '6',), '(51.555555,29.555555)'),
    (('(51.55555,29.55555)', '6',), '(51.555550,29.555550)'),
    (('(51.555555,29.555555)', '5',), '(51.55555,29.55555)'),
    (('(51.555555,29.555555)', '7',), '(51.555555,29.555555)'),
)
@pytest.mark.parametrize('target, answer', TEST_ZAOKRAGLIJ)
def test_testuj_wielokrotne_data(target, answer):
    data, dokladnosc = target
    assert mont_demont.plikMP1.zaokraglij(data, dokladnosc) == answer

TEST_KOMENTARZ_NA_OTWARTE_I_ENTRYPOINT = (
    (([';EntryPoint:(55.55555,22.22222)\n;;Otwarte:Pn-Nie\nala ma kota'],
      [';EntryPoint:(55.55555,22.22222)\n;;Otwarte:Pn-Nie\nala ma kota', '[POI]', 'Type=0x2800',
       'Label=78', 'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)',
       'Miasto=Zagerze', 'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),
    ([';EntryPoint:(55.55555,22.22222)\n;;Otwarte:Pn-Nie\nala ma kota'],
     [';EntryPoint:(55.55555,22.22222)\n;;Otwarte:Pn-Nie\nala ma kota', '[POI]', 'Type=0x2800', 'Label=78',
      'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)', 'Miasto=Zagerze',
                        'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR'])),
    (([';;EntryPoint:(55.55555,22.22222)\n;Otwarte:Pn-Nie\nala ma kota'],
      [';;EntryPoint:(55.55555,22.22222)\n;Otwarte:Pn-Nie\nala ma kota', '[POI]', 'Type=0x2800',
       'Label=78', 'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)',
       'Miasto=Zagerze', 'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),
    (['ala ma kota'], ['ala ma kota', '[POI]', 'Type=0x2800', 'Label=78', 'HouseNumber=78',
                        'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)', 'Miasto=Zagerze',
                        'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR',
                        'EntryPoint=(55.55555,22.22222)','Otwarte=Pn-Nie']),),
    (([';;EntryPoint=(55.55555,22.22222)\nala ma kota\n;;otwarte=Pn-Nie'],
      [';;EntryPoint=(55.55555,22.22222)\nala ma kota\n;;otwarte=Pn-Nie', '[POI]', 'Type=0x2800',
       'Label=78', 'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)',
       'Miasto=Zagerze', 'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),
    (['ala ma kota\n;;otwarte=Pn-Nie'], ['ala ma kota\n;;otwarte=Pn-Nie', '[POI]', 'Type=0x2800', 'Label=78', 'HouseNumber=78',
                        'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)', 'Miasto=Zagerze',
                        'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR',
                        'EntryPoint=(55.55555,22.22222)']),),
    (([';otwarte=Pn-Nie\n;;EntryPoint:(55.55555,22.22222)\nala ma kota'],
      [';otwarte=Pn-Nie\n;;EntryPoint:(55.55555,22.22222)\nala ma kota', '[POI]', 'Type=0x2800',
       'Label=78', 'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)',
       'Miasto=Zagerze', 'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),
    (['ala ma kota'], ['ala ma kota', '[POI]', 'Type=0x2800', 'Label=78', 'HouseNumber=78',
                        'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)', 'Miasto=Zagerze',
                        'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR',
                        'EntryPoint=(55.55555,22.22222)', 'Otwarte=Pn-Nie']),),
    (([';komentarz3\n;komentarz2\n;komentarz1'],
      [';komentarz3\n;komentarz2\n;komentarz1', '[POI]', 'Type=0x2800',
       'Label=78', 'HouseNumber=78', 'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)',
       'Miasto=Zagerze', 'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),
    ([';komentarz3\n;komentarz2\n;komentarz1'], [';komentarz3\n;komentarz2\n;komentarz1', '[POI]', 'Type=0x2800',
                        'Label=78', 'HouseNumber=78',
                        'StreetDesc=Zagrze', 'Data0=(51.87048,19.94907)', 'Miasto=Zagerze',
                        'Plik=UMP-PL-Lodz/src/gSlupia_2017i.adr', 'KodPoczt=96-128', 'Typ=ADR']),),
)

@pytest.mark.parametrize('target, answer', TEST_KOMENTARZ_NA_OTWARTE_I_ENTRYPOINT)
def test_testuj_wielokrotne_data(target, answer):
    args = Args()
    args.cityidx = False
    args.entry_otwarte_to_extras = True
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, None)
    obiekt_na_mapie = mont_demont.ObiektNaMapie('jakis_plik', [], tabKonw, args)
    obiekt_na_mapie.Dane1 = target[1]
    obiekt_na_mapie.Komentarz = target[0]
    obiekt_na_mapie.komentarz_na_entrypoint_i_otwarte()
    assert obiekt_na_mapie.Dane1 == answer[1]


TEST_KIERUNKOWOSC_RONDA = {
    ('(51.22184,19.04221),(51.22177,19.04218),(51.22172,19.04221),(51.22167,19.04231),(51.22168,19.04245),(51.22175,19.04252),(51.22183,19.04251),(51.22188,19.04243),(51.22189,19.04232),(51.22184,19.04221)', -1),
}
@pytest.mark.parametrize('target, answer', TEST_KIERUNKOWOSC_RONDA)
def testuj_clockwisecheck(target, answer):
    assert mont_demont.TestyPoprawnosciDanych.clockwisecheck(target) == answer

TEST_PACZOWANIE_GRANIC_CZESCIOWYCH = (
    ('granice_1.diff', 'granice_1_OK.diff',),
    ('granice_2.diff', 'granice_2_OK.diff',),
    ('granice_3.diff', 'granice_3_OK.diff',),
    ('granice_4.diff', 'granice_4_OK.diff',),
    ('granice_5.diff', 'granice_5_OK.diff',),
    ('granice_6.diff', 'granice_6_OK.diff',),
    ('granice_7.diff', 'granice_7_OK.diff',),
    ('granice_8.diff', 'granice_8_OK.diff',),
    ('granice_9.diff', 'granice_9_OK.diff',),
)

@pytest.mark.parametrize('target, answer', TEST_PACZOWANIE_GRANIC_CZESCIOWYCH)
def testuj_konwertuj_latke(target, answer):
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    paczer_granic = mont_demont.PaczerGranicCzesciowych(Zmienne, 'granice.txt')
    with open(target, 'r') as granice_test_file:
        granice_test_target = granice_test_file.readlines()
    with open(answer, 'r') as granice_test_answer_file:
        granice_test_answer = granice_test_answer_file.readlines()
    assert paczer_granic.konwertujLatke(granice_test_target) == granice_test_answer

TEST_PACZOWANIE_GRANIC_CZESCIOWYCH_PODZIAL_NA_REKORDY = (
    ('granice_9.diff', 'granice_9_malpki.diff',),
)
@pytest.mark.parametrize('target, answer', TEST_PACZOWANIE_GRANIC_CZESCIOWYCH_PODZIAL_NA_REKORDY)
def testuj_konwertuj_latke(target, answer):
    with open(target, 'r') as granice_test_file:
        granice_test_target = granice_test_file.readlines()
    with open(answer, 'r') as granice_test_answer_file:
        granice_test_answer = granice_test_answer_file.readlines()
    assert mont_demont.PaczerGranicCzesciowych.zamien_komentarz_na_malpki(granice_test_target) == granice_test_answer

TEST_USUN_PUSTA_NUMERACJE = (
    (OrderedDict({'Numbers1': '2,B,10,10,N,-1,-1,97-330,-1,-1,-1', 'Numbers2': '3,N,-1,-1,N,-1,-1'}), OrderedDict({'Numbers1': '2,B,10,10,N,-1,-1,97-330,-1,-1,-1', 'Numbers2': '3,N,-1,-1,N,-1,-1'}),),
    (OrderedDict({'Numbers21': '23,N,-1,-1,N,-1,-1'}), OrderedDict({},),),
)

@pytest.mark.parametrize('target, answer', TEST_USUN_PUSTA_NUMERACJE)
def testuj_usun_pusta_numeracje(target, answer):
    assert mont_demont.plikMP1.usun_pusta_numeracje(target) == answer
