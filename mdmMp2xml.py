#!/usr/bin/env python3
# vim: set fileencoding=utf-8 et :
# or :e ++enc=utf-8
# txt2osm, an UnofficialMapProject .txt to OpenStreetMap .osm converter.
# Copyright (C) 2008  Mariusz Adamski, rhn
# Copyright (C) 2009  Andrzej Zaborowski
# Copyright (C) 2012  Michal Gorski
# Copyright (C) 2013-2019  Tadeusz Knapik
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import sys
import math
import re
import pprint
import os
import shutil
try:
    import cPickle as pickle
except:
    import pickle
from multiprocessing import Pool
from datetime import datetime
import time
# import pdb
from xml.sax import saxutils
from optparse import OptionParser
from collections import defaultdict, OrderedDict
import os.path
from functools import partial
import copy
import tempfile

class MylistB(object):
    """
    The class for storage of borders file data points
    """
    def __init__(self):
        # dictionary containing key: value pairs. key is an integer number seperate for each point
        # value is actuall reference to node data (see below for self.v)
        self.k = {}
        # a list of nodes data, node is in a form of dict eg: dictionary eg.
        # {id: '1600019', timestamp: '2023-06-16T16:02:23Z', visible: 'true',  version: '1', changeset: '1',
        # lat: '50.157630', lon: '19.332180}
        self.v = []

    def __len__(self):
        return len(self.k)

    def __getitem__(self, key):
        return self.v[key] #
        for k in self.k:
            if self.k[k] == key:
                return k

    def index(self, value):
        return self.k[value]

    def __setitem__(self, key, value): #
        if key in self.v: #
            del self.k[self.v[key]] #
        self.k[value] = key #
        self.v[key] = value #

    def __contains__(self, value):
        return value in self.k

    def append(self, value):
        self.v.append(value) #
        self.k[value] = len(self.k)

    def __iter__(self):
        return self.v.__iter__() #
        return self.k.__iter__()


class Mylist(object):
    """
    The modified list bultin type, that support faster return of element index
    """
    def __init__(self, borders, base):
        self.k = {}
        self.v = []
        self.b = base
        self.borders = borders

    def __len__(self):  # OK
        return len(self.v) + self.b

    def __getitem__(self, key):  # OK
        if key < len(self.borders):
            return self.borders[key]
        return self.v[key - self.b]

    def index(self, value):          # OK
        if value in self.borders:
            return self.borders.index(value)
        return self.k[value]

    def __setitem__(self, key, value):  #
        raise ParsingError('Hej hej')
        if key in v:  #
            del self.k[self.v[key]]  #
        self.k[value] = key  #
        self.v[key] = value  #

    def __contains__(self, value):    # OK
        if value in self.borders:
            return True
        return value in self.k

    def append(self, value):          # OK
        self.v.append(value)
        self.k[value] = len(self.v)+self.b-1

    def __iter__(self):               # OK
        # return self.v.__iter__() #
        return self.k.__iter__()

    def points_numbers(self):
        return [self.k[a] + self.b for a in self.k]


class Features(object):  # fake enum
    poi, polyline, polygon, ignore = range(4)


class ParsingError(Exception):
    pass


class ProgressBar(object):
    def __init__(self, options, obszar=None, glob_progress_bar_queue=None):
        self.progress_bar_queue = None
        self.obszar = None
        if obszar:
            self.obszar = os.path.basename(obszar).split('_')[0]
        if glob_progress_bar_queue is not None:
            self.progress_bar_queue = glob_progress_bar_queue
        elif hasattr(options, 'progress_bar_queue'):
            self.progress_bar_queue = options.progress_bar_queue
        # [ num_lines % 100, num_lines % 100 *1, 2, 3 itd, 100% value]
        self.pbar_params = {'mp': [0, 0, 0], 'drp': [0, 0, 0]}

    def set_val(self, _line_num, pb_name):
        if self.progress_bar_queue is None:
            return
        if _line_num == self.pbar_params[pb_name][1]:
            self.pbar_params[pb_name][1] += self.pbar_params[pb_name][0]
            self.progress_bar_queue.put((self.obszar, pb_name, 'curr', _line_num))
        return

    def start(self, num_lines_to_process, pb_name):
        if self.progress_bar_queue is None:
            return
        if num_lines_to_process > 100:
            self.pbar_params[pb_name][0] = int(num_lines_to_process / 100)
            self.pbar_params[pb_name][1] = int(num_lines_to_process / 100)
        else:
            self.pbar_params[pb_name][0] = 1
            self.pbar_params[pb_name][1] = 1
        self.progress_bar_queue.put((self.obszar, pb_name, 'max', num_lines_to_process))
        self.pbar_params[pb_name][2] = num_lines_to_process
        return

    def set_done(self, pb_name):
        if self.progress_bar_queue is not None:
            self.progress_bar_queue.put((self.obszar, pb_name, 'done', self.pbar_params[pb_name][2]))
        return


class NodeGeneralizator(object):
    def __init__(self):
        self.borders_point_last_id = 0
        self.points_las_id = 0
        self.ways_last_id = 0
        self.border_points = list()
        self.t_table_nodes = list()
        self.t_table_ways = list()
        self.t_table_relations = list()
        self.last_val = 0

    def insert_borders(self, borders):
        self.border_points = borders
        self.borders_point_last_id = len(borders) - 1

    def insert_node(self, node_val):
        self.t_table_nodes.append(len(node_val))
        self.points_las_id += len(node_val)

    def insert_way(self, way_val):
        self.t_table_ways.append(len(way_val))
        self.ways_last_id += len(way_val)

    def insert_relation(self, way_val):
        self.t_table_relations.append(len(way_val))

    def get_node_id(self, task_id, orig_id):
        if orig_id in self.border_points:
            return orig_id
        new_id = 1
        for a in range(task_id - 1):
            new_id += self.t_table_nodes[a]
        return orig_id + new_id + self.borders_point_last_id

    def get_way_id(self, task_id, orig_id):
        new_id = 1
        for a in range(task_id - 1):
            new_id += self.t_table_relations[a]
        return orig_id + new_id + self.points_las_id + self.borders_point_last_id

    def get_relation_id(self, task_id, orig_id):
        new_id = 1
        for a in range(task_id - 1):
            new_id += self.t_table_ways[a]
        return orig_id + new_id + self.points_las_id + self.borders_point_last_id + self.ways_last_id


class NodesToWayNotFound(ValueError):
    """
    Raised when way of two nodes can not be found
    """
    def __init__(self, node_a, node_b):
        self.node_a = node_a
        self.node_b = node_b

    def __str__(self):
        return "<NodesToWayNotFound %r,%r>" % (self.node_a, self.node_b,)


__version__ = '0.8.1'



# Krok zwiekszania osm_id per obszar. Istotny gdy nie ma normalize_ids
# zbyt duzy moze powodowac problemy z aplikacjami ktore na jego podstawie cos
# sobie wyznaczaja/obliczaja/zapamietuja etc (przyklad: nominatim)
idperarea = 0

pline_types = {
    0x1:  ["highway",  "motorway"],
    0x2:  ["highway",  "trunk"],
    0x3:  ["highway",  "primary"],
    0x4:  ["highway",  "secondary"],
    0x5:  ["highway",  "tertiary"],
    0x6:  ["highway",  "residential"],
    0x7:  ["highway",  "living_street", "note", "FIXME: select one of: living_street, service, residential"],
    0x8:  ["highway",  "trunk_link"],
    0x9:  ["highway",  "motorway_link"],
    0xa:  ["highway",  "track", "tracktype", "grade2", "access", "yes"],
    0xb:  ["highway",  "primary_link"],
    0xc:  ["junction", "roundabout"],
    0xd:  ["highway",  "cycleway"],
    0xe:  ["highway",  "tertiary", "tunnel", "yes"],
    0xf:  ["highway",  "track", "tracktype", "grade4"],
    0x14: ["railway",  "rail"],
    0x15: ["note", "morskie"],  # TODO
    0x16: ["highway",  "path"],
    # 0x16: ["highway",  "pedestrian"],
    0x18: ["waterway", "stream"],
    0x19: ["_rel",     "restriction"],
    0x1a: ["route",    "ferry"],
    0x1b: ["route",    "ferry"],
    0x1c: ["boundary", "administrative", "admin_level", "8"],
    0x1d: ["boundary", "administrative", "admin_level", "4"],
    0x1e: ["boundary", "administrative", "admin_level", "2"],
    0x1f: ["waterway", "canal"],
    0x20: ["barrier",  "wall"],  # TODO
    0x21: ["barrier",  "wall"],  # TODO
    0x22: ["barrier",  "city_wall"],  # TODO
    0x23: ["highway",  "track", "note", "fixme"],  # TODO
    0x24: ["highway",  "road"],  # TODO
    0x25: ["barrier",  "retaining_wall"],  # TODO
    0x26: ["waterway", "drain"],
    0x27: ["aeroway",  "runway"],
    0x28: ["man_made", "pipeline"],
    0x29: ["power", "line", "barrier", "retaining_wall", "note", "fixme: choose one"],
    0x2a: ["boundary", "area"],
    0x2b: ["boundary", "prohibited"],
    0x2c: ["boundary", "historical", "admin_level", "2"],
    # 0x2f: ["_rel",     "lane_restriction"], # znaki TODO
    0x2f: ["note", "fixme"],
    0x44: ["boundary", "administrative", "admin_level", "9"],
    # 0x4b: ["note", "fixme"],
    # below used for external nodes marking, for mkgmap use --add-boundary-nodes-at-admin-boundaries=3
    # ponizsze to granica routingu, dla mkgmap dodaj opcję --add-boundary-nodes-at-admin-boundaries=3 aby oznaczyc nody
    # graniczne
    0x4b: ["boundary", "administrative", "admin_level", "3"],
    0xe00: ["highway", "footway", "ref", "Czerwony szlak", "marked_trail_red", "yes", "access", "no"],
    0xe01: ["highway", "footway", "ref", "Żółty szlak", "marked_trail_yellow", "yes", "access", "no"],
    0xe02: ["highway", "footway", "ref", "Zielony szlak", "marked_trail_green", "yes", "access", "no"],
    0xe03: ["highway", "footway", "ref", "Niebieski szlak", "marked_trail_blue", "yes", "access", "no"],
    0xe04: ["highway", "footway", "ref", "Czarny szlak", "marked_trail_black", "yes", "access", "no"],
    0xe07: ["highway", "footway", "ref", "access", "no", "Szlak", "note", "FIXME"],
    0xe08: ["highway", "cycleway", "ref", "Czerwony szlak", "marked_trail_red", "yes", "access", "no"],
    0xe09: ["highway", "cycleway", "ref", "Żółty szlak", "marked_trail_yellow", "yes", "access", "no"],
    0xe0a: ["highway", "cycleway", "ref", "Zielony szlak", "marked_trail_green", "yes", "access", "no"],
    # dziwny kod dla poi!
    0x1e0a: ["highway", "cycleway", "ref", "Zielony szlak", "marked_trail_green", "yes", "access", "no"],
    0xe0b: ["highway", "cycleway", "ref", "Niebieski szlak", "marked_trail_blue", "yes", "access", "no"],
    0xe0c: ["highway", "cycleway", "ref", "Czarny szlak", "marked_trail_black", "yes", "access", "no"],
    0xe0d: ["highway", "cycleway", "ref", "Zielony szlak z liściem", "marked_trail_green", "yes", "access", "no"],
    0xe0f: ["highway", "cycleway", "ref", "Szlak", "access", "no", "note", "FIXME"],
    0xe10: ["railway", "tram"],
    0xe11: ["railway", "abandoned"],
    0xe12: ["highway", "construction"],  # nieuzywane
    0xe13: ["railway", "construction"],  # nieuzywane
    0x6701: ["highway", "path"],
    0x6702: ["highway", "track"],
    0x6707: ["highway", "path", "ref", "Niebieski szlak", "bicycle", "yes", "marked_trail_blue", "yes", "access", "no"],
    0x10e00: ["highway", "footway", "ref", "Czerwony szlak", "marked_trail_red", "yes", "osmc", "yes", "osmc_color",
              "red", "route", "hiking", "access", "no"],
    0x10e01: ["highway", "footway", "ref", "Żółty szlak", "marked_trail_yellow", "yes", "osmc", "yes", "osmc_color",
              "yellow", "route", "hiking", "access", "no"],
    0x10e02: ["highway", "footway", "ref", "Zielony szlak",
             "marked_trail_green", "yes", "osmc", "yes", "osmc_color", "green", "route", "hiking", "access", "no"],
    0x10e03: ["highway", "footway", "ref", "Niebieski szlak",
             "marked_trail_blue", "yes", "osmc", "yes", "osmc_color", "blue", "route", "hiking", "access", "no"],
    0x10e04: ["highway", "footway", "ref", "Czarny szlak",
              "marked_trail_black", "yes", "osmc", "yes", "osmc_color", "black", "route", "hiking", "access", "no"],
    0x10e07: ["highway", "footway", "ref", "Szlak", "note", "FIXME",
              "marked_trail_multi", "yes", "osmc", "yes", "osmc_color", "multi", "route", "hiking", "access", "no"],
    0x10e08: ["highway", "cycleway", "ref", "Czerwony szlak",
              "marked_trail_red", "yes", "osmc", "yes", "osmc_color", "red", "route", "bicycle", "access", "no"],
    0x10e09: ["highway", "cycleway", "ref", "Żółty szlak", "marked_trail_yellow",
              "yes", "osmc", "yes", "osmc_color", "yellow", "route", "bicycle", "access", "no"],
    0x10e0a: ["highway", "cycleway", "ref", "Zielony szlak",
              "marked_trail_green", "yes", "osmc", "yes", "osmc_color", "green", "route", "bicycle", "access", "no"],
    0x10e0b: ["highway", "cycleway", "ref", "Niebieski szlak",
              "marked_trail_blue", "yes", "osmc", "yes", "osmc_color", "blue", "route", "bicycle", "access", "no"],
    0x10e0c: ["highway", "cycleway", "ref", "Czarny szlak",
              "marked_trail_black", "yes", "osmc", "yes", "osmc_color", "black", "route", "bicycle", "access", "no"],
    0x10e0d: ["highway", "cycleway", "ref", "Szlak",
              "marked_trail_black", "yes", "osmc", "yes", "osmc_color", "multi", "route", "bicycle", "access", "no"],
    0x10e0f: ["highway", "footway", "ref", "Szlak", "marked_trail_purple", "yes", "osmc", "yes", "osmc_color",
              "purple", "route", "hiking", "access", "no"],

    0x10e10: ["railway", "tram"],
    0x10e11: ["highway", "proposed", "proposed", "residental"],  # proponowane male
    0x10e12: ["highway", "proposed", "proposed", "trunk"],  # proponowane duze
    0x10e13: ["highway", "construction"],
    0x10e14: ["railway", "rail"],
    0x10e15: ["railway", "abandoned"],
    0x10e16: ["aerialway", "gondola", "access", "foot"],
    0x10e17: ["aerialway", "drag_lift"],
    0x10e1a: ["man_made", "dyke", "embankment", "yes"],  # TODO
    0x10e1b: ["barrier", "city_wall"],
    0x10e1c: ["boundary", "national_park"],
    0x10f14: ["line", "blue"],
    0x10f15: ["line", "white"],
    0x10f16: ["line", "yellow"],
    0x10f17: ["line", "red"],
    0x10f18: ["line", "green"],
    0x10f19: ["line", "orange"],
    0x10f1a: ["man_made", "jetty"],
    0x10f1b: ["man_made", "pipeline", "location", "underwater"],
    0x10f1c: ["power", "cable", "location", "underwater"],
    0x10f1d: ["line", "recommended"],
    0x10f1e: ["line", "leading"],
    0x10f1f: ["line", "separation"],
}

umpshape_types = {
# placeholder
}

