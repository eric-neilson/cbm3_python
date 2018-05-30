import os, shutil, glob, logging, multiprocessing, subprocess
from simulator import Simulator
from cbm3data.aidb import AIDB
from cbm3data.projectdb import ProjectDB
from simulation.resultsloader import ResultsLoader
from simulation.createaccountingrules import CreateAccountingRules

def externalExeWorker(executablePath):
    wd = os.getcwd()
    os.chdir(os.path.dirname(executablePath))
    cmd = '"'  + executablePath + '" '
    with open(os.devnull, 'w') as FNULL:
        subprocess.check_call(cmd, stdout=FNULL, stderr=FNULL)
    os.chdir(wd)

def loaderWorker(params):
    loader = ResultsLoader()
    loader.loadResults(
        params["templateDBPath"], 
        params["outputDBPath"], 
        params["aidbPath"], 
        params["projectDBPath"], 
        params["projectSimulationDirectory"])

class BatchRunner(object):
    def __init__(self, projectPath, toolboxPath, batchRunDir, 
                 aidbPath, cbmDir, outputDir, numProcesses, 
                 scenarioMin, scenarioMax, dist_classes_path, 
                 dist_rules_path):

        self.__validateArgs(projectPath, toolboxPath, batchRunDir, 
                 aidbPath, cbmDir, outputDir, numProcesses, 
                 scenarioMin, scenarioMax, dist_classes_path, 
                 dist_rules_path)
        self.toolboxPath = toolboxPath
        self.batchRunDir = batchRunDir
        self.outputDir = outputDir
        defaultAidbPath = os.path.join(toolboxPath, "Admin", "DBs", "ArchiveIndex_Beta_Install.mdb")
        if aidbPath.lower() != defaultAidbPath.lower():
            shutil.copy(aidbPath, defaultAidbPath)
        self.workingAidbPath = defaultAidbPath
        self.defaultWorkingDirectory = os.path.join(toolboxPath, "temp")
        self.cbmDir = cbmDir
        self.projectPath = projectPath
        self.numProcesses = numProcesses
        with AIDB(self.workingAidbPath, False) as aidb, \
             ProjectDB(projectPath, False) as proj:
            aidb.DeleteProjectsFromAIDB()
            self.projectDir = os.path.dirname(projectPath)
            self.simulationIds = aidb.AddProjectToAIDB(proj)
            self.simulationIds = self.simulationIds[(scenarioMin-1):scenarioMax]
            self.rrdbTemplate = os.path.join(os.path.dirname( __file__ ), "RRDB_Template.accdb")
            self.dist_classes_path = dist_classes_path
            self.dist_rules_path = dist_rules_path
            if not os.path.exists(batchRunDir):
                os.makedirs(batchRunDir)

    def __validateArgs(self, projectPath, toolboxPath, batchRunDir, 
                 aidbPath, cbmDir, outputDir, numProcesses, 
                 scenarioMin, scenarioMax, dist_classes_path, 
                 dist_rules_path):
        errors = []
        if not os.path.exists(projectPath): 
            errors.append("projectPath not found '{0}'".format(projectPath))
        elif not os.path.isfile(projectPath): 
                errors.append("projectPath is not a file '{0}'".format(projectPath))

        if not os.path.exists(toolboxPath):
            errors.append("toolboxPath not found '{0}'".format(toolboxPath))

        if not os.path.exists(aidbPath): 
            errors.append("aidbPath not found '{0}'".format(aidbPath))
        elif not os.path.isfile(aidbPath): 
                errors.append("aidbPath is not a file '{0}'".format(aidbPath))

        if not os.path.exists(cbmDir): 
            errors.append("cbmDir not found '{0}'".format(cbmDir))

        if not isinstance(scenarioMin, ( int, long )) or not isinstance(scenarioMax, ( int, long )):
            errors.append("scenarioMin and scenarioMax must be integers" )
        elif scenarioMin < 1 or scenarioMin > scenarioMax:
                errors.append("scenarioMin must be >= 1 and scenarioMax must be >= scenarioMin" )

        if not os.path.exists(dist_classes_path):
            errors.append("dist_classes_path not found '{0}'".format(dist_classes_path))

        if not os.path.exists(dist_rules_path):
            errors.append("dist_rules_path not found '{0}'".format(dist_rules_path))

        for error in errors:
            logging.error(error)
        
        if len(errors) > 0:
            raise ValueError("validation errors: {0}".format(errors))

    def Run(self):
        self.SerialCreateMakelistFiles(self.simulationIds)
        self.ParallelRunMakelist(self.simulationIds)
        self.CopyMakelistResultsToProjectDir(self.simulationIds)
        self.SerialCreateCBMFiles(self.simulationIds)
        self.ParallelRunCBM(self.simulationIds)
        self.CopyCBMResultsToProjectDir(self.simulationIds)
        self.ParallelLoadCBMResults(self.simulationIds)
        self.CopyResultsDBToProjectDir(self.simulationIds)
        self.copyResultsToOutputDir(self.simulationIds)
        self.CleanUpbatchRunDir()

    def CleanUpbatchRunDir(self):
        for s in os.listdir(self.batchRunDir):
            file_path = os.path.join(self.batchRunDir, s)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def GetWorkingPath(self, simulationId):
        return os.path.join(self.batchRunDir, str(simulationId))
        
    def SerialCreateMakelistFiles(self, simulationIds):
        logging.info("Creating Makelist Files")
        for simulationId in simulationIds:
            sim = Simulator(
                executablePath = self.cbmDir, 
                simID = simulationId, 
                projectPath = self.projectPath, 
                CBMRunDir = self.defaultWorkingDirectory, 
                toolboxPath = self.toolboxPath)
            sim.CleanupRunDirectory()
            sim.CreateMakelistFiles()
            workingPath = self.GetWorkingPath(simulationId)
            makelistWorkingPath = os.path.join(workingPath, "Makelist")
            logging.info(workingPath)
            if os.path.exists(makelistWorkingPath):
                #clean out any old results
                shutil.rmtree(makelistWorkingPath)
            shutil.copytree(
                os.path.join(self.defaultWorkingDirectory, "Makelist"),
                makelistWorkingPath)

    def ParallelRunMakelist(self, simulationIds):
        logging.info("Running makelist in parallel");
        makelistWorkingPaths = []
        for simulationId in simulationIds:
            makelistWorkingPath = os.path.join(
                self.GetWorkingPath(simulationId), 
                "Makelist", "Makelist.exe")
            makelistWorkingPaths.append(makelistWorkingPath)
            shutil.copy(os.path.join(self.cbmDir, "Makelist.exe"),
                makelistWorkingPath)
        try:
            p = multiprocessing.Pool(self.numProcesses)
            p.map(externalExeWorker, makelistWorkingPaths)
        finally:
            p.close()
            p.join()
    
    def CopyResultsDBToProjectDir(self, simulationIds):
        logging.info("copying results database to project dir")
        for simulationId in simulationIds:
            cbmResultsDir = os.path.join(self.projectDir, str(simulationId), "{0}.accdb".format(simulationId))
            cbmOutputPath = os.path.join(self.GetWorkingPath(simulationId), "{0}.accdb".format(simulationId))
            shutil.copy(cbmOutputPath, cbmResultsDir)

    def CopyCBMResultsToProjectDir(self, simulationIds):
        logging.info("copying cbm results to project dir")
        for simulationId in simulationIds:
            cbmResultsDir = os.path.join(self.projectDir, str(simulationId), "CBMRun")
            cbmOutputPath = os.path.join(self.GetWorkingPath(simulationId), "CBMRun")
            shutil.copytree(cbmOutputPath, cbmResultsDir)

    def CopyMakelistResultsToProjectDir(self, simulationIds):
        logging.info("copying makelist results to project dir")
        for simulationId in simulationIds:
            makelistResultsDir = os.path.join(self.projectDir, str(simulationId), "Makelist")
            makelistOutputPath = os.path.join(self.GetWorkingPath(simulationId), "Makelist")
            shutil.copytree(makelistOutputPath, makelistResultsDir)

    def CopyMakelistOutputToCBMInput(self, makelistOutputDir,cbmInputDir):
        logging.info("copying makelist output {0} to {1}".format(makelistOutputDir, cbmInputDir))
        for f in glob.iglob(os.path.join(makelistOutputDir, '*.ini')):
            shutil.copy2(f, cbmInputDir)

    def dropMakelistResultsFromProject(self):
        # cleans out old makelist results from the project copied to temp, and the original project
        # if we dont do this for every run it accumulates for all of the UC runs and gets too big
        paths = [os.path.join(self.defaultWorkingDirectory, os.path.basename(self.projectPath)),
                 self.projectPath]


        for p in paths:
            with ProjectDB(p, False) as proj:
                maxID = proj.GetMaxID("tblSVLAttributes", "SVOID")
                maxBatchDeleteSize = 10000
                iterations = maxID / maxBatchDeleteSize
                remainder = maxID % maxBatchDeleteSize
                for i in range(0, iterations):
                    min = i * maxBatchDeleteSize
                    max = min + maxBatchDeleteSize
                    proj.ExecuteQuery("DELETE FROM tblSVLAttributes WHERE tblSVLAttributes.SVOID Between {min} And {max};"
                                      .format(min=min, max=max))
    
                if remainder > 0:
                    min = iterations * maxBatchDeleteSize
                    max = iterations * maxBatchDeleteSize + remainder
                    proj.ExecuteQuery("DELETE FROM tblSVLAttributes WHERE tblSVLAttributes.SVOID Between {min} And {max};"
                                      .format(min=min, max=max))

    def SerialCreateCBMFiles(self, simulationIds):
        logging.info("creating CBM input");
        for simulationId in simulationIds:
            cbmRunDir = os.path.join(self.defaultWorkingDirectory, "CBMRun")
            if os.path.exists(cbmRunDir):
                shutil.rmtree(cbmRunDir)
            workingPath = self.GetWorkingPath(simulationId)
            logging.info(workingPath)
            sim = Simulator(
                executablePath = self.cbmDir, 
                simID = simulationId, 
                projectPath = self.projectPath, 
                CBMRunDir = self.defaultWorkingDirectory, 
                toolboxPath = self.toolboxPath)
            sim.CleanupRunDirectory()
            #copy project to temp dir, and copy makelist batch run dir to temp dir
            shutil.copy(self.projectPath, self.defaultWorkingDirectory)
            shutil.copytree(os.path.join(self.GetWorkingPath(simulationId), "Makelist"), 
                            os.path.join( self.defaultWorkingDirectory, "Makelist"))
            sim.loadMakelistSVLS()
            temp_proj_path = os.path.join(self.defaultWorkingDirectory, os.path.basename(self.projectPath))
            with ProjectDB(temp_proj_path, False) as temp_proj:
                cr = CreateAccountingRules(temp_proj, self.dist_classes_path, self.dist_rules_path)
                cr.create_accounting_rules()
                temp_proj.close()
                self.dropMakelistResultsFromProject()
                sim.CreateCBMFiles()
                makelistResultsDir = os.path.join(self.GetWorkingPath(simulationId), "Makelist", "output")
                self.CopyMakelistOutputToCBMInput(makelistResultsDir, os.path.join(cbmRunDir, "input"))
                workingCBMPath = os.path.join(workingPath, "CBMRun")
                if os.path.exists(workingCBMPath):
                    shutil.rmtree(workingCBMPath)
                shutil.copytree(cbmRunDir, workingCBMPath)

    def ParallelRunCBM(self, simulationIds):
        logging.info("Running cbm in parallel");
        cbmWorkingPaths = []
        for simulationId in simulationIds:
            simpath = self.GetWorkingPath(simulationId)
            cbmWorkingPath = os.path.join(simpath, "CBMRun", "CBM.exe")
            shutil.copy(os.path.join(self.cbmDir, "CBM.exe"),
                cbmWorkingPath)
            cbmWorkingPaths.append(cbmWorkingPath)
        try:
            p = multiprocessing.Pool(self.numProcesses)
            p.map(externalExeWorker, cbmWorkingPaths)
        finally:
            p.close()
            p.join()

    def ParallelLoadCBMResults(self, simulationIds):

        logging.info("Loading results in parallel")
        parameters = []
        for simulationId in simulationIds:
            parameters.append( 
            {
                "templateDBPath": self.rrdbTemplate,
                "outputDBPath": os.path.join(self.GetWorkingPath(simulationId), "{0}.accdb".format(str(simulationId))),
                "aidbPath": self.workingAidbPath,
                "projectDBPath": self.projectPath,
                "projectSimulationDirectory": os.path.join(self.GetWorkingPath(simulationId))
            })
        try:
            p = multiprocessing.Pool(self.numProcesses)
            p.map(loaderWorker, parameters) 
        finally:
            p.close()
            p.join()


    def copyResultsToOutputDir(self, simulationIds):
        logging.info("copying cbm results to output dir")
        for simulationId in simulationIds:
            finalResultsDir = os.path.join(self.outputDir, self.GetProjectName())
            if not os.path.exists(finalResultsDir):
                os.makedirs(finalResultsDir) 
            finalResultsPath = os.path.join(finalResultsDir, "{0}.accdb".format(simulationId))
            cbmOutputPath = os.path.join(self.GetWorkingPath(simulationId), "{0}.accdb".format(simulationId))
            shutil.copy(cbmOutputPath, finalResultsPath)



    def GetProjectName(self):
        return os.path.splitext(os.path.basename(self.projectPath))[0]

