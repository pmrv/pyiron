# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.

from __future__ import print_function
from ast import literal_eval
import numpy as np
import pandas as pd
import shutil
import os
from pyiron.base.settings.generic import Settings
from pyiron.base.generic.parameters import GenericParameters
from pyiron.atomistics.job.potentials import PotentialAbstract

__author__ = "Joerg Neugebauer, Sudarsan Surendralal, Jan Janssen"
__copyright__ = (
    "Copyright 2020, Max-Planck-Institut für Eisenforschung GmbH - "
    "Computational Materials Design (CM) Department"
)
__version__ = "1.0"
__maintainer__ = "Sudarsan Surendralal"
__email__ = "surendralal@mpie.de"
__status__ = "production"
__date__ = "Sep 1, 2017"

s = Settings()


class LammpsPotential(GenericParameters):

    """
    This module helps write commands which help in the control of parameters related to the potential used in LAMMPS
    simulations
    """

    def __init__(self, input_file_name=None):
        super(LammpsPotential, self).__init__(
            input_file_name=input_file_name,
            table_name="potential_inp",
            comment_char="#",
        )
        self._potential = None
        self._attributes = {}
        self._df = None

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, new_dataframe):
        self._df = new_dataframe
        # ToDo: In future lammps should also support more than one potential file - that is currently not implemented.
        try:
            self.load_string("".join(list(new_dataframe["Config"])[0]))
        except IndexError:
            raise ValueError(
                "Potential not found! "
                "Validate the potential name by self.potential in self.list_potentials()."
            )

    def remove_structure_block(self):
        self.remove_keys(["units"])
        self.remove_keys(["atom_style"])
        self.remove_keys(["dimension"])

    @property
    def files(self):
        if len(self._df["Filename"].values[0]) > 0 and self._df["Filename"].values[0] != ['']:
            absolute_file_paths = [
                files for files in list(self._df["Filename"])[0] if os.path.isabs(files)
            ]
            relative_file_paths = [
                files
                for files in list(self._df["Filename"])[0]
                if not os.path.isabs(files)
            ]
            for path in relative_file_paths:
                for resource_path in s.resource_paths:
                    if os.path.exists(
                        os.path.join(resource_path, "lammps", "potentials")
                    ):
                        resource_path = os.path.join(
                            resource_path, "lammps", "potentials"
                        )
                    if os.path.exists(os.path.join(resource_path, path)):
                        absolute_file_paths.append(os.path.join(resource_path, path))
                        break
            if len(absolute_file_paths) != len(list(self._df["Filename"])[0]):
                raise ValueError("Was not able to locate the potentials.")
            else:
                return absolute_file_paths

    def copy_pot_files(self, working_directory):
        if self.files is not None:
            _ = [shutil.copy(path_pot, working_directory) for path_pot in self.files]

    def get_element_lst(self):
        return list(self._df["Species"])[0]

    def to_hdf(self, hdf, group_name=None):
        if self._df is not None:
            with hdf.open("potential") as hdf_pot:
                hdf_pot["Config"] = self._df["Config"].values[0]
                hdf_pot["Filename"] = self._df["Filename"].values[0]
                hdf_pot["Name"] = self._df["Name"].values[0]
                hdf_pot["Model"] = self._df["Model"].values[0]
                hdf_pot["Species"] = self._df["Species"].values[0]
        super(LammpsPotential, self).to_hdf(hdf, group_name=group_name)

    def from_hdf(self, hdf, group_name=None):
        with hdf.open("potential") as hdf_pot:
            try:
                self._df = pd.DataFrame(
                    {
                        "Config": [hdf_pot["Config"]],
                        "Filename": [hdf_pot["Filename"]],
                        "Name": [hdf_pot["Name"]],
                        "Model": [hdf_pot["Model"]],
                        "Species": [hdf_pot["Species"]],
                    }
                )
            except ValueError:
                pass
        super(LammpsPotential, self).from_hdf(hdf, group_name=group_name)

    def get(self, parameter_name, default_value=None):
        """
        Get the value of a specific parameter from LammpsPotential - if the parameter is not available return
        default_value if that is set.

        Args:
            parameter_name (str): parameter key
            default_value (str): default value to return is the parameter is not set

        Returns:
            str: value of the parameter
        """
        i_line, multi_word_lst = self._find_line(parameter_name)
        if i_line > -1:
            val = self._dataset["Value"][i_line]
            if multi_word_lst is not None:
                num_words = len(multi_word_lst)
                val = val.split(" ")
                val = " ".join(val[(num_words - 1) :])
            try:
                val_v = literal_eval(val)
            except (ValueError, SyntaxError):
                val_v = val
            if callable(val_v):
                val_v = val
            return val_v
        elif default_value is not None:
            return default_value
        else:
            raise NameError("parameter not found: " + parameter_name)

    def _find_line(self, key_name):
        """
        Internal helper function to find a line by key name

        Args:
            key_name (str): key name

        Returns:
            list: [line index, line]
        """
        params = self._dataset["Parameter"]
        multiple_key = key_name.split()
        multi_word_lst = [None]
        if len(multiple_key) > 1:
            key_length = len(multiple_key)
            first = multiple_key[0]
            i_line_first_lst = np.where(np.array(params) == first)[0]
            i_line_lst, multi_word_lst = [], []
            for i_sel in i_line_first_lst:
                values = self._dataset["Value"][i_sel].split()
                if len(values) < key_length:
                    continue
                sel_value = values[: key_length - 1]
                is_different = False
                for i, sel in enumerate(sel_value):
                    if not (sel.strip() == multiple_key[i + 1].strip()):
                        is_different = True
                        continue
                if is_different:
                    continue
                multi_word_lst.append([params[i_sel]] + sel_value)
                i_line_lst.append(i_sel)
        else:
            if len(params) > 0:
                i_line_lst = np.where(np.array(params) == key_name)[0]
            else:
                i_line_lst = []
        if len(i_line_lst) == 0:
            return -1, None
        elif len(i_line_lst) == 1:
            return i_line_lst[0], multi_word_lst[0]
        else:
            error_msg = list()
            error_msg.append("Multiple occurrences of key_name: " + key_name + ". They are as follows")
            for i in i_line_lst:
                error_msg.append("dataset: {}, {}, {}".format(i,
                                                              self._dataset["Parameter"][i],
                                                              self._dataset["Value"][i]))
            error_msg = "\n".join(error_msg)
            raise ValueError(error_msg)


