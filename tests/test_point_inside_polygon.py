import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import znajdz_wystajace
from collections import OrderedDict

class Args(object):
    def __init__(self):
        pass


TEST_POINT_INSIDE = ()

@pytest.mark.parametrize('target, answer', )
def test_point_inside_polygone(target, answer)