#set up logging to print to console window and to log file
def start_logging(fn=".\\script.log",fmode='w'):
    #
    # From http://docs.python.org/2/howto/logging-cookbook.html#logging-cookbook
    #
    rootLogger = logging.getLogger()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')
    rootLogger.removeHandler(rootLogger.handlers[0]) #remove the basic handler
    logFormatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%m-%d %H:%M')

    fileHandler = logging.FileHandler(fn, fmode)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    rootLogger.setLevel(logging.INFO)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-process CBM-CFS3 batch runner.  " +
                    "Can run projects that contain multiple simulation scenarios partially in parallel.  "+
                    "Requires installation of the Operational-Scale CBM-CFS3 toolbox")

    parser.add_argument("--projectPath", help = "path to a CBM-CFS3 project database", required=True)
    parser.add_argument("--outputPath", help = "directory where the simulation output will be written. This script will attempt to create it if it does not exist", required=True)
    parser.add_argument("--minID", help = "the inclusive minimum simulation ID to simulate. The simulation ids are defined in the project db table tblSimulation", required=True)
    parser.add_argument("--maxID", help = "the inclusive maximum simulation ID to simulate. The simulation ids are defined in the project db table tblSimulation", required=True)
    parser.add_argument("--dist_classes_path", help = "file path to the disturbance classes csv file used for extended accounting", required=True)
    parser.add_argument("--dist_rules_path", help = "file path to the disturbance classes csv file used for extended accounting", required=True)

    parser.add_argument("--aidb", help="the file path to the archive index database to use. If unspecified the default archive index is used", required=False)
    parser.add_argument("--exePath", help="the file path to a folder containing the CBM-CFS3 executables. If unspecified the default executables are used", required=False)
    
    args = vars(parser.parse_args())
    projectPath = args["projectPath"] 
    outputPath =  args["outputPath"] 
    minId = int(args["minID"])
    maxId = int(args["maxID"])
    dist_classes_path = args["dist_classes_path"]
    dist_rules_path = args["dist_rules_path"]
    aidb = args["aidb"] if "aidb" in args else r"C:\Program Files (x86)\Operational-Scale CBM-CFS3\Admin\DBs\ArchiveIndex_Beta_Install.mdb"
    exepath = args["exePath"] if "exePath" in args else r"C:\Program Files (x86)\Operational-Scale CBM-CFS3\Admin\Executables"

    if not os.path.exists(outputPath):
        os.makedirs(outputPath)

    logname = os.path.join(outputPath, "{0}.log".format(os.path.splitext(os.path.basename(projectPath))[0]))
    start_logging(logname)
    try:
        b = BatchRunner(projectPath, 
                        r"C:\Program Files (x86)\Operational-Scale CBM-CFS3",
                        r"C:\Program Files (x86)\Operational-Scale CBM-CFS3\batchruns",
                        aidb,
                        exepath,
                        outputPath,
                        multiprocessing.cpu_count(), 
                        minId, maxId,dist_classes_path, 
                        dist_rules_path)

        b.Run()
    except Exception as ex:
        logging.exception("error in batchrunner")
        raise ex