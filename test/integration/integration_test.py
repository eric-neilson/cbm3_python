import os
import shutil
import tempfile
import unittest
from cbm3_python.cbm3data import sit_helper
import pandas as pd
from cbm3_python.cbm3data.accessdb import AccessDB
from cbm3_python.simulation import projectsimulator
from cbm3_python.cbm3data import cbm3_results
def get_db_table_names():
    return dict(
        age_class_table_name="sit_age_classes",
        classifiers_table_name="sit_classifiers",
        disturbance_events_table_name="sit_events",
        disturbance_types_table_name="sit_disturbance_types",
        inventory_table_name="sit_inventory",
        transition_rules_table_name="sit_transitions",
        yield_table_name="sit_yield")


def import_delimited(working_dir, mapping_file_path, sit_import_method):
    imported_project_path = os.path.join(
        working_dir, "cbm3_project.mdb")
    shutil.copy(
        mapping_file_path,
        os.path.join(working_dir, os.path.basename(mapping_file_path)))
    sit_import_method(
        working_dir, imported_project_path,
        initialize_mapping=False,
        archive_index_db_path=None,
        working_dir=working_dir,
        toolbox_install_dir=None)
    return imported_project_path


def import_mdb_xls(working_dir, sit_mdb_path, mapping_file_path, xls=False):

    imported_project_path = os.path.join(
        working_dir, "cbm3_project.mdb")

    import_args = dict(
        mdb_xls_path=sit_mdb_path,
        imported_project_path=imported_project_path,
        mapping_path=mapping_file_path,
        initialize_mapping=False,
        archive_index_db_path=None,
        working_dir=working_dir,
        toolbox_install_dir=None)

    table_names = get_db_table_names()
    if xls:
        table_names = {k: f"{v}$" for k, v in table_names.items()}
    import_args.update(table_names)

    sit_helper.mdb_xls_import(**import_args)
    return imported_project_path


def as_data_frame(query, access_db_path):
    with AccessDB(access_db_path) as access_db:
        df = pd.read_sql(query, access_db.connection)
    return df


def mdb_to_delimited(sit_mdb_path, ext, output_dir):
    if ext == ".tab":
        sep = "\t"
    elif ext == ".csv":
        sep = ","
    else:
        raise ValueError()
    for k, v in get_db_table_names().items():
        df = as_data_frame(f"SELECT * FROM {v}", sit_mdb_path)
        df.to_csv(os.path.join(output_dir, f"{v}{ext}"), sep=sep, index=False)


class IntegrationTests(unittest.TestCase):

    def test_integration(self):
        this_dir = os.path.dirname(os.path.realpath(__file__))
        mapping_file_path = os.path.join(this_dir, "mapping.json")
        sit_mdb_path = os.path.join(this_dir, "cbm3_sit.mdb")
        sit_xls_path = os.path.join(this_dir, "cbm3_sit.xls")
        with tempfile.TemporaryDirectory() as tempdir:

            mdb_working_dir = os.path.join(tempdir, "mdb")
            os.makedirs(mdb_working_dir)
            mdb_project = import_mdb_xls(
                mdb_working_dir, sit_mdb_path, mapping_file_path)

            xls_working_dir = os.path.join(tempdir, "xls")
            os.makedirs(xls_working_dir)
            xls_project = import_mdb_xls(
                xls_working_dir,
                sit_xls_path,
                mapping_file_path, xls=True)

            csv_working_dir = os.path.join(tempdir, "csv")
            os.makedirs(csv_working_dir)
            mdb_to_delimited(sit_mdb_path, ".csv", csv_working_dir)
            csv_project = import_delimited(
                csv_working_dir, mapping_file_path, sit_helper.csv_import)

            tab_working_dir = os.path.join(tempdir, "tab")
            os.makedirs(tab_working_dir)
            mdb_to_delimited(sit_mdb_path, ".tab", tab_working_dir)
            tab_project = import_delimited(
                tab_working_dir, mapping_file_path, sit_helper.tab_import)

            mdb_results = projectsimulator.run(mdb_project)
            xls_results = projectsimulator.run(xls_project)
            csv_results = projectsimulator.run(csv_project)
            tab_results = projectsimulator.run(tab_project)

            mdb_pools = cbm3_results.load_pool_indicators(mdb_results)
            xls_pools = cbm3_results.load_pool_indicators(xls_results)
            csv_pools = cbm3_results.load_pool_indicators(csv_results)
            tab_pools = cbm3_results.load_pool_indicators(tab_results)

            # double check the results are not empty
            self.assertFalse(mdb_pools.empty)
            self.assertTrue(mdb_pools.equals(xls_pools))
            self.assertTrue(mdb_pools.equals(csv_pools))
            self.assertTrue(mdb_pools.equals(tab_pools))
