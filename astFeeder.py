# This program feeds the various packets of asts to the history extractor in a
# multithreaded way. This is used for creating the massive amount of histories
# for training.

import glob, os
import extract_histories
import multiprocessing
import time
import CustomExceptions
from multiprocessing import Pool, Process, Queue
from threading import Lock

# Only to switch between handling the training or the testing file
switch = "training"
# Path to the resultfolder of astDevider.py wich is a folder with one smaller ast file per project.
pathToData = "/home/pa/SharedData/FullData/" + switch + "/"


def feed(queue, jsonFiles):
    ''' Feeds the jsonFiles as input into the pipeline time after time

    Input:
        queue:      The input queue used by the extractor
        jsonFiles:  All the jsonFiles to process
    '''
    global sizeInputqueue
    for file in jsonFiles:
        try:
            queue.put(file)
            sizeInputqueue += 1
        except e as Exception:
            time.sleep(5)
            continue
    print ("Feeder-Thread terminated")



def extract(queueIn, queueOut):
    ''' Extracts the histories and passes the results to the storing thread.

    Input:
        queueIn:    Input coming from the feed
        queueOut:   Output going to the store function
    '''

    # For all Files
    while True:
        try:
            fileName = queueIn.get(block=False)

        except:
            time.sleep(5)
            continue

        try:
            print("Extracting " + fileName)
            result = (None, None, None)  # 0: Filename; 1: "hist, err ; 2: result

            # Try to extract the histories and give result to storing
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

        except Exception as e:
            continue

    print("Extraction-Thread terminated!")



def store(queue, placeholder):
    ''' Taking the output from the extraction and write it to files

    Input:
        queue:          Queue with the output from the extraction
        (placeholder:    Only necesary because it has to be a tuple in line 177.)
    '''


    # Prepare the targets
    projectsStatusFile = open("ProjectsStatus.txt", "w+")
    completeHistoryFile = open("Histories.hist", "w+")

    # Store until all files processed
    counter = 0
    while counter < OverallAmountOfFiles:
        try:
            fileName, type, histAndVars = queue.get(block=False)
        except:
            time.sleep(1)
            continue
        print("Storing "+ str(counter) + " :  " + fileName)

        try:
            # When extraction was successfull
            if type == "hist":
                hist = histAndVars[0]
                vars = histAndVars[1:]
                completeHistoryFile.write(hist + "\n")
                projectsStatusFile.write("OK       : " + fileName + "\n")

                # Create a separate file for history
                file = open(pathToData + fileName[:-5] + ".hist", "w+")
                file.write(hist)
                file.close()

                # Create a separate file for usage of variables
                file = open(pathToData + fileName[:-5] + ".env", "w+")
                for vartype in vars:
                    for classname in vartype:
                        if classname != None:
                            file.write(classname + " ")
                    file.write("\n")
                file.close()

            # Else only write status message
            else:
                projectsStatusFile.write(histAndVars + ": " + fileName + "\n")
        except Exception as e:
            pass
        counter += 1

    projectsStatusFile.close()
    completeHistoryFile.close()
    print("Storing-Thread terminated!")





if __name__ == "__main__":
    '''
    Set up the history generation in a multithreaded way. The folder is traversed and each json file
    is passed to a pipeline, driving the history_extrator.
    '''

    # Counters for debugging
    OverallAmountOfFiles = 0
    sizeInputqueue = 0
    globCounter = 0
    lock = Lock()

    prefixList1 = ["a"]
    prefixList2 = ["b"]
    prefixList3 = ["c", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    prefixList4 = ["d", "e", "f", "g", "h", ]
    prefixList5 = ["i", "j", "k"]
    prefixList6 = ["l", "m"]
    prefixList7 = ["n", "o", "p", "q", "r"]
    prefixList8 = ["s"]
    prefixList9 = ["t", "u", "v", "w", "x", "y", "z"]

    prefixRemaining = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "a", "b", "c", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "d", "e", "f", "g", "h", "i"]

    # Create list of the interesting files
    jsonFiles = []
    for fileName in os.listdir(pathToData):
        if fileName.endswith(".json") and fileName[0].lower() in ["j"]:
            jsonFiles.append(fileName)
    OverallAmountOfFiles = len(jsonFiles)


    # Create a pipeline
    nthreads = multiprocessing.cpu_count()
    nthreads = nthreads if nthreads > 1 else 2 # Make possible for single core machines
    workerQueue = Queue(10000)
    writerQueue = Queue(10000)
    feedProc = Process(target=feed, args=(workerQueue, jsonFiles))
    # Keep one core for writing
    calcProc = [Process(target=extract, args=(workerQueue, writerQueue)) for i in range(nthreads)]
    writProc = Process(target=store, args=(writerQueue, "placeholder"))
    
    # Start the pipeline
    start = time.time()
    feedProc.start()
    for p in calcProc:
        p.start()
    writProc.start()

    # Make sure that everything runs through (extractor must be also finished when writProc is finished.
    feedProc.join()
    writProc.join()

    print(time.time() - start)
    print("FINISHED!")