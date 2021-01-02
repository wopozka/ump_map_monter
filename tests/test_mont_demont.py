import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mont_demont

class Args(object):
    def __init__(self):
        pass

TEST_ZWROC_REKORD_PLIKU_MP = (
    (
        ';dekomunizacja: J. Krasickiego -> Ignacego Krasickiego\n;Uchwala nr 0007.XXVIII.241.2017 Rady Miejskiej w <AF>migrodzie z dnia 7 czerwca 2017 r.\n[POLYLINE]\nType=0x6\nLabel=Krasickiego\nEndLevel=1\nDirIndicator=1\nData0=(51.46427,16.90135),(51.46412,16.90261),(51.46404,16.90367)\nNumbers1=0,E,14,14,O,9,3\nNumbers2=1,N,-1,-1,O,1,1\nMiasto=Zmigrod\nPlik=UMP-PL-Leszno/src/ZMIGROD.ulice.txt\n',
         ({
            'Komentarz': [';dekomunizacja: J. Krasickiego -> Ignacego Krasickiego', ';Uchwala nr 0007.XXVIII.241.2017 Rady Miejskiej w <AF>migrodzie z dnia 7 czerwca 2017 r.'],
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
)

@pytest.mark.parametrize('target, answer', TEST_ZWROC_REKORD_PLIKU_MP)
def test_zwroc_rekord_pliku_mp(target, answer):
    zmienne = mont_demont.UstawieniaPoczatkowe('wynik.mp')
    args = Args()
    stderr_stdout_writer = mont_demont.errOutWriter(args)
    tabela_konwersji_typow = mont_demont.tabelaKonwersjiTypow(zmienne, stderr_stdout_writer)
    assert mont_demont.plikMP1(zmienne, args, tabela_konwersji_typow, Montuj=0).zwroc_rekord_pliku_mp(target) == (answer, [key for key in answer])


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