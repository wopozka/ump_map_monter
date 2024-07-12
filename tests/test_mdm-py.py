import pytest
import sys
import os.path
import importlib
from mont_demont import UstawieniaPoczatkowe
from tempfile import NamedTemporaryFile
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
mdm_py = importlib.import_module('mdm-py')

CZY_KLUCZE_OK_I_BRAK_KONFLIKTOW = (
    ('Data0=aaa\nLabel=', (set(), set()),),
)

@pytest.mark.parametrize('target, answer', CZY_KLUCZE_OK_I_BRAK_KONFLIKTOW)
def test_cvs_sprawdz_czy_tylko_dozwolone_klucze_i_brak_konfliktow(target, answer):
    tmp_file = NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
    tmp_file.write(target)
    tmp_file.close()
    zmienne = UstawieniaPoczatkowe('wynik.mp')
    zmienne.KatalogzUMP, nazwa_pliku = os.path.split(tmp_file.name)
    if answer[0]:
        _answer0 = {nazwa_pliku: answer[0]}
    else:
        answer0 = {}
    if answer[1]:
        answer1 = {nazwa_pliku}
    else:
        answer1 = set()
    assert mdm_py.cvs_sprawdz_czy_tylko_dozwolone_klucze_i_brak_konfliktow([nazwa_pliku], zmienne) == (answer0, answer1)
    os.remove(tmp_file.name)
