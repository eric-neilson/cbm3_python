import csv, os, sys, json, argparse, datetime, logging
from analyse_report_fil import *
from util import loghelper

sys.path.append('../')

def load_json(path):
    with open(path, 'r') as f:
        return json.loads(f.read())

def mine_report_fils(config, project_prefixes):
    mined_report_fil_paths = {}
    for p in project_prefixes:
        inpath = config["report_fil_path_format"].format(project_prefix=p)
        outpath =  config["mined_report_fil_path_format"].format(project_prefix=p)

        with open(inpath, 'r') as infile, \
             open(outpath, 'w') as outfile:
            logging.info("{0}: reading cbm report.fil '{1}'".format(p, inpath))
            analyse_report_fil(
                inputFile=infile,
                outputFile=outfile,
                delimiter=",")
            mined_report_fil_paths[p] = outpath
    return mined_report_fil_paths

def load_report_fil_data(mined_report_fil_paths):
    data = []

    for k,v in mined_report_fil_paths.items():
        with open(v) as csvfile:
            logging.info("{0}: loading cbm report.fil '{1}'".format(k, v))
            reader = csv.DictReader(csvfile)
            project_data = list(reader)
            for row in project_data:
                row["project"] = k
            data.extend(project_data)
    return data

def index_rows(data):
    grouped_data = {}
    logging.info("indexing rows")
    for row in data:
        default_dist_type = int(row["Default Disturbance Type"])
        if default_dist_type != 4:
            continue
        disturbance_group = (row["project"],int(row["Disturbance Group"])) #composite key (project,disturbance group)
        year = int(row["Year"])
        if disturbance_group in grouped_data:
            grouped_data[disturbance_group][year] = row
        else:
            grouped_data[disturbance_group] = {year: row}
    return grouped_data

def identify_inadequate_disturbance_groups(grouped_data):

    inadequate_dist_groups = []
    inadequate_dist_group_keys = set([])
    for k,v in grouped_data.items():
        timesteps = sorted(v.keys())
        for t in timesteps:
            if float(v[t]["Surplus Biomass C"]) < 1e-10 or float(v[t]["Biomass C Prop'n"]) > 1.0:
                inadequate_dist_groups.append({"disturbance_group": k, "shortfall_year": t})
                inadequate_dist_group_keys.add(k)
                logging.info("project {0} disturbance group {1} has harvest shortfall".format(k[0],k[1]))
                break;
    return inadequate_dist_group_keys, inadequate_dist_groups

def compute_cumulative_shortfalls(inadequate_dist_groups, grouped_data):
    for d in inadequate_dist_groups:
        dist_group = d["disturbance_group"]
        timesteps = sorted([x for x in grouped_data[dist_group].keys() if x >= d["shortfall_year"]])
        cumulative_shorfall = 0
        for t in timesteps:
            cumulative_shorfall += float(grouped_data[dist_group][t]["Target Biomass C"])
        logging.info("project {0} disturbance group {1} cumulative shortfall: {2}"
                     .format(dist_group[0],dist_group[1],cumulative_shorfall))
        d["cumulative_shortfall"] = cumulative_shorfall

def identify_adequate_groups(first_projection_year, grouped_data, inadequate_dist_group_keys):
    adequate_dist_groups = []
    for k,v in grouped_data.items():
        if k in inadequate_dist_group_keys:
            continue
        last_timestep = sorted(v.keys())[-1]
        d_g = {"disturbance_group": k, "end_surplus": float(v[last_timestep]["Surplus Biomass C"])}
        projection_years = [year for year in sorted(v.keys()) if year >= first_projection_year]
        d_g["total_projection_target"] = sum([float(v[x]["Target Biomass C"]) for x in projection_years])
        d_g["incoming_harvest_shifts"] = []
        adequate_dist_groups.append(d_g)
        logging.info("project {0} disturbance group {1} biomass surplus: {2}"
                     .format(k[0],k[1],d_g["end_surplus"]))
    return adequate_dist_groups

def reduce_harvest_targets(inadequate_dist_groups, error_margin, first_projection_year, grouped_data):
    for d in inadequate_dist_groups:
        dist_group = d["disturbance_group"]
        harvest_shift = d["cumulative_shortfall"] * (1.0 + error_margin/100.0)
    
        projection_years = [year for year in sorted(grouped_data[dist_group].keys()) if year >= first_projection_year]
        total_projection_target = sum([float(grouped_data[dist_group][year]["Target Biomass C"]) for year in projection_years])
        #new harvest target is the sum of the projection target for all years less the reduction
        new_harvest_target = total_projection_target - harvest_shift
        harvest_proportion = new_harvest_target/total_projection_target
        d["harvest_shift"] = harvest_shift
        d["harvest_proportion"] = harvest_proportion

