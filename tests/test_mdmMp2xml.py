import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mdmMp2xml
from collections import OrderedDict

TEST_NORMALIZATION = (
        (('border', 'filename=1', '0_0',), '0_0'),
        (('border', 'filename=1', '1_0',), '1_0'),
        (('border', 'filename=2', '2_1',), '2_1'),
        (('border', 'filename=3', '3_2',),  '3_2'),
        (('node', 'filename=1', '1_node0',), '1_node0'),
        (('node', 'filename=1', '1_node1',), '1_node1'),
        (('node', 'filename=1', '1_node9',), '1_node9'),
        (('node', 'filename=2', '2_node0',), '2_node0'),
        (('node', 'filename=2', '2_node1',), '2_node1'),
        (('node', 'filename=2', '2_node9',), '2_node9'),
        (('node', 'filename=3', '3_node3',), '3_node3'),
        (('way', 'filename=1', '1_way0',), '1_way0'),
        (('way', 'filename=3', '3_way9',), '3_way9'),
        (('relation', 'filename=1', '1_relation0',), '1_relation0'),
        (('relation', 'filename=2', '2_relation2',), '2_relation2'),
        (('relation', 'filename=3', '3_relation9',), '3_relation9'),
)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZATION)
def test_normalization_ids(target, answer):
    nodes_list = OrderedDict()
    ways_list = OrderedDict()
    relations_list = OrderedDict()
    ids_normalizer = mdmMp2xml.NodeGeneralizator()
    nodes_list_border = ['0_0', '1_0', '1_1', '1_2', '2_0', '2_1', '2_2', '3_0', '3_1', '3_2']
    ids_normalizer.insert_borders(nodes_list_border)
    nodes_list['1'] = ['1_node' + str(a) for a in range(10)]
    nodes_list['2'] = ['2_node' + str(a) for a in range(10)]
    nodes_list['3'] = ['3_node' + str(a) for a in range(10)]
    ways_list['1'] = ['1_way' + str(a) for a in range(10)]
    ways_list['2'] = ['2_way' + str(a) for a in range(10)]
    ways_list['3'] = ['3_way' + str(a) for a in range(10)]
    relations_list['1'] = ['1_relation' + str(a) for a in range(10)]
    relations_list['2'] = ['2_relation' + str(a) for a in range(10)]
    relations_list['3'] = ['3_relation' + str(a) for a in range(10)]
    all_points = nodes_list_border + nodes_list['1'] + nodes_list['2'] + nodes_list['3'] + ways_list['1'] + \
                 ways_list['2'] + ways_list['3'] + relations_list['1'] + relations_list['2'] + relations_list['3']
    for b in range(3):
        ids_normalizer.insert_node(str(b+1), nodes_list[str(b+1)])
        ids_normalizer.insert_way(str(b+1), ways_list[str(b+1)])
        ids_normalizer.insert_relation(str(b+1), relations_list[str(b+1)])
    if 'border' == target[0]:
        file_group_name = target[1].split('=')[1]
        target_index = nodes_list_border.index(target[2])
        assert ids_normalizer.get_node_id(file_group_name, target[2], target_index) == all_points.index(answer) + 1
    if 'node' == target[0]:
        file_group_name = target[1].split('=')[1]
        target_index = nodes_list[file_group_name].index(target[2])
        assert ids_normalizer.get_node_id(file_group_name, target[2], target_index) == all_points.index(answer) + 1
    elif 'way' == target[0]:
        file_group_name = target[1].split('=')[1]
        target_index = ways_list[file_group_name].index(target[2])
        assert ids_normalizer.get_way_id(file_group_name, target_index) == all_points.index(answer) + 1
    elif 'relation' == target[0]:
        file_group_name = target[1].split('=')[1]
        target_index = relations_list[file_group_name].index(target[2])
        assert ids_normalizer.get_relation_id(file_group_name, target_index) == all_points.index(answer) + 1
