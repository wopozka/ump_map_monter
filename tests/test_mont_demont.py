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
    (';;Gmina=Rozdrazew\n\n[POI]\nType=0x2800\nLabel=1\nHouseNumber=1\nStreetDesc=Wygoda\nData0=(51.78184,17.44398)\nMiasto=Wygoda\nPlik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr\nKodPoczt=63-708\nTyp=ADR\n',
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
        [';;Gmina=Rozdrazew', '[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00', 'EntryPoint=(51.77364,17.46213)',
         '[END]\n'
        ]
    ),
    (
        [
         ';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00',
         '51.77364,  17.46213,  0,1,Debowiec;1,Debowiec,ADR,63-708',
        ],
        ['[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00', '[END]\n'
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
        ['[POI]', 'Type=0x2800', 'Label=1', 'HouseNumber=1', 'StreetDesc=Debowiec',
         'Data0=(51.77364,17.46213)', 'Miasto=Debowiec', 'Plik=UMP-PL-Leszno/src/gRozdrazew_2017i.adr',
         'KodPoczt=63-708', 'Typ=ADR', 'EntryPoint=(51.77364,17.46213)', '[END]\n'
        ]
    ),
)

@pytest.mark.parametrize('target, answer', TEST_ADR_TO_MP)
def test_plik_pnt_procesuj(target, answer):
    args = Args()
    args.cityidx = False
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    globalneIndeksy = mont_demont.IndeksyMiast()
    punkt_z_adr = mont_demont.Adr('UMP-PL-Leszno/src/gRozdrazew_2017i.adr', globalneIndeksy, tabKonw, args)
    przetwarzanyPlik = mont_demont.plikPNT('UMP-PL-Leszno/src/gRozdrazew_2017i.adr', args, punkt_z_adr)
    zawartoscPlikuADR = target
    assert przetwarzanyPlik.procesuj(zawartoscPlikuADR) == answer

TEST_ENTRYPOINT_OTWARTE_NA_KOMENTARZ = (
    ({'EntryPoint': '(51.77364,17.46213)', 'Otwarte': 'Mo-Sa 6:00-24:00; Su 7:00-24:00'}, {'Komentarz': [';;EntryPoint:(51.77364,17.46213)', ';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00']}),
    ({'Komentarz': ['la la la'], 'EntryPoint': '(51.77364,17.46213)', 'Otwarte': 'Mo-Sa 6:00-24:00; Su 7:00-24:00'}, {'Komentarz': ['la la la', ';;EntryPoint:(51.77364,17.46213)', ';;Otwarte=Mo-Sa 6:00-24:00; Su 7:00-24:00']}),

)

@pytest.mark.parametrize('target, answer', TEST_ENTRYPOINT_OTWARTE_NA_KOMENTARZ)
def test_entrypoint_otwarte_na_komentarz(target, answer):
    assert mont_demont.plikMP1.przenies_otwarte_i_entrypoint_do_komentarza(OrderedDict(target)) == answer

