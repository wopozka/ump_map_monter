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
