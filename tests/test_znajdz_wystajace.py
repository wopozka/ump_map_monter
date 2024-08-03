import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import znajdz_wystajace

TEST_ZNAJDZ_WYSTAJACE = (
    # ((51.97663, 20.13882, 'Lodz',), True,),
    ((50.28584, 17.66668, 'Poznan',), False),
)

@pytest.mark.parametrize('target, answer', TEST_ZNAJDZ_WYSTAJACE)
def test_is_inside(target, answer):
    test_case = znajdz_wystajace.PolygonyObszarow('obszary.txt', test_mode=True)
    assert test_case.is_inside(target[0], target[1], nazwaobszaru=target[2]) == answer
