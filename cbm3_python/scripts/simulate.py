# Copyright (C) Her Majesty the Queen in Right of Canada,
#  as represented by the Minister of Natural Resources Canada

import os
import json
import argparse
import datetime
import logging
import cbm3_python.simulation.projectsimulator as projectsimulator
from cbm3_python import toolbox_defaults
from cbm3_python.util import loghelper


def main():
    try:
        logpath = os.path.join(
            "{0}_{1}.log".format(
                "simulation",
                datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")))
        loghelper.start_logging(logpath, 'w+')

        parser = argparse.ArgumentParser(
            description="CBM-CFS3 simulation script. Simulates a CBM-CFS3 "
                        "project access database by automating functions in "
                        "the Operational-Scale CBM-CFS3 toolbox")

        parser.add_argument(
            "project_path",
            help="path to a cbm project database file")
        parser.add_argument(
            "--project_simulation_id",
            help="integer id for the simulation scenario to run in the "
                 "project (tblSimulation.SimulationID). If not specified "
                 "the highest numeric SimulationID is used.")
        parser.add_argument(
            "--n_timesteps",
            help="the number of timesteps to run the specified project. "
                 "If not specified the value in tblRunTableDetails will be "
                 "used.")
        parser.add_argument(
            "--aidb_path",
            help="path to a CBM-CFS3 archive index database. If unspecified a "
                 "typical default value is used.")
        parser.add_argument(
            "--toolbox_installation_dir",
            help="the Operational-Scale CBM-CFS3 toolbox installation "
                 "directory. If unspecified a typical default value is used.")
        parser.add_argument(
            "--cbm_exe_path",
            help="directory containing CBM.exe and Makelist.exe. If "
                 "unspecified a typical default value is used.")
        parser.add_argument(
            "--results_database_path",
            help="optional file path into which CBM results will be loaded."
                 "if unspecified a default value is used.")
        parser.add_argument(
            "--tempfiles_output_dir",
            help="optional directory where CBM tempfiles will be copied "
                 "after simulation.  If unspecified a default directory is "
                 "used.")
        parser.add_argument(
            "--skip_makelist",
            action="store_true",
            help="If set then skip running makelist. Useful for "
                 "afforestation only projects and for re-using existing "
                 "makelist results.")
        parser.add_argument(
            "--use_existing_makelist_output",
            action="store_true",
            help="if set the existing values in the project "
                 "database will be used in place of a new set of values"
                 "generated by the makelist executable.")
        parser.add_argument(
            "--copy_makelist_results",
            nargs="?", const=True, default=False,
            help="If present makelist *svl output is directly copied from the "
                 "makelist output dir to the cbm input dir rather than using "
                 "the toolbox load svl and dump svl procedures. If specified "
                 "with a directory, the makelist output files in the "
                 "specified directory will be copied to the CBM input "
                 "directory")
        parser.add_argument(
            "--stdout_path",
            help="optionally redirect makelist and CBM standard output to "
                 "the specified file. If unspecified standard out is directed "
                 "to the console window")
        parser.add_argument(
            "--dist_classes_path",
            help="one of a pair of optional file paths used to configure "
                 "extended kf6 accounting")
        parser.add_argument(
            "--dist_rules_path",
            help="one of a pair of optional file paths used to configure "
                 "extended kf6 accounting")
        parser.add_argument(
            "--loader_settings",
            help="An optional json formatted string indicating settings for "
                 "loading CBM results. If omitted the CBM-Toolbox built-in "
                 "loader is used.")

        args = parser.parse_args()

        toolbox_installation_dir = \
            toolbox_defaults.get_install_path() \
            if not args.toolbox_installation_dir \
            else os.path.abspath(args.toolbox_installation_dir)

        aidb_path = \
            toolbox_defaults.get_archive_index_path() \
            if not args.aidb_path else os.path.abspath(args.aidb_path)

        project_path = os.path.abspath(args.project_path)

        cbm_exe_path = \
            toolbox_defaults.get_cbm_executable_dir() \
            if not args.cbm_exe_path else os.path.abspath(args.cbm_exe_path)

        results_database_path = None if not args.results_database_path else \
            os.path.abspath(args.results_database_path)

        tempfiles_output_dir = None if not args.tempfiles_output_dir else \
            os.path.abspath(args.tempfiles_output_dir)

        stdout_path = \
            None if not args.stdout_path \
            else os.path.abspath(args.stdout_path)

        dist_classes_path = \
            None if not args.dist_classes_path \
            else os.path.abspath(args.dist_classes_path)

        dist_rules_path = \
            None if not args.dist_rules_path \
            else os.path.abspath(args.dist_rules_path)

        loader_settings = \
            None if not args.loader_settings \
            else json.loads(args.loader_settings)

        results_path = projectsimulator.run(
            project_path=project_path,
            project_simulation_id=args.project_simulation_id,
            n_timesteps=args.n_timesteps,
            aidb_path=aidb_path,
            toolbox_installation_dir=toolbox_installation_dir,
            cbm_exe_path=cbm_exe_path,
            results_database_path=results_database_path,
            tempfiles_output_dir=tempfiles_output_dir,
            skip_makelist=args.skip_makelist,
            stdout_path=stdout_path,
            use_existing_makelist_output=args.use_existing_makelist_output,
            copy_makelist_results=args.copy_makelist_results,
            dist_classes_path=dist_classes_path,
            dist_rules_path=dist_rules_path,
            loader_settings=loader_settings)
        logging.info("simulation finish, results path: {0}"
                     .format(results_path))

    except Exception:
        logging.exception("")


if __name__ == '__main__':
    main()
