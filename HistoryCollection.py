import copy

#from enum import Enum
#class SpecialTags(Enum):
#    ic = 1 # If Condition
#    sc = 2 # Switch Condition
#    cc = 3 # Case Condition
#    wc = 4 # WhileCondition
#    fh = 5 # ForHeader
#    ec = 6 # Condition of an ConditionalExpression
#    on = 7 # When the code is executed in an on-Event


class HistoryCollection(object):
    '''
    This is the central class that administrates the available histories.
    -It has functions to add new events to the history of specific objects. 
     Doing so it contains additional logic to handle return statements.
    -Further it offers functions to merge the HistoryCollections returned from the distinct child nodes.
    -Finally it contains the stringification function, that returns the whole history in the 
     required output format, described in the paper.
    '''


    def __init__(self):
        ''' Creates a new initial historyCollection '''
        # List of encapsulated HistoryCollections. The order of the list corresponds to the order of events in time. 
        # Each element can be an atomic event tuple (objectname, eventname, position, context)) or a List of inner HistoryCollections.
        # All HistoryCollections within one inner List represent parallel execution traces. They emerge during conditonal clauses.
        self.histories = []

        # This flag holds whether this history is the body of a loop. If so, the loop depth of all contained history 
        # events will be incremented by one during history construction.
        self.loopBody = False

        # This attribute notes, whether this history is placed at a special position. So during history generation, this
        # special information can be included into the histories if desired.
        self.specialTag = "-"

 

    def addEventToHistory (self, obj, methodSignature, position, contextFunction):
        ''' Adds an event of an object to the history.
        Used within the nodes, where something is executed.
        The contextFunction is necessary to handle return statements- 
        Special-tag  and loopDepth for the event are later determined by setting this value for the whole
        historyCollection
        
        To get it right: This function is only used in nodes where execution happens, mostly child nodes. 
        In all other cases only the resulting HistoryCollections of the children are merged. Like this
        the complete history is built recursively.

        Input: 
            obj:                The abstract object to whose abstract history the event belongs to. It is really the 
                                abstract object and will be later during history processing assigned to all the 
                                corresponding concrete objects.
            methodSignature:    The name of the function called, which is added to the histories of the abstract object.
                                Is also allowed to be a property acces. (Yes... it shouldn't be called methond then! ;) )
            position:           The position at which the operation appeared
            context:            The functionContext in which the event appeared. This is necessary to stop adding 
                                to histories, that include already a return statement within the context of this function. 
        '''
        self.histories.append((obj,methodSignature, position, contextFunction))



    def addHistoryCollection (self, historyCollection):
        """ Adds another historyCollection to the histories of the calling one.
        This is done by storing this history collection in the list of the parent historyCollection.
        The deep encapsulation is necessary since each historyCollection might contain
        additional information.

        Input: 
        historyCollection:  The other HistoryCollection, whose traces shall be 
                            appended to this one.
        """
        if not historyCollection.isEmpty():
           self.histories.append([historyCollection])


    def addHistoriesConditional (self, historyCollections):
        """ Appends other historyCollections to the calling one, looking onto it as 
        a case. That means the histories are appended as parallel histories, to handle 
        later on the correct history reconstruction.

        Input: 
            historyCollections:     List of HistoryCollection, whose traces shall be 
                                    appended to the own ones.
        """
        emptyHistFound = False
        filteredCollection = []
        for hist in historyCollections:
            if not hist.isEmpty():
                filteredCollection.append(hist)
            else:
                emptyHistFound = True
        if emptyHistFound:
            filteredCollection.append(HistoryCollection())
        if len(filteredCollection) >= 2:
            self.histories.append(filteredCollection)


    def tagAsSpecialNode(self, tag):
        ''' Marks this HistoryCollection with a special tag.
        Usecase is for example the expression inside an if-condition
        
        Input: 
            tag: string - the special tag ("fh", "wc", "ic", "sc")
        '''
        self.specialTag = tag


    def markAsLoopBody(self):
        ''' Marks this history as a loopBody. 
        This causes all contained events to have a by one 
        increased loopingDepth property later during history 
        construction.
        '''
        self.loopBody = True




    def toOutputFormat(self, objectCollection):
        """ Do the postprocessing for created history
        So out of the recursive temporal datastructure, creates the 
        final output format with concrete histories per object.
        For this all the things like crossproduct for all conditional 
        parallel execution pathes are taken into account.
        Remove empty results and anonymous objecs, that were not used.

        Input:
            state:  The state that was built together with the history.
                    Used to resolve the abstract objects into the concrete ones.
        """
        history = self._toOutputFormatInner(objectCollection, 0)

        # Remove empty traces
        for obj in history:
            history[obj] = [concreteTrace for concreteTrace in history[obj] if len(concreteTrace) > 0]

        # Remove unused anonymous objects
        resultHistory = {}
        for obj in history: #TODO PROLEM!
            if not obj.startswith("anonymous"):
                resultHistory[obj] = history[obj]
            else:
                # anonymous objects, that are used are kept
                for concreteTrace in history[obj]:
                    if (len(concreteTrace) > 1):
                        resultHistory[obj] = history[obj]
                        continue

        return resultHistory


    def _toOutputFormatInner(self, objectCollection, loopdepth):
        """ Returns the created histories in the required format.
        This can be understood as the output function of the history. Since the 
        HistoryCollection only holds as few data as possible during runtime, 
        only here a lot of work has to be done. The combinatorical combination 
        of the parallel execution pathes happens here.

        Input:
            objectCollection:   The histories always reference the abstract objects. Therefore
                                the objectCollection has to be given to be capable to add the history 
                                elements to the true atomar objects.
            loopdepth:          To set the looping depth properly
        
        Output:
            histories:          {objectname : [all its histories]} where each history is a list 
                                of events
                                At this point the objectnames are still the object names. So the class
                                name plus an additional "_number". To finally get the histories for API 
                                Classes, this has to be removed.
        """

        # When no events here, at least return empty history for handling cases
        if len(self.histories) == 0:
            return {}

        # For all further calculations set loopdepth one deeper
        if (self.loopBody):
            loopdepth = loopdepth + 1

        # The result will be a map from an object to its history
        result = {}
        for element in self.histories:

            # HistoryCollections to add for next Timestep
            # (crossproduct between all execution paths for each object for each parallel HistoryCollection)
            if isinstance(element, (list)):
                newHistories = {}

                # First gather all inner results to collect all objects (necessary for not handled cases)
                objects = set(result.keys())
                innerResults = []
                for historyCollection in element:
                    innerResults.append(historyCollection._toOutputFormatInner(objectCollection, loopdepth))
                for objs in innerResults:
                    objects.update(objs.keys())
                for existingObj in objects:
                    newHistories[existingObj] = []

                # Then go through all histories and for each of the objects, add an empty statement or the existing one
                emptyCaseHandled = set()
                for innerResult in innerResults:
                    for existingObj in objects:
                        if existingObj in innerResult:
                            if existingObj in result:
                                for concreteHistory in innerResult[existingObj]:
                                    for concretePreviousHistory in result[existingObj]:
                                        h =  copy.deepcopy(concretePreviousHistory)
                                        h.extend(concreteHistory)
                                        newHistories[existingObj].append(h)
                            else:
                                newHistories[existingObj].extend(innerResult[existingObj])
                        elif not existingObj in emptyCaseHandled:
                            # Add the empty case only one time
                            emptyCaseHandled.add(existingObj)
                            if existingObj in result:
                                # When not in coditional path, keep previous trace
                                newHistories[existingObj].extend(result[existingObj])
                            else:
                                # Or at least add an empty execution
                                newHistories[existingObj].append([])

                # Optimization would be to not copy the last element but alter the already available histories in result
                result = newHistories


            # Else single real Event
            else:
                # Fist map the abstract objects to the real objects
                obj,functioname,pos,contextFn = element 
                objs = objectCollection.getConcreteObjects(obj)
                for obj in objs:
                    if obj in result:
                        for history in result[obj]:
                            # Take care that events are not added, when in the specific
                            # history already a ret appeared for that function
                            if not (history[-1][2] == "ret" and history[-1][1] == contextFn):
                                history.append((functioname,pos, loopdepth, self.specialTag))
                    else:
                        result[obj] = [[(functioname, pos, loopdepth, self.specialTag)]]
                                    
        return result



    def isEmpty(self):
        ''' Returns whether this historyCollection does not contain events '''
        return len(self.histories) == 0