# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.

import numpy as np
from pyiron.atomistics.master.murnaghan import Murnaghan

__author__ = "Jan Janssen"
__copyright__ = "Copyright 2017, Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department"
__version__ = "1.0"
__maintainer__ = "Jan Janssen"
__email__ = "janssen@mpie.de"
__status__ = "production"
__date__ = "Sep 1, 2017"


class MurnaghanInt(Murnaghan):
    def run_if_interactive(self):
        self.ref_job_initialize()
        self.ref_job.master_id = self.job_id
        self.ref_job.server.run_mode.interactive = True
        for strain in self._job_generator.parameter_list:
            self.ref_job = self._job_generator.modify_job(job=self.ref_job, parameter=strain)
            self.ref_job.run()

        self.ref_job.interactive_close()
        self.status.collect = True
        self.run()

    def ref_job_initialize(self):
        if len(self._job_list) > 0:
            self._ref_job = self.pop(-1)
            if self._job_id is not None and self._ref_job._master_id is None:
                self._ref_job.master_id = self.job_id

    def collect_output(self):
        if self.server.run_mode.interactive:
            ham = self.project_hdf5.inspect(self.child_ids[0])
            erg_lst = ham["output/generic/energy_tot"]
            vol_lst = ham["output/generic/volume"]
            arg_lst = np.argsort(vol_lst)

            self._output["volume"] = vol_lst[arg_lst]
            self._output["energy"] = erg_lst[arg_lst]

            with self.project_hdf5.open("output") as hdf5_out:
                for key, val in self._output.items():
                    hdf5_out[key] = val

            self.fit_murnaghan(self.input['fit_order'])
        else:
            super(MurnaghanInt, self).collect_output()
