# Preprocessing:
# This script devides the huge file with the asts into smaller files, one for each project in the base.
# The assignment of each ast to a project is done by exploiting the two "programs_ .txt" files.
import sys


# Define globally where to look for data (To not blow up the VM, the full dataset was stored on the host machine)
# The mounting instruction is still in the command history.
# In the mounted folder there were only the programs_eval.json (5.1GB), the programs_eval.txt (3.4MB),
# the programs_training.json (10.8GB) and the programs_training.txt (6.9MB)
pathToFullData = "/home/pa/SharedData/FullData"
# Only to switch between handling the training or the testing file.
switch = "training"





if __name__ == "__main__":
    '''
    This class is an additional script, that devides the huge file with all the ASTs into
    multiple files, one per folder. To do this, it takes the information out of the
    programs_ast.txt. an bee seen as kind of preprocessing.
    '''

    # Create a dictionary of which lines belong to which object
    fullPathFile = open(pathToFullData + "/programs_"+ switch + ".txt", "r")
    fullAstFile = open(pathToFullData + "/programs_"+ switch + ".json", "r", encoding='latin-1')
    projectDict = {}
    i = 0
    offset = 0
    for line in fullPathFile:
        projectName = line[5:line.find("/", 6)]
        if not projectName in projectDict:
            projectDict[projectName] = []
        projectDict[projectName].append((i, offset, line))
        i += 1
        # Remember the offset within the ast file to be capable to jump there later.
        offset += len(fullAstFile.readline())
        if i % 1000 == 0:
            print(i)

    # Go through all projects in the dictionary and create a file with the asts and one with the pathes for debugging.
    i = 0
    for projectName in projectDict:
        # Create one file per project
        pathFile = open(pathToFullData + "/" + switch + "/" + projectName + ".txt", "w+")
        astFile = open(pathToFullData + "/" + switch + "/" + projectName + ".json", "w+")
        for fileTuple in projectDict[projectName]:
            # Write one file per project with the filenames in it (for debugging)
            pathFile.write(fileTuple[2])

            # Write create the really necessary file per project with the ASTs in it
            fullAstFile.seek(fileTuple[1])
            curLine = fullAstFile.readline()
            astFile.write(curLine)

        pathFile.close()
        astFile.close()
        i += 1
        if i % 1000 == 0:
            print(i)

    print("Success")