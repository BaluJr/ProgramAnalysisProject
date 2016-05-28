import os.path
from subprocess import Popen, PIPE
import sys, getopt
import json
from State import State
from HistoryCollection import HistoryCollection

#Cannot expand the folder. The set of folders cannot be opened. The server is not available. Contact your administrator if this condition persists. 


#TODO:
# -Break, Continue Statement
# -Looking how to handle Return and historiy extension etc for recursive functions 
#  (because then check, whether last history element equals to state.functionName, makes problem
# support bind to change the "this"!?
# Jsonparser has a problem! Missing AssignmentOperator field!
# -Object appear at multiple positions...


class history_extractor:
    aselst = None
    callgraph = None
    history = None

    def __init__(self, ast, callgraph):
        ''' Constructor immediatly sets ast and callgraph this extractor shall work on. 
        '''
        self.ast = ast
        self.callgraph = callgraph


    def generateHistories(self):
        ''' Creates the history for the ast and callgraph given during initialization
        No input and no return.
        '''
        hist, ret = self._analyseStatement(0, State());
        self.history = hist
        

    def getHistoryString(self, astObjects):
        ''' Returns the crated history
        Depending on whether specific nodes are given as parameter or not 
        it gives a list of those histories or a list of otherwise a list
        off all histories for all regarded classes.

        Input:
            astObjects:     [optional] Specific nodes for which one wants to get
                            the history.

        Return:
            hist:           History in the output format defined in the paper.
        '''
        historyString = self.historyCollection.toOutputFormat(astObjects);
        # Number, which was used to distinguish between multiple elements is cut away sothat only class name remains.
        return [(cur.rfind('-'), L[cur]) for cur in L] 


    def _analyseStatement(self, nodeNumber, state):
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
            return tmpHis #Statements don't have a return value
            
        elif t in ["Program","BlockStatement","WithStatement"]:
            if "children" in curNode:
                hist = HistoryCollection()
                for i in curNode["children"]:
                    tmpHist = self._analyseStatement(i, state) 
                    hist.addHistoryCollection(tmpHist)
                return hist       

        if t in ["EmptyStatement", "DebuggerStatement"]:
            return HistoryCollection()

        # Control Flow (ignore completly)
        if t in ["BreakStatement", "ContinueStatement"]:
            return HistoryCollection()#-> Handle later!
        elif t == "ReturnStatement": 
            # Extend the the "__return__" variable and add the "return" statement to the history.
            hist, ret = self._analyseExpression(curNode["children"][0]["value"],state)
            if ret: 
                state.env_set["__return__"] = ret # Merging is done automatically
                hist.addEventToHistory(ret, state.functionName,"ret", state.functionName)
            return hist

        # Choice
        elif t == "IfStatement":
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("ic")
            thenState = state.copy()
            hist_then = self._analyseStatement(curNode["children"][0], thenState)
            elseState = state.copy()
            hist_else = self._analyseStatement(curNode["children"][0], state.copy())
            state.mergeIn(thenState,elseState)
            hist.addHistoriesConditional([hist_then,hist_else], state.functionName)

        elif t == "SwitchStatement":
            # TODO: At the moment the test expressions for the cases are ignored.
            # Have to be added later taking into account, that for later cases all previous testexpressions have to be added to the history.
            hist, ret = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("sc")
            condHistories = []
            condStates = []
            for case in curNode["children"][1:]:
                isDefault = len(case["children"]) == 1
                if not isDefault:
                    innerHist, ret = self._analyseExpression(case["children"][0], state)
                    innerHist.tagAsSpecialNode("cc")
                    tmpHist, ret = self._analyseStatement(case["children"][1], state)
                    innerHist.mergeHistoryCollections(tmpHist)
                else:
                    # For default the statement is only child
                    innerHist = self._analyseStatement(case["children"][0], state)
                condHistories.append(tmpHist)
            hist.addHistoriesConditional(condHistories)
            return hist
        
        # Exceptions (ignored at the moment)
        #ThrowStatement
        #TryStatement( CatchClause )
    
        # Loops
        elif t is "WhileStatement" or t is "DoWhileStatement":
            hist = self._analyseExpression(curNode["children"][0], state)
            hist.tagAsSpecialNode("wc")
            tmpHist = self._analyseStatement(curNode["children"][1], state)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)
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
            # Pay attention: the for in for an array only gives the indices!!!!
            # SO NO IDEA HOW TO HANDLE -> maybe a special case
            tmpHist, ret =self._analyseExpression(curNode["children"][1], state)
            tmpHist.tagAsSpecialNode("fh")
            hist.addHistoryCollection(tmpHist)
            tmpHist = self._analyseStatement(curNode["children"][2], state)
            tmpHist.markAsLoopBody()
            hist.addHistoryCollection(tmpHist)

        ### Declarations (handled here toghether with Declarators)
        elif t == "VariableDeclaration":
            # There might be multiple declarators as eg. "var a = 4, b = 5"
            for declarator in [self.ast[node] for node in curNode["children"]]:
                # Create the local variable
                state.env_createLocal(declarator["value"])
                if "children" in declarator:
                    hist, ret = self._analyseExpression(declarator["children"][0], state)
                    state.env_set(self.ast[declarator["value"]], ret)
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
        '''
    
        ### Get Statement and handle each type 
        curNode =self.ast[nodeNumber]
        t = curNode["type"]   

        ### Identifier handled together with expression
        if t in ["Identifier", "Property"]:
            # When value type, None will be the result
            return HistoryCollection(), [curNode["value"]] ##state.env_get(curNode["value"])
        ### Expressions
        elif t == "ThisExpression":
            # the this is only a special local variable
            return HistoryCollection(), state.context
                  
        elif t == "ArrayExpression":
            # Handle as object (returning it as reference makes sense. Since also internally. Creat object and then return reference.)
            state.newObject("array", 0, nodeNumber)
            return newObject
        elif t == "ArrayAccess":
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)      
            # Here history is added to the pts on the left, Noch schauen ob Rückgabe als Pts oder string
           ## ret  = state.heap_get(leftRet, rightRet) Das wird eben dort gemacht, wo man es braucht!
            return hist, [leftRet, rightRet]
        elif t == "ObjectExpression":
            obj = state.newObject("ObjectExpression", 0, nodeNumber) #Todo change TreeID
            hist = HistoryCollection();
            for child in curNode["children"]:
                prop = self.ast[child]
                tmpHist, propertyValue = self._analyseExpression(prop["children"][0], state)
                hist.addHistoryCollection(tmpHist)
                state.heap_add(obj, prop["value"], propertyValue)
            return hist, obj
        elif t == "FunctionExpression": 
            # Is handled by callgraph, just like FunctionDeclaration
            return HistoryCollection(), None

        # Unary operations
        if t == "UnaryExpression":
            # only the history is used ret should already be None since always value
            his, ret = self._analyseExpression(curNode["children"][0], state)
            return his, None
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
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self.analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)
            
            # So now I return the access pathes instead of the values themselves. Like this assignments are not possible to handle
            if len(leftRet) == 1:
                # When only a variable
                state.env_set(leftRet, rightRet)
            else:
                # When multiple access pathes it has to be done over the heap (assume that program correct)
                obj = state.env_get(leftRet)
                for cur in leftRet[1:-1]:
                    obj = state.heap_get(obj, cur)
                state.heap_set(obj, rightRet)
            return hist, rightRet
        elif t == "LogicalExpression":
            hist, leftRet = self.analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self.analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)
            # For an "or" both result values possible, for "and" only second
            if curNode["type"] == "||":
                #TODO: leftRet um rightRet erweitern
                pass
            else:
                # Hinterher anschauen: muss man da irgendwie gucken, ob None als condition?
                return hist, state.getTarget(rightRet)
            
        elif t in "MemberExpression":
            hist, leftRet = self._analyseExpression(curNode["children"][0], state)
            rightHist, rightRet = self._analyseExpression(curNode["children"][1], state) 
            hist.addHistoryCollection(rightHist)            
            hist.addEventToHistory(leftRet, rightRet, 0, state.functionName)
            return hist, [item for sublist in [leftRet, rightRet] for item in sublist ] # flatten accessorlist

        elif t == "ConditionalExpression":
            hist = self.analyseExpression(curNode["children"][0], state, curDepth)
            hist.tagAsSpecialNode("ic")
            hist.addHistoryCollection(tmpHist)
            hist_then, ret_then = self._analyseExpression(curNode["children"][0], state)
            hist_else, ret_else = self._analyseExpression(curNode["children"][0], state)
            hist.addHistoryCollection([hist_then,hist_else]) 
            # Does not matter whether return ret_then or ret_else, since already merged in state
            return hist, ret_else

        elif t == "CallExpression":
            """ Arranges the function call. 
            Looks whether the designated function can be found using the callgraph.
            The corresponding node is then called with env only set to the parameters. 
            
            Functions from FunctionExpressions are exactly identically referenced by callgraph as 
            the functions from FunctionDeclaration. Only difference: Expression has no first child 
            with name.

            The special fields "state.context" and "state.functionName" are additonal information 
            stored in the environment needed for calculation!
            """   
            
            if (self.ast[curNode["children"][0]]["type"] == "FunctionExpression"):
                # Set the function  
                fnNode = self.ast[curNode["children"][0]]

                # Create the subfunction context   
                subfunctionState = state.prepareForSubfunction(state.context, "anonym"+str(nodeNumber))
                for i, param in enumerate(curNode["children"][1:-1]):
                    tmpHist, tmpRet = self._analyseExpression(param, state)
                    hist.addHistoryCollection(tmpHist)    
                    subfunctionState.env_set(fnNode["children"][i+1]["value"],tmpRet)

            elif  (self.ast[curNode["children"][0]]["type"] == "MemberExpression"):
                # Immediatly handled here, because necessary to set the context
                hist, leftRet = self._analyseExpression(curNode["children"][0], state)
                rightHist, rightRet = self._analyseExpression(curNode["children"][1], state) 
                hist.addHistoryCollection(rightHist)      
                
                # Set the function             
                fnNode = self.ast[self.callgraph[curNode["id"]]]

                # Create the subfunction context   
                newState = state.prepareForSubfunction(leftRet, rightRet)
                for i, param in enumerate(curNode["children"][1:-1]):
                    tmpHist, tmpRet = self._analyseExpression(param, state)
                    hist.addHistoryCollection(tmpHist)    
                    subfunctionState.env_set(fnNode["children"][i+1]["value"],tmpRet)

            elif (self.curNode["children"][0]["type"] == "Identifier"):                  
                # Set the function             
                fnNode = self.ast[self.callgraph[curNode["id"]]]
              
                # Create the subfunction context   
                subfunctionState = state.prepareForSubfunction(state.context, curNode["children"][0]["value"])
                for i, param in enumerate(curNode["children"][1:-1]):
                    tmpHist, tmpRet = self._analyseExpression(param, state)
                    hist.addHistoryCollection(tmpHist)    
                    subfunctionState.env_set(fnNode["children"][i+1]["value"],tmpRet)

            else:
                raise("CallExpression has a unknown child for node" + nodeNumber);
            

            # Execute the functions blockstatement (last child)
            fnHist, ret = self._analyseStatement(fnNode["children"][-1], subfunctionState)
            hist.addHistoryCollection(fnHist)
            return hist, ret

        elif t == "NewExpression":
            return state.newObject(self.ast[curNode["children"][0]]["value"], nodeNumber)
            
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
        elif t in ["Literal", "LiteralString", "LiteralRegExp", "LiteralNull", "LiteralNumber"]:
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
    """ Takes ASTs and creates the callgraph for the files
    It takes the asts and creates codefiles from it by using the jsprinter. Then it 
    let jscallgraph create the callgraph. To do so it avoids writing to files, but 
    immediatly passes in the code per commandline. (The source of the jscallgraph has 
    been changed to realize this. See comment in code below.).
    Then the lines and columns of the ASTs are also printed. 
    Finally the results are put together sothat the callgraph is returned immediatly 
    as a mapping from AST node to another AST node. That makes it later easy to lookup 
    functionality.
    Special objects (window, XHTTPRequest, etc. are handled in a special way.). For this 
    I have to ask the creators of JSCallgraph how it is implemented.
    At the moment only a single AST is supported since in the histories testcases only a 
    single AST is given. 
    For the real training purposes later on it might be interesting to read multiple ASTs
    at once (eg. all files of a certain project). Then the js-callgraph is capable of 
    detecting calls across multiple files.
       
    Input:
        filepath:       full path of the file to process including filename 

    Output:
        ast:             the callgraph parsed into the callgraph format (see callgraph class)
        callgrapgh the javascrip code (potentially not interesting for calling functions)
    """
        
    #! I CHANGED THE JS-CALLGRAPH CODE sothat it immediatly reads the input from the argument instead
    # from a separate file. In the implementation below only a single file is taken.
    # In asutils.js -> Line100 in function: buildAST exchange by the following function:
    """ function buildAST(files) {
	source = files[0]
        var ast = {
            type: 'ProgramCollection',
            programs: [],
            attr: {}
        };
        //sources.forEach(function (source) {
            var prog = esprima.parse(source, { loc: true, range: true });
            prog.attr = { filename: "inputfile", sloc : sloc(source, "javascript").sloc};
            ast.programs.push(prog);
        //});
        init(ast);
        ast.attr.sloc = ast.programs
            .map(function(program){
                return program.attr.sloc;
            }).reduce(function(previous, current) {
            return previous + current;
        });
        return ast;
    } """
    
    # Parse the AST
    astFile = open(astFilePath, "r")
    astString = astFile.read()
    ast = json.loads(astString,"r" )


    # Reconstuct the javascript code by saving to file and 
    #p1 = Popen(["/home/pa/desktop/json_printer/bin/syntree/main", "--num_data_records=1","--data=" + astFilePath,"--logtostderr"], stderr=PIPE)
    #jscode = p.stderr.read()
    #filteredJscode= []
    #for i,line in jscode.split("\n"):
    #    if (line.startswith("I0510")):
    #        filteredJscode.add(line); 
    #jscode = ''.join(filteredJscode)
    jscode = "(function()  {\nvar httpRequest;\ndocument.getElementById(\"ajaxButton\").onclick = (function()  {\nmakeRequest(\"test.html\");\n}\n);\nfunction makeRequest(url)  {\nhttpRequest = new XMLHttpRequest();\nif (! httpRequest)  {\nalert(\"Giving up :( Cannot create an XMLHTTP instance\");\nreturn false;\n}\nhttpRequest.onreadystatechange = alertContents;\nhttpRequest.open(\"GET\", url);\nhttpRequest.send();\n}\n;\n}\n)();"

    jscodeLinePositions = [0]
    for line in jscode.split("\n"):
        jscodeLinePositions.append(jscodeLinePositions[-1] + len(line)+2) # PAY ATTENTION +2 bcause of \n Don'T know whether necessary when executing real commands

   
    # Get the mapping from astElements to position in jscode
    #p2 = Popen(["/home/pa/desktop/json_printer/bin/syntree/main", "--num_data_records=1", "--mode=info", "--data=" + astFilePath, "--logtostderr"], stderr=PIPE)
    #astToCodeMapping = p2.stderr.read()
    astToCodeMapping = "Log file created at: 2016/05/28 07:15:13\nRunning on machine: PA\nLog line format: [IWEF]mmdd hh:mm:ss.uuuuuu threadid file:line] msg\nI0528 07:15:13.073760 10443 main.cpp:47] Loading training data...\nI0528 07:15:13.075572 10443 tree.cpp:2010] Parsing done.\nI0528 07:15:13.075584 10443 tree.cpp:2017] Remaining trees after removing trees with more than 30000 nodes: 1\nI0528 07:15:13.075603 10443 main.cpp:50] Training data with 1 trees loaded.\nI0528 07:15:13.075713 10443 main.cpp:62] 0 1 1\nI0528 07:15:13.075716 10443 main.cpp:62] 1 1 1\nI0528 07:15:13.075719 10443 main.cpp:62] 2 1 1\nI0528 07:15:13.075721 10443 main.cpp:62] 3 1 1\nI0528 07:15:13.075723 10443 main.cpp:62] 4 1 13\nI0528 07:15:13.075726 10443 main.cpp:62] 5 2 4\nI0528 07:15:13.075728 10443 main.cpp:62] 6 2 8\nI0528 07:15:13.075731 10443 main.cpp:62] 7 3 4\nI0528 07:15:13.075732 10443 main.cpp:62] 8 3 4\nI0528 07:15:13.075736 10443 main.cpp:62] 9 3 4\nI0528 07:15:13.075737 10443 main.cpp:62] 10 3 4\nI0528 07:15:13.075739 10443 main.cpp:62] 11 3 4\nI0528 07:15:13.075742 10443 main.cpp:62] 12 3 4\nI0528 07:15:13.075744 10443 main.cpp:62] 13 3 13\nI0528 07:15:13.075747 10443 main.cpp:62] 14 3 28\nI0528 07:15:13.075749 10443 main.cpp:62] 15 3 42\nI0528 07:15:13.075752 10443 main.cpp:62] 16 3 52\nI0528 07:15:13.075753 10443 main.cpp:62] 17 3 64\nI0528 07:15:13.075755 10443 main.cpp:62] 18 4 7\nI0528 07:15:13.075758 10443 main.cpp:62] 19 4 7\nI0528 07:15:13.075760 10443 main.cpp:62] 20 4 7\nI0528 07:15:13.075762 10443 main.cpp:62] 21 4 19\nI0528 07:15:13.075765 10443 main.cpp:62] 22 7 4\nI0528 07:15:13.075767 10443 main.cpp:62] 23 7 13\nI0528 07:15:13.075769 10443 main.cpp:62] 24 7 25\nI0528 07:15:13.075772 10443 main.cpp:62] 25 7 30\nI0528 07:15:13.075774 10443 main.cpp:62] 26 8 7\nI0528 07:15:13.075776 10443 main.cpp:62] 27 8 7\nI0528 07:15:13.075778 10443 main.cpp:62] 28 8 7\nI0528 07:15:13.075780 10443 main.cpp:62] 29 8 21\nI0528 07:15:13.075783 10443 main.cpp:62] 30 8 25\nI0528 07:15:13.075785 10443 main.cpp:62] 31 9 7\nI0528 07:15:13.075788 10443 main.cpp:62] 32 9 11\nI0528 07:15:13.075790 10443 main.cpp:62] 33 9 13\nI0528 07:15:13.075793 10443 main.cpp:62] 34 9 26\nI0528 07:15:13.075794 10443 main.cpp:62] 35 10 10\nI0528 07:15:13.075798 10443 main.cpp:62] 36 10 10\nI0528 07:15:13.075799 10443 main.cpp:62] 37 10 10\nI0528 07:15:13.075801 10443 main.cpp:62] 38 10 16\nI0528 07:15:13.075803 10443 main.cpp:62] 39 11 10\nI0528 07:15:13.075806 10443 main.cpp:62] 40 11 17\nI0528 07:15:13.075809 10443 main.cpp:62] 41 13 7\nI0528 07:15:13.075810 10443 main.cpp:62] 42 13 7\nI0528 07:15:13.075814 10443 main.cpp:62] 43 13 7\nI0528 07:15:13.075815 10443 main.cpp:62] 44 13 7\nI0528 07:15:13.075817 10443 main.cpp:62] 45 13 19\nI0528 07:15:13.075819 10443 main.cpp:62] 46 13 40\nI0528 07:15:13.075822 10443 main.cpp:62] 47 14 7\nI0528 07:15:13.075824 10443 main.cpp:62] 48 14 7\nI0528 07:15:13.075826 10443 main.cpp:62] 49 14 7\nI0528 07:15:13.075829 10443 main.cpp:62] 50 14 7\nI0528 07:15:13.075831 10443 main.cpp:62] 51 14 19\nI0528 07:15:13.075834 10443 main.cpp:62] 52 14 24\nI0528 07:15:13.075835 10443 main.cpp:62] 53 14 31\nI0528 07:15:13.075839 10443 main.cpp:62] 54 15 7\nI0528 07:15:13.075840 10443 main.cpp:62] 55 15 7\nI0528 07:15:13.075842 10443 main.cpp:62] 56 15 7\nI0528 07:15:13.075845 10443 main.cpp:62] 57 15 7\nI0528 07:15:13.075847 10443 main.cpp:62] 58 15 19\n" 
   
    astToCodeMappingSplitted = astToCodeMapping.split("\n")[7:]
    astToCodeMapping = []
    for line in astToCodeMappingSplitted:
        astToCodeMapping.append([int(x) for x in line[line.find("]")+2:].split()[1:] ])


    mapping = {} # {1: 3, 38: 10, 86: 16, 105: 19, 136: 22, 232: 36, 354: 48, 385: 55}
    for node in ast[:-1]:
        if node["type"] in ["FunctionExpression", "FunctionDeclaration", "CallExpression"]:
            position = astToCodeMapping[node["id"]]
            mapping[jscodeLinePositions[position[0]-1] + position[1]] = node["id"]
            


    # Preprocess the reconstructed javascript code -> remove log lines etc.
    #q = Popen(["node /home/pa/Desktop/js_call_graph/javascript-call-graph/main.js", "--cg", jscode], stdout=PIPE)
    #callgraph = p.stdout.read()
    callgraph = "IsolatedCode.js@1:1-468 -> IsolatedCode.js@1:1-464\nIsolatedCode.js@3:38-75 -> Document_prototype_getElementById\nIsolatedCode.js@4:107-131 -> IsolatedCode.js@7:144-460\nIsolatedCode.js@8:193-213 -> XMLHttpRequest\nIsolatedCode.js@10:252-307 -> Window_prototype_alert\nIsolatedCode.js@14:400-428 -> Window_prototype_open\nIsolatedCode.js@14:400-428 -> XMLHttpRequest_prototype_open\nIsolatedCode.js@15:436-454 -> XMLHttpRequest_prototype_send\n"

    mappedCallgraph = {}
    for line in callgraph.split("\n"):
        caller, target = line.split(" -> ")
        caller = mapping[ int(caller[caller.find(":")+1:caller.find("-") ]) ]
        if "@" in target:           
            target = mapping[ int(target[target.find(":")+1:target.find("-") ] )]
        mappedCallgraph[caller] = target

    return ast, mappedCallgraph
        

def extract_histories(astsFilePath, testsFilePath):
    """ Extracts histories available in the designated files.

    Input:
    astString:     Path to file containing that contain an abstract syntax tree
    tests:         If the histories shall be reduced 

    Output:
    histories:      List of history objects as a string, formatted like in the paper
    """
    testFile = open(testFilePath, "r")
    
    # Get the corresponding callgraph 
    ast, callgraph = prepare_files(astsFilePath)
    
    # Analyse the given ast with help of the callgraph and return result
    hist_extractor = history_extractor(ast, callgraph)
    hist_extractor.generateHistories()    
    historiesString = hist_extractor.getHistoryString()
    return historiesString








######################################################################
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
    histories = extract_histories(astFilePath,testFilePath)

    # Write the histories
    resultPath = os.path.basename(astFilePath) + "/ResultingHistories"
    histFile = open(resultPath, "rw")
    for hist in histories:
        histFile.write(hist + "\n")