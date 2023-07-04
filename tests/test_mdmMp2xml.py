import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import mdmMp2xml
from collections import OrderedDict
from mdmMp2xml import MylistB, Mylist

TEST_NORMALIZATION = (
        (('border', 'filename1', (0, 0),), (0, 0)),
        (('border', 'filename1', (0, 1),), (0, 1)),
        (('border', 'filename2', (0, 2),), (0, 2)),
        (('border', 'filename3', (0, 3),), (0, 3)),
        (('node', 'filename1', (1, 0),), (1, 0)),
        (('node', 'filename1', (1, 1),), (1, 1)),
        (('node', 'filename1', (1, 9),), (1, 9)),
        (('node', 'filename2', (2, 0),), (2, 0)),
        (('node', 'filename2', (2, 1),), (2, 1)),
        (('node', 'filename2', (2, 2),), (2, 2)),
        (('node', 'filename2', (2, 9),), (2, 9)),
        (('node', 'filename3', (3, 3),), (3, 3)),
        (('way', 'filename1', '1_way0',), '1_way0'),
        (('way', 'filename1', '1_way2',), '1_way2'),
        (('way', 'filename1', '1_way3',), '1_way3'),
        (('way', 'filename1', '1_way9',), '1_way9'),
        (('way', 'filename2', '2_way0',), '2_way0'),
        (('way', 'filename2', '2_way1',), '2_way1'),
        (('way', 'filename2', '2_way9',), '2_way9'),
        (('way', 'filename3', '3_way0',), '3_way0'),
        (('way', 'filename3', '3_way9',), '3_way9'),
        (('relation', 'filename1', '1_relation0',), '1_relation0'),
        (('relation', 'filename2', '2_relation2',), '2_relation2'),
        (('relation', 'filename3', '3_relation9',), '3_relation9'),
)

@pytest.mark.parametrize('target, answer', TEST_NORMALIZATION)
def test_normalization_ids(target, answer):
    borders = MylistB()
    points_list = OrderedDict()
    for a in range(19):
        borders.append((0, a))
    points_list_sum = Mylist(borders)
    points_list['filename1'] = Mylist(borders)
    points_list['filename2'] = Mylist(borders)
    points_list['filename3'] = Mylist(borders)
    ways_list = OrderedDict()
    relations_list = OrderedDict()
    ids_normalizer = mdmMp2xml.NodeGeneralizator()
    ids_normalizer.insert_borders(borders)
    for a in range(10):
        _point = (1, a)
        points_list_sum.append(_point)
        points_list['filename1'].append(_point)
        points_list_sum.append((0, a,))
        points_list['filename1'].append((0, a,))
    ways_list['filename1'] = ['1_way' + str(a) for a in range(10)]
    relations_list['filename1'] = ['1_relation' + str(a) for a in range(10)]
    for a in range(10):
        _point = (2, a)
        points_list_sum.append(_point)
        points_list['filename2'].append(_point)
        points_list_sum.append((0, a,))
        points_list['filename2'].append((0, a,))
    ways_list['filename2'] = ['2_way' + str(a) for a in range(10)]
    relations_list['filename2'] = ['2_relation' + str(a) for a in range(10)]
    for a in range(10):
        _point = (3, a)
        points_list_sum.append(_point)
        points_list['filename3'].append(_point)

    ways_list['filename3'] = ['3_way' + str(a) for a in range(10)]
    relations_list['filename3'] = ['3_relation' + str(a) for a in range(10)]

    for fname in ('filename1', 'filename2', 'filename3'):
        ids_normalizer.insert_points(fname, points_list[fname])
        ids_normalizer.insert_ways(fname, ways_list[fname])
        ids_normalizer.insert_relations(fname, relations_list[fname])


    # simulate asking for id for the first time, and asking for id for the second time
    for a in range(2):
        if 'border' == target[0]:
            file_group_name = target[1]
            target_index = points_list[file_group_name].index(target[2])
            assert ids_normalizer.get_point_id(file_group_name, target_index) == points_list_sum.index(answer) + 1

        if 'node' == target[0]:
            file_group_name = target[1]
            target_index = points_list[file_group_name].index(target[2])
            assert ids_normalizer.get_point_id(file_group_name, target_index) == points_list_sum.index(answer) + 1

        elif 'way' == target[0]:
            file_group_name = target[1]
            target_index = ways_list[file_group_name].index(target[2])
            sum_way = []
            for filename in ('filename1', 'filename2', 'filename3'):
                sum_way += ways_list[filename]
            assert ids_normalizer.get_way_id(file_group_name, target_index) == len(points_list_sum) + \
                   sum_way.index(answer) + 1

        elif 'relation' == target[0]:
            file_group_name = target[1]
            target_index = relations_list[file_group_name].index(target[2])
            sum_way = []
            for filename in ('filename1', 'filename2', 'filename3'):
                sum_way += ways_list[filename]
            sum_rels = []
            for filename in ('filename1', 'filename2', 'filename3'):
                sum_rels += relations_list[filename]
            assert ids_normalizer.get_relation_id(file_group_name, target_index) == len(points_list_sum) + \
                   len(sum_way) + sum_rels.index(answer) + 1

        # simulate asking for id for the first time, and asking for id for the second time
        ids_normalizer.get_point_id('filename1', points_list['filename1'].index((1, 1)))
        ids_normalizer.get_point_id('filename2', points_list['filename2'].index((2, 2)))
        ids_normalizer.get_point_id('filename3', points_list['filename3'].index((3, 3)))
        ids_normalizer.get_way_id('filename1', ways_list['filename1'].index('1_way0'))
        ids_normalizer.get_way_id('filename2', ways_list['filename2'].index('2_way9'))
        ids_normalizer.get_way_id('filename3', ways_list['filename3'].index('3_way9'))
        ids_normalizer.get_relation_id('filename1', relations_list['filename1'].index('1_relation0'))
        ids_normalizer.get_relation_id('filename2', relations_list['filename2'].index('2_relation2'))
        ids_normalizer.get_relation_id('filename3', relations_list['filename3'].index('3_relation9'))
