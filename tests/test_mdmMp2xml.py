import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mdmMp2xml

TEST_NORMALIZATION = (
        ('1_node1', '1_node1'),
        # ('2_node2', '2_node2'),
        # ('3_node3', '3_node3'),
        # (('node', 1, 11), 11),
        # (('node', 2, 11), 21),
        # (('node', 2, 20), 30),
        # (('node', 3, 11), 31),
        # (('node', 3, 20), 40),
        # (('way', 1, 1), 41),
        # (('way', 1, 10), 51),

)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZATION)
def test_normalization_ids(target, answer):
    nodes_list = list()
    ways_list = list()
    relations_list = list()
    ids_normalizer = mdmMp2xml.NodeGeneralizator(test_mode=True)
    ids_normalizer.border_point_ids = tuple(a+1 for a in range(10))
    nodes_list.append([a for a in range(10)])
    nodes_list.append(['1_node' + str(a) for a in range(10)])
    nodes_list.append(['2_node' + str(a) for a in range(10)])
    nodes_list.append(['3_node' + str(a) for a in range(10)])
    ways_list.append(['1_way' + str(a) for a in range(10)])
    ways_list.append(['2_way' + str(a) for a in range(10)])
    ways_list.append(['3_way' + str(a) for a in range(10)])
    relations_list.append(['1_node' + str(a) for a in range(10)])
    relations_list.append(['2_node' + str(a) for a in range(10)])
    relations_list.append(['3_node' + str(a) for a in range(10)])
    all_points = nodes_list[0] + nodes_list[1] + nodes_list[2] + nodes_list[3] + ways_list[0] + ways_list[1] \
                 + ways_list[2] + relations_list[0] + relations_list[1] + relations_list[2]

    for b in range(3):
        ids_normalizer.set_ofsets([[a for a in range(10)], [a for a in range(10)], [a for a in range(10)]])
    ids_normalizer.initialize_ofsets()
    if 'node' in target:
        groupid, node = target.split('_')
        assert ids_normalizer.get_node_id(int(groupid), nodes_list[int(groupid)].index(target))\
               == all_points.index(answer)
    elif 'way' in target:
        groupid, node = target.split('_')
        assert ids_normalizer.get_way_id(int(groupid), ways_list[int(groupid)].index(target)) \
               == all_points.index(answer)
    elif 'relation' in target:
        groupid, node = target.split('_')
        assert ids_normalizer.get_relation_id(int(groupid), relations_list[int(groupid)].index(target)) \
               == all_points.index(answer)
