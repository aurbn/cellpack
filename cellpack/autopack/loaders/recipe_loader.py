# -*- coding: utf-8 -*-
import copy
import os

import json
from json import encoder

import cellpack.autopack as autopack
from cellpack.autopack.utils import deep_merge

encoder.FLOAT_REPR = lambda o: format(o, ".8g")


class RecipeLoader(object):
    # TODO: add all default values here
    default_values = {
        "bounding_box": [[0, 0, 0], [100, 100, 100]],
    }

    def __init__(self, input_file_path):
        _, file_extension = os.path.splitext(input_file_path)
        self.latest_version = 1.0
        self.file_path = input_file_path
        self.file_extension = file_extension
        self.recipe_data = self._read()
        self.roots = self._find_roots()

    @staticmethod
    def create_output_dir(out_base_folder, recipe_name, sub_dir=None):
        os.makedirs(out_base_folder, exist_ok=True)
        output_folder = os.path.join(out_base_folder, recipe_name)
        if sub_dir is not None:
            output_folder = os.path.join(output_folder, sub_dir)
        os.makedirs(output_folder, exist_ok=True)
        return output_folder

    @staticmethod
    def _resolve_object(key, objects):
        current_object = objects[key]
        inherit_key = current_object["inherit"]
        base_object = objects[inherit_key]
        new_object = deep_merge(copy.deepcopy(base_object), current_object)
        objects[key] = new_object

    @staticmethod
    def _sort(key, visited, stack, edges):
        visited[key] = True
        for element in edges[key]:
            if visited[element] is False:
                RecipeLoader._sort(element, visited, stack, edges)
        stack.append(key)

    @staticmethod
    def _topological_sort(objects):
        edges = dict()
        for key, values in objects.items():
            if key not in edges:
                edges[key] = []
            if "inherit" in values:
                edges[key].append(values["inherit"])
                # "sphere_25": ["base"]
                # "sphere_50": ["sphere_25"]
                # "base": []
        stack = []
        visited = {key: False for key in objects}
        for key, value in objects.items():
            if visited[key] is False:
                RecipeLoader._sort(key, visited, stack, edges)
        return stack

    @staticmethod
    def resolve_inheritance(objects):
        stack = RecipeLoader._topological_sort(objects)
        for key in stack:
            if "inherit" in objects[key]:
                RecipeLoader._resolve_object(key, objects)
        return objects

    def _read(self):
        new_values = json.load(open(self.file_path, "r"))
        recipe_data = RecipeLoader.default_values.copy()
        recipe_data = deep_merge(recipe_data, new_values)
        # TODO: request any external data before returning
        recipe_data["objects"] = RecipeLoader.resolve_inheritance(
            recipe_data["objects"]
        )
        return recipe_data

    def _find_roots(self):
        comp_dic = self.recipe_data["composition"]
        reference_dic = {}
        for key, entry in comp_dic.items():
            for _, ref_keys in entry.get("regions", {}).items():
                for ref_key in ref_keys:
                    if not isinstance(ref_key, dict):
                        reference_dic[ref_key] = key
        return set(comp_dic.keys()).difference(set(reference_dic.keys()))

    def _request_sub_recipe(self, inode):
        filename = None
        if inode is not None:
            if "include" in inode:
                filename = inode["include"]
        if filename is not None:
            filename = autopack.retrieveFile(
                filename,
                # destination = recipe+os.sep+"recipe"+os.sep+"ingredients"+os.sep,
                cache="recipes",
            )
            with open(filename, "r") as fp:  # doesnt work with symbol link ?
                data = json.load(fp)
        elif inode is not None:
            data = inode
        else:
            print("filename is None and not ingredient dictionary provided")
            return None
        return data

    @staticmethod
    def _migrate_version(recipe):
        if "format_version" not in recipe:
            recipe["bounding_box"] = recipe["options"]["boundingBox"]
        return recipe

    def _load_json(self):
        """
        Read in a Json Recipe.
        """
        sortkey = str.lower

        new_values = json.load(open(self.file_path, "r"))
        recipe_data = RecipeLoader.default_values.copy()
        recipe_data.update(new_values)
        # are there any custom paths
        if "paths" in recipe_data["recipe"]:
            custom_paths = recipe_data["recipe"]["paths"]
            autopack.updateReplacePath(custom_paths)

        autopack.current_recipe_path = self.file_path
        if (
            "format_version" not in recipe_data
            or recipe_data["format_version"] != self.latest_version
        ):
            recipe_data = RecipeLoader._migrate_version(recipe_data)

        if "cytoplasme" in recipe_data:
            ingrs_dic = recipe_data["cytoplasme"]["ingredients"]
            if len(ingrs_dic):
                for ing_name in sorted(ingrs_dic, key=sortkey):  # ingrs_dic:
                    # either xref or defined
                    ing_dic = ingrs_dic[ing_name]
                    sub_recipe = self._request_sub_recipe(inode=ing_dic)
                    recipe_data["cytoplasme"]["ingredients"][ing_name] = sub_recipe
        if "compartments" in recipe_data:
            # use some include ?
            if len(recipe_data["compartments"]):
                # include all compartments from given filename.
                # transform the geometry of the compartment packing rep
                for cname in recipe_data["compartments"]:
                    if cname == "include":
                        for i, compartment in enumerate(
                            recipe_data["compartments"]["include"]
                        ):
                            node = {"include": compartment["from"]}
                            sub_recipe = self._request_sub_recipe(inode=node)
                            recipe_data["compartments"][
                                compartment["from"]
                            ] = sub_recipe["compartments"]
                        continue
                    comp_dic = recipe_data["compartments"][cname]
                    rep = None
                    if "rep" in comp_dic:
                        rep = str(comp_dic["rep"])
                    rep_file = ""
                    if "rep_file" in comp_dic:
                        rep_file = str(comp_dic["rep_file"])
                    #                print (len(rep),rep == '',rep=="",rep != "None",rep != "None" or len(rep) != 0)
                    if rep is not None and len(rep) != 0 and rep != "" and rep != "":
                        rname = rep_file.split("/")[-1]
                        fileName, fileExtension = os.path.splitext(rname)
                        if fileExtension == "":
                            rep_file = rep_file + fileExtension
                        else:
                            rep_file = rep_file + "." + fileExtension
                    else:
                        rep = None
                        rep_file = None

                    if "surface" in comp_dic:
                        snode = comp_dic["surface"]
                        ingrs_dic = snode["ingredients"]
                        if len(ingrs_dic):
                            for ing_name in sorted(
                                ingrs_dic, key=sortkey
                            ):  # ingrs_dic:
                                # either xref or defined
                                ing_dic = ingrs_dic[ing_name]
                                sub_recipe = self._request_sub_recipe(inode=ing_dic)
                                comp_dic["surface"]["ingredients"][
                                    ing_name
                                ] = sub_recipe

                                # setup recipe
                    if "interior" in comp_dic:
                        snode = comp_dic["interior"]
                        ingrs_dic = snode["ingredients"]
                        if len(ingrs_dic):
                            for ing_name in sorted(
                                ingrs_dic, key=sortkey
                            ):  # ingrs_dic:
                                # either xref or defined
                                ing_dic = ingrs_dic[ing_name]
                                sub_recipe = self._request_sub_recipe(inode=ing_dic)
                                comp_dic["interior"]["ingredients"][
                                    ing_name
                                ] = sub_recipe

        return recipe_data

    def get_all_ingredients(self, results_data_in):
        all_ingredients = []
        recipe_data = self.recipe_data
        if "cytoplasme" in results_data_in:
            if len(results_data_in["cytoplasme"]["ingredients"]) != 0:
                for ingredient in results_data_in["cytoplasme"]["ingredients"]:
                    all_ingredients.append(
                        {
                            "results": results_data_in["cytoplasme"]["ingredients"][
                                ingredient
                            ],
                            "recipe_data": recipe_data["cytoplasme"]["ingredients"][
                                ingredient
                            ],
                        }
                    )
        if "compartments" in results_data_in:
            for compartment in results_data_in["compartments"]:
                current_compartment = results_data_in["compartments"][compartment]
                if "surface" in current_compartment:
                    for ingredient in current_compartment["surface"]["ingredients"]:
                        all_ingredients.append(
                            {
                                "results": current_compartment["surface"][
                                    "ingredients"
                                ][ingredient],
                                "recipe_data": recipe_data["compartments"][compartment][
                                    "surface"
                                ]["ingredients"][ingredient],
                            }
                        )
                if "interior" in current_compartment:
                    for ingredient in current_compartment["interior"]["ingredients"]:
                        all_ingredients.append(
                            {
                                "results": current_compartment["interior"][
                                    "ingredients"
                                ][ingredient],
                                "recipe_data": recipe_data["compartments"][compartment][
                                    "interior"
                                ]["ingredients"][ingredient],
                            }
                        )
        return all_ingredients
