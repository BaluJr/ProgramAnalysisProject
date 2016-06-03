from __future__ import print_function
from subprocess import Popen, PIPE
import sys, getopt
import json
from State import State
from HistoryCollection import HistoryCollection



UseTestingCodejs = False


class history_extractor:

    def __init__(self, ast, callgraph):
        ''' Constructor immediatly sets ast and callgraph this extractor shall work on. 
        '''
        self.ast = ast
        self.callgraph = callgraph
        self.history = None
        self.outputHist = None
        self.nodeToObject = {}

    def generateHistories(self):
        ''' Creates the history for the ast and callgraph given during initialization
        No input and no return.
        '''
        state = State()
        hist = self._analyseStatement(0, state)
        self.history = hist
        self.outputHist = self.history.toOutputFormat(state)

        

    def getHistoryString(self, astObjects = None):
        ''' Returns the created history
        Depending on whether specific nodes are given as parameter or not 
        it gives a list of those histories or a list of otherwise a list
        off all histories for all regarded classes.

        Input:
            astObjects:     [optional] Specific nodes for which one wants to get
                            the history.

        Return:
            hist:           History in the output format defined in the paper.
        '''


        if astObjects == None:
            # If return histories for whole classes, cut away the object numbers
            outputString = ""
            for obj in self.outputHist:
                if obj.startswith("anonymous"):
                    continue

                classTag = "<" + obj.split("_")[0] + ">"
                for concreteTrace in self.outputHist[obj]:
                    #outputString += classTag
                    for event in concreteTrace:
                        outputString += "<" + ','.join([str(event[i]) for i in range(4)])  + ">"
                    outputString += "\n"
        else:
            outputString = ""
            for astObject in astObjects:
                treeId , nodeId = astObject.split("\t")
                # At the moment only nodeNumber is used. Handling multiple asts has to be done depending on how needed
                # for neural network
                obj = self.nodeToObject[int(nodeId)]

                startTag = "<" + treeId + "><" + nodeId + ">"
                for concreteTrace in self.outputHist[obj]:
                    outputString += startTag
                    for event in concreteTrace:
                        outputString += "<" + ','.join([str(event[i]) for i in range(4)]) + ">"
                    outputString += "\n"

        return outputString


    def _analyseStatement(self, astNumber, nodeNumber, state):
        ''' Analyses a single statment
        Executes a statement returning its history. A return value is not provided.
        Handling "return" is done by observing the special return-Element in the
        env after a function has run through.
        There is no return value -> This is handled differently: There is a special return value in "env"
        this can be then be read when the function call returns! 
        To handle the histories: A certain history is NOT extended if its last event 
        is ret with the function beeing the same element the special "context.functionName" points 
        to in the current context -> Handle recursive calls later! 
        In Statements (despite for the return statement), merging the HistorieCollections 
        returned by the Expressions is the only thing, that is done concerning histories.

        Input:
            nodeNumber:     The node in the AST to analyse
            env:            EnvironmentObject containing the local and global environment with the 
                            mapping from variables to (possibly abstract) objects
            heap:           The ObjectCollection object. Management of the objects and their fields

        Return:
            hist:           HistoryManager for this node
        '''
       
        ### Get Statement and type 
        curNode = self.ast[nodeNumber]
        t = curNode["type"]
            
        ### Analyse the Statements based on type
        if t == "ExpressionStatement":
            tmpHis, ret = self._analyseExpression(curNode["children"][0], state)
            return tmpHis
            
        elif t in ["Program","BlockStatement","WithStatement"]:
            if "children" in curNode:
                hist = HistoryCollection()
                for i in curNode["children"]:
                    tmpHist = self._analyseStatement(i, state) 
                    hist.addHistoryCollection(tmpHist)
                return hist       

        if t in ["EmptyStatement", "DebuggerStatement"]:
            return HistoryCollection()

        # Control Flow (ignore completly, TODO)
        if t in ["BreakStatement", "ContinueStatement"]:
            return HistoryCollection()
        elif t == "ReturnStatement": 
            # Extend the the "__return__" variable and add the "return" statement to the history.
            hist, ret = self._analyseExpression(curNode["children"][0],state)
            if ret:
                returnObject = state.getTarget(ret)
                state.env_set("__return__", returnObject)# Merging is done automatically
                hist.addEventToHistory(returnObject, state.functionName,"ret", state.functionName)
            return hist

        # Choice
        elif t == "IfStatement":
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("ic")
            thenState = state.copy()
            hist_then = self._analyseStatement(curNode["children"][1], thenState)
            # Check whether else is given
            if len(curNode["children"]) == 3:
                elseState = state.copy()
                hist_else = self._analyseStatement(curNode["children"][2], elseState)
                state.mergeIn([thenState,elseState])
                hist.addHistoriesConditional([hist_then,hist_else])
            else:
                hist.addHistoriesConditional([hist_then,HistoryCollection()])
                state.mergeIn([thenState])
            return hist

        elif t == "SwitchStatement":
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("sc")
            condHistories = []
            condStates = []
            preceedingCaseConditions = []
            for case in curNode["children"][1:]:
                condStates.append(state.copy())
                case = self.ast[case]
                innerHist = HistoryCollection()
                # Handle previous case conditions
                for precCaseCond in preceedingCaseConditions:
                    tmpHist, ret = self._analyseExpression(precCaseCond, condStates[-1])
                    innerHist.addHistoryCollection(tmpHist)
                # Handle current case
                isDefault = len(case["children"]) == 1
                if not isDefault:
                    preceedingCaseConditions.append(case["children"][0]);
                    tmpHist, ret = self._analyseExpression(case["children"][0], condStates[-1])
                    tmpHist.tagAsSpecialNode("cc")
                    innerHist.addHistoryCollection(tmpHist)
                    tmpHist = self._analyseStatement(case["children"][1], condStates[-1])
                    innerHist.addHistoryCollection(tmpHist)
                else:
                    # For default the statement is only child
                    tmpHist = self._analyseStatement(case["children"][0], condStates[-1])
                    innerHist.addHistoriesConditional(tmpHist)
                condHistories.append(innerHist)
            hist.addHistoriesConditional(condHistories)
            state.mergeIn(condStates)
            return hist
        
        # Exceptions (ignored at the moment)
        #ThrowStatement
        #TryStatement( CatchClause )
    
        # Loops
        elif t in ["WhileStatement", "DoWhileStatement"]:
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("wc")
            tmpHist = self._analyseStatement(curNode["children"][1], state)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist
        elif t in "ForStatements": # YEAH! The scope is acutally the same as everywhere!
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            tmpHist, ret = self._analyseExpression(curNode["children"][1], state)
            hist.addHistoryCollection(tmpHist)
            tmpHist, ret = self._analyseExpression(curNode["children"][2], state)
            hist.addHistoryCollection(tmpHist)
            hist.tagAsSpecialNode("fh")
            tmpHist = self._analyseStatement(curNode["children"][3], state)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist

        elif t == "ForInStatement": 
            # The scope is the same for the iterator name!
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("fh")
            
            # Since we do not handle loops, immediatly assign all elements within the returned enumerable (Whether array or object does not matter because both in heap)
            # TODO: the for in for an array only gives the indices!!!! NO IDEA HOW TO HANDLE -> maybe a special case
            tmpHist, ret =self._analyseExpression(curNode["children"][1], state)
            tmpHist.tagAsSpecialNode("fh")
            hist.addHistoryCollection(tmpHist)
            tmpHist = self._analyseStatement(curNode["children"][2], state)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist

        ### Declarations (handled here toghether with Declarators)
        elif t == "VariableDeclaration":
            # There might be multiple declarators as eg. "var a = 4, b = 5"
            for declarator in [self.ast[node] for node in curNode["children"]]:
                # Create the local variable
                state.env_createLocal(declarator["value"])
                if "children" in declarator:
                    hist, ret = self._analyseExpression(declarator["children"][0], state)
                    state.env_set(declarator["value"], ret)
                    return hist
                else:
                    return HistoryCollection()
        elif t == "FunctionDeclaration": 
            # Doing nothing since calls are handled by the callgraph
            return HistoryCollection()
        
        # For all other nodes, where no specific strategy has been assigned
        else:
            raise NameError('NodeName not handled')


                               
    def _analyseExpression(self, nodeNumber, state):
        ''' Analyses a single expression node. 
        In contrast to statements, expressions always have a return value.
        Expressions are the more interesting and difficult part since only 
        here instructions are really executed and histories get written.

        Input:
            nodeNumber:     The node in the AST to analyse
            state:          The state of the current execution (contains environment, heap, objects)

        Return:
            hist:           HistoryManager for this node
            ret:            The return value of this expression is either a concrete (abstract) object or 
                            a list of accessors. These two cases have to be handled separatly.
                            The parent statement/expression has to handle what to do with it. This is 
                            necessary to realize assignment statements properly.
                            For variable list has one member. For MemberExpressions two.
        '''
    
        ### Get Statement and handle each type 
        curNode =self.ast[nodeNumber]
        t = curNode["type"]   

        ### Identifier handled together with expression
        if t in ["Identifier", "Property"]:

            # For realizing the histories for specific nodes: Store to which object this node belongs to
            object = state.env_get(curNode["value"])
            if object != None:
                self.nodeToObject[nodeNumber] = object
            return HistoryCollection(), [curNode["value"]]
        ### Expressions
        elif t == "ThisExpression":
            # the this is only a special local variable
            return HistoryCollection(), state.context
                  
        elif t == "ArrayExpression":
            # Handle as object (returning it as reference makes sense. Since also internally. Creat object and then return reference.)
            newObj = state.newObject("array", 0, nodeNumber)
            return HistoryCollection(), newObj
        elif t == "ArrayAccess":
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)
            return hist, [leftRet, rightRet]
        elif t == "ObjectExpression":
            obj = state.newObject("ObjectExpression", 0, nodeNumber)
            hist = HistoryCollection()
            for child in curNode["children"]:
                prop = self.ast[child]
                tmpHist, propertyValue = self._analyseExpression(prop["children"][0], state)
                hist.addHistoryCollection(tmpHist)
                state.heap_add(obj, prop["value"], propertyValue)
            return hist, obj
        elif t == "FunctionExpression":
            return HistoryCollection(), None

        # Unary operations
        if t == "UnaryExpression":
            # only the history is used ret should already be None since always value
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            return hist, None
        elif t in ["UpdateExpression"]:
            return HistoryCollection(), None
        
        # Binary operations
        elif t == "BinaryExpression":
            # Return value can be ignored -> tested, that not possible to return reference in rasonable way
            # Always both parts executed. So histories can be concatenated
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            rightHist, ret = self._analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)
            return hist, None
            
        elif t == "AssignmentExpression":
            # Execute expressions and assign right to left, AssignmentOperation missing in Parser!
            # Good news: javascript gives error when callexpression on left site of assignment
            # TODO: When it is a "on..." Property -> Execute the functionExpression in Behind
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state)
            rightRet = state.getTarget(rightRet) # need only target
            hist.addHistoryCollection(rightHist)
            if rightRet != None:
                if len(leftRet) == 1:
                    # When only a variable
                    state.env_set(leftRet[0], rightRet)

                    # Do the nodeToObject mapping when single assignment
                    potentialIdentifier = self.ast[curNode["children"][0]]
                    if potentialIdentifier["type"] == "Identifier": #TODO HIER MUSS ICH ES IRGENDWIE SCHAFFEN DAS MAPPING VON IDENTIFIER ZU NODE RICHTIG ZU MACHEN!
                        self.nodeToObject[potentialIdentifier["id"]] = rightRet
                else:
                    # When two elements in list do over heap
                    state.heap_add(leftRet[0],leftRet[1], rightRet)
            return hist, rightRet

        elif t == "LogicalExpression":
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state)
            hist.addHistoryCollection(rightHist)
            # For an "or" both result values possible, for "and" only second
            if curNode["type"] == "||":
                state.mergeObjects(state.getTarget(leftRet), state.getTarget(rightRet))
                if (leftRet == None):
                    return hist, rightRet
                else:
                    # If they were both != None, does not matter what to return since merged either way
                    return hist, leftRet
            else:
                return hist, state.getTarget(rightRet) #If even more strage constructs -> Bad Luck
            
        elif t in "MemberExpression":
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            leftRet = state.getTarget(leftRet) # we use target
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state)
            rightRet = rightRet[0] # we use value
            hist.addHistoryCollection(rightHist)            
            hist.addEventToHistory(leftRet, rightRet, 0, state.functionName)
            return hist, [leftRet, rightRet]

        elif t == "ConditionalExpression":
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("ic")
            state_then = state.copy()
            hist_then, ret_then = self._analyseExpression(curNode["children"][0], stateThen)
            state_else = state.copy()
            hist_else, ret_else = self._analyseExpression(curNode["children"][0], stateElse)
            hist.addHistoryCollection([hist_then,hist_else]) 
            state.mergeIn([state_then, state_else])
            # Does not matter whether return ret_then or ret_else, since already merged in state
            return hist, ret_else

        elif t == "CallExpression":
            """ Most important element for histories! Arranges the function calls.
            Looks whether the designated function can be found using the callgraph.
            The corresponding node is then called with env only set to the parameters.
            Functions from FunctionExpressions are exactly identically referenced by callgraph as 
            the functions from FunctionDeclaration. Only difference: Expression has no first child 
            with name.
            The special fields "state.context" and "state.functionName" are additonal information 
            stored in the environment needed for calculation!
            """   
            
            if (self.ast[curNode["children"][0]]["type"] == "FunctionExpression"):
                # Set the function  (in this case salways available)
                fnNode = self.ast[curNode["children"][0]]

                # Create the subfunction context   
                subfunctionState = state.prepareForSubfunction(state.context, "anonym"+str(nodeNumber))
                for i, param in enumerate(curNode["children"][1:]):
                    hist, tmpRet = self._analyseExpression(param, state)
                    subfunctionState.env_set(fnNode["children"][i+1]["value"],tmpRet)

            elif  (self.ast[curNode["children"][0]]["type"] == "MemberExpression"):
                hist, ret = self._analyseExpression(curNode["children"][0], state)
                
                # Set the function (at the moment ignore document and window links)
                if not curNode["id"] in self.callgraph or not isinstance(self.callgraph[curNode["id"]],int):
                    newObj = state.newObject("anonymous", 0,curNode["id"])
                    hist.addEventToHistory(newObj, ret[-1], "ret", state.functionName)
                    return hist, newObj

                # Otherwise set the function and functioncontext
                fnNode = self.ast[self.callgraph[curNode["id"]]]
                subfunctionState = state.prepareForSubfunction(state.getTarget(ret[:-1]), ret[-1])
                for i, param in enumerate(curNode["children"][1:]):
                    tmpHist, tmpRet = self._analyseExpression(param, subfunctionState)
                    hist.addHistoryCollection(tmpHist)    
                    subfunctionState.env_set(fnNode["children"][i+1]["value"],tmpRet)

            elif (self.ast[curNode["children"][0]]["type"] == "Identifier"):
                hist = HistoryCollection()

                # When no callinformation, only add event to history and create potential object
                if not curNode["id"] in self.callgraph or not isinstance(self.callgraph[curNode["id"]],int):
                    newObj = state.newObject("anonymous", 0, curNode["id"])
                    hist.addEventToHistory(newObj,self.ast[curNode["children"][0]]["type"],"ret",state.functionName)
                    return hist, newObj

                # Otherwise set the function and functioncontext
                fnNode = self.ast[self.callgraph[curNode["id"]]]
                subfunctionState = state.prepareForSubfunction(state.context, self.ast[curNode["children"][0]]["value"])
                for i, param in enumerate(curNode["children"][1:]):
                    tmpHist, tmpRet = self._analyseExpression(param, state)
                    hist.addHistoryCollection(tmpHist)
                    tmpRet = state.getTarget(tmpRet)
                    parameterName = self.ast[fnNode["children"][i+1]]["value"]
                    subfunctionState.env_createLocal(parameterName)
                    subfunctionState.env_set(parameterName,tmpRet)

            else:
                raise("CallExpression has a unknown child for node" + nodeNumber);
            

            # Execute the functions blockstatement (last child)
            fnHist = self._analyseStatement(fnNode["children"][-1], subfunctionState)
            hist.addHistoryCollection(fnHist)
            ret = subfunctionState.env_get("__return__")
            return hist, ret

        elif t == "NewExpression":
            return HistoryCollection(), state.newObject(self.ast[curNode["children"][0]]["value"], 0, nodeNumber)
            
        elif t == "SequenceExpression":
            # Multiple expressions. 
            # multivardeclaration is separate case: There the comma are multiple VariableDeclarators
            if "children" in curNode:
                hist = HistoryCollection()
                ret = None
                for i in curNode["children"]:
                    tmpHist, ret = self._analyseExpression(i, state) 
                    hist.addHistoryCollection(tmpHist, state.get["__thisFunction__"])
                return hist, ret
            
        ### Literals handled as expression
        elif t.startswith("Literal"): # ["Literal", "LiteralString", "LiteralRegExp", "LiteralBoolean",  "LiteralNull", "LiteralNumber"]:
            # If they are analysed seperately like here return None. If they are necessary, 
            # immediatly handle from the parent node (like for example the identifier in CallExpression)
            return HistoryCollection(), None
            
        # For all other nodes, where no specific strategy has been assigned
        else:
            raise NameError('NodeName not handled')







        
