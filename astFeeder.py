# This program feeds the various packets of asts to the history extractor in a
# multithreaded way.
import glob, os
import extract_histories
import multiprocessing
import time
import CustomExceptions
from multiprocessing import Pool, Process, Queue


switch = "eval"
pathToData = "/home/pa/SharedData/FullData/" + switch + "/"
OverallAmountOfFiles = 10000


def feed(queue, jsonFiles):
    for file in jsonFiles:
        queue.put(file)


def extract(queueIn, queueOut):
    while True:
        try:
            fileName = queueIn.get(block=False)
        except:
            break

        print("Extracting " + fileName)
        result = (None, None, None)  # 0: Filename; 1: "hist, err ; 2: result

        # Try to extract the histories
        try:
            historyAndVars = extract_histories.extract_histories(pathToData + fileName)
            result = (fileName, "hist", historyAndVars)
        except CustomExceptions.CallgraphException as e:
            print("Callgraph error in " + fileName)
            result = (fileName, "err", "Callgraph")
        except CustomExceptions.MappingException as e:
            print("Mapping error in " + fileName)
            result = (fileName + str(e.args[0]), "err", "Mapping  ")
        except Exception as e:
            print("History error in " + fileName)
            result = (fileName, "err", "Histories")
        queueOut.put(result)


def store(queue, test):
    '''
    This last step is taking care of the string
    '''

    # Prepare the targets
    projectsStatusFile = open("ProjectsStatus.txt", "w+")
    completeHistoryFile = open("Histories.hist", "w+")
    i = 0
    time.sleep(10)
    while i < OverallAmountOfFiles:
        try:
            fileName, type, histAndVars = queue.get(block=False)
        except:
            time.sleep(10)
            continue

        print("Storing " + fileName)

        # When successfull
        if type == "hist":
            hist = histAndVars[0]
            vars = histAndVars[1:]
            completeHistoryFile.write(hist + "\n")
            projectsStatusFile.write("OK       : " + fileName + "\n")

            # Create a dedicated file for history
            file = open(pathToData + fileName[:-5] + ".hist", "w+")
            file.write(hist)
            file.close()

            # Create a dedicated file for usage
            file = open(pathToData + fileName[:-5] + ".env", "w+")
            for vartype in vars:
                for classname in vartype:
                    file.write(classname + " ")
                file.write("\n")
            file.close()
        # Else only write status message
        else:
            projectsStatusFile.write(histAndVars + ": " + fileName + "\n")
        i += 1

    projectsStatusFile.close()
    completeHistoryFile.close()


if __name__ == "__main__":
    '''
    Set up the history generation in a multithreaded way. The folder is traversed and each json file
    is passed to history_extrator.
    '''

    # Create list of the interesting files
    jsonFiles = []
    prefixList = ["d", "e", "f", "g", "h", "i", "j", "k", "l"]
    for fileName in os.listdir(pathToData):
        if fileName.endswith(".json") and fileName[0] in prefixList: #fileName.startswith("dachcom-digital"):
            jsonFiles.append(fileName)
    OverallAmountOfFiles = len(jsonFiles)

    # Handle all the files
    nthreads = multiprocessing.cpu_count()
    workerQueue = Queue()
    writerQueue = Queue()
    feedProc = Process(target=feed, args=(workerQueue, jsonFiles))
    calcProc = [Process(target=extract, args=(workerQueue, writerQueue)) for i in range(1)]
    writProc = Process(target=store, args=(writerQueue, "test"))

    start = time.time()
    # Fill the pipeline first
    feedProc.start()
    feedProc.join()

    # Start the pipeline
    for p in calcProc:
        p.start()
    writProc.start()

    # Make sure that everything ran through
    for p in calcProc:
        p.join()
    writProc.join()

    print("FINISHED!")
    print(time.time() - start)