shape_types = {
    0x1:  ["landuse",  "residential"],
    0x2:  ["landuse",  "residential"],
    0x3:  ["highway",  "pedestrian", "area", "yes"],
    0x4:  ["landuse",  "military"],
    0x5:  ["amenity",  "parking"],
    0x6:  ["building", "garages"],
    0x7:  ["aeroway",  "aerodrome"],
    0x8:  ["landuse",  "retail", "building", "shops", "shop", "fixme", "fixme", "Tag manually!"],
    0x9:  ["leisure",  "marina"],  # a wild guess
    0xa:  ["building", "university"],
    0xb:  ["amenity",  "hospital"],
    0xc:  ["landuse",  "industrial"],  # a wild guess
    0xd:  ["landuse",  "construction"],
    0xe:  ["landuse",  "industrial"],  # runway na lotniskach
    0x13: ["building", "yes"],
    0x14: ["natural",  "wood"],  # sometimes landuse=military
    0x15: ["natural",  "wood"],
    0x16: ["natural",  "wood"],
    0x17: ["leisure", "park"],
    0x18: ["leisure",  "pitch", "sport", "tennis"],
    0x19: ["leisure",  "pitch"],  # or stadium...
    0x1a: ["landuse",  "cemetery"],
    0x1e: ["landuse",  "forest", "leisure", "nature_reserve"],
    0x1f: ["landuse",  "forest", "leisure", "nature_reserve"],
    0x20: ["tourism",  "attraction"],  # a wild guess (forest?)
    0x28: ["natural",  "water"],
    0x29: ["natural",  "water"],
    0x32: ["natural",  "water"],
    0x3b: ["natural",  "water"],  # how does this differ from 0x40?
    0x3c: ["natural",  "water"],  # how does this differ from 0x40?
    0x3d: ["natural",  "water"],  # how does this differ from 0x40?
    0x3e: ["natural",  "water"],  # how does this differ from 0x40?
    0x3f: ["natural",  "water"],  # how does this differ from 0x40?
    0x40: ["natural",  "water"],
    0x41: ["natural",  "water", "amenity", "fountain"],
    0x42: ["landuse",  "reservoir"],  # how does this differ from 0x40?
    0x43: ["landuse",  "reservoir"],  # how does this differ from 0x40?
    0x44: ["landuse",  "reservoir"],  # how does this differ from 0x40?
    0x45: ["landuse",  "reservoir"],  # how does this differ from 0x40?
    0x46: ["waterway", "riverbank"],
    0x47: ["waterway", "riverbank"],  # how does this differ from 0x46?
    0x48: ["waterway", "riverbank"],  # how does this differ from 0x46?
    0x49: ["waterway", "riverbank"],  # how does this differ from 0x46?
    0x4a: ["highway",  "residential", "oneway", "yes"],
    0x4c: ["natural",  "water"],  # how does this differ from 0x40?
    0x4d: ["natural",  "glacier"],
    0x4e: ["landuse",  "allotments"],
    0x4f: ["natural",  "scrub"],
    0x50: ["natural",  "wood"],
    0x51: ["natural",  "wetland"],
    0x52: ["leisure",  "garden", "tourism", "zoo"],
    0x53: ["landuse",  "landfill"],

    0x2d0a: ["leisure",  "stadium"],
}
umppoi_types = {
                'SUSHI': 0x2a025,
                'GRILL': 0x2a031,
                'KEBAB': 0x2a032,
                'THAI': 0x2a041,
                'MLECZNY': 0x2a121,
                'LIBANSKA': 0x2a135,

                'UCZELNIA': 0x2c055,
                'PRZEDSZKOLE': 0x2c056,
                'ZLOBEK': 0x2c057,

                'BENZYNA': 0x2f01,
                'PALIWO': 0x2f01,
                'PRAD': 0x2f011,

                'RENT_A_BIKE': 0x2f021,
                'ROWERY': 0x2f021,
                'RENTACAR': 0x2f022,
                'RENT_A_BOAT': 0x2f023,
                'LODKI': 0x2f023,

                'BANK': 0x2f06,
                'ATMBANK': 0x2f061,
                'ATM': 0x2f062,
                'KANTOR': 0x2f063,

                'BUS': 0x2f080,            
                'TRAM': 0x2f081,            
                'METRO': 0x2f082,            
                'PKS': 0x2f083,            
                'PKP': 0x2f084,            
                'TAXI': 0x2f085,            

                'PRZYCHODNIA': 0x30025,
                'WETERYNARZ': 0x30026,
                'DENTYSTA': 0x30027,

                'FO': 0x56001,
                'FP': 0x56002,
                'FS': 0x56003,
                'RL': 0x56004,

                'NM': 0x57001,
                'NPK': 0x57002,
                'SPK': 0x57003,

                'ZABYTEK': 0x64001,

                'KIRKUT': 0x64031,
}

poi_types = {
    0x04:   ["place",    "city"],
    0x05:   ["place",    "city"],
    0x06:   ["place",    "city"],
    0x07:   ["place",    "city"],
    0x08:   ["place",    "town"],
    0x09:   ["place",    "town"],
    0x0a:   ["place",    "town"],
    0x0b:   ["place",    "town"],
    0x0c:   ["place",    "village"],
    0x0d:   ["place",    "village"],
    0x0e:   ["place",    "village"],
    0x2d:   ["amenity",  "townhall"],

    0x0100: ["place",    "city"],  # Also used for voivodeships, regions
    0x0200: ["place",    "city"],
    0x0300: ["place",    "city"],  # Also used for country nodes, seas
    0x0400: ["place",    "city"],
    0x0500: ["place",    "city"],
    0x0600: ["place",    "city"],
    0x0700: ["place",    "city"],
    0x0800: ["place",    "city"],
    0x0900: ["place",    "city"],
    0x0a00: ["place",    "town"],
    0x0b00: ["place",    "town"],
    0x0c00: ["place",    "town"],
    0x0d00: ["place",    "village"],
    0x0e00: ["place",    "village"],
    0x0f00: ["place",    "village"],
    0x1000: ["place",    "village"],
    0x1100: ["place",    "village"],
    0x1150: ["landuse",  "construction"],
    0x1200: ["bridge",   "yes"],
    0x1300: ["leisure",   "marina"],
    0x1500: ["place",    "locality"],
    0x1600: ["man_made", "lighthouse"],
    0x1602: ["man_made", "beacon", "mark_type", "ais"],
    0x1603: ["man_made", "beacon", "mark_type", "racon"],
    0x1605: ["amenity",  "citymap_post", "tourism", "information"],
    0x1606: ["man_made", "beacon", "mark_type", "beacon"],
    0x1607: ["man_made", "beacon", "mark_type", "safe_water"],
    0x1608: ["man_made", "beacon", "mark_type", "lateral_left"],
    0x1609: ["man_made", "beacon", "mark_type", "lateral_right"],
    0x160a: ["man_made", "beacon", "mark_type", "isolated_danger"],
    0x160b: ["man_made", "beacon", "mark_type", "special"],
    0x160c: ["man_made", "beacon", "mark_type", "cardinal"],
    0x160d: ["man_made", "beacon", "mark_type", "other"],
    0x160e: ["amenity",  "signpost"],
    0x160f: ["man_made", "beacon", "mark_type", "white"],
    0x1610: ["man_made", "beacon", "mark_type", "red"],
    0x1611: ["man_made", "beacon", "mark_type", "green"],
    0x1612: ["man_made", "beacon", "mark_type", "yellow"],
    0x1613: ["man_made", "beacon", "mark_type", "orange"],
    0x1614: ["man_made", "beacon", "mark_type", "magenta"],
    0x1615: ["man_made", "beacon", "mark_type", "blue"],
    0x1616: ["man_made", "beacon", "mark_type", "multicolored"],
    0x1708: ["note",     "deadend"],
    0x1709: ["bridge",   "yes"],
    0x170b: ["note",     "verify!"],
    0x170f: ["man_made", "beacon", "mark_type", "white"],
    0x1710: ["barrier",  "gate"],
    0x17105: ["highway",  "stop"],
    0x1711: ["note",     "FIXME"],
    0x1712: ["landuse",  "construction"],
    0x170a: ["note",     "FIXME: verify"],
    0x170d: ["note",     "FIXME"],
    0x1805: ["man_made", "beacon", "traffic_signals"],
    0x1806: ["man_made", "beacon", "mark_type", "beacon_red"],
    0x1807: ["man_made", "beacon", "mark_type", "beacon_north"],
    0x1808: ["man_made", "beacon", "mark_type", "lateral_right_B"],
    0x1809: ["man_made", "beacon", "mark_type", "lateral_left_B"],
    0x180a: ["man_made", "beacon", "mark_type", "beacon_danger"],
    0x180b: ["man_made", "beacon", "mark_type", "mooring_buoy"],
    0x180c: ["man_made", "beacon", "mark_type", "cardinal_north"],
    0x180d: ["man_made", "beacon", "mark_type", "main_right"],
    0x1905: ["man_made", "beacon", "notice_board", "tablica"],
    0x1906: ["man_made", "beacon", "mark_type", "beacon_green"],
    0x1907: ["man_made", "beacon", "mark_type", "beacon_south"],
    0x1908: ["man_made", "beacon", "mark_type", "beacon_red-green-red"],
    0x1909: ["man_made", "beacon", "mark_type", "beacon_green-red-green"],
    0x190a: ["man_made", "beacon", "mark_type", "beacon_safe"],
    0x190b: ["man_made", "beacon", "mark_type", "dolphin"],
    0x190c: ["man_made", "beacon", "mark_type", "cardinal_south"],
    0x190d: ["man_made", "beacon", "mark_type", "main_left"],
    0x1a06: ["man_made", "beacon", "mark_type", "beacon_yellow"],
    0x1a07: ["man_made", "beacon", "mark_type", "beacon_east"],
    0x1a08: ["man_made", "beacon", "mark_type", "beacon_red-white"],
    0x1a09: ["man_made", "beacon", "mark_type", "beacon_green-white"],
    0x1a0a: ["man_made", "beacon", "mark_type", "beacon_black-white"],
    0x1a0b: ["man_made", "beacon"],
    0x1a0c: ["man_made", "beacon", "mark_type", "cardinal_east"],
    0x1a0d: ["man_made", "beacon", "mark_type", "main_left_B"],
    0x1a10: ["man_made", "beacon"],
    0x1b00: ["note",     "fixme"],
    0x1b02: ["natural",  "peak"],
    0x1b05: ["amenity",  "signpost"],
    0x1b06: ["man_made", "beacon", "mark_type", "beacon_white"],
    0x1b07: ["man_made", "beacon", "mark_type", "beacon_west"],
    0x1b08: ["man_made", "beacon", "mark_type", "beacon_white-red"],
    0x1b09: ["man_made", "beacon", "mark_type", "beacon_white-green"],
    0x1b0a: ["man_made", "beacon", "mark_type", "beacon_white-black"],
    0x1b0b: ["man_made", "beacon", "mark_type", "beacon_black"],
    0x1b0c: ["man_made", "beacon", "mark_type", "cardinal_west"],
    0x1b0d: ["man_made", "beacon", "mark_type", "main_right_B"],
    0x1b0f: ["aeroway",  "taxiway"],
    0x1c00: ["barrier",  "obstruction"],
    0x1c01: ["man_made", "ship_wreck", "visibility", "yes"],
    0x1c02: ["man_made", "ship_wreck", "visibility", "no"],
    0x1c03: ["man_made", "ship_wreck", "visibility", "no"],
    0x1c04: ["man_made", "ship_wreck", "visibility", "no"],
    0x1c05: ["barrier",  "obstruction", "visibility", "yes"],
    0x1c06: ["barrier",  "obstruction", "visibility", "no"],
    0x1c07: ["barrier",  "obstruction", "visibility", "no"],
    0x1c08: ["barrier",  "obstruction", "visibility", "no"],
    0x1c09: ["barrier",  "obstruction", "visibility", "no"],
    0x1c0a: ["barrier",  "obstruction", "visibility", "no"],
    0x1c0b: ["man_made",  "obstruction", "visibility", "no"],
    0x1c0c: ["barrier",  "obstruction", "visibility", "no"],
    0x1c0d: ["barrier",  "obstruction", "visibility", "no"],
    0x1e00: ["place",    "region"],
    0x1f00: ["place",    "region"],
    0x2000: ["highway",  "exit"],
    0x2100: ["highway",  "services"],
    0x210f: ["highway",  "services"],
    0x2110: ["highway",  "services"],
    0x2200: ["highway",  "rest_area"],
    0x2400: ["amenity",  "weigh_station"],
    0x2500: ["highway",  "toll"],
    0x2501: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2502: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2503: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2504: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2505: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2506: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2507: ["highway",  "motorway_junction", "barrier", "toll_booth"],  # VIATOLL
    0x2600: ["highway",  "rest_area"],
    0x2700: ["highway",  "exit"],
    0x2800: ["note",    "housenumber"], 
    0x2900: ["landuse",  "commercial"],
    0x2a:   ["amenity",  "restaurant"],
    0x2a00: ["amenity",  "restaurant"],
    0x2a01: ["amenity",  "restaurant", "cuisine", "american"],
    0x2a02: ["amenity",  "restaurant", "cuisine", "asian"],
    0x2a025: ["amenity",  "restaurant", "cuisine", "sushi"],
    0x2a03: ["amenity",  "restaurant", "cuisine", "barbecue"],
    0x2a030: ["amenity",  "restaurant", "cuisine", "barbecue"],
    0x2a031: ["amenity",  "restaurant", "cuisine", "grill"],
    0x2a032: ["amenity",  "restaurant", "cuisine", "kebab"],
    0x2a04: ["amenity",  "restaurant", "cuisine", "chinese"],
    0x2a041: ["amenity",  "restaurant", "cuisine", "thai"],
    0x2a05: ["shop",     "bakery"],
    0x2a06: ["amenity",  "restaurant", "cuisine", "international"],
    0x2a07: ["amenity",  "fast_food",  "cuisine", "burger"],
    0x2a08: ["amenity",  "restaurant", "cuisine", "italian"],
    0x2a09: ["amenity",  "restaurant", "cuisine", "mexican"],
    0x2a0a: ["amenity",  "restaurant", "cuisine", "pizza"],
    0x2a0b: ["amenity",  "restaurant", "cuisine", "sea_food"],
    0x2a0c: ["amenity",  "restaurant", "cuisine", "grill"],
    0x2a0d: ["shop",  "pastry"],
    0x2a0e: ["amenity",  "cafe"],
    0x2a0f: ["amenity",  "restaurant", "cuisine", "french"],
    0x2a10: ["amenity",  "restaurant", "cuisine", "german"],
    0x2a11: ["amenity",  "restaurant", "cuisine", "british"],
    0x2a12: ["amenity",  "restaurant", "cuisine", "vegetarian"],
    0x2a121: ["amenity",  "fast_food",  "cuisine", "polish"],
    0x2a13: ["amenity",  "restaurant", "cuisine", "greek"],
    0x2a135: ["amenity",  "restaurant", "cuisine", "lebanese"],
    0x2a14: ["amenity",  "restaurant", "cuisine", "regional"],
    0x2b00: ["tourism",  "hostel"],
    0x2b01: ["tourism",  "hotel"],
    0x2b015: ["tourism",  "motel"],
    0x2b02: ["tourism",  "hostel"],
    0x2b03: ["tourism",  "camp_site"],
    0x2b04: ["tourism",  "hotel"],
    0x2c00: ["tourism",  "attraction"],
    0x2c005: ["tourism",  "viewpoint"],
    0x2c01: ["tourism",  "attraction", "leisure", "park"],
    0x2c015: ["leisure",  "playground"],
    0x2c02: ["tourism",  "museum"],
    0x2c025: ["tourism",  "museum", "amenity", "arts_centre"],
    0x2c03: ["amenity",  "library"],
    0x2c04: ["historic", "castle"],
    0x2c040: ["historic", "castle", "castle_type", "dworek"],
    0x2c041: ["historic", "castle", "castle_type", "palace"],
    0x2c042: ["historic", "castle", "castle_type", "fortress"],
    0x2c043: ["historic", "castle", "castle_type", "fortress"],
    0x2c05: ["amenity",  "school"],
    0x2c055: ["amenity",  "university"],
    0x2c056: ["amenity",  "kindergarten", "note", "Przedszkole"],
    0x2c057: ["amenity",  "kindergarten", "note", "Żłobek"],
    0x2c06: ["leisure",  "park"],
    0x2c07: ["tourism",  "zoo"],
    0x2c08: ["leisure",  "sports_centre"],
    0x2c080: ["leisure",  "pitch"],
    0x2c081: ["leisure",  "stadium"],
    0x2c09: ["amenity",  "theatre", "note", "concert_hall"],
    0x2c0a: ["amenity",  "restaurant", "cuisine", "wine_bar"],
    0x2c0b: ["amenity",  "place_of_worship", "religion", "christian"],
    0x2c0c: ["natural",  "spring", "amenity", "spa"],
    0x2c10: ["tourism", "artwork", "artwork_type", "mural"],
    0x2d00: ["leisure",  "track"],
    0x2d01: ["amenity",  "theatre"],
    0x2d02: ["amenity",  "pub"],
    0x2d03: ["amenity",  "cinema"],
    0x2d04: ["amenity",  "nightclub"],
    0x2d045: ["amenity",  "casino"],
    0x2d05: ["sport",    "golf", "leisure", "golf_course"],
    0x2d06: ["sport",    "skiing"],
    0x2d07: ["sport",    "9pin"],
    0x2d08: ["sport",    "skating"],
    0x2d09: ["sport",    "swimming"],
    0x2d0a: ["leisure",  "stadium"],
    0x2d0a0: ["leisure",  "sports_centre", "sport", "fitness"],
    0x2d0a1: ["leisure",  "sports_centre", "sport", "tennis"],
    0x2d0a2: ["leisure",  "sports_centre", "sport", "skating"],
    0x2d0b: ["sport",    "sailing"],
    0x2e:   ["shop",     "stationery"],
    0x2e00: ["shop",     "mall"],
    0x2e01: ["shop",     "department_store"],
    0x2e02: ["shop",     "convenience"],
    0x2e025: ["amenity",  "marketplace"],
    0x2e03: ["shop",     "supermarket"],
    0x2e04: ["shop",     "mall"],
    0x2e05: ["amenity",  "pharmacy"],
    0x2e06: ["shop",     "convenience"],
    0x2e07: ["shop",     "clothes"],
    0x2e08: ["shop",     "garden_centre"],
    0x2e09: ["shop",     "furniture"],
    0x2e0a: ["shop",     "outdoor"],
    0x2e0a5: ["shop",     "bicycle"],
    0x2e0b: ["shop",     "computer"],
    0x2e0c: ["shop",     "pets"],
    0x2f00: ["amenity",  "miscellaneous"],
    0x2f01: ["amenity",  "fuel"],
    0x2f011: ["amenity", "charging_station"],
    0x2f02: ["amenity",  "car_rental"],
    0x2f021: ["amenity",  "bicycle_rental"],
    0x2f022: ["amenity",  "car_rental"],
    0x2f023: ["amenity",  "boat_rental"],
    0x2f03: ["shop",     "car_repair"],
    0x2f030: ["shop",     "car"],
    0x2f04: ["aeroway",  "aerodrome"],
    0x2f05: ["amenity",  "post_office"],
    0x2f050: ["amenity",  "post_office", "type", "courier"],
    0x2f051: ["amenity",  "post_office", "type", "courier", "operator", "dhl"],
    0x2f052: ["amenity",  "post_office", "type", "courier", "operator", "ups"],
    0x2f06: ["amenity",  "bank"], 
    0x2f061: ["amenity",  "bank", "atm", "yes"],
    0x2f062: ["amenity",  "atm"],
    0x2f063: ["amenity",  "bureau_de_change"],
    0x2f07: ["shop",     "car"],
    0x2f08: ["amenity",  "bus_station"],
    0x2f080: ["highway",  "bus_stop"],
    0x2f081: ["railway",  "tram_stop"],
    0x2f082: ["railway",  "station", "station", "subway"],
    0x2f083: ["highway",  "bus_stop", "operator", "PKS"],
    0x2f084: ["railway",  "station", "operator", "PKP"],
    0x2f085: ["amenity",  "taxi"],

    0x2f09: ["waterway", "boatyard"],
    0x2f0a: ["shop",     "car_wrecker"],
    0x2f0b: ["amenity",  "parking"],
    0x2f0c: ["tourism",  "information"],
    0x2f0d: ["amenity",  "automobile_club"],
    0x2f0e: ["amenity",  "car_wash"],
    0x2f0f: ["shop",     "outdoor", "operator", "Garmin"],
    0x2f10: ["amenity",  "personal_service"],
    0x2f104: ["amenity",  "personal_service", "shop", "hairdresser"],
    0x2f105: ["amenity",  "personal_service", "shop", "tattoo"],
    0x2f106: ["amenity",  "personal_service", "shop", "optician"],
    0x2f11: ["landuse",  "industrial", "amenity", "factory"],
    0x2f12: ["amenity",  "wifi"],
    0x2f13: ["shop",     "bicycle"],
    0x2f14: ["amenity",  "public_building", ],
    0x2f144: ["amenity",  "public_building", "type", "social"],
    0x2f145: ["amenity",  "personal_service", "shop", "laundry"],
    0x2f15: ["office",   "company"],
    0x2f16: ["amenity",  "parking", "truck_stop", "yes"],
    0x2f17: ["amenity",  "travel_agency"],
    0x2f18: ["amenity",  "vending_machine", "vending", "public_transport_tickets"],
    0x2f1b: ["office",   "company"],
    0x3000: ["amenity",  "public_building"],
    0x3001: ["amenity",  "police"],
    0x3002: ["amenity",  "hospital"],
    0x30025: ["amenity",  "doctors"],
    0x30026: ["amenity",  "veterinary"],
    0x30027: ["amenity",  "dentist"],
    0x3003: ["amenity",  "townhall"],
    0x3004: ["amenity",  "courthouse"],
    0x3005: ["amenity",  "nightclub"],
    0x3006: ["amenity",  "border_station"],
    0x3007: ["amenity",  "townhall"],
    0x3008: ["amenity",  "fire_station"],
    0x4000: ["leisure",  "golf_course"],
    0x4100: ["landuse",  "reservoir"],
    0x4200: ["man_made", "ship"],
    0x4300: ["leisure",  "marina"],
    0x4400: ["amenity",  "fuel"],
    0x4500: ["amenity",  "restaurant"],
    0x4600: ["amenity",  "fast_food"],
    0x4800: ["tourism",  "camp_site"],
    0x4900: ["leisure",  "park"],
    0x4700: ["waterway", "dock"],
    0x4701: ["waterway", "boat_ramp"],
    0x4a00: ["tourism",  "picnic_site"],
    0x4b00: ["amenity",  "hospital"],
    0x4c00: ["tourism",  "information"],
    0x4d00: ["amenity",  "parking"],
    0x4e00: ["amenity",  "toilets"],
    0x4f00: ["amenity",  "shower"],
    0x5000: ["amenity",  "drinking_water"],
    0x5100: ["amenity",  "telephone"],
    0x5200: ["tourism",  "viewpoint"],
    0x5300: ["sport",    "skiing"],
    0x5400: ["sport",    "swimming"],
    0x5500: ["waterway", "dam"],  #  Map_Features requires a way
    0x5600: ["highway",  "speed_camera"],
    0x56001: ["highway",  "speed_camera", "enforcement", "average_speed"],
    0x56002: ["highway",  "speed_camera", "type", "portable"],
    0x56003: ["highway",  "speed_camera", "type", "permanent"],
    0x56004: ["highway",  "speed_camera", "enforcement", "traffic_signals"],
    0x5700: ["hazard",   "yes"],
    0x57001: ["hazard",   "dangerous_junction"],
    0x57002: ["railway",   "level_crossing"],
    0x57003: ["railway",   "level_crossing", "crossing:barrier", "yes"],
    0x5800: ["seamark:calling-in_point:traffic_flow", "NS"],
    0x5801: ["seamark:calling-in_point:traffic_flow", "EW"],
    0x5802: ["seamark:calling-in_point:traffic_flow", "NW-SE"],
    0x5803: ["seamark:calling-in_point:traffic_flow", "NE-SW"],
    0x5804: ["seamark:calling-in_point:traffic_flow", "N"],
    0x5805: ["seamark:calling-in_point:traffic_flow", "S"],
    0x5806: ["seamark:calling-in_point:traffic_flow", "E"],
    0x5807: ["seamark:calling-in_point:traffic_flow", "W"],
    0x5808: ["seamark:calling-in_point:traffic_flow", "NW"],
    0x5809: ["seamark:calling-in_point:traffic_flow", "NE"],
    0x580a: ["seamark:calling-in_point:traffic_flow", "SW"],
    0x580b: ["seamark:calling-in_point:traffic_flow", "SE"],
    0x5900: ["aeroway",  "aerodrome"],
    0x5901: ["aeroway",  "aerodrome"],
    0x5902: ["aeroway",  "aerodrome"],
    0x5903: ["aeroway",  "aerodrome"],
    0x5904: ["aeroway",  "helipad"],
    0x5905: ["aeroway",  "aerodrome"],
    0x593f: ["aeroway",  "aerodrome"],
    0x5a00: ["highway",  "milestone"],
    0x5a01: ["boundary", "marker"],
    0x5a02: ["waterway",  "milestone"],
    0x5c00: ["place",    "hamlet"],
    0x5d00: ["tourism",  "information"],
    0x5f00: ["natural",  "scree"],
    0x5e00: ["highway", "elevator"],
    0x6100: ["military", "bunker", "building", "bunker", "amenity", "shelter"],
    0x6101: ["historic", "ruins"],
    0x6200: ["depth",    "_name"],
    0x6300: ["ele",      "_name"],
    0x6400: ["historic", "monument", "note", "FIXME"],
    0x64001: ["historic", "building"],
    0x6401: ["bridge",   "yes"],
    0x6402: ["building", "residental"],
    0x6403: ["landuse",  "cemetery"],
    0x64030: ["landuse",  "cemetery", "religion", "christian"],
    0x64031: ["landuse",  "cemetery", "religion", "jewish"],
    0x6404: ["amenity",  "place_of_worship", "religion", "christian", "historic", "wayside_cross"],
    0x6405: ["amenity",  "public_building"],
    0x6406: ["amenity",  "ferry_terminal"],
    0x6407: ["waterway", "dam"],  #  Map_Features requires a way
    0x6408: ["amenity",  "hospital"],
    0x6409: ["man_made", "water_works"],  #  random pick from Map_Features
    0x640a: ["amenity",  "signpost"],
    0x640b: ["landuse",  "military"],
    0x640c: ["man_made", "mineshaft"],
    0x640d: ["man_made", "works", "waterway", "oil_platform"],
    0x640e: ["leisure",  "park"],
    0x640f: ["amenity",  "post_box"],
    0x6410: ["amenity",  "school"],
    0x6411: ["man_made", "tower"],
    0x64110: ["man_made", "tower", "height", "short"],
    0x64111: ["man_made", "tower", "height", "tall"],
    0x6412: ["highway",  "trailhead", "note", "fixme"],
    0x6413: ["tunnel",   "yes", "layer", "-1"],
    0x64135: ["natural",  "cave_entrance"],
    0x6414: ["amenity",  "drinking_water"],
    0x6415: ["historic", "fort", "building", "fortress"],
    0x64155: ["historic", "ruins", "building", "bunker"],
    0x6416: ["tourism",  "hotel"],
    0x6500: ["waterway", "other"],
    0x6502: ["highway",  "ford"],
    0x6503: ["natural",  "bay"],
    0x6504: ["natural",  "water", "waterway", "bend"],
    0x6505: ["waterway", "lock_gate"],
    0x6506: ["waterway", "lock_gate"],
    0x6507: ["natural",  "spring", "man_made", "water_works"],
    0x6508: ["waterway", "waterfall"],
    0x6509: ["amenity",  "fountain", "note", "fixme"],
    0x650a: ["natural",  "glacier"],
    0x650b: ["waterway", "dock"],
    0x650c: ["natural",  "land"],        # Island as a POI
    0x650d: ["natural",  "water"],       # Lake as a POI
    0x650e: ["natural",  "spring"],      # geyser -> spring or volcano?
    # 0x650f: ["natural",  "water"],       # Pond as a POI
    0x650f: ["amenity",  "toilets"],
    0x6511: ["natural",  "spring"],
    0x6512: ["waterway", "stream"],
    0x6513: ["natural",  "water"],       # Swamp as a POI
    0x6600: ["place",    "locality", "note", "fixme (kurhan?)"],
    0x6601: ["barrier",  "sally_port"],
    0x6602: ["landuse",  "commercial"],
    0x6603: ["natural",  "bay"],
    0x6604: ["natural",  "beach"],
    0x6605: ["lock",     "yes"],
    0x6606: ["place",    "locality", "locality_type", "cape"],
    0x6607: ["natural",  "cliff"],       # Cliff as a POI
    0x6608: ["natural",  "peak"],
    0x6609: ["natural",  "plain"],
    0x660a: ["natural",  "tree"],
    0x660b: ["place",    "locality", "note", "fixme"],
    0x660c: ["place",    "locality", "note", "fixme"],
    0x660d: ["place",    "locality", "note", "fixme"],
    0x660e: ["natural",  "volcano"],
    0x660f: ["man_made",  "windmill"],
    0x6610: ["mountain_pass", "yes"],
    0x6611: ["man_made", "tower"],
    0x6612: ["amenity",  "watersports_rental"],
    0x6613: ["natural",  "peak", "place", "region"],
    0x6614: ["natural",  "scree"],
    0x6615: ["natural",  "peak", "place", "locality", "note", "fixme", "sport", "skiing"],
    0x6616: ["natural",  "peak"],
    0x6617: ["place",    "locality", "natural",  "valley"],
    0x6618: ["natural",  "wood"],        # Wood as a POI

    0x6701: ["highway",  "footway", "ref", "Zielony szlak", "marked_trail_green", "yes"],
    0x6702: ["highway",  "footway", "ref", "Czerwony szlak", "marked_trail_red", "yes"],
    0x6703: ["highway",  "footway", "ref", "Niebieski szlak", "marked_trail_blue", "yes"],
    0x6704: ["highway",  "footway", "ref", "Żółty szlak", "marked_trail_yellow", "yes"],
    0x6705: ["highway",  "footway", "ref", "Czarny szlak", "marked_trail_black", "yes"],
    0x6707: ["highway",  "cycleway", "ref", "Żółty szlak", "marked_trail_yellow", "yes"],
    0x6708: ["highway",  "cycleway", "ref", "Czerwony szlak", "marked_trail_red", "yes"],
    0x6709: ["highway",  "cycleway", "ref", "Niebieski szlak", "marked_trail_blue", "yes"],
    0x670a: ["highway",  "cycleway", "ref", "Zielony szlak", "marked_trail_green", "yes"],
    0x670b: ["highway",  "cycleway", "ref", "Czarny szlak", "marked_trail_black", "yes"],
    0xf201: ["highway",  "traffic_signals"],
}