######################################################################
# GOBAL FUNCTIONS
######################################################################
def prepare_files(astFilePath):
    """ Takes a file with ASTs, loads them and creates callgraphs
    It takes the asts and creates codefiles from it by using the jsprinter. Then it 
    let jscallgraph create the callgraph. To do so it avoids writing to files, but 
    immediatly passes in the code per commandline. (The source of the jscallgraph has 
    been changed to realize this. See in the project readme).
    Then the lines and columns of the ASTs are also printed. 
    Finally the results are put together sothat the callgraph is returned immediatly 
    as a mapping from AST node to another AST node. That makes it later easy to lookup 
    functionality.
    Special objects (window, XHTTPRequest, etc. are handled in a special way.). For this 
    I have to ask the creators of JSCallgraph how it is implemented.
    The multiple ASTs in the file are handled at the same time sothat calls between them are possible.
       
    Input:
        filepath:       full path of the file including one ast per line

    Output:
        asts:           The parsed asts
        callgraphs      An array of callmappings from (astId, nodeId) to (astId, nodeId)
    """
        

    # 0) If javascriptcode given instead AST -> Create ast-file to use default behaviour afterwards and use that astFilePath
    if (UseTestingCodejs):
        # javascriptcode given -> Generate ast and save as file
        p0 = Popen(["/home/pa/Desktop/js_parser/bin/js_parser.js",
                    "/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories/IsolatedCode.js"]
                    , stdout=PIPE)
        genAst = p0.stdout.read().decode("utf-8")
        astFilePath = "/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories/isolatedCode_programs.json"
        text_file = open(astFilePath, "w")
        text_file.write(genAst)
        text_file.close()




    # A) Parse the AST
    astFile = open(astFilePath, "r")
    asts = []
    for line in astFile:
        if len(line) > 1:
            asts.append(json.loads(line))

    # B) Reconstruct the code from AST
    p1 = Popen(["/home/pa/Desktop/json_printer/bin/syntree/main", "--num_data_records=" + str(len(asts)),
                "--data=" + astFilePath,
                "--logtostderr"], stderr=PIPE)
    jscode = p1.stderr.read().decode("utf-8")
    filteredJscode = []
    jscodeLinePositions = []
    resultJscode = []
    for line in jscode.split("\n")[4:]:
        if line.startswith("I0"):
            filteredJscode.append([])
            jscodeLinePositions.append([-1])
        else:
            filteredJscode[-1].append(line)
            jscodeLinePositions[-1].append(jscodeLinePositions[-1][-1] + len(line) + 1) # add 1 for newline
    for i, program in enumerate(filteredJscode):
        resultJscode.append('\n'.join(program))
        jscodeLinePositions[i][0] = 0 # I HAVE ABSOLUTLY NO CLUE, WHY THE MAPPING IS THAT STRANGE AND THERE IS ALWAYS AN OFFSET OF 1
   
    # C) Get the mapping from position in sourcefile to astNode by analysing the node
    p2 = Popen(["/home/pa/Desktop/json_printer/bin/syntree/main", "--num_data_records=" + str(len(asts)),
                "--data=" + astFilePath,
                "--mode=info", "--logtostderr"], stderr=PIPE)
    rawAstToCodeMapping = p2.stderr.read().decode("utf-8").split("\n")[4:]
    processedAstToCodeMapping = []
    for line in rawAstToCodeMapping:
        parsedLine = line[line.find("]")+2:].split()
        if len(parsedLine) == 0:
            continue

        if parsedLine[0] == "0":
            processedAstToCodeMapping.append([])

        processedAstToCodeMapping[-1].append([int(x) for x in parsedLine[1:] ])
    mapping = []
    for i, ast in enumerate(asts):
        mapping.append({})
        for node in ast[:-1]:
            if node["type"] in ["FunctionExpression", "FunctionDeclaration", "CallExpression"]:
                position = processedAstToCodeMapping[i][node["id"]]
                mapping[-1][jscodeLinePositions[i][position[0]-1] + position[1]] = node["id"]

    resultJscode[1] = resultJscode[1].replace('"use strict";\n',"")
    resultJscode[1] = resultJscode[1].replace('module.exports = PathUtils;', "")


    # D) Create the callgraph with the AST nodes as entries
    q = Popen(["node", "/home/pa/Desktop/js_call_graph/javascript-call-graph/main.js", "--cg", str(resultJscode[2])], stdout=PIPE)# "|||".join(resultJscode)], stdout=PIPE)
    callgraph = q.stdout.read().decode("utf-8")
    mappedCallgraph =  [dict() for x in range(len(asts))]
    for line in callgraph.split("\n"):
        if not "->" in line:
            continue
        caller, target = line.split(" -> ")
        callerAst = int(caller[0:caller.find("@")])
        callerPos = int(caller[caller.find(":")+1:caller.find("-") ])
        if not callerPos in mapping[callerAst]:
            continue
        caller = mapping[callerAst][ callerPos ]
        if "@" in target:
            targetAst = int(caller[0:caller.find("@")])
            targetPos = int(target[target.find(":")+1:target.find("-") ] )
            if not targetPos in mapping[targetAst]:
                continue
            target = (targetAst, mapping[targetAst][targetPos])
            mappedCallgraph[callerAst][caller] = target

    return asts, mappedCallgraphs



