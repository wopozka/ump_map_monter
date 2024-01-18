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
from multiprocessing import Pool, Process
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
        # key is node id (v.index(str(lat), str(lon))), value tuple(str(lat), str(lon))
        self.k = {}
        # tuple(str(lat), str(lon))
        self.v = []

    def __len__(self):
        return len(self.k)

    def __getitem__(self, key):
        return self.v[key]  #
        for k in self.k:
            if self.k[k] == key:
                return k

    def index(self, value):
        return self.k[value]

    def __setitem__(self, key, value):
        if key in self.v:
            del self.k[self.v[key]]
        self.k[value] = key
        self.v[key] = value

    def __contains__(self, value):
        return value in self.k

    def append(self, value):
        self.v.append(value)  #
        self.k[value] = len(self.k)

    def __iter__(self):
        return self.v.__iter__()
        return self.k.__iter__()


class Mylist(object):
    """
    The modified list bultin type, that support faster return of element index
    """
    def __init__(self, borders):
        # key is node id (v.index(str(lat), str(lon))), value tuple(str(lat), str(lon))
        self.k = {}
        # tuple(str(lat), str(lon))
        self.v = []
        self.b = len(borders)
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

    def get_point_id(self, value):
        return self.index(value)


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
        self.borders_point_len = 0
        self.t_table_points = OrderedDict()
        self.t_table_ways = OrderedDict()
        self.t_table_relations = OrderedDict()
        self.sum_points = -1
        self.sum_ways = -1
        self.points_offset = dict()
        self.ways_offset = dict()
        self.relations_offset = dict()

    def insert_borders(self, borders):
        self.borders_point_len = len(borders)

    def insert_points(self, file_group_name, points):
        len_points = len(points) - self.borders_point_len
        self.t_table_points[file_group_name] = len_points
        self.points_offset[file_group_name] = -1

    def insert_ways(self, file_group_name, way_val):
        self.t_table_ways[file_group_name] = len(way_val)
        self.ways_offset[file_group_name] = -1

    def insert_relations(self, file_group_name, way_val):
        self.t_table_relations[file_group_name] = len(way_val)
        self.relations_offset[file_group_name] = -1

    def get_point_id(self, file_group_name, orig_id):
        if orig_id < self.borders_point_len:
            return orig_id + 1
        if self.points_offset[file_group_name] > -1:
            return self.points_offset[file_group_name] + orig_id
        new_id = 1
        for a in self.t_table_points:
            if a == file_group_name:
                break
            new_id += self.t_table_points[a]
        self.points_offset[file_group_name] = new_id
        return new_id + orig_id

    def get_way_id(self, file_group_name, orig_id):
        if self.sum_points == -1:
            self.sum_points = sum(self.t_table_points[a] for a in self.t_table_points)
        if self.ways_offset[file_group_name] == -1:
            self.ways_offset[file_group_name] = 1
            for a in self.t_table_ways:
                if a == file_group_name:
                    break
                self.ways_offset[file_group_name] += self.t_table_ways[a]
        return self.ways_offset[file_group_name] + orig_id + self.sum_points + self.borders_point_len

    def get_relation_id(self, file_group_name, orig_id):
        if self.sum_points == -1:
            self.sum_points = sum(self.t_table_points[a] for a in self.t_table_points)
        if self.sum_ways == -1:
            self.sum_ways = sum(self.t_table_ways[a] for a in self.t_table_ways)
        if self.relations_offset[file_group_name] == -1:
            self.relations_offset[file_group_name] = 1
            for a in self.t_table_relations:
                if a == file_group_name:
                    break
                self.relations_offset[file_group_name] += self.t_table_relations[a]
        return self.relations_offset[file_group_name] + orig_id + self.sum_ways + self.sum_points + \
               self.borders_point_len


class NodesToWayNotFound(ValueError):
    """
    Raised when way of two nodes can not be found
    """
    def __init__(self, node_a, node_b):
        self.node_a = node_a
        self.node_b = node_b

    def __str__(self):
        return "<NodesToWayNotFound %r,%r>" % (self.node_a, self.node_b,)


class MessagePrinters(object):
    def __init__(self, workid='', working_file='', verbose=False):
        self.working_thread = os.getpid()
        self.workid = workid
        self.working_file = ''
        if working_file:
            self.working_file = ': ' + working_file
        self.verbose = verbose
        self.warning_num = 0
        self.error_num = 0
        self.msg_core = str(self.working_thread) + ":" + str(self.workid) + self.working_file + ":"

    def printdebug(self, p_string):
        if self.verbose:
            sys.stderr.write("\tDEBUG: " + self.msg_core + str(p_string) + "\n")

    def printerror(self, p_string):
        self.error_num += 1
        sys.stderr.write("\tERROR: " + self.msg_core + str(p_string) + "\n")

    def printinfo(self, p_string):
        sys.stderr.write("\tINFO: " + self.msg_core + str(p_string) + "\n")

    def printinfo_nlf(self, p_string):
        sys.stderr.write("\tINFO: " + self.msg_core + str(p_string) + "\n")

    def printwarn(self, p_string):
        self.warning_num += 1
        sys.stderr.write("\tWARNING: " + self.msg_core + str(p_string) + "\n")

    def get_warning_num(self):
        return self.warning_num

    def get_error_num(self):
        return self.error_num


# some global constants
__version__ = '0.8.3'
extra_tags = " version='1' changeset='1' "
runstamp = ''

# in case we need it for future, just placeholder
umppline_types = dict()

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
    0x3:  ["landuse",  "residential"],
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
    0x1714: ["traffic_sign",  "maxweight"],
    0x1715: ["traffic_sign",  "maxwight"],
    0x1716: ["traffic_sign",  "maxheight"],
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
    0x6100: ["military", "bunker", "building", "bunker"],
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

glob_progress_bar_queue = None


def set_runstamp(r_stamp):
    global runstamp
    runstamp = r_stamp


def get_runstamp():
    global runstamp
    return runstamp


def path_file(filename):
    if filename.startswith('~'):
        return os.path.abspath(os.path.join(os.getcwd(), os.path.expanduser(filename)))
    return os.path.abspath(os.path.join(os.getcwd(), filename))


def create_pickled_file_name(pickle_type, task_idx):
    return "UMP-PL.normal." + task_idx + '.' + pickle_type + "_pickle"


def recode(line):
    try:
        return line
        # return unicode(line, "cp1250").encode("UTF-8")
    except:
        sys.stderr.write("warning: couldn't recode " + line + " in UTF-8!\n")
        return line


def bpoints_append(node, bpoints):
    if node not in bpoints:
        bpoints.append(node)


def lats_longs_from_line(nodes_str):
    lats = []
    longs = []
    for la, element in enumerate(nodes_str.split(',')):
        try:
            coord = '{:.{n_dec_digits}f}'.format(float(element.strip('()')), n_dec_digits=6)
        except ValueError:
            return tuple()
        if la % 2:
            longs.append(coord)
        else:
            lats.append(coord)
    return tuple(zip(lats, longs))


def points_from_bline(points_str):
    """Appends new points to the points list"""
    # Kwadrat dla Polski.
    # 54.85628,13.97873
    # 48.95703,24.23996
    # Ekspansja, niech pamieta granice dla z grubsza calej Europy kontynentalnej
    maxN = 72.00000
    maxW = -12.00000
    maxS = 34.00000
    maxE = 50.00000
    points = []
    for point in lats_longs_from_line(points_str):
        if maxN > float(point[0]) > maxS and maxW < float(point[1]) < maxE:
            points.append(point)
    return points


# TxF: ucinanie przedrostkow
def cut_prefix(string):
    if string.startswith("aleja ") or string.startswith("Aleja ") or string.startswith("rondo ") or \
       string.startswith("Rondo ") or string.startswith("osiedle ") or string.startswith("Osiedle ") or \
       string.startswith("pasaż ") or string.startswith("Pasaż "):
        string = re.sub(r"^\w+ ", "", string)
    return string


def convert_btag(key, value, options, bpoints, messages_printer=None):
    if key.lower() in ('label',):
        pass
    elif key in ('Data0',):
        for _tmpnode in points_from_bline(value):
            bpoints_append(_tmpnode, bpoints)
    elif key == 'Type':
        if int(value, 0) == 0x4b:
            pass
        elif int(value, 0) == 0x1e:
            pass
        else:
            messages_printer.printerror("Unknown line type " + hex(int(value, 0)))
    elif key == 'EndLevel':
        pass
    else:
        if options.ignore_errors:
            messages_printer.printerror("Unknown key: " + key)
            messages_printer.printerror("Value:       " + value)
        else:
            raise ParsingError("Unknown key " + key + " in polyline / polygon")


