import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import znajdz_bledy_numeracji

TEST_NUMERACJA = (
    (['', 'E', '2', '4', 'O', '1', '3'], '',),
    (['', 'N', '-1', '-1', 'O', '1', '3'], '',),
    (['', 'N', '-1', '-1', 'B', '1', '4'], '',),
    (['', 'N', '-1', '-1', 'E', '1', '2'], '(E,1,2)',),
    (['', 'E', '3', '2', 'N', '-1', '-1'], '(E,3,2)',),
    (['', 'O', '2', '4', 'O', '1', '3'], '(O,2,4)',),
    (['', 'E', '6', '8', 'O', '2', '4'], '(O,2,4)',),
    (['', 'O', '2', '5', 'O', '1', '3'], '(O,2,5)',),
)

@pytest.mark.parametrize('target, answer', TEST_NUMERACJA)
def test_sprawdzParzystosc(target, answer):
    wynik_testu = znajdz_bledy_numeracji.Mapa.sprawdzParzystosc(target)
    rezultat_testu = ''
    if wynik_testu:
        rezultat_testu = '(' + wynik_testu[0].split('(')[1]
    assert rezultat_testu == answer


TEST_ZWROC_REKORD_MP = (
    (['[POI]', 'Type=0x1', 'Label=aaa', 'Data0=(11.11111,11.11111)', '[END]'], ([], [], [])),
    (['[POLYLINE]', 'Type=0x1', 'Label=aaa', 'Data0=(11.11111,11.11111),(11.11111,11.11111)', '[END]'],
     ([{'Type': '0x1', 'Data0': '(11.11111,11.11111),(11.11111,11.11111)'}], [], [])),
    (['[POLYLINE]', 'Type=0x1', 'Label=aaa', 'Data0=(11.11111,11.11111),(11.11111,11.11111)', '', ';komentarz', '[POLYLINE]', 'Type=0x1', 'Label=aaa', 'Data0=(22.22222,22.22222),(22.22222,22.22222)', '[END]'],
     ([{'Type': '0x1', 'Data0': '(22.22222,22.22222),(22.22222,22.22222)'}], [], [])),
    (['[POLYLINE]', 'Type=0x1', 'Data0=(11.11111,11.11111),(11.11111,11.11111)', '[END]', '', '[POLYLINE]', 'Type=0x19', 'Data0=(11.11111,11.11111),(11.11111,11.11111),(11.11111,11.11111)', '[END]', ''],
     ([{'Type': '0x1', 'Data0': '(11.11111,11.11111),(11.11111,11.11111)'}], [{'Type': '0x19', 'Data0': '(11.11111,11.11111),(11.11111,11.11111),(11.11111,11.11111)'}], [])),
)

@pytest.mark.parametrize('target, answer', TEST_ZWROC_REKORD_MP)
def test_sprawdz_zwroc_rekord_mp(target, answer):
    wynik_testu = znajdz_bledy_numeracji.Mapa.zwroc_rekordy_pliku_mp(target)
    assert wynik_testu == answer