# Lines with a # above can be removed to save half of the memory used
# (but some look-ups will be slower)
# k zawiera slownik {[lat,lon]->poz,....} ; mapowanie (lat,lon)->id
# v zawiera tablice { [lat,lon], [lat,lon],....}  mapowanie id->(lat,lon)
bpoints = MylistB()

# later will be initialized as Mylist instance, lets leave it None for now.
points = None
# pointattrs = {}
pointattrs = defaultdict(dict)
ways = []
relations = []

maxtypes = {}
working_thread = os.getpid()
workid = 0

# borders = None
# borders_resize = 1
# nominatim_build = 0
extra_tags = " version='1' changeset='1' "
idpfx = ""
maxid = 0

glob_progress_bar_queue = None

def printdebug(string, options):
    global working_thread
    if options.verbose:
        sys.stderr.write("\tDEBUG: "+str(working_thread)+":"+str(workid)+":"+str(string)+"\n")


def printerror(string):
    sys.stderr.write("\tERROR: "+str(working_thread)+":"+str(workid)+":"+str(string)+"\n")


def printinfo(string):
    sys.stderr.write("\tINFO: "+str(working_thread)+":"+str(workid)+":"+str(string)+"\n")


def printinfo_nlf(string):
    sys.stderr.write("\tINFO: "+str(working_thread)+":"+str(workid)+":"+str(string))


def printwarn(string):
    sys.stderr.write("\tWARNING: "+str(working_thread)+":"+str(workid)+":"+str(string)+"\n")
        

def recode(line):
    try:
        return line
        # return unicode(line, "cp1250").encode("UTF-8")
    except:
        sys.stderr.write("warning: couldn't recode " + line + " in UTF-8!\n")
        return line


def bpoints_append(node):
    bpoints.append(node)
        

def add_bline(nodes_str):
    """Appends new nodes to the points list"""
    # Kwadrat dla Polski.
    # 54.85628,13.97873
    # 48.95703,24.23996
    # Ekspansja, niech pamieta granice dla z grubsza calej Europy kontynentalnej
    maxN = 72.00000
    maxW = -12.00000
    maxS = 34.00000
    maxE = 50.00000
    nodes = []
    for element in nodes_str.split(','):
        element = element.strip('()')
        nodes.append(element)

    lats = []
    longs = []

    for la in nodes[::2]:
        l = len(la)
        if l < 9:
            la += '0' * (9 - l)
        lats.append(la)

    for lo in nodes[1::2]:
        l = len(lo)
        if l < 9:
            lo += '0' * (9 - l)
        longs.append(lo)
    
    nodes = list(zip(lats, longs))
        
    for node in nodes:
        if node not in bpoints:
            if maxN > float(node[0]) > maxS and maxW < float(node[1]) < maxE:
                bpoints_append(node) 
    
        
# TxF: ucinanie przedrostkow
def cut_prefix(string):
    if string.startswith("aleja ") or string.startswith("Aleja ") or string.startswith("rondo ") or \
       string.startswith("Rondo ") or string.startswith("osiedle ") or string.startswith("Osiedle ") or \
       string.startswith("pasaż ") or string.startswith("Pasaż "):
        string = re.sub("^\w+ ", "", string)
    return string


def convert_btag(way, key, value, feat, options):
    if key.lower() in ('label',):
        pass
    elif key in ('Data0',):
        add_bline(value)
    elif key == 'Type':
        if int(value, 0) == 0x4b:
            pass
        elif int(value, 0) == 0x1e:
            pass
        else:
            printerror("Unknown line type " + hex(int(value, 0)))
    elif key == 'EndLevel':
        pass
    else:
        if options.ignore_errors:
            printerror("Unknown key: " + key)
            printerror("Value:       " + value)
            pass 
        else:
            raise ParsingError("Unknown key " + key + " in polyline / polygon")


def parse_borders(infile, options):
    polyline = None
    feat = None
    comment = None
    linenum = 0
    for line in infile:
        line = line.strip()
        linenum += 1
        if line.startswith(';'):
            strn = recode(line[1:].strip(" \t\n"))
            if comment is not None:
                comment = comment + " " + strn
            else:
                comment = strn
        elif line == "[POI]":
            feat = Features.ignore
        elif line == "[POLYGON]":
            feat = Features.ignore
        elif line == "[POLYLINE]":
            polyline = {}
            feat = Features.polyline
        elif line == '[END]':
            way = {'_timestamp': borderstamp}
            for key in polyline:
                if polyline[key] != '':
                    convert_btag(way, key, polyline[key], feat, options)
            polyline = None
        elif feat == Features.ignore:
            pass
        elif polyline is not None and line != '':
            try:
                key, value = line.split('=', 1)
            except:
                print(line)
                raise ParsingError('Can\'t split the thing')
            key = key.strip()
            polyline[key] = recode(value).strip()
        elif line != '':
            raise ParsingError('Unhandled line ' + str(linenum) + ":" + line)


# Mercator
def projlat(lat):
    lat = math.radians(lat)
    return math.degrees(math.log(math.tan(lat) + 1.0 / math.cos(lat)))


def projlon(lon):
    return lon


def unproj(lat, lon):
    lat = math.radians(lat)
    return math.degrees(math.atan(math.sinh(lat))), lon
# def unproj(lat, lon):
#    return (lat, lon / math.cos(lat / 180.0 * math.pi))
# def projlat(lat):
#    return lat
# def projlon(lat, lon):
#    return lon * math.cos(lat / 180.0 * math.pi)            
            
            
def tag(way, pairs):
    for key, value in zip(pairs[::2], pairs[1::2]):
        way[key] = value


def polygon_make_ccw(shape):
    nodes = shape['_nodes']
    num = len(nodes) - 1
    if num < 3:
        return

    angle = 0.0
    epsilon = 0.001
    # TODO: zoptymalizować, bo (b,c) bieżącej iteracji stają się (a,b) następnej
    for i in range(num):
        try:
            a = (i + 0)
            b = (i + 1)
            c = (i + 2) % num
            # No projection needed
            alat = float(points[nodes[a]][0])
            alon = float(points[nodes[a]][1])
            blat = float(points[nodes[b]][0])
            blon = float(points[nodes[b]][1])
            clat = float(points[nodes[c]][0])
            clon = float(points[nodes[c]][1])
            ablen = math.hypot(blat - alat, blon - alon)
            bclen = math.hypot(clat - blat, clon - blon)
            # Vector cross product (?)
            cross = (blat - alat) * (clon - blon) - (blon - alon) * (clat - blat)
            # Vector dot product (?)
            dot = (blat - alat) * (clat - blat) + (blon - alon) * (clon - blon)

            sine = cross / (ablen * bclen)
            cosine = dot / (ablen * bclen)
            angle += signbit(sine) * math.acos(cosine)
        except:
            pass
    angle = math.degrees(-angle)

    if -360.0 - epsilon < angle < -360.0 + epsilon:  # CW
        nodes.reverse()
    elif 360.0 - epsilon < angle < 360.0 + epsilon:  # CCW
        pass
    else:
        # Likely an illegal shape
        shape['fixme'] = "Weird shape"
        

