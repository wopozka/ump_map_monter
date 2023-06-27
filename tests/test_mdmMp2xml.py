import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mdmMp2xml

TEST_NORMALIZATION = (
        ('1_node0', '1_node0'),
        ('1_node1', '1_node1'),
        ('1_node9', '1_node9'),
        ('2_node0', '2_node0'),
        ('2_node1', '2_node1'),
        ('2_node9', '2_node9'),
        ('3_node3', '3_node3'),
        ('1_way0', '1_way0'),
        ('3_way9', '3_way9'),
        ('1_relation0', '1_relation0'),
        ('2_relation2', '2_relation2'),
        ('3_relation9', '3_relation9'),

)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZATION)
def test_normalization_ids(target, answer):
    nodes_list = list()
    ways_list = list()
    relations_list = list()
    ids_normalizer = mdmMp2xml.NodeGeneralizator(test_mode=True)
    nodes_list_border = [a for a in range(10)]
    ids_normalizer.insert_borders(nodes_list_border)
    nodes_list.append(['1_node' + str(a) for a in range(10)])
    nodes_list.append(['2_node' + str(a) for a in range(10)])
    nodes_list.append(['3_node' + str(a) for a in range(10)])
    ways_list.append(['1_way' + str(a) for a in range(10)])
    ways_list.append(['2_way' + str(a) for a in range(10)])
    ways_list.append(['3_way' + str(a) for a in range(10)])
    relations_list.append(['1_relation' + str(a) for a in range(10)])
    relations_list.append(['2_relation' + str(a) for a in range(10)])
    relations_list.append(['3_relation' + str(a) for a in range(10)])
    all_points = nodes_list_border + nodes_list[0] + nodes_list[1] + nodes_list[2] + ways_list[0] + ways_list[1] \
                 + ways_list[2] + relations_list[0] + relations_list[1] + relations_list[2]
    for b in range(3):
        ids_normalizer.insert_node(nodes_list[b])
        ids_normalizer.insert_way(ways_list[b])
        ids_normalizer.insert_relation(relations_list[b])

    if 'node' in target:
        task_id = int(target.split('_')[0])
        target_index = nodes_list[task_id - 1].index(target)
        assert ids_normalizer.get_node_id(task_id, target_index) == all_points.index(answer)
    elif 'way' in target:
        task_id = int(target.split('_')[0])
        target_index = ways_list[task_id - 1].index(target)
        assert ids_normalizer.get_way_id(task_id, target_index) == all_points.index(answer)
    elif 'relation' in target:
        task_id = int(target.split('_')[0])
        target_index = relations_list[task_id - 1].index(target)
        assert ids_normalizer.get_relation_id(task_id, target_index) == all_points.index(answer)
