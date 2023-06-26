import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mdmMp2xml

TEST_NORMALIZATION = (
        (('node', 1, 1), 1),
        (('node', 1, 2,), 2),
        (('node', 2, 1), 1),
        (('node', 1, 11), 11),
        (('node', 2, 11), 21),
        (('node', 2, 20), 30),
        (('node', 3, 11), 31),
        (('node', 3, 20), 40),
        (('way', 1, 1), 41),
        (('way', 1, 10), 51),

)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZATION)
def test_normalization_ids(target, answer):
    ids_normalizer = mdmMp2xml.NodeGeneralizator(test_mode=True)
    ids_normalizer.border_point_ids = tuple(a+1 for a in range(10))
    node_1 = tuple(11 + a for a in range(10))
    way_1 = tuple(a for a in range(10))
    relation_1 = tuple(a for a in range(10))

    for a in range(3):
        ids_normalizer.set_ofsets((node_1, way_1, relation_1))
    ids_normalizer.initialize_ofsets()
    if target[0] == 'node':
        assert ids_normalizer.get_node_id(target[1], target[2]) == answer
    if target[0] == 'way':
        assert ids_normalizer.get_way_id(target[1], target[2]) == answer

