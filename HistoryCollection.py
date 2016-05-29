import copy
from enum import Enum

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
        # Each element can be an event tuple (objectname, eventname, position, context)) or a List of inner HistoryCollections.
        # All HistoryCollections within one List represent parallel execution traces. They emerge during conditonal clauses.
        self.histories = []

        # This flag holds whether this history is the body of a loop. If so, the loop depth of all contained history 
        # events will be incremented by one during history construction.
        self.loopBody = False

        # This attribute notes, whether this history is placed at a special position. So during history generation, this
        # special information can be included into the histories if desired.
        self.specialTag = ""

 

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
            obj:                The abstract object to whose abstract history the event is attached to
            methodSignature:    The name of the function called, which is added to the histories of the pts targets
                                In our solution. Is also allowed to be a property acces. In this case name missleading.
        position:               The position at which the pts appeared
        context:                The functionContext in which the event appeared. This is necessary to stop adding 
                                to histories, that include already a return statement within the context of this function. 
        '''
        self.histories.append((obj,methodSignature, position, contextFunction))


    def addHistoryCollection (self, historyCollection):
        """ Adds another historyCollection to the histories of the calling one.
        If there are multiple histories for the same object do the 
        union, what means doing the crossproduct between the histories.
        Take care that deep copyies.
        The deep encapsulation is necessary since each historyCollection might contain
        additional information.

        Input: 
        historyCollection:  The other HistoryCollection, whose traces shall be 
                            appended to the own ones.
        """
        if not historyCollection.isEmpty():
           # if not historyCollection.loopBody and historyCollection.specialTag == "":
           #     if not historyCollection.isEmpty():
           #         self.histories.append((historyCollection.histories))
           # else
           self.histories.append([historyCollection])


    def addHistoriesConditional (self, historyCollections):
        """ Appends another historyCollection to the calling one in context of a case.
        This functions takes into account that all alternative historyCollections 
        have to be regarded and kept as one possible track.

        Input: 
        historyCollection:  List of HistoryCollection, whose traces shall be 
                            appended to the own ones.
        context:    TODO    The functionContext in which the event appeared. This is necessary to stop adding 
                            to histories, that include already a return within the context of this function.  
        """
        historyCollections = filter(lambda histCollection: histCollection.isEmpty(), historyCollections)
        if len(historyCollections) != 0:
            self.histories.append(historyCollections)


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
        increased by loopingDepth property. 
        '''
        self.loopBody = True




    def toOutputFormat(self, objectCollection):
        """ Returns the created histories in the required format.
        This can be understood as the output function of the history. Since the 
        HistoryCollection only holds as few data as possible during runtime, 
        only here a lot of work has to be done. The combinatorical combination 
        of the parallel execution pathes happens here.

        Input:
            objectCollection:   The histories always reference the abstract objects. Therefore
                                the objectCollection has to be given to be capable to add the history 
                                elements to the true atomar objects.
        
        Output:
            histories:          {objectname : [all its histories]} where each history is a list 
                                of events
                                At this point the objectnames are still the object names. So the class
                                name plus an additional "_number". To finally get the histories for API 
                                Classes, this has to be removed.
        """
        
        
        # The result will be a map from an object to its history
        result = {}
        for element in self.histories:

            # HistoryCollections to add for next Timestep
            # (crossproduct between all execution paths for each object for each parallel HistoryCollection)
            if isinstance(element, (list)):
                newHistories = {}

                for historyCollection in element:
                    innerResult = historyCollection.toOutputFormat(objectCollection)
                    for object in innerResult:
                        if not object in newHistories:
                            newHistories[object] = []

                        # If already in previous history
                        if object in result:
                            # For all but one (the last) the previous history has to be doubled
                            for concreteHistory in innerResult[object]:
                                for concretePreviousHistory in result[object]:
                                    h =  copy.deepcopy(concretePreviousHistory)
                                    h.extend(concreteHistory)
                                    newHistories[object].append(h)
                        else:
                            newHistories[object].extend(innerResult[object])

                # Keep the elements, whose histories were not expanded
                for obj in set(result.keys())-set(newHistories.keys()):
                    newHistories[obj] = result[obj]

                # Optimization would be to not copy the last element but alter the already available histories in result
                result = newHistories

            # Else single real Event :)
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
                                history.append((functioname,pos,self.specialTag))
                    else:
                        result[obj] = [[(functioname,pos,self.specialTag)]]
                                    
        return result


    def isEmpty(self):
        return len(self.histories) == 0