def parse_borders_return_bpoints(infile, options, border_stamp):
    bpoints = MylistB()
    messages_printer = MessagePrinters(workid='borders', verbose=options.verbose)
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
            way = {'_timestamp': border_stamp}
            for key in polyline:
                if polyline[key] != '':
                    convert_btag(key, polyline[key], options, bpoints, messages_printer=messages_printer)
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
    return bpoints


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


def get_type_from_umptyp(way, ump_spw_types):
    if 'ump:typ' in way and way['ump:typ'] in ump_spw_types:
        return ump_spw_types[way['ump:typ']]
    return int(way['ump:type'], 0)


def tag(way, spw_types):
    for key, value in zip(spw_types[::2], spw_types[1::2]):
        way[key] = value


def polygon_make_ccw(shape, c_points):
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
            alat = float(c_points[nodes[a]][0])
            alon = float(c_points[nodes[a]][1])
            blat = float(c_points[nodes[b]][0])
            blon = float(c_points[nodes[b]][1])
            clat = float(c_points[nodes[c]][0])
            clon = float(c_points[nodes[c]][1])
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


def add_addrinfo(f_way, street, city, region, right, map_elements_props):
    nodes = f_way['_nodes']
    count = f_way['_c']
    filestamp = f_way['_timestamp']
    addrs = f_way['_addr']
    interp_types = {"o": "odd", "e": "even", "b": "all"}
    prev_house = "xx"
    prev_node = None
    points = map_elements_props['points']
    pointattrs = map_elements_props['pointattrs']
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
                while low_node in map_elements_props['points']:
                    low_node = (low_node[0] + normlat / 10,
                                low_node[1] + normlon / 10)
                attrs['addr:housenumber'] = low
                points_append(low_node, attrs.copy(), filestamp=filestamp, map_elements_props=map_elements_props)

            pt1 = len(points)
            hi_node = unproj(nlat + dlat - shortlat, nlon + dlon - shortlon)
            while hi_node in points:
                hi_node = (hi_node[0] - normlat / 10, hi_node[1] - normlon / 10)
            attrs['addr:housenumber'] = hi
            points_append(hi_node, attrs.copy(), filestamp=filestamp, map_elements_props=map_elements_props)

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
                # '_src': srcidx,
                'is_in': city,
                'NumberX': 'yes'
            }
            if low != hi:
                map_elements_props['ways'].append(way)

            prev_house = hi
            prev_node = hi_node
        else:
            prev_house = "xx"


def points_append(point, attrs, filestamp=None, map_elements_props=None):
    if map_elements_props is None:
        return
    if point in map_elements_props['points']:
        return
    _points = map_elements_props['points']
    _pointattrs = map_elements_props['pointattrs']
    attrs['_timestamp'] = filestamp
    _points.append(point)
    _pointattrs[_points.get_point_id(point)] = attrs


def prepare_line(points_str, filestamp=None, closed=False, map_elements_props=None):
    """Appends new nodes to the points list"""
    points = lats_longs_from_line(points_str)
    # if there is some problem with DataX coordinates, then points is empty
    if not points:
        return 0, tuple()
    for point in points:
        points_append(point, {}, filestamp=filestamp, map_elements_props=map_elements_props)
    try:
        point_indices = list(map(map_elements_props['points'].get_point_id, points))
    except:
        print(map_elements_props['points'])
        print(point)
        raise ParsingError('Can\'t map node indices')
    pts = 0
    for point_idx in point_indices:
        if '_out' not in map_elements_props['pointattrs'][point_idx]:
            pts += 1
    if closed:
        point_indices.append(point_indices[0])
    return pts, point_indices


def convert_tags_return_way(mp_record, feat, ignore_errors, filestamp=None, map_elements_props=None,
                            messages_printer=None):
    maxspeeds = {'0': '8', '1': '20', '2': '40', '3': '56', '4': '72', '5': '93', '6': '108', '7': '128'}
    levels = {1: "residential", 2: "tertiary", 3: "secondary", 4: "trunk"}
    exceptions = ('emergency', 'goods', 'motorcar', 'psv', 'taxi', 'foot', 'bicycle', 'hgv')
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
                success, code_tag, code_value, label = \
                    extract_reference_code(label, refpos, messages_printer=messages_printer)
                if success:
                    if code_tag and code_value:
                        way[code_tag] = code_value
                else:
                    if ignore_errors:
                        messages_printer.printerror('Unknown ref code: ' + code_value + ' for label: ' + value +
                                                    '. Ignoring.')
                    else:
                        raise ParsingError('Problem parsing label ' + value)
            if 'name' not in way and label:
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
            count, way['_nodes'] = prepare_line(value, filestamp=filestamp, closed=feat == Features.polygon,
                                                map_elements_props=map_elements_props)
            # jesli nie uda sie skonwertowac DataX na cos poprawnego to wtedy zwroc pusty slownik.
            if not way['_nodes']:
                return {}
            if '_c' in way:
                way['_c'] += count
            else:
                way['_c'] = count
            # way['layer'] = num ??
        elif key.startswith('_Inner'):
            count, nodes = prepare_line(value, filestamp=filestamp, closed=feat == Features.polygon,
                                        map_elements_props=map_elements_props)
            if not nodes:
                return {}
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
            way['ump:type'] = value
            # if feat == Features.polyline:
            #     if int(value, 0) in pline_types:
            #         tag(way, pline_types[int(value, 0)])
            #     else:
            #         messages_printer.printerror("Unknown line type "+hex(int(value, 0)))
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
            misckey, miscvalue = extract_miscinfo(value, messages_printer=messages_printer)
            if misckey and miscvalue:
                way[misckey] = miscvalue
        elif key == 'Transit':  # "no thru traffic" / "local traffic only"
            if value.lower().startswith('n'):
                way['access'] = 'destination'
        elif key == 'Moto':
            if value.lower().startswith('y'):
                way['motorcycle'] = 'yes'
            else:
                way['motorcycle'] = 'no'
        elif key in ('RouteParam', 'Routeparam'):
            r_params = extract_routeparam(value)
            if r_params:
                for rp_key, rp_val in r_params.items():
                    way[rp_key] = rp_val
            else:
                if options.ignore_errors:
                    messages_printer.printerror('Corrupted RouteParam parameters: %s' % value)
                else:
                    raise ParsingError('Corrupted RouteParam parameters: %s' % value)
        elif key == 'RestrParam':
            params = value.split(',')
            excpts = []
            for i, val in enumerate(params[4:]):
                if val == '1':
                    excpts.append(exceptions[i])
            way['except'] = ','.join(excpts)
        elif key == 'HLevel0':
            if feat != Features.polyline:
                if options.ignore_errors:
                    messages_printer.printerror('HLevel0 used on a polygon')
                else:
                    raise ParsingError('HLevel0 used on a polygon')
            else:
                level_list = extract_hlevel_v2(value)
                if level_list:
                    way['_levels'] = level_list
                else:
                    messages_printer.printerror('HLevel0 value corrupted. Ignoring')
        elif key == 'Szlak':
            # czy to jest w ogole gdzies wykorzystywane?
            trial_tag, trial_refs, unknown_refs = extract_szlak(value)
            for t_tag in trial_tag:
                way[t_tag] = 'yes'
            way['ref'] = ";".join(trial_refs)
            for u_ref in unknown_refs:
                messages_printer.printerror("Unknown 'Szlak' colour: " + u_ref)
        elif key.startswith('NumbersExt'):
            messages_printer.printerror("warning: " + key + " tag discarded")
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
                messages_printer.printwarn("W: Unknown key: " + key)
                messages_printer.printwarn("W: Value:       " + value)
            else:
                raise ParsingError("Unknown key " + key + " in polyline / polygon")
    return way


