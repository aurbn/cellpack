# -*- coding: utf-8 -*-
from enum import Enum
import os

import json
from json import encoder

encoder.FLOAT_REPR = lambda o: format(o, ".8g")


class MetaEnum(Enum):
    @classmethod
    def values(cls):
        return [member.value for member in cls]

    @classmethod
    def is_member(cls, item):
        values = cls.values()
        return item in values


class Place_Methods(MetaEnum):
    JITTER = "jitter"
    SPHERES_SST = "spheresSST"
    PANDA_BULLET = "pandaBullet"
    PANDA_BULLET_RELAX = "pandaBulletRelax"


class Inner_Grid_Methods(MetaEnum):
    # Working inner grid methods
    RAYTRACE = "raytrace"
    SCANLINE = "scanline"
    TRIMESH = "trimesh"


class ConfigLoader(object):
    def __init__(self, input_file_path):
        _, file_extension = os.path.splitext(input_file_path)
        self.file_path = input_file_path
        self.file_extension = file_extension
        self.default_values = {
            "version": 1.0,
            "bounding_box": [[0, 0, 0], [100, 100, 100]],
            "format": "simularium",
            "inner_grid_method": "raytrace",
            "live_packing": False,
            "ordered_packing": False,
            "out": "out/",
            "overwrite_place_method": False,
            "place_method": Place_Methods.JITTER,
            "save_analyze_result": False,
            "show_grid_plot": False,
            "spacing": None,
            "use_periodicity": False,
        }
        self.config = self._read()

    @staticmethod
    def _test_types(config):
        if not Place_Methods.is_member(config["place_method"]):
            raise TypeError((f"place_method must be one of {Place_Methods.values()}, not {config['place_method']}"))
        if not Inner_Grid_Methods.is_member(config["inner_grid_method"]):
            raise TypeError((f"inner_grid_method must be one of {Inner_Grid_Methods.values()}, not {config['inner_grid_method']}"))
        if not isinstance(config["bounding_box"], list) or len(config["bounding_box"]) != 2:
            raise TypeError("bounding_box must be an array of 2 arrays")
        bools = ["live_packing", "ordered_packing", "overwrite_place_method", "save_analyze_result", "show_grid_plot", "use_periodicity"]
        for should_be_bool in bools:
            if not isinstance(config[should_be_bool], bool):
                raise TypeError((f"{should_be_bool} should be a boolean, not {config[should_be_bool]}"))

    def _read(self):
        """
        Read in a Json Config file.
        """
        new_values = json.load(open(self.file_path, "r"))
        config = self.default_values.copy()
        config.update(new_values)
        ConfigLoader._test_types(config)

        return config