def add_addrinfo(nodes, addrs, street, city, region, right, count):
    interp_types = {"o": "odd", "e": "even", "b": "all"}
    prev_house = "xx"
    prev_node = None

    attrs = {'_timestamp': filestamp, 'addr:street': street}
    attrs['NumberX'] = 'yes'
    if region:
        attrs['is_in:state'] = region
    if city:
        attrs['addr:city'] = city
        attrs['is_in'] = city
    for n, node in enumerate(nodes[:-1]):
        if n in addrs and node != nodes[n + 1]:
            type = addrs[n][right * 3 + 0].lower()
            if type not in interp_types:
                continue
            type = interp_types[type]
            low = addrs[n][right * 3 + 1]
            hi = addrs[n][right * 3 + 2]

            dist = 0.0002  # degrees
            lat = projlat(float(points[node][0]))
            # lon = projlon(lat, float(points[node][1]))
            lon = projlon(float(points[node][1]))
            nlat = projlat(float(points[nodes[n + 1]][0]))
            # nlon = projlon(nlat, float(points[nodes[n + 1]][1]))
            nlon = projlon(float(points[nodes[n + 1]][1]))
            dlen = math.hypot(nlat - lat, nlon - lon)
            normlat = (nlat - lat) / dlen * dist
            normlon = (nlon - lon) / dlen * dist
            if right:
                dlat = -normlon
                dlon = normlat
            else:
                dlat = normlon
                dlon = -normlat
            if dlen > dist * 5:
                shortlat = normlat * 2
                shortlon = normlon * 2
            elif dlen > dist * 3:
                shortlat = normlat
                shortlon = normlon
            else:
                shortlat = 0
                shortlon = 0

            if 0: #prev_house == low:
                low_node = prev_node
            elif low == hi:
                shortlat = (nlat - lat) / 2
                shortlon = (nlon - lon) / 2
                pt0 = 0
            else:
                pt0 = len(points)
                low_node = unproj(lat + dlat + shortlat, lon + dlon + shortlon)
                while low_node in points:
                    low_node = (low_node[0] + normlat / 10,
                                low_node[1] + normlon / 10)
                attrs['addr:housenumber'] = low
                points_append(low_node, attrs.copy())

            pt1 = len(points)
            hi_node = unproj(nlat + dlat - shortlat, nlon + dlon - shortlon)
            while hi_node in points:
                hi_node = (hi_node[0] - normlat / 10, hi_node[1] - normlon / 10)
            attrs['addr:housenumber'] = hi
            points_append(hi_node, attrs.copy())

            if len(addrs[n]) >= 8:
                if addrs[n][6] != "-1":
                    pointattrs[pt0]['addr:postcode'] = addrs[n][6]
                if addrs[n][7] != "-1":
                    pointattrs[pt1]['addr:postcode'] = addrs[n][7]
            if len(addrs[n]) >= 14:
                if addrs[n][8] != "-1":
                    pointattrs[pt0]['addr:city'] = addrs[n][8]
                if addrs[n][9] != "-1":
                    pointattrs[pt0]['addr:region'] = addrs[n][9]
                if addrs[n][10] != "-1":
                    pointattrs[pt0]['addr:country'] = addrs[n][10]
                if addrs[n][11] != "-1":
                    pointattrs[pt1]['addr:city'] = addrs[n][11]
                if addrs[n][12] != "-1":
                    pointattrs[pt1]['addr:region'] = addrs[n][12]
                if addrs[n][13] != "-1":
                    pointattrs[pt1]['addr:country'] = addrs[n][13]

            way = {
                '_timestamp': filestamp,
                '_nodes': [pt0, pt1],
                'addr:interpolation': type,
                '_c': count,
                ## '_src': srcidx,
                'is_in': city,
                'NumberX': 'yes'
            }
            if low != hi:
                ways.append(way)

            prev_house = hi
            prev_node = hi_node
        else:
            prev_house = "xx"
        

def points_append(node, attrs):
    # attrs['_src'] = srcidx
    attrs['_timestamp'] = filestamp
    points.append(node)
    pointattrs[points.index(node)] = attrs

            
def prepare_line(nodes_str, closed=False):
    """Appends new nodes to the points list"""
    nodes = []
    for element in nodes_str.split(','):
        element = element.strip('()')
        nodes.append(element)

    #  lats = nodes[::2]
    #  longs = nodes[1::2]

    lats = []
    longs = []

    for la in nodes[::2]:
        l = len(la)
        if l < 9:
            la += '0' * (9 - l)
        lats.append(la)

    for lo in nodes[1::2]:
        l = len(lo)
        if l < 9:
            lo += '0' * (9 - l)
        longs.append(lo)

    nodes = list(zip(lats, longs))
    for node in nodes:
        if node not in points:
            points_append(node, {})
    try:
        node_indices = list(map(points.index, nodes))
    except:
        print(points)
        print(node)
        raise ParsingError('Can\'t map node indices')
    pts = 0
    for node in node_indices:
        if '_out' not in pointattrs[node]:
            pts += 1
    if closed:
        node_indices.append(node_indices[0])
    return pts, node_indices

            
def convert_tags_return_way(mp_record, feat, ignore_errors):
    maxspeeds = {'0': '8', '1': '20', '2': '40', '3': '56', '4': '72', '5': '93', '6': '108', '7': '128'}
    levels = {1: "residential", 2: "tertiary", 3: "secondary", 4: "trunk"}
    exceptions = ('emergency', 'goods', 'motorcar', 'psv', 'taxi', 'foot', 'bicycle', 'hgv')
    reftype = {0x02: 'ref', 0x05: 'ref', 0x1d: 'loc_name',  # Abbrevations
               0x1f: 'ele', 0x2a: 'int_ref',  #  Fixme should differentate the types
               0x2b: 'int_ref', 0x2c: 'int_ref', 0x2d: 'ref', 0x2e: 'ref', 0x2f: 'ref', 0x1e: 'loc_name',
               0x01: 'int_ref', 0x02: 'int_ref', 0x04: 'ref', 0x06: 'ref'}
    ump_countries = {'Austria': "Austria", 'Białoruś': "Belarus", 'Czechy': "Czech Republic", 'Grecja': "Grecja",
                     'Litwa': "Lithuania", 'Łotwa': "Latvia", 'Niemcy': "Germany", 'Rosja': "Russia",
                     'Słowacja': "Slovakia", 'Ukraina': "Ukraine", 'Węgry': "Hungary"}
    turn_lanes = {"*": "none", "S": "through", "T": "through", "Z": "reverse", "P": "right", "L": "left",
                  "osP": "sharp_right", "osL": "sharp_left", "leP": "slight_right", "leL": "slight_left",
                  "doP": "merge_to_right", "doL": "merge_to_left",
                  # 2 specjalne dla pasów tylko w jedną stronę ale wymagające kontynuacji na następnym odcinku
                  "(P)": "right;through", "(L)": "left;through",
                  # Przy kontynuacji dla podwójnych skrzyżowań (stosować przed, a w środku już bez *, pamiętając o
                  # odjęciu lewoskrętów) w przeciwieństwie do 7ways gdzie jest none, w osmand można stosować prawidłowe
                  # oznaczenia gdyż ma to inną funkcję.
                  "*S": "through", "*T": "through", "*Z": "reverse", "*P": "right", "*L": "left",
                  "+": ";",  # faster conversion
                  "|": "|"}
    way = {'_timestamp': filestamp}
    for key, value in mp_record.items():
        if not value:
            continue
        if key.lower() in ('label',):
            label = value
            refpos = label.find("~[")
            if refpos > -1:
                try:
                    # refstr, sep, right = label[refpos + 2:].partition(' ')            # py_ver >= 2.5 version
                    label_split = label[refpos + 2:].split(' ', 1)                        # above line in py_ver = 2.4
                    if len(label_split) == 2:
                        refstr, right = label[refpos + 2:].split(' ', 1)
                    else:
                        refstr = label_split[0]
                        right = ""

                    code, ref = refstr.split(']')
                    label = (label[:refpos] + right).strip(' \t')
                    way[reftype[int(code, 0)]] = ref.replace("/", ";")
                except:
                    if code.lower() == '0x06':
                        label = ref + label
                        pass
                    elif code.lower() == '0x1b':
                        way['loc_name'] = right
                        label = ref + label
                    elif code.lower() == '0x1c':
                        way['loc_name'] = ref
                        label = ref + label
                    elif code.lower() == '0x1c':
                        label = value.replace('~[0x1c]', '')
                        printerror("1C" + label)
                    elif code.lower() == '0x1e':
                        label = value.replace('~[0x1e]', ' ')
                        printerror("1E" + label)
                    else:
                        raise ParsingError('Problem parsing label ' + value)
            if 'name' not in way and label != "":
                way['name'] = label.strip()
        elif key.lower() in ('label2',):
            way['loc_name'] = value
        elif key.lower() in ('fulllabel',):
            pass
        elif key.lower() == 'label3':
            way['alt_name'] = value
        elif key.lower() == 'adrlabel':
            way['alt_name'] = value
        elif key.lower() == 'typ':
            way['ump:typ'] = value
        elif key == 'DirIndicator':
            if value == '1':
                way['oneway'] = 'yes'
            else:
                way['oneway'] = value
        elif key in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4',):
            num = int(key[4:])
            count, way['_nodes'] = prepare_line(value, closed=feat == Features.polygon)
            if '_c' in way:
                way['_c'] += count
            else:
                way['_c'] = count
            # way['layer'] = num ??
        elif key.startswith('_Inner'):
            count, nodes = prepare_line(value, closed=feat == Features.polygon)
            if '_innernodes' not in way:
                way['_innernodes'] = []
                if feat != Features.polygon:
                    way['_join'] = 1
            way['_innernodes'].append(nodes)
            if '_c' in way:
                way['_c'] += count
            else:
                way['_c'] = count
        elif key == 'Type':
            if feat == Features.polyline:
                way['ump:type'] = value
                if int(value, 0) in pline_types:
                    tag(way, pline_types[int(value, 0)])
                else:
                    printerror("Unknown line type "+hex(int(value, 0)))
            else:
                way['ump:type'] = value
        elif key in ('EndLevel', 'Level', 'Levels',):
            # if 'highway' not in way:
            #     way['highway'] = levels[int(value, 0)]
            # way['layer'] = str(value) ??
            pass
        elif key.lower() == 'miasto':
            way['addr:city'] = value.replace('@', ';')
            way['is_in'] = value.replace('@', ';')
        elif key.lower() == 'streetdesc':
            way['addr:street'] = value
        elif key.lower() == 'cityname':
            way['addr:city'] = value.replace('@', ';')
            way['is_in'] = value.replace('@', ';')
        elif key == 'MiscInfo':
            # wiki => "wikipedia=pl:" fb, url => "website="
            if '=' in value:
                misckey, miscvalue = value.split("=", 1)
                if misckey == 'url':
                    if miscvalue.startswith('http') or miscvalue.find(':') > 0:
                        way['website'] = miscvalue
                    else:
                        way['website'] = r"http://"+miscvalue
                elif misckey == 'wiki':
                    if not miscvalue.startswith('http'):
                        way['wikipedia'] = "pl:"+miscvalue
                    else:
                        way['website'] = miscvalue
                elif misckey == 'fb':  # 'facebook' tag isn't widely used
                    if not miscvalue.startswith('http'):
                        way['website'] = "https://facebook.com/" + miscvalue
                    else:
                        way['website'] = miscvalue
                pass
            else:
                printerror("Niewlaciwy format MiscInfo: " + value)
        elif key == 'Transit':  # "no thru traffic" / "local traffic only"
            if value.lower().startswith('n'):
                way['access'] = 'destination'
        elif key == 'Moto':
            if value.lower().startswith('y'):
                way['motorcycle'] = 'yes'
            else:
                way['motorcycle'] = 'no'
        elif key in ('RouteParam', 'Routeparam'):
            params = value.split(',')
            way['ump:speed_limit'] = params[0]
            way['ump:route_class'] = params[1]
            if params[0] != '0':
                way['maxspeed'] = maxspeeds[params[0]]  # Probably useless
            if params[2] == '1':
                way['oneway'] = 'yes'
            if params[3] == '1':
                way['toll'] = 'yes'
            for i, val in enumerate(params[4:]):
                if val == '1':
                    way[exceptions[i]] = 'no'
        elif key == 'RestrParam':
            params = value.split(',')
            excpts = []
            for i, val in enumerate(params[4:]):
                if val == '1':
                    excpts.append(exceptions[i])
            way['except'] = ','.join(excpts)
        elif key == 'HLevel0':
            if feat != Features.polyline:
                raise ParsingError('HLevel0 used on a polygon')
            curlevel = 0
            curnode = 0
            level_list = []
            for level in value.split(')'):
                if level == "":
                    break
                pair = level.strip(', ()').split(',')
                start = int(pair[0], 0)
                level = int(pair[1], 0)
                if start > curnode and level != curlevel:
                    level_list.append((curnode, start, curlevel))
                    curnode = start
                curlevel = level
            level_list.append((curnode, -1, curlevel))
            way['_levels'] = level_list
        elif key == 'Szlak':
            ref = []
            for colour in value.split(','):
                if colour.lower() == 'zolty':
                    ref.append('Żółty szlak')
                    way['marked_trail_yellow'] = 'yes'
                elif colour.lower() == 'zielony':
                    ref.append('Zielony szlak')
                    way['marked_trail_green'] = 'yes'
                elif colour.lower() == 'czerwony':
                    ref.append('Czerwony szlak')
                    way['marked_trail_red'] = 'yes'
                elif colour.lower() == 'niebieski':
                    ref.append('Niebieski szlak')
                    way['marked_trail_blue'] = 'yes'
                else:
                    ref.append(colour)
                    printerror("Unknown 'Szlak' colour: " + colour)
            way['ref'] = ";".join(ref)
        elif key.startswith('NumbersExt'):
            printerror("warning: " + key + " tag discarded")
        elif key.startswith('Numbers'):
            unused = int(key[7:], 0)
            value = value.split(',')
            if len(value) < 7:
                raise ParsingError("Bad address info specification")
            if '_addr' not in way:
                way['_addr'] = {}
            way['_addr'][int(value[0], 0)] = value[1:]
        elif key.lower() == 'rampa':
            way['bridge'] = 'yes'
        elif key == 'Highway':
            way['ref'] = value
        elif key.startswith('Exit'):
            way[key.lower()] = value
        elif key == 'OvernightParking':
            way['overnight_parking'] = 'yes'
        elif key == 'Phone':
            way['phone'] = value
        elif key == 'HouseNumber':
            way['addr:housenumber'] = value
        elif key == 'KodPoczt':
            way['addr:postcode'] = value
        elif key == 'ZIP':
            way['addr:postcode'] = value
        elif key == 'Zip':
            pass
        elif key == 'Time':
            way['hour_on'] = value
        elif key == 'Height_f':
            way['wysokosc'] = value
        elif key == 'Rozmiar':
            way['Rozmiar'] = value
        elif key == 'ForceSpeed':
            fspeed = value  # Routing helper
        elif key == 'ForceClass':
            fclass = value  # Routing helper
            # Ignore it for the moment, seems to be used mainly for temporary setups
            # such as detours.
        elif key == 'Speed':
            way['maxspeed'] = value
        elif key == 'Lanes':
            way['lanes'] = value
        elif key == 'LA':
            # TODO: LA moze miec LA=|dane| lub LA=dane oraz LA=+|dane1|;-|dane2|
            if ";" in value:
                # lanes:forward=1 lanes:backward=2 i lanes=3   tak, sumujemy
                # turn:lanes:forward= turn:lanes:backward=
                la = value.split(';')
                pass
            else:
                if value[0] == "|":  # można by użyć strip gdyby nie to że |||cośtam| jest poprawne (acz niezalecane)
                    value = value[1:]
                if value[-1] == "|":
                    value = value[:-1]
                way['turn:lanes'] = "".join([turn_lanes.get(op, op) for op in re.split('([|+])', value)])
                way['lanes'] = str(value.count('|') + 1)
        elif key == 'Floors':
            way['building:levels'] = value
        elif key == 'Height_m' or key == 'MaxHeight':
            way['maxheight'] = value
        elif key == 'MaxWidth':
            way['maxwidth'] = value
        elif key == 'MaxWeight' or key == 'Weight_t':
            way['maxweight'] = value
        elif key == 'Oplata:moto':
            way['charge:motorcycle'] = value
        elif key == 'Oplata':
            way['charge'] = value
        elif key == 'Czas':
            way['duration'] = value
        elif key in ('Plik', 'City',):
            pass
        elif key == 'RegionName':
            way['is_in:state'] = value
        elif key == 'CountryName':
            way['is_in:country'] = re.sub('-UMP~.*$', '', value)
            if way['is_in:country'] in ump_countries:
                way['is_in:country'] = ump_countries[way['is_in:country']]
        elif key == 'CountryCode':
            way['is_in:country_code'] = value
        elif key in ('Sign', 'SignPos', 'SignAngle',):
            # TODO: znaki zakazu
            pass
        elif key in ('DontDisplayAddr', 'DontDisplayAdr',):
            # TODO: obsluga adresacji
            pass
        elif key in ('DontFind',):
            # TODO: obsluga adresacji
            pass
        elif key in ('SignLabel',):
            # TODO: pomysl Art
            signs = value.split(';')
            for sign in signs:
                if sign.strip() == "":  # puste pozycje ignorujemy
                    pass
                # wersja uproszczona bez dodatkowych liter E,T,O
                elif sign[0] == '+':
                    if len(signs) == 1:
                        way['destination'] = sign[1:].replace("\\", ";")
                    else:
                        way['destination:forward'] = sign[1:].replace("\\", ";")
                elif sign[0] == '-':
                    way['destination:backward'] = sign[1:].replace("\\", ";")
        elif key in ('TLanes', 'Rodzaj', 'Weight_t',):
            # experymenty Ar't
            pass
        elif key in ('RoadID',):
            # lets omit routing params for maps with routing data
            pass
        elif key.startswith('Nod'):
            # lets omit routing params for maps with routing data
            pass
        # WebPage jest tagiem dla budynkow, Oplata:rower, Oplata: moto ignorujemy na chwile obecna
        elif key in ('WebPage', 'Oplata:rower', 'Oplata:moto',):
            pass
        else:
            if ignore_errors:
                printwarn("W: Unknown key: " + key)
                printwarn("W: Value:       " + value)
                pass
            else:
                raise ParsingError("Unknown key " + key + " in polyline / polygon")
    return way