def postprocess_poi_tags(way):
    if 'ump:type' in way:
        if way['ump:type'] in ('0x6616', '0x6617'):
            # for peeks and valleys elevation in meters is stored as streetdesc, copy it
            if 'addr:street' in way and way['addr:street']:
                way['ele'] = way['addr:street']
        elif way['ump:type'] == '0x1714':
            if 'name' in way:
                way['maxweight'] = way['name']
        elif way['ump:type'] == '0x1715':
            if 'name' in way:
                way['maxwight'] = way['name']
        elif way['ump:type'] == '0x1716':
            if 'name' in way:
                way['maxheight'] = way['name']

    # Label=Supermarket (24h), Typ=24H
    if 'name' in way and (way['name'].find('(24h)') > -1 or way['name'].find('(24H)') > -1 or
                          way['name'].find('{24h}') > -1 or way['name'].find('{24H}') > -1):
        way['opening_hours'] = "24/7"
    else:
        if 'ump:typ' in way and way['ump:typ'] == "24H":
            way['opening_hours'] = "24/7"
    if 'addr:street' in way:
        match = re.match('(.*)[,/] *(.*)', way['addr:street'])
        if match:
            way['addr:street'] = match.group(2)
            # if 'addr:housenumber' in way:
            # way['addr:housenumber'] += ''.join(' (', match.group(1), ')')
    return way


def parse_txt(infile, options, progress_bar=None, border_points=None, messages_printer=None, filestamp=None):
    if border_points is None:
        border_points = []
    otwarteDict = {r"([Pp]n|pon\.)": "Mo", r"([Ww]t|wt\.)": "Tu", r"([Ss]r|śr|Śr|śr\.)": "We", r"([Cc]z|czw\.)": "Th",
                   r"([Pp]t|piąt\.|pt\.)": "Fr", r"([Ss]o|[Ss]b|sob\.)": "Sa", r"([Nn]d|ni|niedz\.)": "Su"}
    maxtypes = {}
    map_elements_props = {'points': Mylist(border_points),  # zmodyfikowana lista do obsługi pointsów
                          'pointattrs': defaultdict(dict),  # format: point_id: {atrybuty pointa}
                          'ways': list(), 'relations': list()  # zwykle listy
                          }
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
            way = convert_tags_return_way(polyline, feat, options.ignore_errors, filestamp=filestamp,
                                          map_elements_props=map_elements_props, messages_printer=messages_printer)
            # w przypadku gdy nie uda sie skonwertowac punktow z DataX, wtedy way bedzie pustym slownikiem, musimy
            # takie cos obsluzyc, albo ignorujemy takie wpisy albo wywalamy program.
            if not way:
                string_polyline = ', '.join(_key + '=' + _val for _key, _val in polyline.items())
                if options.ignore_errors:
                    messages_printer.printerror("Corrupted DataX values for poi/polyline/polygon. Ignoring data.")
                    messages_printer.printerror(string_polyline)
                    comment = None
                    polyline = None
                    continue
                else:
                    raise ParsingError("Corrupted DataX values for poi/polyline/polygon: " + string_polyline)

            if feat == Features.polygon:
                u_type = get_type_from_umptyp(way, umpshape_types)
                if u_type in shape_types:
                    tag(way, shape_types[u_type])
                else:
                    messages_printer.printerror("Unknown shape type " + hex(u_type))

            elif feat == Features.poi:
                u_type = get_type_from_umptyp(way, umppoi_types)
                if u_type in poi_types:
                    tag(way, poi_types[u_type])
                else:
                    messages_printer.printerror("Unknown poi type " + hex(u_type))
                way = postprocess_poi_tags(way)

            elif feat == Features.polyline:
                u_type = get_type_from_umptyp(way, umppline_types)
                if u_type in pline_types:
                    tag(way, pline_types[u_type])
                else:
                    messages_printer.printerror("Unknown line type " + hex(u_type))
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
                        p = re.compile(r'\^', re.IGNORECASE)	 # to moze byc wielolinijkowy komentarz
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
                adr_error_msg, adr_street = extract_street_for_addr(way)
                if adr_error_msg:
                    messages_printer.printerror("Line:" + str(linenum) + ":Numeracja - brak poprawnej nazwy ulicy: '"
                                                + adr_error_msg + "'.")
                if 'addr:city' in way:
                    adr_miasto = way['addr:city']
                else:
                    adr_miasto = 'MIASTO_missing'
                    messages_printer.printerror("Line:" + str(linenum) + ":Numeracja - brak Miasto=!")
                if 'is_in:state' in way:
                    adr_region = way['is_in:state']
                else:
                    adr_region = ""
                    messages_printer.printerror("Line:" + str(linenum) + ":Numeracja - brak RegionName=!")
                add_addrinfo(way, adr_street, adr_miasto, adr_region, 0, map_elements_props)
                add_addrinfo(way, adr_street, adr_miasto, adr_region, 1, map_elements_props)
                del way['_addr']
            if 'ele' in way and 'name' in way and way['ele'] == '_name':
                way['ele'] = way.pop('name').replace(',', '.')
            if 'depth' in way and 'name' in way and way['depth'] == '_name':
                way['depth'] = way.pop('name').replace(',', '.')
            if feat == Features.polygon:
                polygon_make_ccw(way, map_elements_props['points'])

            if feat == Features.poi:
                # execution order shouldn't matter here, unlike in C
                map_elements_props['pointattrs'][way.pop('_nodes')[0]] = way
                if not way.pop('_c'):
                    way['_out'] = 1
            else:
                map_elements_props['ways'].append(way)

        elif feat == Features.ignore:
            # Ignore everything within e.g. [IMG ID] until some other
            # rule picks up something interesting, e.g. a polyline
            pass
        elif polyline is not None and line != '':
            if '=' in line:
                key, value = line.split('=', 1)
            else:
                if options.ignore_errors:
                    messages_printer.printerror('Line:' + str(linenum) + ':Missing = in line: %s. Ignoring' % line)
                else:
                    messages_printer.printerror('Line:' + str(linenum) + 'Missing = in line: %s' % line)
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
                    messages_printer.printerror("Line:" + str(linenum) + ": Ignoring repeated key " + key + "!")
            polyline[key] = recode(value).strip()
        elif line.startswith(';'):
            strn = recode(line[1:].strip(" \t\n"))
            if comment is not None:
                comment = comment + "^ " + strn
            else:
                comment = strn
        elif line != '':
            raise ParsingError('Unhandled line ' + line)
    return maxtypes, map_elements_props


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
    # let's return simple dictionary, as defaultdict resulted in creating empty entry in case of list
    # comprehension
    return {a: tmp_node_ways_rel[a] for a in tmp_node_ways_rel}, \
           {a: tmp_node_ways_rel_multipolygon[a] for a in tmp_node_ways_rel_multipolygon}


def nodes_to_way_id(a, b, node_ways_relation=None, map_elements_props=None, messages_printer=None):
    _points = map_elements_props['points']
    _ways = map_elements_props['ways']
    if a not in node_ways_relation or b not in node_ways_relation:
        raise NodesToWayNotFound(a, b)
    ways_a = set([road_id for road_id in node_ways_relation[a] if road_id < len(_ways) and _ways[road_id] is not None])
    ways_b = set([road_id for road_id in node_ways_relation[b] if road_id < len(_ways) and _ways[road_id] is not None])
    way_ids = ways_a.intersection(ways_b)
    if len(way_ids) == 1:
        return tuple(way_ids)[0]
    elif len(way_ids) > 1:
        messages_printer.printerror("DEBUG: multiple roads found for restriction. Using only one")
        for way_id in way_ids:
            messages_printer.printerror(str(_ways[way_id]))
            messages_printer.printerror(str([_points[node] for node in _ways[way_id]['_nodes']]))
        return tuple(way_ids)[0]
    else:
        messages_printer.printerror("DEBUG: no roads found for restriction.")
        messages_printer.printerror(','.join(_points[a]) + ' ' + ','.join(_points[b]))
        messages_printer.printerror(str(node_ways_relation[a]))
        messages_printer.printerror(str(node_ways_relation[b]))
        for way in _ways:
            if way is None:
                continue
            way_nodes = way['_nodes']
            if a in way_nodes:
                messages_printer.printerror("DEBUG: node a: %r found in way: %r" % (a, way))
            if b in way_nodes:
                messages_printer.printerror("DEBUG: node b: %r found in way: %r" % (b, way))
        raise NodesToWayNotFound(a, b)
    return None


def nodes_to_way(a, b, node_ways_relation=None, map_elements_props=None, messages_printer=None):
    _ways = map_elements_props['ways']
    return _ways[nodes_to_way_id(a, b, node_ways_relation=node_ways_relation, map_elements_props=map_elements_props,
                                 messages_printer=messages_printer)]


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


