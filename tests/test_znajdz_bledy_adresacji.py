import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import znajdz_bledy_adresacji
from znajdz_bledy_adresacji import OdcinekNumeracji


TEST_NORMALIZUJ_NAZWE = (
    ('Główna', 'główna'),
    ('  Główna   Ulica ', 'główna ulica'),
    ('~[0x2f]Główna', ''),
    ('~[0x2f] Główna', 'główna'),
    ('{ul.}Główna', 'główna'),
)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZUJ_NAZWE)
def test_normalizuj_nazwe(target, answer):
    assert znajdz_bledy_adresacji.normalizuj_nazwe(target) == answer


TEST_NUMER_BEZ_LITERY = (
    ('12', 12),
    (' 7 ', 7),
    ('12a', None),
    ('12/14', None),
    ('', None),
)

@pytest.mark.parametrize('target, answer', TEST_NUMER_BEZ_LITERY)
def test_numer_bez_litery(target, answer):
    assert znajdz_bledy_adresacji.numer_bez_litery(target) == answer


PUNKTY_DROGI = [(52.0, 21.0), (52.0, 21.001), (52.0, 21.002), (52.0, 21.003)]


def test_odcinki_numeracji_podzial_i_strony():
    numeracje = ['0,O,1,11,E,2,12', '2,N,-1,-1,E,14,20,00-001,00-002,Inne,,,,,']
    odcinki = znajdz_bledy_adresacji.odcinki_numeracji(PUNKTY_DROGI, numeracje, 'Miasto')
    assert odcinki == [
        ('miasto', OdcinekNumeracji(1, 11, 'O', '', PUNKTY_DROGI[0:3])),
        ('miasto', OdcinekNumeracji(2, 12, 'E', '', PUNKTY_DROGI[0:3])),
        ('miasto', OdcinekNumeracji(14, 20, 'E', '00-002', PUNKTY_DROGI[2:4])),
    ]


def test_odcinki_numeracji_kod_pocztowy():
    # kod z Numbers ma pierwszenstwo przed KodPoczt= drogi
    numeracje = ['0,O,1,11,E,2,12,11-111,-1']
    odcinki = znajdz_bledy_adresacji.odcinki_numeracji(PUNKTY_DROGI, numeracje, 'Miasto', '99-999')
    assert [odcinek.kod for _, odcinek in odcinki] == ['11-111', '99-999']


TEST_KODY_ZGODNE = (
    ('11-111', '11-111', True),
    ('11-111', '22-222', False),
    ('', '22-222', True),
    ('11-111', '', True),
)

@pytest.mark.parametrize('kod1, kod2, answer', TEST_KODY_ZGODNE)
def test_kody_zgodne(kod1, kod2, answer):
    assert znajdz_bledy_adresacji.kody_zgodne(kod1, kod2) == answer


def test_odcinki_numeracji_miasto_strony():
    numeracje = ['0,O,1,11,E,2,12,,,Lewe,,,Prawe,,']
    odcinki = znajdz_bledy_adresacji.odcinki_numeracji(PUNKTY_DROGI, numeracje, 'Miasto')
    assert [miasto for miasto, _ in odcinki] == ['lewe', 'prawe']


TEST_WARTOSC_T = (
    (5, OdcinekNumeracji(1, 11, 'O', '', []), 0.4),
    (5, OdcinekNumeracji(11, 1, 'O', '', []), 0.6),
    (6, OdcinekNumeracji(1, 11, 'O', '', []), None),
    (13, OdcinekNumeracji(1, 11, 'O', '', []), None),
    (6, OdcinekNumeracji(2, 12, 'E', '', []), 0.4),
    (6, OdcinekNumeracji(1, 11, 'B', '', []), 0.5),
    (3, OdcinekNumeracji(3, 3, 'O', '', []), 0.5),
)

@pytest.mark.parametrize('numer, odcinek, answer', TEST_WARTOSC_T)
def test_wartosc_t_dla_numeru(numer, odcinek, answer):
    assert znajdz_bledy_adresacji.wartosc_t_dla_numeru(numer, odcinek) == answer


def test_interpoluj_punkt():
    lamana = [(52.0, 21.0), (52.0, 21.001), (52.001, 21.001)]
    assert znajdz_bledy_adresacji.interpoluj_punkt(lamana, 0) == (52.0, 21.0)
    assert znajdz_bledy_adresacji.interpoluj_punkt(lamana, 1) == (52.001, 21.001)
    # pierwszy odcinek jest krotszy od drugiego (cos(52) * 0.001 < 0.001), wiec polowa wypada na drugim
    szerokosc, dlugosc = znajdz_bledy_adresacji.interpoluj_punkt(lamana, 0.5)
    assert dlugosc == pytest.approx(21.001)
    assert 52.0 < szerokosc < 52.001


def test_odleglosc_m():
    # 0.001 stopnia szerokosci to ok. 111 m
    assert znajdz_bledy_adresacji.odleglosc_m((52.0, 21.0), (52.001, 21.0)) == pytest.approx(111.2, abs=0.5)