def parse_txt(infile, options, filename='', progress_bar=None):
    otwarteDict = {"([Pp]n|pon\.)": "Mo", "([Ww]t|wt\.)": "Tu", "([Ss]r|śr|Śr|śr\.)": "We", "([Cc]z|czw\.)": "Th",
                   "([Pp]t|piąt\.|pt\.)": "Fr", "([Ss]o|[Ss]b|sob\.)": "Sa", "([Nn]d|ni|niedz\.)": "Su"}
    maxtypes = {}
    polyline = None
    feat = None
    comment = None
    linenum = 0
    for line in infile:
        linenum += 1
        progress_bar.set_val(linenum, 'mp')
        line = line.strip()
        if line == "[POLYLINE]":
            polyline = {}
            feat = Features.polyline
        elif line == "[POLYGON]":
            polyline = {}
            feat = Features.polygon
        elif line == "[POI]":
            polyline = {}
            feat = Features.poi
        elif line in ("[IMG ID]", '[CYFRY]', '[SIGN]', '[RESTRICT]'):
            polyline = {}
            feat = Features.ignore
        elif line == '[END]' and feat != Features.ignore:
            way = convert_tags_return_way(polyline, feat, options.ignore_errors)
            if feat == Features.polygon:
                if 'ump:typ' in way:
                    utyp = way['ump:typ']
                    if utyp in umpshape_types:
                        t = umpshape_types[utyp]
                    else:
                        t = int(way['ump:type'], 0)
                else:
                    t = int(way['ump:type'], 0)
                if t in shape_types:
                    tag(way, shape_types[t])
                else:
                    printerror("Unknown shape type " + hex(t))

            elif feat == Features.poi:
                if 'ump:typ' in way:
                    utyp = way['ump:typ']
                    if utyp in umppoi_types:
                        t = umppoi_types[utyp]
                    else:
                        t = int(way['ump:type'], 0)
                else:
                    t = int(way['ump:type'], 0)
                # obsluga bledow Type=
                if t in poi_types:
                    tag(way, poi_types[t])
                else:
                    printerror("Unknown poi type " + hex(t))

                # Label=Supermarket (24h), Typ=24H
                if 'name' in way and (way['name'].find('(24h)') > -1 or way['name'].find('(24H)') > -1 or
                                      way['name'].find('{24h}') > -1 or way['name'].find('{24H}') > -1):
                    way['opening_hours'] = "24/7"
                else:
                    if 'ump:typ' in way and way['ump:typ'] == "24H":
                        way['opening_hours'] = "24/7"

                # pooprawa nazw ulic dla POI (gdy wpisane sa dwie ulice przedzielone slashem)
                if 'addr:street' in way:
                    match = re.match('(.*)[,/] *(.*)', way['addr:street'])
                    if match:
                        way['addr:street'] = match.group(2)
                        # if 'addr:housenumber' in way:
                        # way['addr:housenumber'] += ''.join(' (', match.group(1), ')')

            elif feat == Features.polyline:

                # TxF: tu potrzebna do wlasciwego indeksowania obsluga przedrostkow
                if 'name' in way and cut_prefix(way['name']) != way['name']:
                    way['short_name'] = cut_prefix(way['name'])
                elif 'loc_name' in way and cut_prefix(way['loc_name']) != way['loc_name']:
                    way['short_name'] = cut_prefix(way['loc_name'])
                elif 'alt_name' in way and cut_prefix(way['alt_name']) != way['alt_name']:
                    way['short_name'] = cut_prefix(way['alt_name'])

                # nie pchajmy rowerow przez '{schody}'
                if 'ump:type' in way and (way['ump:type'] == "0x16") and ('name' in way) and \
                        (way['name'].find('schody') > -1):
                    way['highway'] = "steps"

            if comment is not None:
                # way['note'] = comment
                if feat == Features.poi and 'opening_hours' not in way:
                    # opening hours taken from the comment
                    p = re.compile('otwarte:', re.IGNORECASE)
                    match = p.search(comment)
                    if match is not None:
                        val = comment[match.end():].strip()
                        p = re.compile('\^', re.IGNORECASE)	 # to moze byc wielolinijkowy komentarz
                        match = p.search(val)
                        if match is not None:
                            val = val[:match.start()]		# odciecie

                        # Pn-So 09:00-20:00; Nd 09:30-18:00" => 'Mo-Sa 09:00-20:00; Su 09:30-18:00'
                        for x in otwarteDict:
                            val = re.sub(x, otwarteDict[x], val)
                        way['opening_hours'] = val
            comment = None
            if 'Type' in polyline and feat == Features.polyline:
                highway = int(polyline['Type'], 0)
                if highway <= 16:
                    for i in way['_nodes']:
                        if i in maxtypes:
                            if maxtypes[i] > highway:
                                maxtypes[i] = highway
                        else:
                            maxtypes[i] = highway
            polyline = None

            if '_addr' in way:
                addrinfo = way.pop('_addr')
                p = re.compile('\{.*\}')                        # dowolny string otoczony klamrami
                if 'alt_name' in way:
                    street = way['alt_name']
                # klamry w nazwie eliminuja wpis jako wlasciwa nazwe dla adresacji
                elif ('name' in way) and (not p.search(way['name'])):
                    street = way['name']
                elif 'loc_name' in way:
                    street = way['loc_name']
                elif 'short_name' in way:
                    street = way['short_name']
                else:
                    if'name' in way:
                        street = way['name']
                    else:
                        street = "<empty>"
                    printerror("Line:" + str(linenum)+":Numeracja - brak poprawnej nazwy ulicy: '" + street + "'.")
                    street = 'STREET_missing'
                try:
                    m = way['addr:city']
                except:
                    m = 'MIASTO_missing'
                    printerror("Line:" + str(linenum) + ":Numeracja - brak Miasto=!")
                try:
                    region = way['is_in:state']
                except:
                    region = ""
                    printerror("Line:" + str(linenum) + ":Numeracja - brak RegionName=!")
                add_addrinfo(way['_nodes'], addrinfo, street, m, region, 0, way['_c'])
                add_addrinfo(way['_nodes'], addrinfo, street, m, region, 1, way['_c'])
            if 'ele' in way and 'name' in way and way['ele'] == '_name':
                way['ele'] = way.pop('name').replace(',', '.')
            if 'depth' in way and 'name' in way and way['depth'] == '_name':
                way['depth'] = way.pop('name').replace(',', '.')
            if feat == Features.polygon:
                polygon_make_ccw(way)

            if feat == Features.poi:
                # execution order shouldn't matter here, unlike in C
                pointattrs[way.pop('_nodes')[0]] = way
                if not way.pop('_c'):
                    way['_out'] = 1
            else:
                ways.append(way)

        elif feat == Features.ignore:
            # Ignore everything within e.g. [IMG ID] until some other
            # rule picks up something interesting, e.g. a polyline
            pass
        elif polyline is not None and line != '':
            try:
                key, value = line.split('=', 1)
            except:
                printerror(line)
                raise ParsingError('Can\'t split the thing')
            key = key.strip()
            if key in polyline:
                if key.startswith('Data'):
                    key = "_Inner0"
                    while key in polyline:
                        key = "_Inner" + str(int(key[6:]) + 1)
                elif key == 'City' and polyline[key] == 'Y':
                    pass
                else:
                    printerror("Line:" + str(linenum) + ": Ignoring repeated key " + key + "!")
            polyline[key] = recode(value).strip()
        elif line.startswith(';'):
            strn = recode(line[1:].strip(" \t\n"))
            if comment is not None:
                comment = comment + "^ " + strn
            else:
                comment = strn
        elif line != '':
            raise ParsingError('Unhandled line ' + line)
    return maxtypes


def create_node_ways_relation(all_ways):
    tmp_node_ways_rel = defaultdict(set)
    tmp_node_ways_rel_multipolygon = defaultdict(set)
    for way_no, way in enumerate(all_ways):
        if way is None:
            continue
        if 'ump:type' in way and int(way['ump:type'], 16) <= 0x16 and int(way['ump:type'], 0) in pline_types and \
                pline_types[int(way['ump:type'], 0)][0] in way:
            for node in way["_nodes"]:
                tmp_node_ways_rel[node].add(way_no)
        if '_innernodes' in way and '_join' not in way:
            for node in way["_nodes"]:
                tmp_node_ways_rel_multipolygon[node].add(way_no)
    # lets return simple dictionary, as defaultdict resulted in creating empty entry in case of list
    # comprehension
    return {a: tmp_node_ways_rel[a] for a in tmp_node_ways_rel}, \
           {a: tmp_node_ways_rel_multipolygon[a] for a in tmp_node_ways_rel_multipolygon}


def nodes_to_way_id(a, b, node_ways_relation=None):
    if a not in node_ways_relation or b not in node_ways_relation:
        raise NodesToWayNotFound(a, b)
    ways_a = set([road_id for road_id in node_ways_relation[a] if road_id < len(ways) and ways[road_id] is not None])
    ways_b = set([road_id for road_id in node_ways_relation[b] if road_id < len(ways) and ways[road_id] is not None])
    way_ids = ways_a.intersection(ways_b)
    if len(way_ids) == 1:
        return tuple(way_ids)[0]
    elif len(way_ids) > 1:
        printerror("DEBUG: multiple roads found for restriction. Using only one")
        for way_id in way_ids:
            printerror(str(ways[way_id]))
            printerror(str([points[node] for node in ways[way_id]['_nodes']]))
        return tuple(way_ids)[0]
    else:
        printerror("DEBUG: no roads found for restriction.")
        printerror(','.join(points[a]) + ' ' + ','.join(points[b]))
        printerror(str(node_ways_relation[a]))
        printerror(str(node_ways_relation[b]))
        for way in ways:
            if way is None:
                continue
            way_nodes = way['_nodes']
            if a in way_nodes:
                printerror("DEBUG: node a: %r found in way: %r" % (a, way))
            if b in way_nodes:
                printerror("DEBUG: node b: %r found in way: %r" % (b, way))
        raise NodesToWayNotFound(a, b)
    return None


def nodes_to_way(a, b, node_ways_relation=None):
    return ways[nodes_to_way_id(a, b, node_ways_relation=node_ways_relation)]


def way_to_way_id(way, node_ways_relation=None):
    if node_ways_relation is None:
        return None
    way_id_set = set()
    for num, node in enumerate(way['_nodes']):
        if num == 0:
            way_id_set = node_ways_relation[node]
        else:
            way_id_set.intersection(node_ways_relation[node])
        if len(way_id_set) == 1:
            return tuple(way_id_set)[0]
    return None


def distKM(lat0, lon0, lat1, lon1):
    degtokm = math.pi * 12742 / 360
    latcorr = math.cos(math.radians(float(lat1)))
    dlat = (float(lat1) - float(lat0)) * degtokm
    dlon = (float(lon1) - float(lon0)) * degtokm * latcorr
    return math.sqrt(dlat ** 2 + dlon ** 2)


def signbit(x):
    if x > 0:
        return 1
    if x < 0:
        return -1


def next_node(pivot=None, direction=None, node_ways_relation=None):
    """
    return either next or previous node relative to the pivot point. In some cases does not do anythnig as the next
    point is the only one
    :param pivot: the node that is our reference
    :param direction: in which direction we are looking, according or against nodes order
    :return: one node of given road
    """
    way_nodes = nodes_to_way(direction, pivot, node_ways_relation=node_ways_relation)['_nodes']
    pivotidx = way_nodes.index(pivot)
    return way_nodes[pivotidx + signbit(way_nodes.index(direction) - pivotidx)]


def split_way(way=None, splitting_point=None, node_ways_relation=None):
    global ways
    l = len(way['_nodes'])
    i = way['_nodes'].index(splitting_point)
    if i == 0 or i == l - 1:
        return
    # tu mozna by jesze przyspieszyc bo index dla listy jest wolny, ale z drugiej strony zakazow nie jest az tak duzo
    # trzeba by pomyslec ewentualnie
    way_id = way_to_way_id(way, node_ways_relation)
    if way_id is None:
        way_id = ways.index(way)
    for way_node in way['_nodes']:
        node_ways_relation[way_node].discard(way_id)
    newway = way.copy()
    newway['_nodes'] = way['_nodes'][:i + 1]
    way['_nodes'] = way['_nodes'][i:]
    # lets add way nodes to the node_ways_relation
    for way_node in way['_nodes']:
        node_ways_relation[way_node].add(way_id)
    ways.append(newway)
    newway_id = len(ways) - 1
    # lets add newway nodes to the node_ways_relation
    for way_node in newway['_nodes']:
        node_ways_relation[way_node].add(newway_id)


def name_turn_restriction(rel, nodes):

    # Multiple via nodes are not approved by OSM anyway
    if 'restriction' not in rel and len(nodes) == 3:
        # No projection needed
        alat = float(points[nodes[0]][0])
        alon = float(points[nodes[0]][1])
        blat = float(points[nodes[1]][0])
        blon = float(points[nodes[1]][1])
        clat = float(points[nodes[2]][0])
        clon = float(points[nodes[2]][1])
        # Vector cross product (?)
        angle = (blat - alat) * (clon - blon) - (blon - alon) * (clat - blat)

        if angle > 0.0:
            rel['restriction'] = 'no_right_turn'
        else:
            rel['restriction'] = 'no_left_turn'
    if len(nodes) == 4:
        rel['restriction'] = 'no_u_turn'    
    

def preprepare_restriction(rel, node_ways_relation=None):
    """
    modification of relation nodes so, that it starts and ends one node after and one node before central point
    called pivot here. It simplifies calculations as in some cases ways are split then, eg when there are levels.
    :param rel: relaton
    :return: None, id modifies nodes by reference
    """
    new_rel_node_first = next_node(pivot=rel['_nodes'][1], direction=rel['_nodes'][0],
                                   node_ways_relation=node_ways_relation)
    new_rel_node_last = next_node(pivot=rel['_nodes'][-2], direction=rel['_nodes'][-1],
                                  node_ways_relation=node_ways_relation)
    rel['_nodes'][0] = new_rel_node_first
    rel['_nodes'][-1] = new_rel_node_last


def prepare_restriction(rel, node_ways_relation=None):
    fromnode = rel['_nodes'][0]
    fromvia = rel['_nodes'][1]
    tonode = rel['_nodes'][-1]
    tovia = rel['_nodes'][-2]
    # The "from" and "to" members must start/end at the Role via node or the Role via way(s), otherwise split it!
    split_way(way=nodes_to_way(fromnode, fromvia, node_ways_relation=node_ways_relation), splitting_point=fromvia,
              node_ways_relation=node_ways_relation)
    split_way(way=nodes_to_way(tonode, tovia, node_ways_relation=node_ways_relation), splitting_point=tovia,
              node_ways_relation=node_ways_relation)


def return_roadid_in_ways(way, road_to_road_id=None):
    return road_to_road_id[id(way)]

def make_restriction_fromviato(rel, node_ways_relation=None):
    nodes = rel.pop('_nodes')
    # from_way_index = ways.index(nodes_to_way(nodes[0], nodes[1]))
    # to_way_index = ways.index(nodes_to_way(nodes[-2], nodes[-1]))
    from_way_index = nodes_to_way_id(nodes[0], nodes[1], node_ways_relation=node_ways_relation)
    to_way_index = nodes_to_way_id(nodes[-2], nodes[-1], node_ways_relation=node_ways_relation)
    rel['_members'] = {
        'from': ('way', [from_way_index]),
        'via':  ('node', nodes[1:-1]),
        'to':   ('way', [to_way_index]),
    }

    rel['_c'] = ways[rel['_members']['from'][1][0]]['_c'] + ways[rel['_members']['to'][1][0]]['_c']
    if rel['_c'] > 0:
        ways[rel['_members']['from'][1][0]]['_c'] += 1
        ways[rel['_members']['to'][1][0]]['_c'] += 1

    return nodes


def make_multipolygon(outer, holes, node_ways_relation=None):
    if node_ways_relation is None:
        outer_index = ways.index(outer)
    else:
        outer_index = way_to_way_id(outer, node_ways_relation)
    if outer_index is None:
        outer_index = ways.index(outer)
    rel = {
        '_timestamp': filestamp,
        'type':     'multipolygon',
        'note':     'FIXME: fix roles manually',
        '_c':       outer['_c'],
        '_members': {
            # 'outer': ('way', [ways.index(outer)]),
            'outer': ('way', [outer_index]),
            'inner': ('way', []),
        },
    }

    for inner in holes:
        way = {
            '_timestamp': filestamp,
            '_c':     outer['_c'],
            '_nodes': inner,
        }
        ways.append(way)
        # rel['_members']['inner'][1].append(ways.index(way))
        rel['_members']['inner'][1].append(len(ways) - 1)
        polygon_make_ccw(way)

        # Assume that the polygon with most nodes is the outer shape and
        # all other polygons are the holes.
        # That's a stupid heuristic but is much simpler than a complete
        # check of which polygons lie entirely inside other polygons and
        # there might turn up some very complex cases like polygons crossing
        # one another and multiple nesting.
        if len(inner) > len(outer['_nodes']):
            tmp = outer['_nodes']
            outer['_nodes'] = inner
            way['_nodes'] = tmp
        way['_nodes'].reverse()

    return rel


def index_to_nodeid(index):
    return index + 1


def index_to_wayid(index):
    return index_to_nodeid(len(points) + index)


