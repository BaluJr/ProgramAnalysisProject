from __future__ import print_function

import json
import sys
from subprocess import Popen, PIPE

import CustomExceptions
from HistoryCollection import HistoryCollection
from State import State

# Global flags for debugging purposes
# Process the code in /tests_histoires/TestingCode.js instead of the given AST. For debugging.
UseTestingCodejs = False
# Write the created js per project into the data folder
WriteCreatedJs = True

# The new JS Standard
es6_standard = ["ForOfStatment", "ArrowFunctionExpression", "YieldExpression", "TemplateLiteral", "TaggedTemplateExpression"
"TemplateElement", "ObjectPattern", "ArrayPattern", "RestElement", "AssignmentPattern", "ClassBody",
"MethodDefinition", "ClassDeclaration", "ClassExpression", "Modules", "ModuleDeclaration", "ModuleSpecifier",
"ImportDeclaration", "ImportSpecifier", "ImportBatchSpecifier", "ExportDeclaration", "ExportBatchSpecifier",
"ExportSpecifier"]


# Flag to limit recursion
RecursionLimit = 5


class history_extractor:

    def __init__(self, asts, callgraphs, astsFilePathDebug):
        ''' Constructor immediatly sets ast and callgraph this extractor shall work on. 
        '''

        self.NameDebug = astsFilePathDebug
        self.asts = asts
        self.callgraphs = callgraphs
        self.histories = []
        self.outputHistories = {}
        self.nodeToObject = [dict() for i in range(len(asts))]

        # The histories created by executed all functions separately
        self.isolatedFunctionHistories = []

        # Necessary for handling the altered prototypes to group which classes belong together
        self.globallyPrototypedClasses = set()
        self.globallyOfferedClasses = set()
        self.globallyUnknownVariables = set()

        # An additional place for storing for which object there exists an hole
        self.holeObjects = {}



    def generateHistories(self):
        ''' Creates the history for the ast and callgraph given during initialization. '''

        # First go through the code like a real execution
        for astNumber in range(len(self.asts)):
            state = State()
            self.histories.append(self._analyseStatement(astNumber, 0, state, 0))

            outputForAST = self.histories[-1].toOutputFormat(state)
            self.outputHistories.update(outputForAST)

        # Then also process each function on its own. This is necessary since most functions
        # won't be executed. Merge these histories into the execution histories.
        # By keeping the longest history, the most favorable execution path is learned.
        for functionHistory in self.isolatedFunctionHistories:
            functionHistory.update(self.outputHistories)
            self.outputHistories = functionHistory

        # Finally also remember which global objects were used and are offered
        self.globallyOfferedClasses = set(
            [classname for classname in state.globalEnvironment
             if classname[0].isupper() and state.globalEnvironment[classname] != None]
        )
        if state.context == "window-0:0":
            for classname in state.localEnvironment:
                if classname[0].isupper():
                    self.globallyOfferedClasses.add(classname)

        self.globallyUnknownVariables = set(
            [variable for variable in state.globalEnvironment
             if variable[0].isupper() and state.globalEnvironment[variable] == None])
       


    def getHistoryString(self, astObjects = None, hole = False):
        ''' Returns the created history.
        This file creates the output string for the histories.
        There are in facts three different modes how to do this.
        A) When hole=true:      Only the histories for elements with a hole in 
                                it are returned
        B) astObjects != None:  Only the histories for the provided testcases are 
                                returned.
        C) Else:                All histories are returned with the class name
                                in the beginning of each history.


        Input:
            astObjects:     [optional] Specific nodes for which one wants to get
                            the history. Given by AST ID and NodeID
            hole:           Whether only the histories until the hole shall be returned
                            This is necessary for predicting suggestions.

        Return:
            hist:           History in the output format defined in the paper.
        '''
        if hole == True:            # A
            astObjects = set(self.holeObjects.values())
            outputString = ""
            for obj in astObjects:
                treeId, nodeId, obj = obj
                outputString += "<" + str(treeId) + "><" + str(nodeId) + ">   "
                for concreteTrace in self.outputHistories[obj]:
                    for event in concreteTrace:
                        outputString += "<" + ','.join([str(event[i]) for i in range(4)]) + "> "
                    outputString += "\n"

        elif astObjects != None:    # B
            outputString = ""
            for astObject in astObjects:
                treeId, nodeId = astObject.split("\t")
                obj = self.nodeToObject[int(treeId)][int(nodeId)]

                startTag = "<" + treeId + "><" + nodeId + ">   "
                for concreteTrace in self.outputHistories[obj]:
                    outputString += startTag
                    for event in concreteTrace:
                        outputString += "<" + ','.join([str(event[i]) for i in range(4)]) + "> "
                    outputString += "\n"

        else:                       # C
            outputString = ""
            for obj in self.outputHistories:
                classTag = "<" + obj.split("-")[0] + ">   "
                for concreteTrace in self.outputHistories[obj]:
                    outputString += classTag
                    for event in concreteTrace:
                        outputString += "<" + ','.join([str(event[i]) for i in range(4)])  + "> "
                    outputString += "\n"

        return outputString




    # Set of functions used for getting the used variables.
    def getGloballyPrototypedClasses(self):
        return self.globallyPrototypedClasses

    def getGloballyOfferedClasses(self):
        return self.globallyOfferedClasses

    def getGloballyUnknownClasses(self):
        return self.globallyUnknownVariables

    def getGloballyUsedClasses(self):
        usedClasses = set()
        for obj in self.outputHistories:
            if obj.startswith("anonymous"):
                continue
            obj = obj.split("-")[0]
            obj = obj[0].upper() + obj[1:]
            usedClasses.add(obj)
        return usedClasses



    # The following functions are now for the internal parsing:

    def _analyseStatement(self, astNumber, nodeNumber, state, recursionDepth):
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
            astNumber:      The ast the statement belongs to
            nodeNumber:     The node in the AST to analyse
            state:          The state with the current environment, the objects and the heap.

        Return:
            hist:           The HistoryCollection for this node
        '''
       
        ### Get Statement and type 
        ast = self.asts[astNumber]
        curNode = ast[nodeNumber]
        t = curNode["type"]
            
        ### Analyse the Statements based on type
        if t == "ExpressionStatement":
            tmpHis, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            return tmpHis


        elif t in ["Program","BlockStatement","WithStatement"]:
            hist = HistoryCollection()
            if "children" in curNode:
                for i in curNode["children"]:
                    tmpHist = self._analyseStatement(astNumber, i, state, recursionDepth)
                    hist.addHistoryCollection(tmpHist)
            return hist

        if t in ["EmptyStatement", "DebuggerStatement"]:
            return HistoryCollection()

        # Control Flow (ignore completly, TODO)
        if t in ["BreakStatement", "ContinueStatement"]:
            return HistoryCollection()
        elif t == "ReturnStatement":
            # Do nothing for returns without return value
            if not "children" in curNode:
                return HistoryCollection()

            # Extend the the "__return__" variable and add the "return" statement to the history.
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0],state, recursionDepth)
            if ret:
                returnObject = state.getTarget(ret)
                state.env_set("__return__", returnObject)# Merging is done automatically
                if returnObject != None:
                    hist.addEventToHistory(returnObject, state.functionName,"ret", state.functionName)
            return hist

        # Choice
        elif t == "IfStatement":
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            hist.tagAsSpecialNode("ic")
            thenState = state.copy()
            hist_then = self._analyseStatement(astNumber, curNode["children"][1], thenState, recursionDepth)
            # Check whether else is given
            if len(curNode["children"]) == 3:
                elseState = state.copy()
                hist_else = self._analyseStatement(astNumber, curNode["children"][2], elseState, recursionDepth)
                state.mergeIn([thenState,elseState])
                hist.addHistoriesConditional([hist_then,hist_else])
            else:
                hist.addHistoriesConditional([hist_then,HistoryCollection()])
                state.mergeIn([thenState])
            return hist

        elif t == "SwitchStatement":
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            hist.tagAsSpecialNode("sc")
            condHistories = []
            condStates = []
            preceedingCaseConditions = []
            for case in curNode["children"][1:]:
                condStates.append(state.copy())
                case = ast[case]
                innerHist = HistoryCollection()
                # Handle previous case conditions
                for precCaseCond in preceedingCaseConditions:
                    tmpHist, ret = self._analyseExpression(astNumber, precCaseCond, condStates[-1], recursionDepth)
                    innerHist.addHistoryCollection(tmpHist)
                # Handle current case
                isDefault = len(case["children"]) == 1
                if not isDefault:
                    preceedingCaseConditions.append(case["children"][0]);
                    tmpHist, ret = self._analyseExpression(astNumber, case["children"][0], condStates[-1], recursionDepth)
                    tmpHist.tagAsSpecialNode("cc")
                    innerHist.addHistoryCollection(tmpHist)
                    tmpHist = self._analyseStatement(astNumber, case["children"][1], condStates[-1], recursionDepth)
                    innerHist.addHistoryCollection(tmpHist)
                else:
                    # For default the statement is only child
                    tmpHist = self._analyseStatement(case["children"][0], condStates[-1], recursionDepth)
                    innerHist.addHistoriesConditional(tmpHist)
                condHistories.append(innerHist)
            hist.addHistoriesConditional(condHistories)
            state.mergeIn(condStates)
            return hist
        
        # Exceptions (ignored at the moment)

        elif t  == "ThrowStatement":
            return HistoryCollection()

        elif t == "TryStatement":
            blockHist = self._analyseStatement(astNumber, curNode["children"][0], state, recursionDepth)
            if len(curNode["children"]) == 3:
                finallyHist = self._analyseStatement(astNumber, curNode["children"][0], state, recursionDepth)
                blockHist.addHistoryCollection(finallyHist)
            return blockHist

        # Loops
        elif t in ["WhileStatement", "DoWhileStatement"]:
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            hist.tagAsSpecialNode("wc")
            tmpHist = self._analyseStatement(astNumber, curNode["children"][1], state, recursionDepth)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist
        elif t == "ForStatement": # YEAH! The scope is acutally the same as everywhere!
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            tmpHist, ret = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            hist.addHistoryCollection(tmpHist)
            tmpHist, ret = self._analyseExpression(astNumber, curNode["children"][2], state, recursionDepth)
            hist.addHistoryCollection(tmpHist)
            hist.tagAsSpecialNode("fh")
            tmpHist = self._analyseStatement(astNumber, curNode["children"][3], state, recursionDepth)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist

        elif t == "ForInStatement": 
            # The scope is the same for the iterator name!
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            hist.tagAsSpecialNode("fh")
            
            # Since we do not handle loops, immediatly assign all elements within the returned enumerable (Whether array or object does not matter because both in heap)
            # TODO: the for in for an array only gives the indices!!!! NO IDEA HOW TO HANDLE -> maybe a special case
            tmpHist, ret =self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            tmpHist.tagAsSpecialNode("fh")
            hist.addHistoryCollection(tmpHist)
            tmpHist = self._analyseStatement(astNumber, curNode["children"][2], state, recursionDepth)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
            return hist

        ### Declarations (handled here toghether with Declarators)
        elif t == "VariableDeclaration":
            # There might be multiple declarators as eg. "var a = 4, b = 5"
            for declarator in [ast[node] for node in curNode["children"]]:
                # Create the local variable
                state.env_createLocal(declarator["value"])
                if "children" in declarator:
                    hist, ret = self._analyseExpression(astNumber, declarator["children"][0], state, recursionDepth)
                    state.env_set(declarator["value"], state.getTarget(ret))
                    return hist
                else:
                    return HistoryCollection()
        elif t == "FunctionDeclaration": 
            # Execute isolated and store in the separate history.
            # Since I remember the ObjectName, afterwards the longest history per object can be taken
            isolatedFunctionState = State()
            for i, param in enumerate(curNode["children"][1:-1]):
                parameterName = ast[curNode["children"][i+1]]["value"]
                isolatedFunctionState.env_createLocal(parameterName)
                isolatedFunctionState.env_set(parameterName, isolatedFunctionState.newObject("anonymous", astNumber, nodeNumber))
            fnHist = self._analyseStatement(astNumber, curNode["children"][-1], isolatedFunctionState, recursionDepth)
            self.isolatedFunctionHistories.append(fnHist.toOutputFormat(isolatedFunctionState))

            # For the run through history, there is no effect
            return HistoryCollection()

        elif t in es6_standard:
            return HistoryCollection()

        # For all other nodes, where no specific strategy has been assigned
        else:
            raise NameError('NodeName not handled')


                               
    def _analyseExpression(self, astNumber, nodeNumber, state, recursionDepth):
        ''' Analyses a single expression node. 
        In contrast to statements, expressions always have a return value.
        Expressions are the more interesting and difficult part since only 
        here instructions are really executed and histories get written.

        Input:
            astNumber:      The ast the statement belongs to
            nodeNumber:     The node in the AST to analyse
            state:          The state of the current execution (contains environment, heap, objects)

        Return:
            hist:           The HistoryCollection for this node
            ret:            List of accessors. These two cases have to be handled separatly.
                            The parent statement/expression has to handle what to do with it. This is 
                            necessary to realize assignment statements properly.
                            For variable list has one member. For MemberExpressions two.
        '''
    

        ### Get Statement and handle each type 
        ast = self.asts[astNumber]
        curNode =ast[nodeNumber]
        t = curNode["type"]   

        ### Identifier handled together with expression
        if t in ["Identifier", "Property"]:
            # Special case for holes
            if curNode["value"] == "_HOLE_":
                return HistoryCollection(), ["_HOLE_"]

            # For realizing the histories for specific nodes: Store to which object this node belongs to
            object = state.env_get(curNode["value"])
            if object != None:
                self.nodeToObject[astNumber][nodeNumber] = object

            # Besides that return the identifier
            return HistoryCollection(), [curNode["value"]]

        ### Expressions
        elif t == "ThisExpression":
            # the this is only a special local variable
            return HistoryCollection(), state.context
                  
        elif t == "ArrayExpression":
            # Handle as object (returning it as reference makes sense. Since also internally. Creat object and then return reference.)
            newObj = state.newObject("array", astNumber, nodeNumber)
            return HistoryCollection(), newObj
        elif t == "ArrayAccess":
            hist, leftRet = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            rightHist, rightRet = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            hist.addHistoryCollection(rightHist)
            return hist, [state.getTarget(leftRet), state.getTarget(rightRet)]
        elif t == "ObjectExpression":
            obj = state.newObject("ObjectExpression", astNumber, nodeNumber)
            hist = HistoryCollection()
            if "children" in curNode:
                for child in curNode["children"]:
                    prop = ast[child]
                    tmpHist, propertyValue = self._analyseExpression(astNumber, prop["children"][0], state, recursionDepth)
                    hist.addHistoryCollection(tmpHist)
                    state.heap_add(obj, prop["value"], state.getTarget(propertyValue))
            return hist, obj

        elif t == "FunctionExpression":
            # Execute isolated and store in the separate history.
            # Since I remember the ObjectName, afterwards the longest history per object can be taken
            isolatedExpressionState = State()
            for i, param in enumerate(curNode["children"][:-1]): # Only parameters and last body
                parameterName = ast[curNode["children"][i]]["value"]
                isolatedExpressionState.env_createLocal(parameterName)
            fnHist = self._analyseStatement(astNumber, curNode["children"][-1], isolatedExpressionState, recursionDepth)
            self.isolatedFunctionHistories.append(fnHist.toOutputFormat(isolatedExpressionState))

            # For the run through history, there is no effect
            return HistoryCollection(), None

        # Unary operations
        if t == "UnaryExpression":
            # only the history is used ret should already be None since always value
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            return hist, None
        elif t == "UpdateExpression":
            return HistoryCollection(), None
        
        # Binary operations
        elif t == "BinaryExpression":
            # Return value can be ignored -> tested, that not possible to return reference in rasonable way
            # Always both parts executed. So histories can be concatenated
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            rightHist, ret = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            hist.addHistoryCollection(rightHist)
            return hist, None
            
        elif t == "AssignmentExpression":
            # Execute expressions and assign right to left, AssignmentOperation missing in Parser!
            # Good news: javascript gives error when callexpression on left site of assignment
            hist, leftRet = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            rightHist, rightRet = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            rightRet = state.getTarget(rightRet) # need only target
            hist.addHistoryCollection(rightHist)
            if rightRet != None:
                if len(leftRet) == 1:
                    # When only a variable
                    state.env_set(leftRet[0], rightRet)

                    # Do the nodeToObject mapping when single assignment
                    potentialIdentifier = ast[curNode["children"][0]]
                    if potentialIdentifier["type"] == "Identifier":
                        self.nodeToObject[astNumber][potentialIdentifier["id"]] = rightRet
                else:
                    # When two elements in list do over heap
                    state.heap_add(leftRet[0],leftRet[1], rightRet)
            return hist, rightRet

        elif t == "LogicalExpression":
            hist, leftRet = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            rightHist, rightRet = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
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
            
        elif t == "MemberExpression":
            hist, leftRet = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            leftRetTarget = state.getTarget(leftRet) # we use target

            # If prototype, return yourself immediatly but additionally mark the given class variable as
            # modified by the code
            if (ast[curNode["children"][1]]["value"] == "prototype"):
                if isinstance(leftRet, list):
                    if len(leftRet) == 1:
                        self.globallyPrototypedClasses.add(leftRet[0])
                    else:
                        self.globallyPrototypedClasses.add(leftRet[1])
                else:
                    self.globallyPrototypedClasses.add(leftRet)
                return hist, leftRet if isinstance(leftRet, list) else [leftRet]

            rightHist, rightRet = self._analyseExpression(astNumber, curNode["children"][1], state, recursionDepth)
            rightRet = rightRet[0] # we use value

            if rightRet == "_HOLE_":
                self.holeObjects[astNumber] = (astNumber, curNode["children"][1], leftRetTarget)

            hist.addHistoryCollection(rightHist)
            if leftRetTarget != None:
                hist.addEventToHistory(leftRetTarget, rightRet, 0, state.functionName)
            return hist, [leftRetTarget, rightRet]

        elif t == "ConditionalExpression":
            hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
            hist.tagAsSpecialNode("ic")
            state_then = state.copy()
            hist_then, ret_then = self._analyseExpression(astNumber, curNode["children"][1], state_then, recursionDepth)
            # Check whether else is given
            if len(curNode["children"]) == 3:
                state_else = state.copy()
                hist_else, ret_else = self._analyseExpression(astNumber, curNode["children"][2], state_else, recursionDepth)
                state.mergeIn([state_then, state_else])
                hist.addHistoriesConditional([hist_then, hist_else])
            else:
                hist.addHistoriesConditional([hist_then, HistoryCollection()])
                state.mergeIn([state_then])
            state.mergeObjects([state.getTarget(ret_else), state.getTarget(ret_then)])
            return hist, ret_then # does not matter which to return since merged (left or right)

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

            jmpAstNumber = astNumber
            if (ast[curNode["children"][0]]["type"] == "FunctionExpression"):
                hist = HistoryCollection()

                # Set the function (at the moment ignore document and window links)
                if recursionDepth > RecursionLimit:
                    # return at least an anonymous return object
                    newObj = state.newObject("anonymous", astNumber, curNode["id"])
                    return HistoryCollection(), newObj

                # Set the function  (in this case always available)
                fnNode = ast[curNode["children"][0]]

                # Create the subfunction context   
                subfunctionState = state.prepareForSubfunction(state.context, "anonym"+str(nodeNumber))
                for i, param in enumerate(curNode["children"][1:]):
                    tmpHist, tmpRet = self._analyseExpression(astNumber, param, state, recursionDepth)
                    hist.addHistoryCollection(tmpHist)
                    tmpRet = state.getTarget(tmpRet)
                    parameterName = ast[fnNode["children"][i]]["value"]
                    subfunctionState.env_createLocal(parameterName)
                    subfunctionState.env_set(parameterName,tmpRet)
                    if tmpRet != None:
                        hist.addEventToHistory(tmpRet, "lamda", i, state.functionName)

            elif  (ast[curNode["children"][0]]["type"] == "MemberExpression"):
                hist, ret = self._analyseExpression(astNumber, curNode["children"][0], state, recursionDepth)
                functionName = ast[ast[curNode["children"][0]]["children"][1]]["value"]

                # Set the function (at the moment ignore document and window links)
                if recursionDepth > RecursionLimit or not curNode["id"] in self.callgraphs[astNumber] or not isinstance(self.callgraphs[astNumber][curNode["id"]], tuple):
                    # Add the call to the object given as a parameter
                    for i, param in enumerate(curNode["children"][1:]):
                        tmpHist, tmpRet = self._analyseExpression(astNumber, param, state, recursionDepth)
                        hist.addHistoryCollection(tmpHist)
                        tmpRet = state.getTarget(tmpRet)
                        if tmpRet != None:
                            hist.addEventToHistory(tmpRet, functionName, i+1, state.functionName)

                    # return at least an anonymous return object
                    newObj = state.newObject("anonymous", astNumber, curNode["id"])
                    hist.addEventToHistory(newObj, ret[-1], "ret", state.functionName)
                    return hist, newObj

                # Otherwise set the function and functioncontext
                jmpAstNumber, nodeId = self.callgraphs[astNumber][curNode["id"]]
                fnNode = self.asts[jmpAstNumber][nodeId]
                subfunctionState = state.prepareForSubfunction(state.getTarget(ret[:-1]) if ret[:-1][0] != None else "anonymous", ret[-1])
                for i, param in enumerate(curNode["children"][1:]):
                    if i >= (len(fnNode["children"])-1):
                        break #In javascript handle too many params no
                    tmpHist, tmpRet = self._analyseExpression(astNumber, param, state, recursionDepth)
                    hist.addHistoryCollection(tmpHist)    
                    tmpRet = state.getTarget(tmpRet)
                    parameterName = self.asts[jmpAstNumber][fnNode["children"][i]]["value"]
                    subfunctionState.env_createLocal(parameterName)
                    subfunctionState.env_set(parameterName,tmpRet)
                    if tmpRet != None:
                        hist.addEventToHistory(tmpRet, functionName, i+1, state.functionName)

            elif (ast[curNode["children"][0]]["type"] == "Identifier"):
                hist = HistoryCollection()

                # When no callinformation, only add event to history and create potential object
                if recursionDepth > RecursionLimit or not curNode["id"] in self.callgraphs[astNumber] or not isinstance(self.callgraphs[astNumber][curNode["id"]],tuple):
                    newObj = state.newObject("anonymous", astNumber, curNode["id"])
                    hist.addEventToHistory(newObj,ast[curNode["children"][0]]["type"],"ret",state.functionName)
                    # Add the call to the object given as a parameter
                    functionName = ast[curNode["children"][0]]["value"]
                    for i, param in enumerate(curNode["children"][1:]):
                        tmpHist, tmpRet = self._analyseExpression(astNumber, param, state, recursionDepth)
                        hist.addHistoryCollection(tmpHist)
                        tmpRet = state.getTarget(tmpRet)
                        if tmpRet != None:
                            hist.addEventToHistory(tmpRet, functionName, i+1, state.functionName)
                    return hist, newObj

                # Otherwise set the function and functioncontext
                jmpAstNumber, nodeId = self.callgraphs[astNumber][curNode["id"]]
                fnNode = self.asts[jmpAstNumber][nodeId]

                subfunctionState = state.prepareForSubfunction(state.context, ast[curNode["children"][0]]["value"])
                for i, param in enumerate(curNode["children"][1:]):
                    if (i if fnNode["type"] == "FunctionExpression" else i + 1) >= (len(fnNode["children"])-1):
                        break #In javascript handle too many params no
                    tmpHist, tmpRet = self._analyseExpression(astNumber, param, state, recursionDepth)
                    hist.addHistoryCollection(tmpHist)
                    tmpRet = state.getTarget(tmpRet)
                    parameterName = self.asts[jmpAstNumber][fnNode["children"][i if fnNode["type"] == "FunctionExpression" else i+1]]["value"]
                    subfunctionState.env_createLocal(parameterName)
                    subfunctionState.env_set(parameterName,tmpRet)
                    if tmpRet != None:
                        hist.addEventToHistory(tmpRet, ast[curNode["children"][0]]["value"], i+1, state.functionName)

            elif  (ast[curNode["children"][0]]["type"] == "CallExpression"):
                return HistoryCollection(), None    #TODO

            elif  (ast[curNode["children"][0]]["type"] == "ArrayAccess"):
                return HistoryCollection(), None    #TODO

            else:
                raise("CallExpression has a unknown child for node" + nodeNumber);
            

            # Execute the functions blockstatement (last child)
            fnHist = self._analyseStatement(jmpAstNumber, fnNode["children"][-1], subfunctionState, recursionDepth + 1)
            hist.addHistoryCollection(fnHist)
            ret = subfunctionState.env_get("__return__")
            return hist, ret

        elif t == "NewExpression":
            # First get the final classname and ignore namespaces
            child = ast[curNode["children"][0]]
            if child["type"] == "MemberExpression":
                className = ast[child["children"][1]]["value"]
            else:
                className = child["value"]
            return HistoryCollection(), state.newObject(className, astNumber, nodeNumber)
            
        elif t == "SequenceExpression":
            # Multiple expressions. 
            # multivardeclaration is separate case: There the comma are multiple VariableDeclarators
            if "children" in curNode:
                hist = HistoryCollection()
                ret = None
                for i in curNode["children"]:
                    tmpHist, ret = self._analyseExpression(astNumber, i, state, recursionDepth)
                    hist.addHistoryCollection(tmpHist, state.get["__thisFunction__"])
                return hist, ret
        elif t == "VariableDeclaration":
            # In the for declarator VariableDeclaration might be an expression
            hist = HistoryCollection();
            for declarator in [ast[node] for node in curNode["children"]]:
                # Create the local variable
                state.env_createLocal(declarator["value"])
                if "children" in declarator:
                    tmpHist, ret = self._analyseExpression(astNumber, declarator["children"][0], state, recursionDepth)
                    state.env_set(declarator["value"], state.getTarget(ret))
                    hist.addHistoryCollection(tmpHist)
            return hist, None

        ### Literals handled as expression
        elif t.startswith("Literal"): # ["Literal", "LiteralString", "LiteralRegExp", "LiteralBoolean",  "LiteralNull", "LiteralNumber"]:
            # If they are analysed seperately like here return None. If they are necessary, 
            # immediatly handle from the parent node (like for example the identifier in CallExpression)
            return HistoryCollection(), None

        elif t in es6_standard:
            return HistoryCollection(), None

        # For all other nodes, where no specific strategy has been assigned
        elif t == "EmptyStatement":
            return HistoryCollection(), None
        else:
            return HistoryCollection(), None







        
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
                    "/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories/TestingCode.js"]
                    , stdout=PIPE)
        genAst = p0.stdout.read().decode("utf-8")
        astFilePath = "/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories/TestingCode_programs.json"
        text_file = open(astFilePath, "w")
        text_file.write(genAst)
        text_file.close()

        
    # A) Parse the AST
    astFile = open(astFilePath, "r")
    asts = []
    for line in astFile:
        if len(line) > 1:
            line = line.replace('?',"_HOLE_")
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
        if line.startswith("I0"): # A I0 line splits the multiple js position infos
            filteredJscode.append([])
            jscodeLinePositions.append([-1])
        elif len(filteredJscode) > 0: # Security for when no js code generated
            # Replace before the counting of line length because callgraoh gets also edited function
            line = line.replace('?',"_HOLE_")
            filteredJscode[-1].append(line)
            jscodeLinePositions[-1].append(jscodeLinePositions[-1][-1] + len(line) + 1) # add 1 for newline
    for i, program in enumerate(filteredJscode):
        resultJscode.append('\n'.join(program))
        #jscodeLinePositions[i][0] = 0; Without more correct

    if (WriteCreatedJs):
        codeFile = open(astFilePath[:-5]+".js", "w+")
        for code in resultJscode:
            codeFile.write(code)
            codeFile.write("\n\n\n\n")


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
        try:
            for node in ast[:-1]: # Skip 0 at the end of AST
                if node["type"] in ["FunctionExpression", "FunctionDeclaration", "CallExpression"]:
                    position = processedAstToCodeMapping[i][node["id"]]
                    mapping[-1][jscodeLinePositions[i][position[0]-1] + position[1]] = node["id"]
        except:
            if (WriteCreatedJs):
                codeFile.close()
            raise CustomExceptions.MappingException(i, resultJscode)


    # D) Create the callgraph with the AST nodes as entries
    q = Popen(["node", "/home/pa/Desktop/js_call_graph/javascript-call-graph/main.js", "--cg", "|||".join(resultJscode)], stdout=PIPE, stderr=PIPE)
    callgraph = q.stdout.read().decode("utf-8")
    error = q.stderr.read()
    if len(error) > 0:
        if (WriteCreatedJs):
            codeFile.write("\n\n\n\n##### CALLGRAPH ERROR #####")
            codeFile.write(error.decode("utf-8"))
            codeFile.close()
        raise CustomExceptions.CallgraphException("Error during callgraph generation", resultJscode)

    if (WriteCreatedJs):
        codeFile.close()

    mappedCallgraphs =  [dict() for x in range(len(asts))]
    for line in callgraph.split("\n"):
        if not "->" in line:
            continue
        caller, target = line.split(" -> ")
        callerAst = int(caller[0:caller.find("@")])
        callerPos = int(caller[caller.find(":")+1:caller.find("-") ])
        if callerPos in mapping[callerAst]:
            caller = mapping[callerAst][callerPos]
        elif callerPos - 1 in mapping[callerAst]:  # There is sometimes a failing offset :(
            caller = mapping[callerAst][callerPos - 1]
        else:
            continue

        if "@" in target:
            targetAst = int(target[0:target.find("@")])
            targetPos = int(target[target.find(":")+1:target.find("-") ] )
            if targetPos in mapping[targetAst]:
                target = (targetAst, mapping[targetAst][targetPos])
            elif targetPos-1 in mapping[targetAst]: # There is sometimes a failing offset :(
                target = (targetAst, mapping[targetAst][targetPos-1])
            else:
                continue
            mappedCallgraphs[callerAst][caller] = target

    return asts, mappedCallgraphs




def extract_histories(astsFilePath, testsFilePath = None, testOnHoles = False):
    """ THIS IS THE MAIN FUNCTION TO CALL FOR THIS CLASS

    Input:
        astsFilePath:       Path to file containing ASTs, one per line
        testsFilePath:      If the histories shall be reduced. Otherwise histories for all the
                            classes are given.
        testOnHoles:        Whether only the histories with a _HOLE_ element in them exist
                            This is necessary for predicting suggestions.

    Output:
        histories:          List of history objects as a string, formatted like in the paper.
                            If tests or holes are given "<tree_id> <node_id>   <token_1> ... <token_n>"
                            Otherwise for whole classes "<class_name>   <token_1> ... <token_n>"
        protos:             Classes whose prototype has been changed within this code
        uses:               Classes which where used
        offered:            Variables, that are created within this module within the global namespace a
                            and which start with capital letter. (They should be classes though).
        unknowns:           Global variables which were accessed but nowhere defined.
    """
    # Get the corresponding callgraph
    asts, callgraphs = prepare_files(astsFilePath)

    # Analyse the given ast with help of the callgraph and return result
    hist_extractor = history_extractor(asts, callgraphs, astsFilePath)

    hist_extractor.generateHistories()

    # Test the access
    protos = hist_extractor.getGloballyPrototypedClasses()
    uses = hist_extractor.getGloballyUsedClasses()
    offered = hist_extractor.getGloballyOfferedClasses()
    unknowns = hist_extractor.getGloballyUnknownClasses()

    # Get the histories (format depends, on wheter testsFilePath given or not)
    tests = None
    if testsFilePath != None:
        tests = open(testsFilePath, "r").read().split("\n")
    historiesString = hist_extractor.getHistoryString(tests, testOnHoles)
    return historiesString, protos, uses, offered, unknowns







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

    try:
        if UseTestingCodejs:
            histories, a, b, c, d = extract_histories(None, None, False)
        else:
            histories, a, b, c, d = extract_histories(astFilePath, testFilePath, len(sys.argv) > 3)
        print(histories)
    except Exception as e:
        eprint(str(e))