def next_node(pivot=None, direction=None, node_ways_relation=None, map_elements_props=None):
    """
    return either next or previous node relative to the pivot point. In some cases does not do anything as the next
    point is the only one
    :param pivot: the node that is our reference
    :param direction: in which direction we are looking, according or against nodes order
    :param node_ways_relation: zbiorcze dane dla drog, relacji i punktow
    :param map_elements_props: elementy mapy: points, pointattrs, ways, relatons
    :return: one node of given road
    """
    way_nodes = nodes_to_way(direction, pivot, node_ways_relation=node_ways_relation,
                             map_elements_props=map_elements_props)['_nodes']
    pivotidx = way_nodes.index(pivot)
    return way_nodes[pivotidx + signbit(way_nodes.index(direction) - pivotidx)]


def split_way(way=None, splitting_point=None, node_ways_relation=None, map_elements_props=None):
    ways = map_elements_props['ways']
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


def name_turn_restriction(rel, nodes, points):
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


def preprepare_restriction(rel, node_ways_relation=None, map_elements_props=None):
    """
    modification of relation nodes so, that it starts and ends one node after and one node before central point
    called pivot here. It simplifies calculations as in some cases ways are split then, eg when there are levels.
    :param rel: relaton
    :param node_ways_relation: node numer: way ids reference
    :param map_elements_props, properties of map points, pointattrs, ways, relations
    :return: None, id modifies nodes by reference
    """
    new_rel_node_first = next_node(pivot=rel['_nodes'][1], direction=rel['_nodes'][0],
                                   node_ways_relation=node_ways_relation, map_elements_props=map_elements_props)
    new_rel_node_last = next_node(pivot=rel['_nodes'][-2], direction=rel['_nodes'][-1],
                                  node_ways_relation=node_ways_relation, map_elements_props=map_elements_props)
    rel['_nodes'][0] = new_rel_node_first
    rel['_nodes'][-1] = new_rel_node_last


def prepare_restriction(rel, node_ways_relation=None, map_elements_props=None):
    fromnode = rel['_nodes'][0]
    fromvia = rel['_nodes'][1]
    tonode = rel['_nodes'][-1]
    tovia = rel['_nodes'][-2]
    # The "from" and "to" members must start/end at the Role via node or the Role via way(s), otherwise split it!
    split_way(way=nodes_to_way(fromnode, fromvia, node_ways_relation=node_ways_relation,
                               map_elements_props=map_elements_props),
              splitting_point=fromvia, node_ways_relation=node_ways_relation,
              map_elements_props=map_elements_props)
    split_way(way=nodes_to_way(tonode, tovia, node_ways_relation=node_ways_relation,
                               map_elements_props=map_elements_props),
              splitting_point=tovia, node_ways_relation=node_ways_relation,
              map_elements_props=map_elements_props)


def make_restriction_fromviato(rel, node_ways_relation=None, map_elements_props=None, messages_printer=None):
    ways = map_elements_props['ways']
    nodes = rel.pop('_nodes')
    # from_way_index = ways.index(nodes_to_way(nodes[0], nodes[1]))
    # to_way_index = ways.index(nodes_to_way(nodes[-2], nodes[-1]))
    from_way_index = nodes_to_way_id(nodes[0], nodes[1], node_ways_relation=node_ways_relation,
                                     map_elements_props=map_elements_props, messages_printer=messages_printer)
    to_way_index = nodes_to_way_id(nodes[-2], nodes[-1], node_ways_relation=node_ways_relation,
                                   map_elements_props=map_elements_props, messages_printer=messages_printer)
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


def make_multipolygon(outer, holes, filestamp=None, node_ways_relation=None, map_elements_props=None):
    ways = map_elements_props['ways']
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
        map_elements_props['ways'].append(way)
        # rel['_members']['inner'][1].append(ways.index(way))
        rel['_members']['inner'][1].append(len(ways) - 1)
        polygon_make_ccw(way, map_elements_props['points'])

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


def xmlize(xml_str):
    return saxutils.escape(xml_str, {'\'': '&apos;'})


def extract_reference_code(label, refpos, messages_printer=None):
    """
    Extracting reference numbers, abbreviations and elevations inserted into map sources by special codes: ~[0x01]XXX
    Parameters
    ----------
    label: map object label
    refpos: location of ~[ in the label
    messages_printer: reference to message printer class, for error printing

    Returns
    -------
    tuple(conversion_result, name_of_way_key, value of reference, new label)
    """
    reftype = {
        # interstate symbol, name can consist only digits, allowed only at beginning of label
        0x01: 'int_ref', 0x2a: 'int_ref',
        # US Highway – shield, name can consist only from digits, allowed only at beginning of label
        0x02: 'int_ref',  0x2b: 'int_ref',
        # US Highway – round symbol, name can consist only from digits, allowed only at beginning of label
        0x03: 'ref', 0x2c: 'ref',
        # Highway – big, allowed only at beginning of label
        0x04: 'ref', 0x2d: 'ref',
        # Main road – middle, allowed only at beginning of label
        0x05: 'ref', 0x2e: 'ref',
        # Main road – small, allowed only at beginning of label
        0x06: 'ref', 0x2f: 'ref',
        # Country, region, abbreviation, eg. Country1=United States~[0x1d]US, Region1=New York~[0x1d]NY
        0x1d: 'loc_name',
        # elevation
        0x1f: 'ele'
    }

    label_split = label[refpos + 2:].split(' ', 1)
    if len(label_split) == 2:
        refstr, right = label[refpos + 2:].split(' ', 1)
    else:
        refstr = label_split[0]
        right = ""

    code, ref = refstr.split(']')
    label = (label[:refpos] + right).strip(' \t')
    try:
        reference_code = int(code, 0)
    except ValueError:
        if messages_printer is not None:
            messages_printer.printerror("Error in reference code: " + code + '. It should be in hex format.')
        return False, code.lower(), ref, label

    if reference_code in reftype:
        return True, reftype[reference_code], ref.replace("/", ";"), label
        # way[reftype[int(code, 0)]] = ref.replace("/", ";")
    else:
        # Used before a letter forces it to be a lower case
        if code.lower() == '0x1b':
            # way['loc_name'] = right
            label = ref + label
            return True, 'loc_name', right, label
        # Separation: on the map visible only the first section (when over 1km), with the mouse sees displayed
        # one the word completely, not separated
        elif code.lower() == '0x1c':
            # way['loc_name'] = ref
            label = ref + label
            return True, 'loc_name', ref, label
        # Separation: on the map visible only the second section(when over 1 km), with the mouse sees displayed one the
        # word completely, by blank separated
        elif code.lower() == '0x1e':
            label = label.replace('~[0x1e]', '')
            if messages_printer is not None:
                messages_printer.printerror("1E" + label)
            return True, '', '', label
        else:
            if messages_printer is not None:
                messages_printer.printerror("Unknown reference code: " + code)
            return False, code.lower(), ref, label
            # raise ParsingError('Problem parsing label ' + label)


def extract_miscinfo(value, messages_printer=None):
    # wiki => "wikipedia=pl:" fb, url => "website="
    if '=' in value:
        misckey, miscvalue = value.split("=", 1)
        if misckey == 'url':
            if miscvalue.startswith('http') or miscvalue.find(':') > 0:
                return 'website', miscvalue
            else:
                return 'website', r"http://" + miscvalue
        elif misckey == 'wiki':
            if miscvalue.startswith('http'):
                return 'website', miscvalue
            else:
                return 'wikipedia', "pl:" + miscvalue
        elif misckey == 'fb':  # 'facebook' tag isn't widely used
            if miscvalue.startswith('http'):
                return 'website', miscvalue
            else:
                return 'website', "https://facebook.com/" + miscvalue
        elif misckey in ('idOrlen', 'idLotos', 'vid', 'MoyaID', 'ZabkaID', 'idPNI', 'id', 'BilID', 'nest'):
            messages_printer.printwarn('Ignoring MiscInfo: ' + value)
        else:
            if messages_printer is not None:
                messages_printer.printerror("Unknown MiscInfo: " + value)
            return '', ''
    else:
        if messages_printer is not None:
            messages_printer.printerror("Improper format MiscInfo: " + value)
    return '', ''