TEST_MODYFIKUJ_PLIK_DLA_POI = (
    ({'Label': 'label', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Label': 'label', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}),
    ({'Label': 'label', 'Plik': 'UMP-PL-Lodz/crs/POI-Lodz.bankomaty.pnt', 'Type': '0x2f06'}, {'Label': 'label', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
    ({'Label': 'label', 'Plik': 'UMP-PL-Lodz/crs/POI-Lodz.bankomaty.pnt', 'Type': '0x2000'}, {'Label': 'label', 'Plik': '_nowosci.txt', 'Type': '0x2000'}),
    ({'Label': 'label', 'Plik': '', 'Type': '0x2000'},{'Label': 'label', 'Plik': '_nowosci.txt', 'Type': '0x2000'}),
    ({'Label': 'label', 'Plik': '', 'Type': '0x2f06'}, {'Label': 'label', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
    ({'Label': 'label', 'Type': '0x2f06'}, {'Label': 'label', 'Type': '0x2f06', 'Plik': '_nowosci.pnt'}),
    ({'Label': 'label', 'Type': '0x2000'}, {'Label': 'label', 'Type': '0x2000', 'Plik': '_nowosci.txt'}),
    ({'Label': 'Miasto', 'Plik': 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt', 'Type': '0xd00'}, {'Label': 'Miasto', 'Plik': '_nowosci.pnt', 'Type': '0xd00'}),
    ({'Label': 'ATM', 'Plik': 'UMP-PL-Lodz/src/cities-Lodz.pnt', 'Type': '0x2f06'}, {'Label': 'ATM', 'Plik': '_nowosci.pnt', 'Type': '0x2f06'}),
)
@pytest.mark.parametrize('target, answer', TEST_MODYFIKUJ_PLIK_DLA_POI)
def test_modyfikuj_plik_dla_poi(target, answer):
    args = Args()
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    assert plikMp.modyfikuj_plik_dla_poi(OrderedDict(target)) == answer

TEST_MODYFIKUJ_PLIK_DLA_POLY = (
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel' :'1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.txt'}, False,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.txt'}),
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel' :'1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'UMP-PL-Lodz/src/DOBRA.ulice.pnt'}, False,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': 'XXX'}, False,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': ''}, False,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)'}, False,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)'}, True,), {'POIPOLY': 'POLYLINE', 'Type': '0x6', 'Label': 'Starowiejska', 'EndLevel': '1', 'Data0': '(51.86757,19.56022),(51.86762,19.55950),(51.86768,19.55851),(51.86772,19.55783),(51.86768,19.55755),(51.86675,19.55321),(51.86666,19.55279),(51.86640,19.55173),(51.86624,19.55123),(51.86566,19.54977),(51.86514,19.54834),(51.86476,19.54694),(51.86450,19.54646),(51.86381,19.54534),(51.86352,19.54462),(51.86339,19.54394),(51.86307,19.54107),(51.86299,19.53973)', 'Plik': '_nowosci.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/LODZ.budynki.txt'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.pnt'}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': ''}, True,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': 'UMP-PL-Lodz/src/LODZ.budynki.txt'}),
    (({'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': ''}, False,), {'POIPOLY': '[POLYGON]', 'Type': '0x8', 'Label': 'ms2', 'Data0': '(51.77867,19.44580),(51.77875,19.44699),(51.77895,19.44693),(51.77886,19.44576)', 'Plik': '_nowosci.txt'}),
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
    plikMp.autoobszary.wypelnijObszarPlikWspolrzedne(['UMP-PL-Lodz/src/LODZ.obszary.txt',
                                                      'UMP-PL-Lodz/src/LODZ.budynki.txt',
                                                      'UMP-PL-Lodz/src/LODZ.kolej.txt',
                                                      'UMP-PL-Lodz/src/LODZ.zakazy.txt'
                                                      ])
    assert plikMp.modyfikuj_plik_dla_polygon_polyline(OrderedDict(target[0])) == answer

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
    (('Lodz', 'ATMBANK',), 'UMP-PL-Lodz/src/POI-Lodz.bankomaty.pnt'),
    (('Leszno', 'ATMBANK',), 'UMP-PL-Leszno/src/POI-Leszno.bankomaty.pnt'),
    (('Lodz', 'MIASTO',), 'UMP-PL-Lodz/src/cities-Lodz.pnt'),
    (('Leszno', 'MIASTO',), 'UMP-PL-Leszno/src/cities-Leszno.pnt'),
)
@pytest.mark.parametrize('target, answer', TEST_AUTO_PLIK_POI_WYKLUCZENIE)
def test_zwroc_plik_dla_typu(target, answer):
    auto_plik = mont_demont.autoPlikDlaPoi()
    for dane_do_zapisu in TEST_PLIK_TYP_DANE:
        auto_plik.dodaj_plik_dla_poi(dane_do_zapisu)
    assert auto_plik.zwroc_plik_dla_typu(target[0], target[1]) == answer

TEST_POPRAWNOSC_DANYCH = (
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
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data0': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Data1': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'Data1',),
    ({'POIPOLY': '[POLYLINE]', 'Type': '0xc', 'Label': 'rondo Solidarnosci', 'EndLevel': '2', 'DirIndicator': '1',
      'Data1': '(51.84588,16.58070),(51.84595,16.58066),(51.84599,16.58058),(51.84600,16.58044),(51.84596,16.58034),(51.84590,16.58029),(51.84583,16.58030)',
      'Miasto': 'Leszno', 'Plik': 'UMP-PL-Leszno/src/LESZNO.ulice.txt'}, 'Data1',),
    ({'POIPOLY': '[POI]', 'Type': '0x2800', 'Label': '43', 'HouseNumber': '43', 'StreetDesc': 'Wyki',
    'Data0': '(51.82457,17.57944)', 'Data1': '(51.82457,17.57944)', 'Miasto': 'Wyki',
    'Plik': 'UMP-PL-Leszno/src/gRozdrazew_2017i.adr', 'KodPoczt': '63-708', 'Typ': 'ADR'}, 'Data1'),
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
@pytest.mark.parametrize('target, answer', TEST_POPRAWNOSC_DANYCH)
def test_testy_poprawnosci_danych(target, answer):
    args = Args()
    Zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabKonw = mont_demont.tabelaKonwersjiTypow(Zmienne, stderr_stdout_writer)
    plikMp = mont_demont.plikMP1(Zmienne, args, tabKonw, 0)
    assert plikMp.testy_poprawnosci_danych(target) == answer