def index_to_relationid(index):
    return index_to_wayid(len(ways) + index)


def xmlize(str):
    return saxutils.escape(str, {'\'': '&apos;'})


def print_point(point, index, ostr):
    global maxid
    global idpfx

    """Prints a pair of coordinates and their ID as XML"""
    if '_out' in pointattrs[index]:
        return
    if '_timestamp' in pointattrs[index]:
        timestamp = pointattrs[index]['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp for point %r\n" % pointattrs[index])
        timestamp = runstamp
    currid = index_to_nodeid(index)
    if currid > maxid:
        maxid = currid
    idstring = idpfx + str(currid)
    head = ''.join(("<node id='", idstring, "' timestamp='", str(timestamp), "' visible='true' ", extra_tags,
                    "lat='", str(point[0]), "' lon='", str(point[1]), "'>\n"))
    # print >>ostr, (head)
    ostr.write(head)
    if '_src' in pointattrs[index]:
        src = pointattrs[index].pop('_src')
    for key in pointattrs[index]:
        if key.startswith('_'):
            continue
        if len(str(pointattrs[index][key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(pointattrs[index][key]) + "\n")
            continue
        try:
            ostr.write(("\t<tag k='%s' v='%s' />\n" % (key, xmlize(pointattrs[index][key]))))
        except:
            sys.stderr.write("converting key " + key + ": " + str(pointattrs[index][key]) + " failed\n")
    ostr.write("</node>\n")


def print_point_pickled(point, pointattrs, task_id, orig_id, node_generalizator, ostr):
    if '_out' in pointattrs:
        return
    if '_timestamp' in pointattrs:
        timestamp = pointattrs['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp for point %r\n" % pointattrs)
        timestamp = runstamp
    currid = node_generalizator.get_node_id(task_id, orig_id)
    idstring = str(currid)
    head = ''.join(("<node id='", idstring, "' timestamp='", str(timestamp), "' visible='true' ", extra_tags,
                    "lat='", str(point[0]), "' lon='", str(point[1]), "'>\n"))
    # print >>ostr, (head)
    ostr.write(head)
    if '_src' in pointattrs:
        src = pointattrs.pop('_src')
    for key in pointattrs:
        if key.startswith('_'):
            continue
        if len(str(pointattrs[key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(pointattrs[key]) + "\n")
            continue
        try:
            ostr.write(("\t<tag k='%s' v='%s' />\n" % (key, xmlize(pointattrs[key]))))
        except:
            sys.stderr.write("converting key " + key + ": " + str(pointattrs[key]) + " failed\n")
    ostr.write("</node>\n")


def print_way(way, index, ostr):
    if way is None:
        return
    global maxid
    global idpfx

    """Prints a way given by way together with its ID to stdout as XML"""
#    pdb.set_trace()
    if '_c' in way:
        if way['_c'] <= 0:
            return
        way.pop('_c')
    if '_timestamp' in way:
        timestamp = way['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp in way %r\n" % way)
        timestamp = runstamp
    currid = index_to_wayid(index)
    if currid > maxid:
        maxid = currid
    idstring = idpfx + str(currid)
    ostr.write("<way id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for nindex in way['_nodes']:
        refstring = idpfx + str(index_to_nodeid(nindex))
        ostr.write("\t<nd ref='%s' />\n" % refstring)

    if '_src' in way:
        src = way.pop('_src')
    for key in way:
        if key.startswith('_'):
            continue
        if len(str(way[key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(way[key]) + "\n")
            continue
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(way[key])))
    ostr.write("</way>\n")

def print_way_pickled(way, task_id, orig_id, node_generalizator, ostr):
    if way is None:
        return
    if '_c' in way:
        if way['_c'] <= 0:
            return
        way.pop('_c')
    if '_timestamp' in way:
        timestamp = way['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp in way %r\n" % way)
        timestamp = runstamp
    currid = node_generalizator.get_way_id(task_id, orig_id)
    idstring = str(currid)
    ostr.write("<way id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for nindex in way['_nodes']:
        refstring = node_generalizator.get_node_id(task_id, nindex)
        ostr.write("\t<nd ref='%s' />\n" % refstring)

    if '_src' in way:
        src = way.pop('_src')
    for key in way:
        if key.startswith('_'):
            continue
        if len(str(way[key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(way[key]) + "\n")
            continue
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(way[key])))
    ostr.write("</way>\n")


def print_relation(rel, index, ostr):
    global maxid
    global idpfx

    """Prints a relation given by rel together with its ID to stdout as XML"""
    if '_c' in rel:
        if rel['_c'] <= 0:
            return
        rel.pop('_c')
    if "_members" not in rel:
        sys.stderr.write("warning: Unable to print relation not having memebers: %r\n" % rel)
        return

    if '_timestamp' in rel:
        timestamp = rel['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp in relation: %r\n" % rel)
        timestamp = runstamp
    currid = index_to_relationid(index)
    if currid > maxid:
        maxid = currid
    idstring = idpfx + str(currid)
    ostr.write("<relation id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for role, (type, members) in rel['_members'].items():
        for member in members:
            if type == "node":
                id = index_to_nodeid(member)
            elif type == "way":
                id = index_to_wayid(member)
            else:
                id = index_to_relationid(member)
            refstring = idpfx + str(id)
            # print >>ostr,("\t<member type='%s' ref='%s' role='%s' />" % (type, refstring, role))
            ostr.write("\t<member type='%s' ref='%s' role='%s' />\n" % (type, refstring, role))

    if '_src' in rel:
        src = rel.pop('_src')
    for key in rel:
        if key.startswith('_'):
            continue
        # print >>ostr,("\t<tag k='%s' v='%s' />" % (key, xmlize(rel[key])))
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(rel[key])))
        # print >>ostr,("\t<tag k='source' v='%s' />" % (source))
    # print >>ostr,("</relation>")
    ostr.write("</relation>\n")


def print_relation_pickled(rel, task_id, orig_id, node_generalizator, ostr):
    """Prints a relation given by rel together with its ID to stdout as XML"""
    if '_c' in rel:
        if rel['_c'] <= 0:
            return
        rel.pop('_c')
    if "_members" not in rel:
        sys.stderr.write("warning: Unable to print relation not having memebers: %r\n" % rel)
        return

    if '_timestamp' in rel:
        timestamp = rel['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp in relation: %r\n" % rel)
        timestamp = runstamp
    currid = node_generalizator.get_relation_id(task_id, orig_id)
    idstring = str(currid)
    ostr.write("<relation id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for role, (type, members) in rel['_members'].items():
        for member in members:
            if type == "node":
                id = node_generalizator.get_node_id(task_id, member)
            elif type == "way":
                id = node_generalizator.get_way_id(task_id, member)
            else:
                id = node_generalizator.get_relation_id(task_id, member)
            refstring = str(id)
            ostr.write("\t<member type='%s' ref='%s' role='%s' />\n" % (type, refstring, role))

    if '_src' in rel:
        src = rel.pop('_src')
    for key in rel:
        if key.startswith('_'):
            continue
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(rel[key])))
    ostr.write("</relation>\n")


def post_load_processing(options, filename='', maxtypes=None, progress_bar=None):
    if maxtypes is None:
        maxtypes = {}
    global relations
    global ways
    # Roundabouts:
    # Use the road class of the most important (lowest numbered) road
    # that meets the roundabout.
    # relations = [rel for rel in ways if '_rel' in rel]
    # relations = OrderedDict({rel_no: ways[rel_no] for rel_no in range(len(ways)) if '_rel' in ways[rel_no]})
    # levelledways = [way for way in ways if '_levels' in way]
    relations = OrderedDict()
    levelledways = OrderedDict()
    for way_no, way in enumerate(ways):
        if '_rel' in way:
            relations[way_no] = way
        elif '_levels' in ways[way_no]:
            levelledways[way_no] = way

    num_lines_to_process = 4 * len(ways) + 4 * len(relations) + len(pointattrs) + len(levelledways)
    _line_num = 0
    progress_bar.start(num_lines_to_process, 'drp')
    # processing roundabouts
    for way in ways:
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if 'junction' in way and way['junction'] == 'roundabout':
            maxtype = 0x7  # service
            for i in way['_nodes']:
                if maxtypes[i] < maxtype:
                    maxtype = maxtypes[i]
            tag(way, pline_types[maxtype])
            if 'oneway' in way:
                del way['oneway']
            # TODO make sure nodes are ordered counter-clockwise

    # Relations:
    # find them, remove from /ways/ and move to /relations/
    #
    # For restriction relations: locate members and split member ways
    # at the "via" node as required by
    # http://wiki.openstreetmap.org/wiki/Relation:restriction

    for way_id, rel in relations.items():
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        rel['type'] = rel.pop('_rel')
        ways[way_id] = None
        rel['_timestamp'] = filestamp

    node_ways_relation, node_multipolygon_relation = create_node_ways_relation(ways)

    # move start and end nodes of restriction to the next/before node to via
    for way_id, rel in relations.items():
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if rel['type'] in ('restriction', 'lane_restriction',):
            try:
                preprepare_restriction(rel, node_ways_relation=node_ways_relation)
                # print "DEBUG: preprepare_restriction(rel:%r) OK." % (rel,)
            except NodesToWayNotFound:
                sys.stderr.write("warning: Unable to find nodes to preprepare restriction from rel: %r\n" % rel)
    # Way level:  split ways on level changes
    # TODO: possibly emit a relation to group the ways
    for way_id, way in levelledways.items():
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if '_levels' in way:
            ways[way_id] = None
            if 'highway' in way and 'ump:type' in way and int(way['ump:type'], 16) <= 0x16:
                for node in way['_nodes']:
                    node_ways_relation[node].discard(way_id)
            nodes = way['_nodes']
            # levels = way.pop('_levels')
            for segment in way.pop('_levels'):
                subway = way.copy()
                if segment[1] == -1:
                    subway['_nodes'] = nodes[segment[0]:]
                else:
                    subway['_nodes'] = nodes[segment[0]:segment[1] + 1]
                if segment[2] != 0:
                    subway['layer'] = str(segment[2])
                if segment[2] > 0:
                    subway['bridge'] = 'yes'
                if segment[2] < 0:
                    subway['tunnel'] = 'yes'
                ways.append(subway)
                if 'highway' in subway and 'ump:type' in subway and int(subway['ump:type'], 16) <= 0x16:
                    new_way_id = len(ways) - 1
                    for node in ways[-1]['_nodes']:
                        node_ways_relation[node].add(new_way_id)

    # we have to transfer relations ordeded dict into the list, as it is easier to add elements to the end
    relations = [relations[road_id] for road_id in relations]
    for way in ways:
        _line_num += 1
        if way is None:
            continue
        progress_bar.set_val(_line_num, 'drp')
        if '_innernodes' in way:
            if '_join' in way:
                del way['_join']
                for segment in way.pop('_innernodes'):
                    subway = way.copy()
                    subway['_nodes'] = segment
                    ways.append(subway)
            else:
                relations.append(make_multipolygon(way, way.pop('_innernodes'),
                                                   node_ways_relation=node_multipolygon_relation))

    # for each relation/restriction split ways at via points as the "from" and "to" members must start/end at the
    # Role via node or the Role via way(s)
    for rel in relations:
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if rel['type'] in ('restriction', 'lane_restriction',):
            try:
                prepare_restriction(rel, node_ways_relation=node_ways_relation)
            except NodesToWayNotFound:
                sys.stderr.write("warning: Unable to find nodes to preprepare restriction from rel: %r\n" % rel)

    # theoretically here we could do
    # ways = [a for a in ways if a is not None]
    for rel in relations:
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if rel['type'] in ('restriction', 'lane_restriction',):
            try:
                rnodes = make_restriction_fromviato(rel, node_ways_relation=node_ways_relation)
                if rel['type'] == 'restriction':
                    name_turn_restriction(rel, rnodes)
            except NodesToWayNotFound:
                sys.stderr.write("warning: Unable to find nodes to " +
                            "preprepare restriction from rel: %r\n" % (rel,))


    # Quirks, but do not overwrite specific values
    for way in ways:
        _line_num += 1
        if way is None:
            continue
        progress_bar.set_val(_line_num, 'drp')
        if 'highway' in way and 'maxspeed' not in way:
            if way['highway'] == 'motorway':
                way['maxspeed'] = '140'
            if way['highway'] == 'trunk':
                way['maxspeed'] = '120'

    for index, point in pointattrs.items():
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if 'shop' in point and point['shop'] == 'fixme':
            for way in ways:
                if index in way['_nodes'] and 'highway' in way:
                    del point['shop']
                    point['noexit'] = 'yes'
                    break
    #   housenumber is used for bus/tram stop ref number
        if 'railway' in point and (point['railway'] == 'tram_stop' or point['railway'] == 'station'):
            if 'addr:housenumber' in point:
                del point['addr:housenumber']
        if 'highway' in point and point['highway'] == 'bus_stop':
            if 'addr:housenumber' in point:
                del point['addr:housenumber']
        # obsluga fotoradarow w formacie fotoradar@50
        if 'highway' in point and point['highway'] == 'speed_camera':
            if 'name' in point:
                speedpos = point['name'].find('@')
                if speedpos > -1:
                    n1, spd = point['name'].split('@')
                    point['maxspeed'] = spd.strip()
                    point['newname'] = n1.strip()

    for way in ways:
        _line_num += 1
        if way is None:
            continue
        progress_bar.set_val(_line_num, 'drp')
        if way['_c'] > 0:
            for node in way['_nodes']:
                if '_out' in pointattrs[node]:
                    del pointattrs[node]['_out']


def save_pickled_data(prefix, num):
    try:
        with open(prefix + ".normal." + str(num) + ".points_pickle", 'wb') as pickle_f:
            pickle.dump(points, pickle_f)
        with open(prefix + ".normal." + str(num) + ".pointsattrs_pickle", 'wb') as pickle_f:
            pickle.dump(pointattrs, pickle_f)
        with open(prefix + ".normal." + str(num) + ".ways_pickle", 'wb') as pickle_f:
            pickle.dump(ways, pickle_f)
        with open(prefix + ".normal." + str(num) + ".relations_pickle", 'wb') as pickle_f:
            pickle.dump(relations, pickle_f)
    except IOError:
        sys.stderr.write("\tERROR: Can't write pickle files \n")
        sys.exit()


def remove_label_braces(local_way):
    new_way = local_way.copy()
    p = re.compile('\{.*\}')  # dowolny string otoczony klamrami
    if 'alt_name' in new_way:
        tmpname = new_way['alt_name']
        if 'name' in new_way:  # przechowanie nazwy z Label
            nname = p.sub("", new_way['name'])
            new_way['alt_name'] = str.strip(nname)
        else:
            new_way.pop('alt_name')
        new_way['name'] = tmpname  # alt_name z Label3 to glowna nazwa do indeksowania

    else:
        if 'name' in new_way:
            nname = p.sub("", new_way['name'])
            new_way['name'] = str.strip(nname)

            if (new_way['name'] == ""):  # zastepowanie pustych name
                if ('loc_name' in new_way):
                    new_way['name'] = new_way['loc_name']
                    new_way.pop('loc_name')
                elif ('short_name' in new_way):
                    new_way['name'] = new_way['short_name']
    return new_way

def add_city_region_atm_to_pointsattr(l_pointsattr):
    _pac = l_pointsattr.copy()
    if options.regions and 'is_in:state' in _pac:
        if 'place' in _pac and _pac['place'] in {'city', 'town', 'village'}:
            _pac['name'] = ''.join((_pac['name'], " (", _pac['is_in:state'], ")"))
        if 'addr:city' in _pac:
            region = ''.join((" (", _pac['is_in:state'], ")"))
            cities = _pac['addr:city'].split(';')
            _pac['addr:city'] = cities.pop(0) + region
            for city in cities:
                _pac['addr:city'] += ";" + city + region
        if 'is_in' in _pac:
            region = ''.join((" (", _pac['is_in:state'], ")"))
            cities = _pac['is_in'].split(';')
            _pac['is_in'] = cities.pop(0) + region
            for city in cities:
                _pac['is_in'] += ";" + city + region

    # dodawanie amenity_atm dla bankomatow (dawniej bylo osmand_amenity=atm)
    if 'amenity' in _pac and _pac['amenity'] == 'atm':
        _pac['amenity_atm'] = 'atm'
    return _pac

def add_city_region_to_way(l_way):
    newway = l_way.copy()
    if 'addr:city' in newway:
        region = ''.join((" (", newway['is_in:state'], ")"))
        cities = newway['addr:city'].split(';')
        newway['addr:city'] = cities.pop(0) + region
        for city in cities:
            newway['addr:city'] += ";" + city + region
    if 'is_in' in newway:
        region = ''.join((" (", newway['is_in:state'], ")"))
        cities = newway['is_in'].split(';')
        newway['is_in'] = cities.pop(0) + region
        for city in cities:
            newway['is_in'] += ";" + city + region
    return newway


def output_normal(prefix, num, options):
    global maxid
    global idpfx

    try:
        f = prefix + ".normal." + str(num) + ".osm"
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open normal output file " + f + "!\n")
        sys.exit()
        
    for point in points:
        index = points.index(point)
        if options.skip_housenumbers:
            if ('note' in pointattrs[index]) and (pointattrs[index]['note'] == 'housenumber'):
                continue
        print_point(point, index, out)

    for index, way in enumerate(ways):
        print_way(way, index, out)

    for index, rel in enumerate(relations):
        print_relation(rel, index, out)

    out.close()


def output_normal_pickled(options, filetypes, pickled_filenames=None, node_generalizator=None):
    try:
        output_files = {a: tempfile.NamedTemporaryFile(mode='w', encoding="utf-8", delete=False) for a in filetypes}
    except IOError as ioerror:
        sys.stderr.write("\tERROR: Can't open normal output file " + ioerror.filename + "!\n")
        sys.exit()

    for task_id, pickled_point in enumerate(pickled_filenames['points']):
        with open(pickled_point, 'rb') as p_file, open(pickled_filenames['pointsattrs'][task_id], 'rb') as pattrs_file:
            orig_id = -1
            for _point, _points_attr in zip(pickle.load(p_file), pickle.load(pattrs_file).values()):
                orig_id += 1
                for filename in output_files:
                    out = output_files[filename]
                    if filename in {'normal', 'navit'}:
                        print_point_pickled(_point, _points_attr, task_id, orig_id, node_generalizator, out)
                    elif filename == 'no_numbers' and 'NumberX' not in _points_attr:
                        print_point_pickled(_point, _points_attr, task_id, orig_id, node_generalizator, out)
                    elif filename == 'index':
                        _pac = add_city_region_atm_to_pointsattr(_points_attr)
                        print_point_pickled(_point, _pac, task_id, orig_id, node_generalizator, out)

    for task_id, pickled_way in enumerate(pickled_filenames['ways']):
        with open(pickled_way, 'rb') as p_file:
            orig_id = -1
            for _way in pickle.load(p_file):
                orig_id += 1
                if _way is None:
                    continue
                for filename in output_files:
                    out = output_files[filename]
                    if filename == 'normal':
                        print_way_pickled(_way, task_id, orig_id, node_generalizator, out)
                    elif filename == 'navit':
                        newway = _way.copy()
                        if 'natural' in newway and newway['natural'] == 'coastline':
                            newway['natural'] = 'water'
                        print_way_pickled(newway, task_id, orig_id, node_generalizator, out)
                    elif filename == 'no_numbers' and 'NumberX' not in _way:
                        print_way_pickled(newway, task_id, orig_id, node_generalizator, out)
                    elif filename == 'index' and 'is_in' in _way:
                        newway = remove_label_braces(_way)
                        if options.regions and 'is_in:state' in newway:
                            newway = add_city_region_to_way(newway)
                        print_way_pickled(newway, task_id, orig_id, node_generalizator, out)

    for task_id, pickled_relation in enumerate(pickled_filenames['relations']):
        with open(pickled_relation, 'rb') as p_file:
            orig_id = -1
            for _relation in pickle.load(p_file):
                orig_id += 1
                print_relation_pickled(_relation, task_id, orig_id, node_generalizator, output_files['normal'])
                if 'navit' in output_files:
                    print_relation_pickled(_relation, task_id, orig_id, node_generalizator, output_files['navit'])
    for out in output_files.values():
        out.close()
    return {a: b.name for a, b in output_files.items()}


def output_navit(prefix, num):
    global maxid
    global idpfx

    try:
        f = prefix + ".navit." + str(num) + ".osm"
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open Navit output file " + f + "!\n")
        sys.exit()

    for point in points:
        index = points.index(point)
        print_point(point, index, out)

    for index, way in enumerate(ways):
        if way is None:
            continue
        newway = way.copy()
        if ('natural' in newway) and (newway['natural'] == 'coastline'):
            newway['natural'] = 'water'
        print_way(newway, index, out)

    for index, rel in enumerate(relations):
        print_relation(rel, index, out)

    out.close()


def output_index_pickled(options, pickled_filenames=None, node_generalizator=None):
    try:
        prefix = 'UMP_PL'
        num = 1
        f = prefix + ".index." + str(num) + ".osm"
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open normal output file " + f + "!\n")
        sys.exit()
    for task_id, pickled_point in enumerate(pickled_filenames['points']):
        with open(pickled_point, 'rb') as p_file, open(pickled_filenames['pointsattrs'][task_id], 'rb') as pattrs_file:
            orig_id = -1
            for _point, _points_attr in zip(pickle.load(p_file), pickle.load(pattrs_file).values()):
                orig_id += 1
                _pac = add_city_region_atm_to_pointsattr(_points_attr)
                print_point_pickled(_point, _pac, task_id, orig_id, node_generalizator, out)

        for task_id, pickled_way in enumerate(pickled_filenames['ways']):
            with open(pickled_way, 'rb') as p_file:
                orig_id = -1
                for _way in pickle.load(p_file):
                    orig_id += 1
                    if _way is None or 'is_in' not in _way:
                        continue
                    newway = remove_label_braces(_way)
                    if options.regions and 'is_in:state' in newway:
                        newway = add_city_region_to_way(newway)

                    print_way_pickled(newway, task_id, orig_id, node_generalizator, out)
    out.write("</osm>\n")
    out.close()

def output_index(prefix, num, options):
    global maxid
    global idpfx

    try:
        f = prefix + ".index." + str(num) + ".osm"
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open index output file " + f + "!\n")
        sys.exit()
    
    for point in points:
        index = points.index(point)
        attrs = pointattrs[index].copy()  # store them here

        if options.regions and 'is_in:state' in pointattrs[index]:
            if 'place' in pointattrs[index] and (pointattrs[index]['place'] == 'city' or
                                                 pointattrs[index]['place'] == 'town' or
                                                 pointattrs[index]['place'] == 'village'):
                pointattrs[index]['name'] = ''.join((pointattrs[index]['name'], " (", pointattrs[index]['is_in:state'],
                                                     ")"))

            if 'addr:city' in pointattrs[index]:
                region = ''.join((" (", pointattrs[index]['is_in:state'], ")"))
                cities = pointattrs[index]['addr:city'].split(';')
                pointattrs[index]['addr:city'] = cities.pop(0) + region
                for city in cities:
                    pointattrs[index]['addr:city'] += ";" + city + region

            if 'is_in' in pointattrs[index]:
                region = ''.join((" (", pointattrs[index]['is_in:state'], ")"))
                cities = pointattrs[index]['is_in'].split(';')
                pointattrs[index]['is_in'] = cities.pop(0) + region
                for city in cities:
                    pointattrs[index]['is_in'] += ";" + city + region

        # dodawanie amenity_atm dla bankomatow (dawniej bylo osmand_amenity=atm)
        if 'amenity' in pointattrs[index] and (pointattrs[index]['amenity'] == 'atm'):
            pointattrs[index]['amenity_atm'] = 'atm'

        print_point(point, index, out)
        pointattrs[index] = attrs.copy()	# restore

    # dla ulic bez nazwy (wyciete {}) uzupelniamy z loc_name lub podobnych
    for index, way in enumerate(ways):
        if way is None:
            continue
        if (not ('is_in' in way)): 
            continue

        newway = way.copy()
        p = re.compile('\{.*\}')                        # dowolny string otoczony klamrami
        if 'alt_name' in newway:
            tmpname = newway['alt_name']
            if 'name' in newway:			# przechowanie nazwy z Label
                nname = p.sub( "", newway['name'])
                newway['alt_name'] = str.strip(nname)
            else:
                newway.pop('alt_name')
            newway['name'] = tmpname			# alt_name z Label3 to glowna nazwa do indeksowania
            
        else:
            if 'name' in newway:
                nname = p.sub( "", newway['name'])
                newway['name'] = str.strip(nname)

                if (newway['name']==""):                     # zastepowanie pustych name
                    if ('loc_name' in newway):
                        newway['name'] = newway['loc_name']
                        newway.pop('loc_name')
                    elif ('short_name' in newway):
                        newway['name'] = newway['short_name']


        if options.regions and 'is_in:state' in newway:
            if 'addr:city' in newway:
                region = ''.join((" (", newway['is_in:state'], ")"))
                cities = newway['addr:city'].split(';')
                newway['addr:city'] = cities.pop(0) + region
                for city in cities:
                    newway['addr:city'] += ";" + city + region

            if 'is_in' in newway:
                region = ''.join((" (", newway['is_in:state'], ")"))
                cities = newway['is_in'].split(';')
                newway['is_in'] = cities.pop(0) + region
                for city in cities:
                    newway['is_in'] += ";" + city + region

        print_way(newway, index, out)

    out.close()


def output_nominatim_pickled(options, pickled_filenames=None):
    streets_counter = defaultdict(list)
    l_ways = list()

    # ponieważ tutaj mamy sporo iterowania z dodawaniem nowych drog, dlatego wczytujemy calosc
    # danych i je osobno obrabiamy. Tworzymy też nowy obiekt node_generalizator
    # relacji wczytywac nie musimy bo z nimi nic nie robimy
    # wczytujemy wszystkie punktu
    local_points = OrderedDict()
    for task_id, pickled in enumerate(pickled_filenames['points']):
        with open(pickled, 'rb') as p_file:
            local_points[task_id] = pickle.load(p_file)

    # wczytujemy wszystkie pointsattrs
    local_pointattrs = OrderedDict()
    for task_id, pickled in enumerate(pickled_filenames['pointsattrs']):
        with open(pickled, 'rb') as p_file:
            local_pointattrs[task_id] = pickle.load(p_file)

    # wczytujemy wszystkie drogi
    local_ways = OrderedDict()
    for task_id, pickled in enumerate(pickled_filenames['ways']):
        with open(pickled, 'rb') as p_file:
            local_ways[task_id] = pickle.load(p_file)


    printdebug("City=>Streets scan start: " + str(datetime.now()), options)

    #  fragment dodajacy krotkie odcinki drog dla wsi ktore nie posiadaja ulic
    #  zbieramy info o wszytskich miastach
    for task_id in local_points:
        for _point, _points_attr in zip(local_points[task_id], local_pointattrs[task_id].values()):
            if 'place' in _points_attr and 'name' in _points_attr:
                n = _points_attr['name']
                p = _points_attr['place']
                lat = _point[0]
                lon = _point[1]
                radius = 0
                if p == 'city':
                    radius = 25
                if p == 'town':
                    radius = 10
                if p == 'village':
                    radius = 5
                m = {'radius': radius, 'lat': lat, 'lon': lon, 'cnt': 0, 'task_id': task_id}
                streets_counter[n].append(m)
                # if n in streets_counter:
                #     streets_counter[n].append(m)
                # else:
                #     streets_counter[n] = [l]
                #     # l = []
                #     # l.append(m)
                #     # streets_counter[n] = l
    printdebug("City=>Streets scan part1: " + str(datetime.now()), options)
    # teraz skan wszystkich ulic
    for task_id in local_ways:
        for _way, _points in zip(local_ways[task_id], local_points[task_id]):
            if _way is None:
                continue
            if 'ref' in _way and 'highway' in _way and 'is_in' not in _way and 'split' not in _way:
                if _way['highway'] in ('trunk', 'primary', 'secondary', 'motorway'):
                    pcnt = len(_way['_nodes'])
                    # printerror("Ref ="+way['ref']+" HW="+way['highway']+" Len="+str(pcnt))
                    start = 0
                    lenKM = 0
                    waydivided = False
                    for i in range(0, pcnt):
                        # printerror("A="+str(i))
                        if i == start:
                            lenKM = 0
                        else:
                            # tutaj poprawic, bo points nie bedzie zmienna globalna
                            lenKM += distKM(_points[_way['_nodes'][i]][0], _points[_way['_nodes'][i]][1],
                                            _points[_way['_nodes'][i - 1]][0], _points[_way['_nodes'][i - 1]][1])
                        if lenKM > 3:
                            newway = _way.copy()
                            newway['_nodes'] = _way['_nodes'][start:i + 1]
                            newway['split'] = str(start) + ":" + str(i) + " KM:" + str(lenKM)
                            l_ways.append({'task_id': task_id, 'newway': newway})
                            start = i
                            lenKM = 0
                            waydivided = True
                    if waydivided:
                        _way['_nodes'] = _way['_nodes'][start:]
                        _way['split'] = 'last'
                    # else:
                    #   printerror("\tRef ="+way['ref']+" HW="+way['highway'])

    # dodajemy nowe drogi do wszystkich drog
    for way in newway:
        local_ways[way['task_id']].append(way['newway'])

    for task_id in local_ways:
        for _way, _points in zip(local_ways[task_id], local_points[task_id]):
            if _way is None:
                continue
            if 'is_in' in _way and 'name' in _way and 'highway' in _way:
                try:
                    towns = _way['is_in'].split(";")
                    waylat = _points[_way['_nodes'][0]][0]
                    waylon = _points[_way['_nodes'][0]][1]
                    for town in towns:
                        if town in streets_counter:
                            found = 0
                            for l in streets_counter[town]:
                                if distKM(l['lat'], l['lon'], waylat, waylon) < l['radius']:
                                    l['cnt'] += 1
                                    found = 1
                                    break
                            if found == 0:
                                printdebug("Brak BLISKIEGO miasta: " + town + " ul.: " + _way['name'] +
                                           " (" + str(waylat) + "," + str(waylon) + ")", options)
                        else:
                            printdebug("Brak Miasta: " + town + " ul.: " + _way['name'] + " (" + str(waylat) +
                                       "," + str(waylon) + ")", options)
                except IndexError:
                    pprint.pprint(_way, sys.stderr)
    printdebug("City=>Streets scan part2: " + str(datetime.now()), options)
    # i dodawanie krotkich ulic

    for miasto in streets_counter:
        for k in streets_counter[miasto]:
            task_id = k['task_id']
            if k['cnt'] != 0:
                printdebug("Ulice: " + miasto + "\tszt. " + str(k['cnt']), options)
            else:
                printdebug("Short way added:" + miasto, options)
                pt0 = (float(k['lat']) + 0.0004, float(k['lon']))
                pt1 = (float(k['lat']) + 0.0008, float(k['lon']))
                pind0 = len(local_points[task_id])
                local_points[task_id].append(pt0)
                local_pointattrs[task_id].append({'_timestamp': filestamp})
                pind1 = len(local_points[task_id])
                local_points[task_id].append(pt1)
                local_pointattrs[task_id].append({'_timestamp': filestamp})
                way = {'_timestamp': filestamp, '_nodes': [pind0, pind1], '_c': 2, 'is_in': miasto,
                    'name': miasto, 'addr:city': miasto, 'highway': "residental"}
                local_ways[task_id].append(way)
    printdebug("City=>Streets scan stop: " + str(datetime.now()), options)

    for task_id in local_ways:
        for way_id, _way in enumerate(local_ways[task_id]):
            _n_way = remove_label_braces(_way)
            if 'name' in _n_way and not _way['name'] and 'addr:city' in _n_way and _n_way['addr:city']:
                _n_way['name'] = _n_way['addr:city']
            local_ways[task_id][way_id] = _n_way
    try:
        f = tempfile.NamedTemporaryFile(mode='w', encoding="utf-8", delete=False)
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open normal output file " + f + "!\n")
        sys.exit()

    node_generalizator = NodeGeneralizator()

    for task_id in local_points:
        node_generalizator.insert_node(local_points[task_id])
        node_generalizator.insert_way(local_ways[task_id])

    for task_id in local_points:
        orig_id = -1
        for _point, _points_attr in zip(local_points[task_id], local_pointattrs[task_id].values()):
            orig_id += 1
            print_point_pickled(_point, _points_attr, task_id, orig_id, node_generalizator, out)

    for task_id in local_ways:
        orig_id = -1
        for _way in local_ways[task_id]:
            orig_id += 1
            if _way is None:
                continue
            if 'ref' in _way and 'highway' in _way:
                if _way['highway'] in {'cycleway', 'path','footway'}:
                    continue
            print_way_pickled(_way, task_id, orig_id, node_generalizator, out)

    # out.write("</osm>\n")
    out.close()
    return f.name

def output_nominatim(prefix, num, options):
    global streets_counter
    global maxid
    global idpfx

    printdebug("City=>Streets scan start: "+str(datetime.now()), options)
    #
    #  fragment dodajacy krotkie odcinki drog dla wsi
    #  ktore nie posiadaja ulic
    #
    #    zbieramy info o wszytskich miastach
    for point in points:
        index = points.index(point)
        if 'place' in pointattrs[index] and 'name' in pointattrs[index] :
            n = pointattrs[index]['name']
            p = pointattrs[index]['place']
            lat = point[0]
            lon = point[1]
            radius = 0 
            if p == 'city':
                radius = 25
            if p == 'town':
                radius = 10
            if p == 'village':
                radius = 5
            m={'radius':radius,'lat':lat,'lon':lon,'cnt':0}
            if n in streets_counter:
                streets_counter[n].append(m)
            else:
                l=[]
                l.append(m)
                streets_counter[n]=l
    printdebug("City=>Streets scan part1: "+str(datetime.now()), options)
    # teraz skan wszystkich ulic
    for way in ways:
        if way is None:
            continue
        if ('ref' in way) and ('highway' in way) and ('is_in' not in way) and ('split' not in way):
            if way['highway' ] == 'trunk' or way['highway'] == 'primary' or way['highway'] == 'secondary' or \
                    way['highway'] == 'motorway':
                pcnt = len(way['_nodes'])
                # printerror("Ref ="+way['ref']+" HW="+way['highway']+" Len="+str(pcnt))
                start = 0
                lenKM = 0
                waydivided = False
                for i in range(0, pcnt):
                # printerror("A="+str(i))
                    if i == start:
                        lenKM = 0
                    else:
                        lenKM += distKM(points[way['_nodes'][i]][0], points[way['_nodes'][i]][1],
                        points[way['_nodes'][i-1]][0], points[way['_nodes'][i-1]][1])
                    if lenKM > 3:
                        newway=way.copy()
                        newway['_nodes'] = way['_nodes'][start:i+1]
                        newway['split'] = str(start)+":"+str(i)+" KM:"+str(lenKM)
                        ways.append(newway)
                        start = i
                        lenKM = 0
                        waydivided = True
                if waydivided:
                    way['_nodes'] = way['_nodes'][start:]
                    way['split'] ='last'
                # else:
                #   printerror("\tRef ="+way['ref']+" HW="+way['highway'])
    for way in ways:
        if way is None:
            continue
        if 'is_in' in way and 'name' in way and 'highway' in way:
            try:
                towns = way['is_in'].split(";")
                waylat = points[way['_nodes'][0]][0]
                waylon = points[way['_nodes'][0]][1]
                for town in towns:
                    if town in streets_counter:
                        found = 0
                        for l in streets_counter[town]:
                            if distKM(l['lat'], l['lon'], waylat, waylon) < l['radius']:
                                l['cnt'] += 1
                                found = 1
                                break
                        if found == 0:
                            printdebug("Brak BLISKIEGO miasta: " + town + " ul.: " + way['name'] + " (" + str(waylat) +
                                       "," + str(waylon) + ")", options)
                    else:
                        printdebug("Brak Miasta: " + town + " ul.: " + way['name'] + " (" + str(waylat) + "," +
                                   str(waylon) + ")", options)
            except IndexError:
                pprint.pprint(way, sys.stderr)
                
    printdebug("City=>Streets scan part2: " + str(datetime.now()), options)
    # i dodawanie krotkich ulic
    for m in streets_counter:
        for k in streets_counter[m]:
            if k['cnt'] != 0:
                printdebug("Ulice: " + m + "\tszt. " + str(k['cnt']), options)
            else:
                printdebug("Short way added:" + m, options)
                pt0 = (float(k['lat']) + 0.0004, float(k['lon']))
                pt1 = (float(k['lat']) + 0.0008, float(k['lon']))
                attrs = {'_timestamp': filestamp}
                pind0 = len(points)
                points_append(pt0, attrs.copy())
                pind1 = len(points)
                points_append(pt1, attrs.copy())
                way = {
                    '_timestamp': filestamp,
                    '_nodes': [pind0, pind1],
                    '_c': 2,
##                    '_src': srcidx,
                    'is_in': m,
                    'name': m,
                    'addr:city':m,
                    'highway': "residental"
                }
                ways.append(way)
    printdebug("City=>Streets scan stop: "+str(datetime.now()), options)


    # oraz na koniec operacja jak w indeksie, czyli usuwanie {}
    # jesli zostaje pusta nazwa, podmien
    for way in ways:
        if way is None:
            continue
        p = re.compile( '\{.*\}')                        # dowolny string otoczony klamrami
        if 'alt_name' in way:
            tmpname = way['alt_name']
            if 'name' in way:                        # przechowanie nazwy z Label
                nname = p.sub( "", way['name'])
                way['alt_name'] = str.strip(nname)
            else:
                way.pop('alt_name')
            way['name'] = tmpname                    # alt_name z Label3 to glowna nazwa do indeksowania

        else:
            if 'name' in way:
                nname = p.sub( "", way['name'])
                way['name'] = str.strip(nname)

                if (way['name']==""):                     # zastepowanie pustych name
                    if ('loc_name' in way):
                        way['name'] = way['loc_name']
                        way.pop('loc_name')
                    elif ('short_name' in way):
                        way['name'] = way['short_name']

        # empty name? put in city name - workaround for no near named road
        if (('name' in way) and (way['name']=="") and ('addr:city' in way) and(way['addr:city']!="")):
            way['name'] = way['addr:city']


    try:
        f=prefix+".nominatim."+str(num)+".osm"
        out = open(f, "w", encoding="utf-8")
    except IOError:
        sys.stderr.write("\tERROR: Can't open nominatim output file " + f + "!\n")
        sys.exit()
               
    for point in points:
        index=points.index(point)
        print_point(point, index, out)

    for index, way in enumerate(ways):
        if way is None:
            continue
        # pomijamy szlaki dla nominatima ("ref" nie wystepuje dla zwyklych tras rowerowych czy chodnikow)
        if ('ref' in way) and ('highway' in way):
            if (way['highway'] == 'cycleway' ) or (way['highway'] == 'path') or (way['highway'] == 'footway'):
                continue
        print_way(way, index, out)
        
    out.close()

def write_output_files(in_file='', dest_filename='', headerf=''):
    elapsed = datetime.now().replace(microsecond=0)
    destination = open(dest_filename, 'w', encoding="utf-8")
    shutil.copyfileobj(open(headerf, 'r', encoding="utf-8"), destination)
    shutil.copyfileobj(open(in_file, 'r', encoding="utf-8"), destination)
    destination.write("</osm>\n")
    destination.close()
    elapsed = datetime.now().replace(microsecond=0) - elapsed
    sys.stderr.write(dest_filename + " ready (took " + str(elapsed) + ").\n")
    return

def worker(task, options):
    # workelem={'idx':n+1,'file':f}
    global points
    global pointattrs
    global ways
    global relations
    global streets_counter
    global working_thread
    global workid
    global filestamp
    global maxid
    global idpfx
    global glob_progress_bar_queue
    
    pointattrs = defaultdict(dict)
    ways = list()
    relations = list()
    maxtypes = dict()
    points = Mylist(bpoints, idperarea*task['idx'])
    if options.normalize_ids:
        idpfx = ":id:" + str(task['idx']) + ":"
    else:
        idpfx = ""
    working_thread = str(os.getpid())
    workid = task['idx']
    maxid = 0
    num_lines_to_process = 0
        
    try:
        if sys.platform.startswith('linux'):
            file_encoding = 'cp1250'
        else:
            file_encoding = 'cp1250'
        infile = open(task['file'], "r", encoding=file_encoding)
        num_lines_to_process = len(infile.readlines())
        infile.seek(0)

    except IOError:
        printerror("Can't open file " + task['file'])
        sys.exit()
    printinfo("Loading " + task['file'])

    filestamp = datetime.fromtimestamp(os.path.getmtime(task['file'])).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        filestamp
    except:
        filestamp = runstamp

    progress_bar = ProgressBar(options, obszar=task['file'], glob_progress_bar_queue=glob_progress_bar_queue)
    progress_bar.start(num_lines_to_process, 'mp')
    maxtypes = parse_txt(infile, options, filename=task['file'], progress_bar=progress_bar)
    progress_bar.set_done('mp')
    infile.close()
    post_load_processing(options, task['file'], maxtypes=maxtypes, progress_bar=progress_bar)
    progress_bar.set_done('drp')
    
      # output_normal("UMP-PL", task['idx'], options)
    # if options.navit_file != None:
    #     output_navit("UMP-PL", task['idx'])	 # no data change
    # if options.nonumber_file != None:
    #     output_nonumbers("UMP-PL", task['idx'])	 # no data change
    # if options.index_file != None:
    #     output_index("UMP-PL", task['idx'], options)  # no data change
    # if options.nominatim_file != None:
    #     output_nominatim("UMP-PL", task['idx'], options)  # data is changed
    save_pickled_data("UMP-PL", task['idx'])

    warn = ''
    printinfo("Finished " + task['file'] + " (" + str(maxid) + " ids)" + warn)
    task['ids'] = maxid		# ale main korzysta z result (ze wzg. na pool.map)
    return task['ids']


def main(options, args):
    if len(args) < 1:
        parser.print_help()
        sys.exit()
    global glob_progress_bar_queue
    global runstamp
    global borderstamp
    if hasattr(options, 'progress_bar_queue'):
        glob_progress_bar_queue = options.progress_bar_queue
    else:
        glob_progress_bar_queue = None

    node_generalizator = NodeGeneralizator()
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    runstamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    runtime = datetime.now().replace(microsecond=0)

    sys.stderr.write("INFO: mdmMp2xml.py ver:" + __version__ +" ran at " + runstamp + "\n")
    if options.threadnum > 32:
        options.threadnum = 32
    if options.threadnum < 1:
        options.threadnum = 1
    if options.borders_file is not None:
        sys.stderr.write("\tINFO: Borders file: " + options.borders_file + "\n")
        sys.stderr.write("\tINFO: Using " + str(options.threadnum) + " working threads.\n")
    if options.verbose:
        sys.stderr.write("\tDEBUG: Extended debug.\n")
    if options.nominatim_file is not None:
        sys.stderr.write("\tINFO: Nominatim output will be written.\n")
    if options.index_file is not None:
        sys.stderr.write("\tINFO: Index output will be written.\n")
    if options.navit_file is not None:
        sys.stderr.write("\tINFO: Navit output will be written.\n")
    if options.nonumber_file is not None:
        sys.stderr.write("\tINFO: NoNumberX output will be written.\n")
    if options.skip_housenumbers:    
        sys.stderr.write("\tINFO: Skiping housenumbers (Type=0x2800) in default output\n")
    if options.positive_ids:    
        sys.stderr.write("\tINFO: The --positive-ids option is obsolete.\n")
    if options.ignore_errors:
        sys.stderr.write("\tINFO: All errors will be ignored.\n")


    if options.borders_file is not None or len(args) == 1:

        if options.borders_file is not None:

            #  parsowanie po nowemu. Najpierw plik granic a potem pliki po kolei.
            if options.borders_file.startswith('~'):
                border_filename = os.path.expanduser(options.borders_file)
            else:
                border_filename = os.path.abspath(options.borders_file)
            elapsed = datetime.now().replace(microsecond=0)
            try:
                borderf = open(border_filename, "r", encoding='cp1250')
            except IOError:
                sys.stderr.write("\tERROR: Can't open border input file " + border_filename + "!\n")
                sys.exit()
            borderstamp = datetime.fromtimestamp(os.path.getmtime(border_filename)).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                borderstamp
            except:
                borderstamp = runstamp

            parse_borders(borderf, options)
            borderf.close()
            node_generalizator.insert_borders(bpoints)
            elapsed = datetime.now().replace(microsecond=0) - elapsed
            sys.stderr.write("\tINFO: " + str(len(bpoints)) + " ids of border points (took " + str(elapsed) + ").\n")
        else:
            borderstamp = runstamp
            sys.stderr.write("\tINFO: Running without border file.\n")

        worklist=[]
        elapsed = datetime.now().replace(microsecond=0)
        for n, f in enumerate(args):
            try:
                if sys.platform.startswith('linux'):
                    file_encoding = 'latin2'
                else:
                    file_encoding = 'cp1250'
                infile = open(f, "r", encoding=file_encoding)
            except IOError:
                sys.stderr.write("\tERROR: Can't open file " + f + "!\n")
                sys.exit()
            sys.stderr.write("\tINFO: Queuing:" + str(n+1)+":" + f + "\n")
            infile.close()
            workelem = {'idx': n+1, 'file': f, 'ids': 0, 'baseid': 0}
            worklist.append(workelem)
        if options.threadnum == 1:
            for workelem in worklist:                
                result = worker(workelem, options)
                # sys.stderr.write("\tINFO: Task " + str(workelem['idx']) + ": " + str(result) + " ids\n")
        else:
            copy_options = copy.copy(options)
            if hasattr(copy_options, 'stdoutqueue'):
                copy_options.stdoutqueue = None
            if hasattr(copy_options, 'stderrqueue'):
                copy_options.stderrqueue = None
            if hasattr(copy_options, 'progress_bar_queue'):
                copy_options.progress_bar_queue = None
            # print(vars(copy_options)
            pool = Pool(processes=copy_options.threadnum)
            # result = pool.map(worker, worklist, options)
            result = pool.map(partial(worker, options=copy_options), worklist)
            pool.terminate()
            for workelem in worklist:
                workelem['ids'] = result[(workelem['idx'])-1]

        elapsed = datetime.now().replace(microsecond=0) - elapsed
        printinfo("Area processing done (took " + str(elapsed) + "). Generating outputs:")

        # wczytaj pliki piklowane i stwórz poprawny node_generalizator
        pickled_filenames = {'points': [], 'pointsattrs': [], 'ways': [], 'relations': []}
        for work_no, workelem in enumerate(worklist):
            pickled_nodes_filename = "UMP-PL" + ".normal." + str(workelem['idx']) + ".points_pickle"
            pickled_filenames['points'].append(pickled_nodes_filename)
            pickled_ways_filename = "UMP-PL" + ".normal." + str(workelem['idx']) + ".ways_pickle"
            pickled_filenames['ways'].append(pickled_ways_filename )
            pickled_relations_filename = "UMP-PL" + ".normal." + str(workelem['idx']) + ".relations_pickle"
            pickled_filenames['relations'].append(pickled_relations_filename)
            pickled_filenames['pointsattrs'].append("UMP-PL" + ".normal." + str(workelem['idx']) + ".pointsattrs_pickle")
            with open(pickled_nodes_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_node(pickled_data)
            with open(pickled_ways_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_way(pickled_data)
            with open(pickled_relations_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_relation(pickled_data)

        # zapisywanie pikli w normalnym trybie
        output_files_to_generate = ['normal']
        if options.navit_file is not None:
            output_files_to_generate.append('navit')
        if options.index_file is not None:
            output_files_to_generate.append('index')
        if options.nonumber_file is not None:
            output_files_to_generate.append('no_number')

        generated_output_filenames = output_normal_pickled(options, output_files_to_generate,
                                                           pickled_filenames=pickled_filenames,
                                                           node_generalizator=node_generalizator)
        if options.nominatim_file is not None:
            generated_nominatim_filename = output_nominatim_pickled(options, pickled_filenames=pickled_filenames)

        # naglowek osm i punkty granic
        printinfo_nlf("Working on header... ")
        elapsed = datetime.now().replace(microsecond=0)
        headerf = "UMP-PL.header.osm"
        try:
            out = open(headerf, "w", encoding="utf-8")
        except IOError:
            printerror("\nCan't create header file " + headerf + "!")
            sys.exit()
        out.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        out.write("<osm version='0.6' generator='mdmMp2xml %s converter for UMP-PL'>\n" % __version__)
        maxid = 0
        idpfx = ""
        if options.borders_file is not None:
            sys.stderr.write("and border points... ")
            for point in bpoints:
                index = bpoints.index(point)
                pointattrs[index]['_timestamp'] = borderstamp
                print_point(point, index, out)                
        out.close()
        elapsed = datetime.now().replace(microsecond=0) - elapsed
        sys.stderr.write("written (took " + str(elapsed) + ").\n")

        if options.nominatim_file is not None:
            printinfo_nlf("Nominatim output... ")
            try:
                write_output_files(in_file=generated_nominatim_filename, dest_filename=options.nominatim_file,
                                   headerf=headerf)
                os.remove(generated_nominatim_filename)
            except IOError:
                sys.stderr.write("\n\tERROR: Nominatim output failed!\n")
                sys.exit()            

        if options.navit_file is not None:
            printinfo_nlf("Navit output... ")
            # elapsed = datetime.now().replace(microsecond=0)
            try:
                write_output_files(in_file=generated_output_filenames['navit'], dest_filename=options.navit_file,
                                   headerf=headerf)
            except IOError:
                sys.stderr.write("\n\tERROR: Navit output failed!\n")
                sys.exit()

        
        if options.index_file is not None:
            printinfo_nlf("OsmAnd index... ")
            try:
                write_output_files(in_file=generated_output_filenames['index'], dest_filename=options.index_file,
                                   headerf=headerf)
            except IOError:
                sys.stderr.write("\n\tERROR: Index output failed!\n")
                sys.exit()                        

        
        if options.nonumber_file is not None:
            printinfo_nlf("NoNumber output... ")
            try:
                write_output_files(in_file=generated_output_filenames['no_number'], dest_filename=options.nonumber_file,
                                   headerf=headerf)
            except IOError:
                sys.stderr.write("\n\tERROR: NoNumber output failed!\n")
                sys.exit()

        printinfo_nlf("Normal output... ")
        try:
            temp_file = tempfile.NamedTemporaryFile(mode='w', encoding="utf-8", delete=False)
            temp_file.close()
            write_output_files(in_file=generated_output_filenames['normal'], dest_filename=temp_file.name,
                               headerf=headerf)
            printinfo_nlf("Normal output copying to stdout or destination file ")
            elapsed = datetime.now().replace(microsecond=0)
            if options.outputfile is None:
                shutil.copyfileobj(open(temp_file.name, 'r', encoding="utf-8"), sys.stdout)
            else:
                with open(options.outputfile, 'a', encoding="utf-8") as _dest:
                    shutil.copyfileobj(open(temp_file.name, 'r', encoding="utf-8"), _dest)
            os.remove(temp_file.name)
            elapsed = datetime.now().replace(microsecond=0) - elapsed
            sys.stderr.write("done (took " + str(elapsed) + ").\n")
            elapsed = datetime.now().replace(microsecond=0) - runtime
            printinfo("mdmMp2xml.py finished after " + str(elapsed) + ".\n")
        except IOError:
            sys.stderr.write("\n\tERROR: Normal output failed!\n")
            sys.exit()

        os.remove(headerf)
        for _filename in generated_output_filenames.values():
            os.remove(_filename)
    else:
        sys.stderr.write("\tINFO: Border file required when more than one area given: --border \n")


# Main program.
if __name__ == '__main__':
    usage = "usage: %prog [options] input1.mp [input2.mp input3.mp ...]"
    parser = OptionParser(usage=usage)
    parser.add_option("--borders", dest="borders_file", type="string", action="store",
                      help="read boarders from FILE", metavar="FILE")
    parser.add_option("--outputfile", dest="outputfile", type="string", action="store",
                     help="output file filename")
    parser.add_option("--threads", dest="threadnum", type="int", action="store", default=1,
                      help="threads number")
    parser.add_option("--index", dest="index_file", type="string", action="store",
                      help="write index output to FILE", metavar="FILE")
    parser.add_option("--nominatim", dest="nominatim_file", type="string", action="store",
                      help="write nominatim output to FILE", metavar="FILE")
    parser.add_option("--navit", dest="navit_file", type="string", action="store",
                      help="write Navit output to FILE", metavar="FILE")
    parser.add_option("--no_NumberX", dest="nonumber_file", type="string", action="store",
                      help="write output to FILE, NumberX lines skipped", metavar="FILE")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="more debug info")
    parser.add_option("--skip_housenumbers",
                      action="store_true", dest="skip_housenumbers", default=False,
                      help="skip housenumbers (Type=0x2800) in stdout")
    parser.add_option("--positive_ids",
                      action="store_true", dest="positive_ids", default=False,
                      help="obsolete")
    parser.add_option("--normalize_ids",
                      action="store_true", dest="normalize_ids", default=False,
                      help="remove gaps in id usage")
    parser.add_option("--ignore_errors",
                      action="store_true", dest="ignore_errors", default=False,
                      help="try to ignore errors in .mp file")
    parser.add_option("--regions",
                      action="store_true", dest="regions", default=False,
                      help="attach regions to cities in the index file")

    (options, args) = parser.parse_args()
    main(options, args)