def extract_hlevel_v2(value):
    """
        converts mp-type HLevel to segment type of levels. Each segment is tuple in a form
        (start_node_num, end_node_num, level), node -1 is to the end of the road. The nodes with the same level are
        joined if possible
        :param value: string: hlevel string
        :return: (start_node_num, end_node_num, level), (end_node_num, end_node_num2, level) ... (end_node_numX, -1, level)
        """
    level_list = []
    try:
        levels = [(int(b[0]), int(b[1]),) for b in [a.split(',') for a in value.strip('()').split('),(')]]
    except ValueError:
        return tuple()
    except IndexError:
        return tuple()
    if levels[0][0] != 0:
        levels = [(0, 0,)] + levels
    for elem_num in range(len(levels) - 1):
        start_node_num = levels[elem_num][0]
        end_node_num = levels[elem_num + 1][0]
        if start_node_num < 0 or end_node_num < 0:
            return tuple()
        if levels[elem_num][1] == 0 and levels[elem_num + 1][1] != 0:
            cur_level = levels[elem_num + 1][1]
        elif levels[elem_num][1] != 0 and levels[elem_num + 1][1] == 0:
            cur_level = levels[elem_num][1]
        elif levels[elem_num][1] < 0 and levels[elem_num + 1][1] < 0:
            cur_level = min(levels[elem_num][1], levels[elem_num + 1][1])
        else:
            cur_level = max(levels[elem_num][1], levels[elem_num + 1][1])
        level_list.append((start_node_num, end_node_num, cur_level))
    level_list.append((levels[-1][0], -1, levels[-1][1]))
    deduplicated_level_list = []
    for elem in level_list:
        if not deduplicated_level_list:
            deduplicated_level_list.append(elem)
            continue
        if elem[2] == deduplicated_level_list[-1][2]:
            start_node_num = deduplicated_level_list[-1][0]
            end_node_num = elem[1]
            cur_level = elem[2]
            deduplicated_level_list[-1] = (start_node_num, end_node_num, cur_level,)
        else:
            deduplicated_level_list.append(elem)
    return tuple(deduplicated_level_list)


def extract_hlevel(value):
    """
    converts mp-type HLevel to segment type of levels. Each segment is tuple in a form
    (start_node_num, end_node_num, level), node -1 is to the end of the road. The nodes with the same level are
    joined if possible
    :param value: string: hlevel string
    :return: (start_node_num, end_node_num, level), (end_node_num, end_node_num2, level) ... (end_node_numX, -1, level)
    """
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
    return level_list


def extract_szlak(value):
    ref = []
    unknonw_ref = []
    trial_tag = []
    for colour in value.split(','):
        if colour.lower() == 'zolty':
            ref.append('Żółty szlak')
            trial_tag.append('marked_trail_yellow')
        elif colour.lower() == 'zielony':
            ref.append('Zielony szlak')
            trial_tag.append('marked_trail_green')
        elif colour.lower() == 'czerwony':
            ref.append('Czerwony szlak')
            trial_tag.append('marked_trail_red')
        elif colour.lower() == 'niebieski':
            ref.append('Niebieski szlak')
            trial_tag('marked_trail_blue')
        else:
            ref.append(colour)
            unknonw_ref.append(colour)
    return trial_tag, ref, unknonw_ref


def extract_street_for_addr(way):
    p = re.compile(r'\{.*\}')  # dowolny string otoczony klamrami
    if 'alt_name' in way:
        return '', way['alt_name']
    # klamry w nazwie eliminuja wpis jako wlasciwa nazwe dla adresacji
    elif ('name' in way) and (not p.search(way['name'])):
        return '', way['name']
    elif 'loc_name' in way:
        return '', way['loc_name']
    elif 'short_name' in way:
        return '', way['short_name']
    else:
        if 'name' in way:
            return way['name'], 'STREET_missing'
        else:
            return "<empty>", 'STREET_missing'

def extract_routeparam(value):
    """
    extracts routeparam values from RouteParam string
    Parameters
    ----------
    value: str: coma seperated values of route param: speed limit, route class, one way, route is toll, no emergency,
    no delivery, no car/motocycle, no bus, no taxi, no pedestrian, no bicycle, no truck, eg: 0,0,0,1,0,0,0,0,0,0,0,0

    Returns
    -------
    dict: {key, value}, empty dict in case of failure
    """
    maxspeeds = {0: '8', 1: '20', 2: '40', 3: '56', 4: '72', 5: '93', 6: '108', 7: '128'}
    exceptions = ('emergency', 'goods', 'motorcar', 'psv', 'taxi', 'foot', 'bicycle', 'hgv')
    try:
        params = tuple(int(a) for a in value.split(','))
    except ValueError:
        return {}
    _way = dict()
    _way['ump:speed_limit'] = str(params[0])
    _way['ump:route_class'] = str(params[1])
    if params[0] != 0:
        _way['maxspeed'] = maxspeeds[params[0]]  # Probably useless
    if params[2] != 0:
        _way['oneway'] = 'yes'
    if params[3] != 0:
        _way['toll'] = 'yes'
    for i, val in enumerate(params[4:]):
        if val != 0:
            _way[exceptions[i]] = 'no'
    return _way