PLIK_MP = """[POLYLINE]
Type=0x6
Label=~[0x2f] Główna
Miasto=Testowo
Data0=(52.00000,21.00000),(52.00000,21.01000)
Numbers1=0,O,1,21,E,2,22
[END]

[POI]
Type=0x2800
Label=11
StreetDesc=Główna
Miasto=Testowo
Data0=(52.00020,21.00500)
[END]

[POI]
Type=0x2800
Label=3
StreetDesc=Główna
Miasto=Testowo
Data0=(52.00020,21.00800)
[END]

[POI]
Type=0x2800
Label=3a
StreetDesc=Główna
Miasto=Testowo
Data0=(52.00020,21.00100)
[END]

[POI]
Type=0x2800
Label=101
StreetDesc=Główna
Miasto=Testowo
Data0=(52.00020,21.00100)
[END]

[POI]
Type=0x2800
Label=1
StreetDesc=Boczna
Miasto=Testowo
Data0=(52.00020,21.00100)
[END]
"""


class Writer(object):
    def __init__(self):
        self.stderr = []
        self.stdout = []

    def stderrorwrite(self, komunikat):
        self.stderr.append(komunikat)

    def stdoutwrite(self, komunikat):
        self.stdout.append(komunikat)


def test_sprawdz():
    punkty_adresowe, drogi = znajdz_bledy_adresacji.zwroc_rekordy_pliku_mp(PLIK_MP.split('\n'))
    sprawdzanie = znajdz_bledy_adresacji.SprawdzanieAdresacji(punkty_adresowe, drogi)
    assert sprawdzanie.pominiete_z_litera == 1
    wyniki = sprawdzanie.sprawdz(150)
    # nr 3 powinien byc przy poczatku drogi (21.0005), a jest ok. 500 m dalej
    assert [(p.numer, round(d, -2)) for p, d, _, _ in wyniki['za_daleko']] == [(3, 500)]
    assert [p.numer for p in wyniki['brak_numeru']] == [101]
    assert [p.ulica for p in wyniki['brak_ulicy']] == ['Boczna']


def test_main(tmp_path):
    plik = tmp_path / 'wynik.mp'
    plik.write_text(PLIK_MP, encoding='cp1250')
    writer = Writer()
    znajdz_bledy_adresacji.main(str(plik), writer, 150)
    assert len(writer.stderr) == 2
    assert writer.stderr[0].startswith('Adres-za daleko: Główna 3, Testowo')
    assert writer.stderr[1].startswith('Adres-brak numeracji liniowej: Główna 101, Testowo')
    raport = (tmp_path / 'wynik_bledy_adresacji.txt').read_text(encoding='cp1250').splitlines()
    assert len(raport) == 3
    assert raport[2].startswith('Adres-ulica bez numeracji liniowej: Boczna 1')


# dwie miejscowosci Testowo z ulica Glowna: 11-111 (szerokosc 52) i 22-222 (szerokosc 53)
PLIK_MP_KODY = """[POLYLINE]
Type=0x6
Label=Główna
Miasto=Testowo
KodPoczt=11-111
Data0=(52.00000,21.00000),(52.00000,21.01000)
Numbers1=0,O,1,21,E,2,22
[END]

[POLYLINE]
Type=0x6
Label=Główna
Miasto=Testowo
Data0=(53.00000,21.00000),(53.00000,21.01000)
Numbers1=0,O,1,21,E,2,22,22-222,22-222
[END]

[POI]
Type=0x2800
Label=3
StreetDesc=Główna
Miasto=Testowo
KodPoczt=22-222
Data0=(52.00020,21.00100)
[END]

[POI]
Type=0x2800
Label=5
StreetDesc=Główna
Miasto=Testowo
Data0=(53.00020,21.00200)
[END]

[POI]
Type=0x2800
Label=9
StreetDesc=Główna
Miasto=Testowo
KodPoczt=22-222
Data0=(52.00020,21.00900)
[END]
"""


def test_sprawdz_kody_pocztowe():
    punkty_adresowe, drogi = znajdz_bledy_adresacji.zwroc_rekordy_pliku_mp(PLIK_MP_KODY.split('\n'))
    wyniki = znajdz_bledy_adresacji.SprawdzanieAdresacji(punkty_adresowe, drogi).sprawdz(150)
    # nr 3 z kodem 22-222 lezy tuz przy numeracji Testowa 11-111 (do Testowa 22-222 jest ok. 111 km)
    # - polozenie sie zgadza, rozni sie tylko kod pocztowy
    assert [(p.numer, round(d, -1), kod) for p, d, _, kod in wyniki['inny_kod']] == [(3, 20, '11-111')]
    # nr 9 z kodem 22-222 jest za daleko od obu miejscowosci - raportujemy najblizsza, czyli Testowo 11-111,
    # a nie Testowo 22-222 ze zgodnym kodem
    assert [(p.numer, round(d, -2), kod) for p, d, _, kod in wyniki['za_daleko']] == [(9, 300, '11-111')]
    # nr 5 bez kodu pasuje do obu miejscowosci - bierzemy blizsza
    assert wyniki['brak_numeru'] == []
    assert wyniki['brak_ulicy'] == []