class LammpsPotentialFile(PotentialAbstract):
    """
    The Potential class is derived from the PotentialAbstract class, but instead of loading the potentials from a list,
    the potentials are loaded from a file.

    Args:
        potential_df:
        default_df:
        selected_atoms:
    """

    def __init__(self, potential_df=None, default_df=None, selected_atoms=None):
        if potential_df is None:
            potential_df = self._get_potential_df(
                plugin_name="lammps",
                file_name_lst={"potentials_lammps.csv"},
                backward_compatibility_name="lammpspotentials",
            )
        super(LammpsPotentialFile, self).__init__(
            potential_df=potential_df,
            default_df=default_df,
            selected_atoms=selected_atoms,
        )

    def default(self):
        if self._default_df is not None:
            atoms_str = "_".join(sorted(self._selected_atoms))
            return self._default_df[
                (self._default_df["Name"] == self._default_df.loc[atoms_str].values[0])
            ]
        return None

    def find_default(self, element):
        """
        Find the potentials

        Args:
            element (set, str): element or set of elements for which you want the possible LAMMPS potentials
            path (bool): choose whether to return the full path to the potential or just the potential name

        Returns:
            list: of possible potentials for the element or the combination of elements

        """
        if isinstance(element, set):
            element = element
        elif isinstance(element, list):
            element = set(element)
        elif isinstance(element, str):
            element = set([element])
        else:
            raise TypeError("Only, str, list and set supported!")
        element_lst = list(element)
        if self._default_df is not None:
            merged_lst = list(set(self._selected_atoms + element_lst))
            atoms_str = "_".join(sorted(merged_lst))
            return self._default_df[
                (self._default_df["Name"] == self._default_df.loc[atoms_str].values[0])
            ]
        return None

    def __getitem__(self, item):
        potential_df = self.find(element=item)
        selected_atoms = self._selected_atoms + [item]
        return LammpsPotentialFile(
            potential_df=potential_df,
            default_df=self._default_df,
            selected_atoms=selected_atoms,
        )


class PotentialAvailable(object):
    def __init__(self, list_of_potentials):
        self._list_of_potentials = list_of_potentials

    def __getattr__(self, name):
        if name in self._list_of_potentials:
            return name
        else:
            raise AttributeError

    def __dir__(self):
        return self._list_of_potentials

    def __repr__(self):
        return str(dir(self))