def print_point_pickled(point, pointattr, task_id, orig_id, node_generalizator, ostr):
    """
    Funkcja drukuje punkt do postaci xmlowej
    Parameters
    ----------
    point: tuple w postaci (latitude, longitude)
    pointattr: dict atrybutow punktow
    task_id: aktualny numer przetwarzanego pliku - potrzebne do node generalizator
    orig_id: oryginalna pozycja w przetwarzanym pliku
    node_generalizator: klasa obslugujaca przeliczanie numerow pointow, way oraz relacji
    ostr: plik wyjsciowy
    Returns None
    -------

    """
    if '_out' in pointattr:
        return
    if '_timestamp' in pointattr:
        timestamp = pointattr['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp for point %r\n" % pointattr)
        timestamp = get_runstamp()
    currid = node_generalizator.get_point_id(task_id, orig_id)
    idstring = str(currid)
    head = ''.join(("<node id='", idstring, "' timestamp='", str(timestamp), "' visible='true' ", extra_tags,
                    "lat='", str(point[0]), "' lon='", str(point[1]), "'>\n"))
    ostr.write(head)
    # if '_src' in pointattr:
    #     src = pointattr.pop('_src')
    for key in pointattr:
        if key.startswith('_'):
            continue
        if len(str(pointattr[key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(pointattr[key]) + "\n")
            continue
        try:
            ostr.write(("\t<tag k='%s' v='%s' />\n" % (key, xmlize(pointattr[key]))))
        except:
            sys.stderr.write("converting key " + key + ": " + str(pointattr[key]) + " failed\n")
    ostr.write("</node>\n")


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
        timestamp = get_runstamp()
    currid = node_generalizator.get_way_id(task_id, orig_id)
    idstring = str(currid)
    ostr.write("<way id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for nindex in way['_nodes']:
        refstring = node_generalizator.get_point_id(task_id, nindex)
        ostr.write("\t<nd ref='%s' />\n" % refstring)

    # if '_src' in way:
    #     src = way.pop('_src')
    for key in way:
        if key.startswith('_'):
            continue
        if len(str(way[key])) > 255:
            sys.stderr.write("\tERROR: key value too long " + key + ": " + str(way[key]) + "\n")
            continue
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(way[key])))
    ostr.write("</way>\n")


def print_relation_pickled(rel, task_id, orig_id, node_generalizator, ostr):
    """Prints a relation given by rel together with its ID to stdout as XML"""
    if '_c' in rel:
        if rel['_c'] <= 0:
            return
        rel.pop('_c')
    if "_members" not in rel:
        sys.stderr.write("warning: Unable to print relation not having members: %r\n" % rel)
        return

    if '_timestamp' in rel:
        timestamp = rel['_timestamp']
    else:
        sys.stderr.write("warning: no timestamp in relation: %r\n" % rel)
        timestamp = get_runstamp()
    currid = node_generalizator.get_relation_id(task_id, orig_id)
    idstring = str(currid)
    ostr.write("<relation id='%s' timestamp='%s' %s visible='true'>\n" % (idstring, str(timestamp), extra_tags))
    for role, (_type, members) in rel['_members'].items():
        for member in members:
            if _type == "node":
                # _nod = _points[member]
                _id = node_generalizator.get_point_id(task_id, member)
            elif _type == "way":
                _id = node_generalizator.get_way_id(task_id, member)
            else:
                _id = node_generalizator.get_relation_id(task_id, member)
            refstring = str(_id)
            ostr.write("\t<member type='%s' ref='%s' role='%s' />\n" % (_type, refstring, role))

    # if '_src' in rel:
    #     src = rel.pop('_src')
    for key in rel:
        if key.startswith('_'):
            continue
        ostr.write("\t<tag k='%s' v='%s' />\n" % (key, xmlize(rel[key])))
    ostr.write("</relation>\n")


def post_load_processing(maxtypes=None, progress_bar=None, map_elements_props=None, filestamp=None,
                         messages_printer=None):
    # Roundabouts: Use the road class of the most important (lowest numbered) road that meets the roundabout.
    if maxtypes is None:
        maxtypes = {}
    ways = map_elements_props['ways']
    pointattrs = map_elements_props['pointattrs']
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
        if ('junction' in way and way['junction'] == 'roundabout') or \
                ('highway' in way and 'ump:type' in way and int(way['ump:type'], 0) == int('0xe', 0)):
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
                preprepare_restriction(rel, node_ways_relation=node_ways_relation,
                                       map_elements_props=map_elements_props)
                # print "DEBUG: preprepare_restriction(rel:%r) OK." % (rel,)
            except NodesToWayNotFound:
                messages_printer.printerror("warning: Unable to find nodes to preprepare restriction from rel: %r\n"
                                            % rel)
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
                if len(subway['_nodes']) > 1:          # not for the last single node
                    ways.append(subway)
                    if 'highway' in subway and 'ump:type' in subway and int(subway['ump:type'], 16) <= 0x16:
                        new_way_id = len(ways) - 1
                        for node in ways[-1]['_nodes']:
                            node_ways_relation[node].add(new_way_id)

    # we have to transfer relations ordered dict into the list, as it is easier to add elements to the end
    map_elements_props['relations'] = [relations[road_id] for road_id in relations]
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
                map_elements_props['relations'].append(make_multipolygon(way, way.pop('_innernodes'),
                                                                         filestamp=filestamp,
                                                                         node_ways_relation=node_multipolygon_relation,
                                                                         map_elements_props=map_elements_props))

    # for each relation/restriction split ways at via points as the "from" and "to" members must start/end at the
    # Role via node or the Role via way(s)
    for rel in map_elements_props['relations']:
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if rel['type'] in ('restriction', 'lane_restriction',):
            try:
                prepare_restriction(rel, node_ways_relation=node_ways_relation, map_elements_props=map_elements_props)
            except NodesToWayNotFound:
                messages_printer.printerror("warning: Unable to find nodes to prepare restriction from rel: %r\n" % rel)

    for rel in map_elements_props['relations']:
        _line_num += 1
        progress_bar.set_val(_line_num, 'drp')
        if rel['type'] in ('restriction', 'lane_restriction',):
            try:
                rnodes = make_restriction_fromviato(rel, node_ways_relation=node_ways_relation,
                                                    map_elements_props=map_elements_props, )
                if rel['type'] == 'restriction':
                    name_turn_restriction(rel, rnodes, map_elements_props['points'])
            except NodesToWayNotFound:
                messages_printer.printerror("warning: Unable to find nodes to preprepare restriction from rel: %r\n"
                                            % rel)

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


def save_pickled_data(pickled_files, map_elements_props=None):
    try:
        for pf_name in pickled_files:
            with open(pickled_files[pf_name], 'wb') as pickle_f:
                pickle.dump(map_elements_props[pf_name], pickle_f)
    except IOError:
        sys.stderr.write("\tERROR: Can't write pickle files \n")
        sys.exit()


def remove_label_braces(local_way):
    new_way = local_way.copy()
    p = re.compile(r'\{.*\}')  # dowolny string otoczony klamrami
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

            if new_way['name'] == "":  # zastepowanie pustych name
                if 'loc_name' in new_way:
                    new_way['name'] = new_way['loc_name']
                    new_way.pop('loc_name')
                elif 'short_name' in new_way:
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


def output_normal_pickled(options, filenames_to_gen, pickled_filenames=None, node_generalizator=None, ids_to_process=0,
                          multiprocessing_queue=None):
    try:
        output_files = {a: open(filenames_to_gen[a], 'a', encoding='utf-8') for a in filenames_to_gen}
    except IOError as ioerror:
        sys.stderr.write("\tERROR: Can't open normal output file " + ioerror.filename + "!\n")
        sys.exit()
    messages_printer = MessagePrinters(workid='1', working_file='', verbose=options.verbose)
    elapsed = datetime.now().replace(microsecond=0)
    messages_printer.printinfo("Generating " + ', '.join(filenames_to_gen) + " output(s). Processing %s ids."
                               % ids_to_process)
    # printed_points = set()
    for task_id, pickled_point in enumerate(pickled_filenames['points']):
        with open(pickled_point, 'rb') as p_file:
            task_id_points = pickle.load(p_file)
        with open(pickled_filenames['pointattrs'][task_id], 'rb') as pattrs_file:
            task_id_pointattrs = pickle.load(pattrs_file)
        for _point in task_id_points:
            point_id = task_id_points.get_point_id(_point)
            _points_attr = task_id_pointattrs[point_id]
            orig_id = task_id_points.index(_point)
            # if _point in printed_points:
            #     print('punkt wydrukowany juz', _point, file=sys.stderr)
            # else:
            #     printed_points.add(_point)
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
    for filetype, out in output_files.items():
        out.write("</osm>\n")
        out.close()
        messages_printer.printinfo("Generated %s file: %s" % (filetype, filenames_to_gen[filetype]))
    elapsed = datetime.now().replace(microsecond=0) - elapsed
    messages_printer.printinfo("Generating " + ', '.join(filenames_to_gen) + " output(s) done (took %s)." % elapsed)
    return


def output_nominatim_points_ways_preprocessing(file_g_name, points_fname, pointattrs_fname, ways_fname,
                                               messages_printer=None, node_generalizator=None):
    """
    Zmiana parametrów dróg i aadresow dla nominatima i zapis do nowych zapiklowanych plikow
    Parameters
    ----------
    file_g_name - unikatowa nazwa/numer pliku pickla w ktrym przechowywane byly dane
    points_fname - nazwa pliku z punktami
    pointattrs_fname - nazwa pliku z pointattraami
    ways_fname - nazwa pliku z drogami
    messages_printer - klasa obslugujaca druk informacji i ostrzezen
    node_generalizator - generalizator nodwo

    Returns OrderedDict {'points': [file1, file2, file3], 'pointsattr': [file1, file2, file3], 'ways': [file1, file2...]
    -------

    """
    l_ways = list()
    streets_counter = defaultdict(list)
    elapsed = datetime.now().replace(microsecond=0)
    # wczytaujemy wszystkie pointy
    nominatim_filestamp = datetime.fromtimestamp(os.path.getmtime(points_fname)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(points_fname, 'rb') as p_file:
        local_points = pickle.load(p_file)

    # wczytujemy wszystkie pointattrs
    local_pointattrs = OrderedDict()
    with open(pointattrs_fname, 'rb') as p_file:
        local_pointattrs = pickle.load(p_file)

    # wczytujemy wszystkie drogi
    local_ways = OrderedDict()
    with open(ways_fname, 'rb') as p_file:
        local_ways = pickle.load(p_file)

    messages_printer.printdebug("City=>Streets scan start: " + str(datetime.now()))

    #  fragment dodajacy krotkie odcinki drog dla wsi ktore nie posiadaja ulic
    #  zbieramy info o wszytskich miastach

    for _point in local_points:
        _points_attr = local_pointattrs[local_points.get_point_id(_point)]
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
            # m = {'radius': radius, 'lat': lat, 'lon': lon, 'cnt': 0, 'task_id': task_id}
            m = {'radius': radius, 'lat': lat, 'lon': lon, 'cnt': 0}
            streets_counter[n].append(m)
    messages_printer.printdebug("City=>Streets scan part1: " + str(datetime.now()))
    # teraz skan wszystkich ulic

    _points = local_points
    for _way in local_ways:
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
                        l_ways.append({'newway': newway})
                        start = i
                        lenKM = 0
                        waydivided = True
                if waydivided:
                    _way['_nodes'] = _way['_nodes'][start:]
                    _way['split'] = 'last'
                # else:
                #   printerror("\tRef ="+way['ref']+" HW="+way['highway'])

    # dodajemy nowe drogi do wszystkich drog
    for way in l_ways:
        local_ways.append(way['newway'])

    for _way in local_ways:
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
                            messages_printer.printdebug("Brak BLISKIEGO miasta: " + town + " ul.: " + _way['name'] +
                                                        " (" + str(waylat) + "," + str(waylon) + ")")
                    else:
                        messages_printer.printdebug("Brak Miasta: " + town + " ul.: " + _way['name'] + " (" +
                                                    str(waylat) + "," + str(waylon) + ")")
            except IndexError:
                pprint.pprint(_way, sys.stderr)
    messages_printer.printdebug("City=>Streets scan part2: " + str(datetime.now()))
    # i dodawanie krotkich ulic

    for miasto in streets_counter:
        for k in streets_counter[miasto]:
            if k['cnt'] != 0:
                messages_printer.printdebug("Ulice: " + miasto + "\tszt. " + str(k['cnt']))
            else:
                messages_printer.printdebug("Short way added:" + miasto)
                pt0 = (float(k['lat']) + 0.0004, float(k['lon']))
                pt1 = (float(k['lat']) + 0.0008, float(k['lon']))
                pind0 = len(local_points)
                local_points.append(pt0)
                pt0_point_id = local_points.get_point_id(pt0)
                local_pointattrs[pt0_point_id] = {'_timestamp': nominatim_filestamp}
                pind1 = len(local_points)
                local_points.append(pt1)
                pt1_point_id = local_points.get_point_id(pt1)
                local_pointattrs[pt1_point_id] = {'_timestamp': nominatim_filestamp}
                way = {'_timestamp': nominatim_filestamp, '_nodes': [pind0, pind1], '_c': 2, 'is_in': miasto,
                       'name': miasto, 'addr:city': miasto, 'highway': "residental"}
                local_ways.append(way)
    messages_printer.printdebug("City=>Streets scan stop: " + str(datetime.now()))

    for way_id, _way in enumerate(local_ways):
        if _way is None:
            continue
        no_braces_way = remove_label_braces(_way)
        if 'name' in no_braces_way and not no_braces_way['name'] and 'addr:city' in no_braces_way and \
                no_braces_way['addr:city']:
            no_braces_way['name'] = no_braces_way['addr:city']
        local_ways[way_id] = no_braces_way

    pickled_file_names = OrderedDict()
    for f_tempname in ('points', 'pointattrs', 'ways'):
        aaa_fname = tempfile.NamedTemporaryFile(mode='w', encoding="utf-8", delete=False, dir=os.getcwd())
        aaa_fname.close()
        pickled_file_names[f_tempname] = aaa_fname.name
    save_pickled_data(pickled_file_names, {'points': local_points, 'pointattrs': local_pointattrs, 'ways': local_ways})
    node_generalizator.insert_points(file_g_name, local_points)
    node_generalizator.insert_ways(file_g_name, local_ways)
    return pickled_file_names


def output_nominatim_pickled(options, nominatim_filename, pickled_filenames=None, border_points=None, ids_to_process=0,
                             multiprocessing_queue=None):
    """
    Generates nominatim output from processed data
    Parameters
    ----------
    options: options command line
    nominatim_filename: the name for nominatim file to be generated
    pickled_filenames: dictionary {'points': [filename1, filename2, filename3...],
                                   'pointparams': [filename1, filename2, filename3...]
                                   'ways': [filename1, filename2, filename3...]
                                   'relations" [filename1, filename2, filename3...]}
    border_points: border points from borders file
    ids_to_process: number of object identifier (points + ways + relaction to proces, relations num is obsolete
    multiprocessing_queue: queue for returning generated filename
    Returns
    -------

    """
    if border_points is None:
        border_points = []
    messages_printer = MessagePrinters(workid='2', working_file='', verbose=options.verbose)
    elapsed = datetime.now().replace(microsecond=0)
    messages_printer.printinfo("Generating nominatim output. Processing %s ids" % ids_to_process)
    node_generalizator = NodeGeneralizator()
    node_generalizator.insert_borders(border_points)
    post_nom_picle_files = {'points': [], 'pointattrs': [], 'ways': []}
    for task_id in range(len(pickled_filenames['points'])):
        local_points = pickled_filenames['points'][task_id]
        local_pointattrs = pickled_filenames['pointattrs'][task_id]
        local_ways = pickled_filenames['ways'][task_id]
        ppm = output_nominatim_points_ways_preprocessing(task_id, local_points, local_pointattrs, local_ways,
                                                         messages_printer=messages_printer,
                                                         node_generalizator=node_generalizator)
        for tmp_elem in post_nom_picle_files:
            post_nom_picle_files[tmp_elem].append(ppm[tmp_elem])

    try:
        out = open(nominatim_filename, 'a', encoding='utf-8')
    except IOError:
        sys.stderr.write("\tERROR: Can't open nominatim output file " + nominatim_filename + "!\n")
        sys.exit()

    for task_id, pickled_point in enumerate(post_nom_picle_files['points']):
        with open(pickled_point, 'rb') as p_file:
            task_id_points = pickle.load(p_file)
        with open(post_nom_picle_files['pointattrs'][task_id], 'rb') as pattrs_file:
            task_id_pointattrs = pickle.load(pattrs_file)
        for _point in task_id_points:
            point_id = task_id_points.get_point_id(_point)
            _points_attr = task_id_pointattrs[point_id]
            print_point_pickled(_point, _points_attr, task_id, point_id, node_generalizator, out)

    for task_id, pickled_way in enumerate(post_nom_picle_files['ways']):
        with open(pickled_way, 'rb') as p_file:
            orig_id = -1
            for _way in pickle.load(p_file):
                orig_id += 1
                if _way is None:
                    continue
                if 'ref' in _way and 'highway' in _way:
                    if _way['highway'] in {'cycleway', 'path', 'footway'}:
                        continue
                print_way_pickled(_way, task_id, orig_id, node_generalizator, out)
    out.write("</osm>\n")
    out.close()
    for g_name in post_nom_picle_files.values():
        for filenam in g_name:
            os.remove(filenam)
    messages_printer.printinfo("Generated nominatim file: %s." % nominatim_filename)
    elapsed = datetime.now().replace(microsecond=0) - elapsed
    messages_printer.printinfo("Generating nominatim output done (took %s)." % elapsed)
    return


def worker(task, options, border_points=None):
    global glob_progress_bar_queue
    if border_points is None:
        border_points = list()
    messages_printer = MessagePrinters(workid=task['idx'], working_file=task['file'], verbose=options.verbose)
    filestamp = task['filestamp']

    try:
        if sys.platform.startswith('linux'):
            file_encoding = 'cp1250'
        else:
            file_encoding = 'cp1250'
        infile = open(task['file'], "r", encoding=file_encoding)
        num_lines_to_process = len(infile.readlines())
        infile.seek(0)

    except IOError:
        messages_printer.printerror("Can't open file " + task['file'])
        sys.exit()
    messages_printer.printinfo("Loading " + task['file'])

    progress_bar = ProgressBar(options, obszar=task['file'], glob_progress_bar_queue=glob_progress_bar_queue)
    progress_bar.start(num_lines_to_process, 'mp')
    maxtypes, map_elements_props = parse_txt(infile, options, progress_bar=progress_bar, border_points=border_points,
                                             messages_printer=messages_printer, filestamp=filestamp)
    progress_bar.set_done('mp')
    infile.close()
    post_load_processing(maxtypes=maxtypes, progress_bar=progress_bar, map_elements_props=map_elements_props,
                         filestamp=filestamp, messages_printer=messages_printer)
    progress_bar.set_done('drp')

    pickled_files_names = {'points': create_pickled_file_name('points', str(task['idx'])),
                           'pointattrs': create_pickled_file_name('pointattrs', str(task['idx'])),
                           'ways': create_pickled_file_name('ways', str(task['idx'])),
                           'relations': create_pickled_file_name('relations', str(task['idx']))}
    save_pickled_data(pickled_files_names, map_elements_props=map_elements_props)
    ids_num = sum(len(map_elements_props[a]) for a in ('points', 'ways', 'relations')) - len(border_points)
    l_warns = str(messages_printer.get_warning_num())
    l_errors = str(messages_printer.get_error_num())
    messages_printer.printinfo("Finished " + task['file'] + " (" + str(ids_num) + " ids)" + ', Warnings: ' + l_warns +
                               ', Errors: ' + l_errors + '.')
    return task['ids']


def main(options, args):
    if len(args) < 1:
        parser.print_help()
        sys.exit()
    global glob_progress_bar_queue
    if hasattr(options, 'progress_bar_queue'):
        glob_progress_bar_queue = options.progress_bar_queue
    else:
        glob_progress_bar_queue = None

    messages_printer = MessagePrinters(workid='main thread', verbose=options.verbose)
    node_generalizator = NodeGeneralizator()
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    set_runstamp(time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    runtime = datetime.now().replace(microsecond=0)
    bpoints = None

    sys.stderr.write("INFO: mdmMp2xml.py ver:" + __version__ + " ran at " + get_runstamp() + "\n")
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
            border_filename = path_file(options.borders_file)
            elapsed = datetime.now().replace(microsecond=0)
            try:
                borderf = open(border_filename, "r", encoding='cp1250')
            except IOError:
                sys.stderr.write("\tERROR: Can't open border input file " + border_filename + "!\n")
                sys.exit()
            if options.force_timestamp is None:
                borderstamp = datetime.fromtimestamp(os.path.getmtime(border_filename)).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                borderstamp = options.force_timestamp
            bpoints = parse_borders_return_bpoints(borderf, options, borderstamp)
            borderf.close()
            node_generalizator.insert_borders(bpoints)
            elapsed = datetime.now().replace(microsecond=0) - elapsed
            sys.stderr.write("\tINFO: " + str(len(bpoints)) + " ids of border points (took " + str(elapsed) + ").\n")
        else:
            if options.force_timestamp is None:
                borderstamp = get_runstamp()
            else:
                borderstamp = options.force_timestamp
            sys.stderr.write("\tINFO: Running without border file.\n")

        worklist = []
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
            if options.force_timestamp is None:
                f_stamp = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                f_stamp = options.force_timestamp
            workelem = {'idx': n+1, 'file': f, 'ids': 0, 'baseid': 0, 'filestamp': f_stamp}
            worklist.append(workelem)
        if options.threadnum == 1:
            for workelem in worklist:
                result = worker(workelem, options, border_points=bpoints)
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
            result = pool.map(partial(worker, options=copy_options, border_points=bpoints), worklist)
            pool.terminate()
            for workelem in worklist:
                workelem['ids'] = result[(workelem['idx'])-1]

        elapsed = datetime.now().replace(microsecond=0) - elapsed
        messages_printer.printinfo("Area processing done (took " + str(elapsed) + "). Reading pickle files:")
        elapsed = datetime.now().replace(microsecond=0)
        # wczytaj pliki piklowane i stwórz poprawny node_generalizator
        pickled_filenames = {'points': [], 'pointattrs': [], 'ways': [], 'relations': []}
        ids_to_process = 0
        ids_to_process_nominatim = 0
        for work_no, workelem in enumerate(worklist):
            _task_idx = str(workelem['idx'])
            pickled_nodes_filename = create_pickled_file_name('points', _task_idx)
            pickled_filenames['points'].append(pickled_nodes_filename)
            pickled_ways_filename = create_pickled_file_name('ways', _task_idx)
            pickled_filenames['ways'].append(pickled_ways_filename)
            pickled_relations_filename = create_pickled_file_name('relations', _task_idx)
            pickled_filenames['relations'].append(pickled_relations_filename)
            pickled_filenames['pointattrs'].append(create_pickled_file_name('pointattrs', _task_idx))
            with open(pickled_nodes_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_points(work_no, pickled_data)
                ids_to_process += len(pickled_data)
                ids_to_process_nominatim += len(pickled_data)
            with open(pickled_ways_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_ways(work_no, pickled_data)
                ids_to_process += len(pickled_data)
                ids_to_process_nominatim += len(pickled_data)
            with open(pickled_relations_filename, 'rb') as pickled_f:
                pickled_data = pickle.load(pickled_f)
                node_generalizator.insert_relations(work_no, pickled_data)
                ids_to_process += len(pickled_data)
        elapsed = datetime.now().replace(microsecond=0) - elapsed
        messages_printer.printinfo("Pickle files reading done (took " + str(elapsed) + "). Generating outputs:")
        elapsed = datetime.now().replace(microsecond=0)
        # zapisywanie pikli w normalnym trybie
        output_files_to_generate = {}
        if options.outputfile is not None:
            output_files_to_generate['normal'] = path_file(options.outputfile)
        else:
            _aaa = tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), encoding='utf-8', delete=False)
            _aaa.close()
            output_files_to_generate['normal'] = _aaa.name
        if options.navit_file is not None:
            output_files_to_generate['navit'] = path_file(options.navit_file)
        if options.index_file is not None:
            output_files_to_generate['index'] = path_file(options.index_file)
        if options.nonumber_file is not None:
            output_files_to_generate['no_number'] = path_file(options.nonumber_file)
        if options.nominatim_file is not None:
            output_files_to_generate['nominatim'] = path_file(options.nominatim_file)

        messages_printer.printinfo_nlf("Working on header and border points ")
        elapsed = datetime.now().replace(microsecond=0)
        for filename in output_files_to_generate.values():
            with open(filename, 'w', encoding='utf-8') as header_f:
                try:
                    header_f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
                    header_f.write("<osm version='0.6' generator='mdmMp2xml %s converter for UMP-PL'>\n" % __version__)
                    if options.borders_file is not None:
                        bpointattrs = defaultdict(dict)
                        for point in bpoints:
                            index = bpoints.index(point)
                            bpointattrs[index]['_timestamp'] = borderstamp
                            print_point_pickled(point, bpointattrs[index], 0, index, node_generalizator, header_f)
                except IOError as f_except:
                    sys.stderr.write("\n\tERROR: Can't write header file for %s!\n" % f_except.filename)
                    sys.exit()
        elapsed = datetime.now().replace(microsecond=0) - elapsed
        messages_printer.printinfo_nlf("written (took " + str(elapsed) + ").")

        if options.nominatim_file is not None and options.threadnum > 1 and not options.monoprocess_outputs:
            nom_filename = output_files_to_generate.pop('nominatim')
            normal_process = Process(target=output_normal_pickled, args=(options, output_files_to_generate,),
                                     kwargs={'pickled_filenames': pickled_filenames,
                                             'node_generalizator': node_generalizator,
                                             'ids_to_process': ids_to_process})
            nominatim_process = Process(target=output_nominatim_pickled, args=(options, nom_filename),
                                        kwargs={'pickled_filenames': pickled_filenames,
                                                'border_points': bpoints,
                                                'ids_to_process': ids_to_process_nominatim})
            normal_process.start()
            nominatim_process.start()
            nominatim_process.join()
            normal_process.join()
        else:
            if options.nominatim_file is not None:
                nom_filename = output_files_to_generate.pop('nominatim')
                output_nominatim_pickled(options, nom_filename, pickled_filenames=pickled_filenames,
                                         border_points=bpoints, ids_to_process=ids_to_process_nominatim)
            output_normal_pickled(options, output_files_to_generate, pickled_filenames=pickled_filenames,
                                  node_generalizator=node_generalizator, ids_to_process=ids_to_process)
        if options.outputfile is None:
            messages_printer.printinfo_nlf("Normal output copying to stdout ")
            try:
                elapsed = datetime.now().replace(microsecond=0)
                shutil.copyfileobj(open(output_files_to_generate['normal'], 'r', encoding="utf-8"), sys.stdout)
                os.remove(output_files_to_generate['normal'])
                elapsed = datetime.now().replace(microsecond=0) - elapsed
                messages_printer.printinfo_nlf("done (took " + str(elapsed) + ").\n")
            except IOError:
                messages_printer.printinfo_nlf("\n\tERROR: Normal output failed!\n")
                sys.exit()
        elapsed = datetime.now().replace(microsecond=0) - runtime
        messages_printer.printinfo("mdmMp2xml.py finished after " + str(elapsed) + ".\n")
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
                      help="obsolete, remove gaps in id usage")
    parser.add_option("--ignore_errors",
                      action="store_true", dest="ignore_errors", default=False,
                      help="try to ignore errors in .mp file")
    parser.add_option("--regions",
                      action="store_true", dest="regions", default=False,
                      help="attach regions to cities in the index file")
    parser.add_option('--monoprocess_outputs', dest="monoprocess_outputs", default=False, action='store_true',
                      help="generate outputs in single process, do not use multiprocessing")
    parser.add_option('--force_timestamp', dest='force_timestamp', type='string', action='store',
                      help='Force given timestamp for map elements, useful for testing. '
                           'Proper format: YYYY-MM-DDTHH:MM:SSZ, eg.: 2023-11-03T09:26:40Z')
    (options, args) = parser.parse_args()
    main(options, args)
