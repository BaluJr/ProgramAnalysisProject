import copy

class State(object):
    """ This class handles the mapping of the objects
    and the Heap. It is reasonable to do this within one file, since the merging always 
    concerns both parts.
    """
    
    
    def __init__(self):
        # In paper: OBJECTS L --
        # The mappings from an object to the one level more abstract one
        self.objectToMoreAbstractObject = {}
        # Another mapping containing for each object a set of all concrete objects included in the abstraction
        self.abstractObjectToObjects = {}    # Remember for all abstr. objects the set of  atomar objects they contain

        # In paper: HEAP -- 
        # Holds the most abstract objects. 
        # Mapping of object/array fields to objects. Handles the references to the other objects.
        self.heap = {"window-0:0": {}, "document-0:0": {}}
        
        # In paper: ENV --
        # Environment is split into the local and global one
        self.localEnvironment = {"__return__": None}
        self.globalEnvironment = {"window": "window-0:0", "document": "document-0:0", "__this__": "window-0:0"}
        
        # Two special fields necessary for administration
        self.functionName = "lambdaExpression"
        self.context = "window-0:0"



    ########################################################################
    # From OBJECTS L  

    def newObject(self, objectClass, astId, astNodeId):
        ''' Returns the name of a new object
        The object ID is created by concatenating its class name with its astID and NodeId in the AST.
        Like this when creating the histories both necessary kinds of histories can be generated.
        By letting away the object name, one gets histories for classes used for learning.
        By letting away the class name on the other hand, eables searches for histories after specific positions in the ast

        Input:
            objectClass:    The class from which the object instantiated
            astId:          The class from which the object instantiated
            astNodeId:      The class from which the object instantiated

        Output:
            objName:        The obj name as "objectClass_astId:astNodeId"
        '''
        name =  objectClass + "-" + str(astId) + ":" + str(astNodeId)
        self.heap[name] = {}
        return name



    def mergeObjects(self, objs):
        """ Merges two most abstract objects to a new most abstract one.
        Does it for the mappings as well as for the heap. By adding the new mapping to the 
        objects dictionary, the recursive search of the most abstract version in _getAbstractObject 
        ends up finding the new abstract object for a concrete object, without having to alter the 
        existing references. Therefore the environment does not have to be altered.
        Important: The name for the merged object has to be deterministically created sothat 
        they are always in order. Otherwise the merging of multiple states would fail!

        Input:
            objs:   List of abstract (or concrete) objects to merge
        """

        objs = [obj for obj in objs if obj != None]
        if len(objs) == 0:
            return None

        # Determine which most abstract objects have to be merged
        mostAbstractObjs = set()
        for obj in objs:
            mostAbstractObjs.add( self.getAbstractObject(obj) )
        if len(mostAbstractObjs) == 1:
            return

        # Update the mappings
        newMostAbstractObj = '-'.join(mostAbstractObjs)
        concretesInNewObject = set()
        for mostAbstractObj in mostAbstractObjs:
            self.objectToMoreAbstractObject[mostAbstractObj] = newMostAbstractObj
            concretesInNewObject.update(self.getConcreteObjects(mostAbstractObj))
        self.abstractObjectToObjects[newMostAbstractObj] = concretesInNewObject

        # Update the heap
        fieldValues = {}
        self.heap[newMostAbstractObj] = {}
        for obj in mostAbstractObjs:
            for field in self.heap[obj]:
                self.heap[newMostAbstractObj][field] = self.heap[obj][field]
                if not field in fieldValues:
                    fieldValues[field] = set([self.heap_get(obj, field)])
                else:
                    fieldValues[field].add(self.heap_get(obj,field))

        # When now new overlapping objects, another merge necessary
        sets = list(fieldValues.values())
        sets.sort(key=len, reverse=True)
        for setOfItemsToMerge in sets:
            if len(setOfItemsToMerge) > 1:
                self.mergeObjects(setOfItemsToMerge)
            else:
                break



    def getAbstractObject(self, obj):
        """ Returns the name of the most abstract object, into which the given object has been merged.
        This works as a recursive search. For each concrete and abstract object the id of the 
        next more abstract object is stored, into which it has been merged. 

        Input: 
            obj:    The object for which we want to get the most abstract one
        """
        if obj == None:
            return None
        while (obj in self.objectToMoreAbstractObject):
            obj = self.objectToMoreAbstractObject[obj]
        return obj

    
    def getConcreteObjects(self, obj):
        """ Returns the list ob concrete objects, contained within the 
        given abstract object 
        
        Input:
            obj:            The abstract object for which the abstracted objects 

        Output:
            concreteObjs:   List of the concrete objects, abstracted by this 
                            object
        """
        if obj in self.abstractObjectToObjects:
            return self.abstractObjectToObjects[obj]
        else:
            # In case the object is not abstract
            return set([obj])





    ########################################################################
    # From HEAP    

    def heap_add(self, obj, field, target):
        """ Adds a field to the designated object.
        Objects references are only added, since we are flow insensitive 
        and a target is never removed. 

        Input: 
            obj:        The object whose field is assigned to
            field:      The field that is assigned to
            target:     The object, that is assigned to the field
        """
        if target == None:
            return 

        # Add to heap
        if not obj in self.heap:
            self.heap[obj] = {field: target}
        else:
            if not field in self.heap[obj] or self.heap[obj] == None:
                self.heap[obj][field] = target
            else:
                # When there was already element at positin do merge
                self.mergeObjects([self.heap[obj][field], target])

    def heap_get(self, obj, field):
        """ Returns the current set referen 

        Input: 
            object:     The object whose field shall be requested
            field:      The name of the field to request
        """

        if obj in self.heap and field in self.heap[obj]:
            return self.getAbstractObject(self.heap[obj][field])
        else:
            return None




    
    ########################################################################
    # From ENVIRONMENT

    def env_get(self, var):
        '''Looks for existance of a variable in environment
        Returns local one if exists. Else global one. Else None.
        The result immediatly points to the most abstract object.

        Input:
            var:    The variable to look for

        Return:
            abtrObj:    The abstract object, the variable points to
        '''

        if var in self.localEnvironment:
            return self.getAbstractObject(self.localEnvironment[var])
        elif var in self.globalEnvironment:
            return self.getAbstractObject(self.globalEnvironment[var])
        else:
            self.globalEnvironment[var] = None
            return None


        
    def env_createLocal (self, name):
        ''' Creates a variable in the local environment

        Input:
            name:   The name of the new variable
        '''
        self.localEnvironment[name] = None



    def env_set (self, var, val):
        ''' Sets a variable in the environment
        If it does not exist in the local environment, sets it within the 
        global one.

        Input:
            var:    The variable to assign to.
            val:    The value to sbe assigned to the variable.
        '''
        if var in self.localEnvironment:
            if self.localEnvironment[var] != None:
                # Ok to keep the old link, since recursive search handles it.
                newObj = self.mergeObjects([self.localEnvironment[var], val])
            else:
                self.localEnvironment[var] = val
        else:
            if var in self.globalEnvironment and self.globalEnvironment[var] != None:
                # Ok to keep the old link, since recursive search handles it.
                newObj = self.mergeObjects([self.globalEnvironment[var], val])
            else:
                self.globalEnvironment[var] = val






    ########################################################################
    # General
    def getTarget(self, accessorList):
        """ Returns the returning value for a concatenation of accessors
        This has been introduced in the very end since was necessary for 
        eg. assignment, that the accessor lists are returned and not the 
        objects themselves.
        If only one accessor, it is a variable. For two accessors, the first
        one is the object and the second one its field. Other cases are not
        posible since cascaded field accesses are devided into multiple
        MemberExpressions.

        Input: 
            accessorList:   List of one or two accessors
        """

        # This is a preparation in case we go over to handle literals
        if isinstance(accessorList, (int, float, bool)):
            return None

        # When already a concrete object
        if not isinstance(accessorList, (list)):
            return accessorList

        # Return the target
        if len(accessorList) == 1:
            result = self.env_get(accessorList[0])
        else:
            result = self.heap_get(accessorList[0], accessorList[1])

        return self.getAbstractObject(result)



    def prepareForSubfunction(self, functionContext, functionName):
        ''' Returns a new state for a subfunction
        It copies the global environment to the new state 
        but discards the local one. It also adapts the special fields for 
        remembering the name and context to the given values
        Since everything is given as reference and not deep-copied, the 
        orgininal state will be properly adapted by what is happening 
        in the subfunction (changes in global environment, heap and objects)

        Input:
            functionContext:    The context (target of this) the function is called in
            functionName:       The name of the function itself (later used for handling ret properly)

        Output:
            subfunctionState:   The new state for the subfunction
        '''
        subfunctionState = State()
        subfunctionState.globalEnvironment = self.globalEnvironment
        subfunctionState.abstractObjectToObjects = self.abstractObjectToObjects
        subfunctionState.objectToMoreAbstractObject = self.objectToMoreAbstractObject
        subfunctionState.heap = self.heap
        subfunctionState.functionName = functionName
        subfunctionState.context = functionContext
        return subfunctionState



    def copy(self):
        ''' Returns a copied state
        It deep copies all components of the original history to the new one to
        create a completly independet equal state.
        Used for handling parallel execution traces in conditional clauses.

        Output:
            copiedState:        A equal but independent new state 
        '''
        copiedState = State()
        copiedState.heap = copy.deepcopy(self.heap)
        copiedState.localEnvironment = copy.deepcopy(self.localEnvironment)
        copiedState.globalEnvironment = copy.deepcopy(self.globalEnvironment)
        copiedState.abstractObjectToObjects = copy.deepcopy(self.abstractObjectToObjects)
        copiedState.objectToMoreAbstractObject = copy.deepcopy(self.objectToMoreAbstractObject)
        copiedState.heap = copy.deepcopy(self.heap)
        copiedState.context =self.context
        copiedState.functionName = self.functionName
        return copiedState



    def mergeIn(self, newStates):
        ''' Merges the given states into this state.
        Merges in the states by taking care to merge the declared 
        variables and heap declarations. If necessary merges objects.
        
        Input:
            states: List of other states to merge in
        '''
        # Extend Env by new variables (Does not matter whether new or old object, since both will end up in same abstraction object)

        for newState in newStates:
            self.globalEnvironment.update(newState.globalEnvironment)
            self.localEnvironment.update(newState.localEnvironment)

        # Extend Heap (Does not matter whether new or old object, since both will end up in same abstraction object)
        for newState in newStates:
            for object in newState.heap:
                if object in self.heap:
                    self.heap[object].update(newState.heap[object])
                else:
                    self.heap[object] = newState.heap[object]

        # Here the magic happens. When we merge here, all the references above will also point to these objects
        for newState in newStates:
            for abstrObj in newState.heap: # go through all most-abstract objects
                concreteObjsSet = newState.getConcreteObjects(abstrObj)
                for concObj in concreteObjsSet:
                    prevAbstrObj = self.getAbstractObject(concObj)
                    # TODO: Test whether again set is necessary
                    objsToMerge = set(concreteObjsSet) - set(self.getConcreteObjects(prevAbstrObj))
                    for objToMerge in objsToMerge:
                        self.mergeObjects([prevAbstrObj, objToMerge])