def extract_histories(astsFilePath, testsFilePath = None):
    """ Extracts histories available in the designated files.

    Input:
    astString:      Path to file containing ASTs, one per line
    tests:          If the histories shall be reduced. Otherwise histories for all the
                    classes are given.

    Output:
    histories:      List of history objects as a string, formatted like in the paper.
                    If tests is given "<tree_id> <node_id> <token_1> ... <token_n>"
                    Otherwise for classes "<class_name> <node_id> <token_1> ... <token_n>"
    """

    # Get the corresponding callgraph 
    ast, callgraph = prepare_files(astsFilePath)
    
    # Analyse the given ast with help of the callgraph and return result
    hist_extractor = history_extractor(ast, callgraph)
    hist_extractor.generateHistories()

    # Get the histories (format depends, on wheter testsFilePath given or not)
    tests = None
    if testsFilePath != None:
        tests = open(testFilePath, "r").read().split("\n")
    historiesString = hist_extractor.getHistoryString(tests)
    return historiesString








######################################################################
def eprint(*args, **kwargs):
    """ Help function to print to stderror stream instead stdout """
    print(*args, file=sys.stderr, **kwargs)


if __name__ == "__main__":
    """
    When called as standalone script only a single AST is awaited. 
    Only the extract_histories above is also capable to handle multiple AST 
    files at once. So from the prediction program this it is possible to 
    handle multiple at ones
    """

    astFilePath = sys.argv[1]
    testFilePath = sys.argv[2]

    # Here it could be reasonable to handle ASTs of the same project at the same time
    histories = extract_histories(astFilePath)

    # Like requested, write output to stdout
    print(histories)