def allocate_reduced_harvest(inadequate_dist_groups, adequate_dist_groups):
    adequate_dist_group_sum = sum([g["end_surplus"] for g in adequate_dist_groups])
    
    for d_i in inadequate_dist_groups:
        for d_a in adequate_dist_groups:
            weight = d_a["end_surplus"] / adequate_dist_group_sum
            shift = d_i["harvest_shift"] * weight
            d_a["incoming_harvest_shifts"].append(shift)

def compute_new_harvest_proportions(adequate_dist_groups):
    for d_a in adequate_dist_groups:
        new_target = d_a["total_projection_target"] + sum(d_a["incoming_harvest_shifts"])
        new_proportion = new_target / d_a["total_projection_target"]
        d_a["harvest_proportion"] = new_proportion

def write_results(adequate_dist_groups, output_file_path, disturbance_group_spugroup_map):
    with open(output_file_path, 'wb') as csvfile:
        writer = csv.writer(csvfile)
    
        get_project_prefix = lambda x: x["disturbance_group"][0]
        get_spugroup = lambda x: disturbance_group_spugroup_map[get_project_prefix(x)][str(x["disturbance_group"][1])]
        get_harvest_proportion = lambda x: x["harvest_proportion"]
    
        rows = [
            [
                get_project_prefix(x),
                get_spugroup(x),
                get_harvest_proportion(x)
            ] for x in adequate_dist_groups]
        rows.extend([
            [
                get_project_prefix(x),
                get_spugroup(x),
                get_harvest_proportion(x)
            ] for x in inadequate_dist_groups])
        rows.sort(key=lambda x: (x[0],x[1]))
        for r in rows:
            writer.writerow(r)

def run_harvest_reallocator(config_path):
    config = load_json(config_path)
    error_margin = config["error_margin_percent"]
    first_projection_year = config["first_projection_year"]

    project_prefixes = config["project_prefixes"]
    output_file_path = config["output_file_path"]
    mined_report_fil_paths = {}

    disturbance_group_spugroup_map = config["disturbance_group_spugroup_map"]

    #0 mine report.fils
    mined_report_fil_paths = mine_report_fils(config, project_prefixes)

    #1. load the mined report.fil data
    data = load_report_fil_data(mined_report_fil_paths)

    #1a. index rows by disturbance group and year, reject rows that dont have default dist type 4
    grouped_data = index_rows(data)

    #2. identify disturbance groups with inadequate biomass for future harvest projection along with the first year at which the shortfall occurs
    inadequate_dist_group_keys, inadequate_dist_groups = identify_inadequate_disturbance_groups(grouped_data)

    #3. compute the cumulative shortfall for each identified inadequate group
    compute_cumulative_shortfalls(inadequate_dist_groups, grouped_data)

    #4. identify the adequate groups by finding the final simulation point surplus for those disturbance groups that have remaining biomass
    adequate_dist_groups = identify_adequate_groups(first_projection_year, grouped_data, inadequate_dist_group_keys)

    #5. reduce the inadequate group's harvest target by the cumulative shortfall + error margin (distributed evenly across projection years)
    reduce_harvest_targets(inadequate_dist_groups, error_margin, first_projection_year, grouped_data)

    #6. allocate the amount reduced first weighted by the remaining biomass, then distributed across projection years to the adequate groups
    allocate_reduced_harvest(inadequate_dist_groups, adequate_dist_groups)
    
    #7. compute the new harvest proportions for the adequate groups
    compute_new_harvest_proportions(adequate_dist_groups)

    #8 write out the results
    write_results(adequate_dist_groups, output_file_path, disturbance_group_spugroup_map)

def main():
    try:
        parser = argparse.ArgumentParser(description="projected harvest reallocator")
        parser.add_argument("--configuration", help="path to json config file")
        args = parser.parse_args()
        
        logpath = os.path.join( os.getcwd(), "harvest_shortfall_allocator_{}.log".format(
            datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")))
        loghelper.start_logging(logpath, 'w+')
        run_harvest_reallocator(args.configuration)

    except Exception as ex:
        logging.exception("")
if __name__ == '__main__':
    main()