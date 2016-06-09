import sys

pathToFullData = "/home/pa/SharedData/FullData"
switch = "eval"

if __name__ == "__main__":
    '''
    This class is an additional script, that devides the huge file with all the ASTs into
    multiple files, one per folder. To do this, it takes the information out of the
    programs_ast.txt
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
        offset += len(fullAstFile.readline())
        if i % 1000 == 0:
            print(i)

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
        if i == 1000:
            print(i)
            i = 0

    print("Success")