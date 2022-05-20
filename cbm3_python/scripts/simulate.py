# Copyright (C) Her Majesty the Queen in Right of Canada,
#  as represented by the Minister of Natural Resources Canada

import os
import sys
import json
import argparse
import datetime
import cbm3_python.simulation.projectsimulator as projectsimulator
from cbm3_python import toolbox_defaults
from cbm3_python.util import loghelper


def simulate_main(args):
    try:
        logpath = os.path.join(
            "{0}_{1}.log".format(
                "simulation",
                datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S"),
            )
        )
        loghelper.start_logging(logpath, "w+")

        parser = argparse.ArgumentParser(
            description="CBM-CFS3 simulation script. Simulates a CBM-CFS3 "
            "project access database by automating functions in "
            "the Operational-Scale CBM-CFS3 toolbox"
        )

        parser.add_argument(
            "project_path",
            type=os.path.abspath,
            help="path to a cbm project database file",
        )
        parser.add_argument(
            "--project_simulation_id",
            type=int,
            help="integer id for the simulation scenario to run in the "
            "project (tblSimulation.SimulationID). If not specified "
            "the highest numeric SimulationID is used.",
        )
        parser.add_argument(
            "--n_timesteps",
            type=int,
            help="the number of timesteps to run the specified project. "
            "If not specified the value in tblRunTableDetails will be "
            "used.",
        )
        parser.add_argument(
            "--aidb_path",
            nargs="?",
            default=toolbox_defaults.get_archive_index_path(),
            type=os.path.abspath,
            help="path to a CBM-CFS3 archive index database. If unspecified a "
            "typical default value is used.",
        )
        parser.add_argument(
            "--toolbox_installation_dir",
            nargs="?",
            default=toolbox_defaults.get_install_path(),
            type=os.path.abspath,
            help="the Operational-Scale CBM-CFS3 toolbox installation "
            "directory. If unspecified a typical default value is used.",
        )
        parser.add_argument(
            "--cbm_exe_path",
            nargs="?",
            default=toolbox_defaults.get_cbm_executable_dir(),
            type=os.path.abspath,
            help="directory containing CBM.exe and Makelist.exe. If "
            "unspecified a typical default value is used.",
        )
        parser.add_argument(
            "--results_database_path",
            type=os.path.abspath,
            help="optional file path into which CBM results will be loaded."
            "if unspecified a default value is used.",
        )
        parser.add_argument(
            "--tempfiles_output_dir",
            type=os.path.abspath,
            help="optional directory where CBM tempfiles will be copied "
            "after simulation.  If unspecified a default directory is "
            "used.",
        )
        parser.add_argument(
            "--skip_makelist",
            action="store_true",
            help="If set then skip running makelist. Useful for "
            "afforestation only projects and for re-using existing "
            "makelist results.",
        )
        parser.add_argument(
            "--use_existing_makelist_output",
            action="store_true",
            help="if set the existing values in the project "
            "database will be used in place of a new set of values"
            "generated by the makelist executable.",
        )
        parser.add_argument(
            "--copy_makelist_results",
            action="store_true",
            help="If present makelist *svl output is directly copied from the "
            "makelist output dir to the cbm input dir rather than using "
            "the toolbox load svl and dump svl procedures. If specified "
            "with a directory, the makelist output files in the "
            "specified directory will be copied to the CBM input "
            "directory",
        )
        parser.add_argument(
            "--stdout_path",
            type=os.path.abspath,
            help="optionally redirect makelist and CBM standard output to "
            "the specified file. If unspecified standard out is directed "
            "to the console window",
        )
        parser.add_argument(
            "--dist_classes_path",
            type=os.path.abspath,
            help="one of a pair of optional file paths used to configure "
            "extended kf6 accounting",
        )
        parser.add_argument(
            "--dist_rules_path",
            type=os.path.abspath,
            help="one of a pair of optional file paths used to configure "
            "extended kf6 accounting",
        )
        parser.add_argument(
            "--save_svl_by_timestep",
            action="store_true",
            help="if set the CBM executable will be configured to "
            "write out all stand database (SVLxxx.dat) files at the end "
            "of every time step.",
        )
        parser.add_argument(
            "--loader_settings",
            type=json.loads,
            help="An optional json formatted string indicating settings for "
            "loading CBM results. If omitted the CBM-Toolbox built-in "
            "loader is used.",
        )

        args = parser.parse_args(args=args)

        results_path = projectsimulator.run(**args.__dict__)
        loghelper.get_logger().info(
            f"simulation finish, results path: {results_path}"
        )

    except Exception:
        loghelper.get_logger().exception("")


def main():
    simulate_main(sys.argv[1:])


if __name__ == "__main__":
    main()
