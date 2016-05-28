# Die HistoryCollections sind fertig. Jetzt muss ich noch überlegen, wie ich das mit den ObjectCollections und Env mache.
# Die Sache ist, dass ich das zusammenmergen zu den komplexeren Objekten irgendwie regeln muss.
# OK habe DIE Strategie. Die mache ich heute auch noch fertig!!!

# Das merging passiert hier automatisch ohne dass es nach aussen auffällt. Muss es ja auch nicht, da die Env nicht geändert wird und die 
# Hist uach einfach die referenzen nimmt, die sie rein bekommt. Dh wir brauchen die folgenden Funktionen:
#
# newObject(class):             Gibt einen eindeutigen Namen für ein neues Objekt der Klasse zurück. Interner Counter für Nummerierung (Integer Overflow nicht behandelt)
# _getMostAbstractObject(obj):  Gibt für ein Objekt das abstrakteste zurück (Das ist nur intern da von aussen nicht gebraucht. Getter geben alle automatisch das abstrakteste aus
# _getConcreteObjects           Gibt für ein Objekt alle enthaltenen Konkreten zurück. (Das wird nur gebraucht (Braucht man auch nur intern)
# getAbstractToConcreteMapping: Das ist quasi die ausgabefunktion, die am ende noch ausgegeben wird und der Historybildung mit auf den Weg gegeben wird! :)
#
# heap_Add(obj, fiel, target): Fügt link hinzu. Wenn es das schon im Heap gibt, wird target und das vorherige Objekt automatisch gemerged
# heap_Get(obj, field): Gibt (sofort) das abstrakteste Objekt zurück
#
# env_Add(var, value):          Fügt variablen Wert zu. Ggf automatisches mergen wenn es die schon gibt.
# env_CreateLocal():            Legt variable in localer Environment an. Fehler, dass mehrfach anlegung wird nich behandelt
# env_Get(var):                 Gibt (sofort) das abstrakteste Objekt zurück.
# [env.prepareForSubfunction]:  siehe unten! 
#                                   
# copy():                       Kopiert alles um es in einem SwitchCase den versch. Cases mitzugeben
# prepareForSubfunction():      Resetted den lokalen Teil der Environment, da die Subfunktion ja in neuer Umgebung. Muss nur beim Übergeben in den PArameter angebeben werden. Gut ist, da das andere Listen sind und daher ByReference, reicht es wenn das in der Subfunktion in dem kopieren Objekt behandelt wird.  Dann ist es auch in dem originalen aktuell.
# merge(States[]):              Die schwierigste funktion. schaut was in den verschiedenen Strängen geändert wurde und merged objekte die sich nun überlappen.
#
# => Bam! Mehr braucht es nicht! Und dann ist auch direkt alles in einem Objekt drin!

class State(object):
    """ This class handles the mapping of the objects
    and the Heap. It is reasonable to do this within one file, since the merging always 
    concerns both parts.
    Handling arrays should work as well since it is rather improbable that objects are assigned 
    to an array in a loop.
    """
    
    
    def __init__(self):
        # From OBJECTS L
        # The mappings from an object to the one level more abstract one
        self.objectToMoreAbstractObject = {}
        # Another mapping containing for each object a set of all concrete objects included in the abstraction
        self.mostAbstractObjects = set()     # The set of the most abstract objects so far (necessary for fast merging of states)
        self.abstractObjectToObjects = {} # Remember for all objects to which objects they split (like an archive)

        # From HEAP  
        # The mapping of object/array fields to objects. Handles the references to the other objects.
        self.heap = {}
        
        # From ENV
        # Environment is split into the local and global one
        self.localEnvironment = {}
        self.globalEnvironment = {"window": {}, "document": {}, "__this__": {}} #Muss mir noch ueberlegen wie ich window und global vereinheitliche
        # Two special fields necessary for administration
        self.functionName = None
        self.context = "window"



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
            objName:        "objectClass_astId:astNodeId"
        '''
        return objectClass + "_" + astId + ":" + astNodeId



    def mergeObjects(self, obj1, obj2): 
        """ Merges two objects to a new abstract one within this state.
        Does it for the mappings as well as for the heap. By adding the new mapping to the 
        objects dictionary, the recursive search of the most abstract version in _getAbstractObject 
        ends up finding the new abstract object for a concrete object, without having to alter the 
        existing references. Therefore the environment does not have to be altered.
        Important: The name for the merged object has to be deterministically created sothat 
        they are always in order. Otherwise the merging of multiple states will fail!

        Input:
            obj1:   The identifier of the first object to merge.
            obj2:   The identifier of the second object to merge.
        """

        # First determine which objects have to be merged
        mappings = {obj1: obj1+obj2, obj2: obj1+obj2}
        mergings = [(obj1+obj2, set(obj1, obj2))]
        newMergings = [set(obj1, obj2)] #, obj...)], set(obj3, obj9)]
        # Go through all new 
        while newMergings:
            # Note the merge of the objects
            for newMerging in newMergings:
                fieldValues = {} # from field to set
                for obj in newMerging:
                    for field in heap[newMerging]:
                        if not field in fieldValues:
                            fieldValues[field] = set(heap[newMerging][field])
                        else:
                            fieldValues[field].add(heap[newMerging][field])

            for field in fieldValues:
                if len(fieldValues[field]) > 1:
                    newMergings.append(fieldValues[field])

        # Then do the merging
        for merging in mergings:
            newObj = {}
            for prevObj in merging[2]:
                for field in prevObj:
                    if prevObj[field] in mappings:
                        target = mappings[prevObj[field]]
                    else:
                        target = prevObj[field] 
                    newObj["field"] = target
        # Remember the new mappings in the official mapping list
        for mapping in mappings:
            objects[mapping] = mappings[mapping]


    def _getAbstractObject(self, obj):
        """ Returns the name of the most abstract object, the given object has been merged into.
        This works as a recursive search. For each concrete and abstract object the id of the 
        next abstract object is stored, into which it has been merged. 

        Input: 
            obj:    The object for which we want to get the most abstract 
        """
        while (obj in self.objects):
            obj = self.objects[obj]
        return obj

    
    def _getConcreteObjects(self, obj):
        """ Returns the list ob concrete objects, abstracted by the 
        given abstract object 
        
        Input:
            obj:            The abstract object for which the abstracted objects 

        Output:
            concreteObjs:   List of the concrete objects, abstracted by this 
                            object
        """
        if obj in mostAbstractObjectToObjects:
            return mostAbstractObjectToObjects[obj]
        elif obj in intermediateAbstractObjectToObjects:
            return intermediateAbstractObjectToObjects[obj]
        else:
            # The object is not abstract
            return obj


    def getTarget(self, accessorString):
        """ Returns the returning value for a concatenation of accessors
        This has been introduced in the very end since was necessary for 
        eg. assignment, that the accessor lists are returned and not the 
        objects themselves.
        Muss ich noch gucken ob das so klappt! Irgendwie könnte ich 
        mit variablen und objekten durcheinander kommen. 
        Bei einem new Statement zB. gebe ich ja ein Element zurück, das ein Objekt
        repräsentiert. Aber ansonsten gehe ich davon aus dass es eine Variable ist
        -> also muss ich unterscheiden zwischen Liste die Zugriffe repräsentiert und 
        Einzelobjekt wenn es keine Liste ist!
        """
        # when already an object is given
        if not isinstance(accessorString, (accessorString)):
            return accessorString

        if len(accessorString) == 0:
            return env_get(accessorString[0])
        else:
            obj = state.env_get(accessorString[0])
            for cur in accessorString[1:-1]:
                obj = state.heap_get(obj, cur)
            return self.heap_get(obj, accessorString[-1])



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

        if not obj in objects:
            objects[obj] = {}
        if not field in objects[obj]:
            objects[obj][field] = set()
        #nee! HAlt! Das führt sofort zu einem merge! Ah das ist genau was wir bei dem dereferencing hatten. 
        
        objects[obj][field].add(target)


    def heap_get(self, obj, field):
        """ Returns the current set referen 

        Input: 
            object:     The object whose field shall be requested
            field:      The name of the field to request
        """
        # Add to the local dictionary of objects
        if obj in self.heap and field in self.heap[obj]:
            return self._getAbstractObject(self.heap[obj])
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
            pts:    The abstract object, the variable points to
        '''

        if var in self.localEnvironment:
            return self._getAbstractObject(self.localEnvironment[var])
        elif var in self.globalEnvironment:
            return self._getAbstractObject(self.globalEnvironment[var])
        else:
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
            self.localEnvironment[var] = val
        else:
            self.globalEnvironment[var] = val






    ########################################################################
    # General
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
        subfunctionState.mostAbstractObjects = self.mostAbstractObjects
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
        copiedState.heap = copy.deepCopy(self.heap)
        copiedState.localEnvironment = copy.deepCopy(self.localEnvironment)
        copiedState.globalEnvironment = copy.deepCopy(self.globalEnvironment)
        copiedState.mostAbstractObjects = copy.deepCopy(self.mostAbstractObjects)
        copiedState.abstractObjectToObjects = copy.deepCopy(self.abstractObjectToObjects)
        copiedState.objectToMoreAbstractObject = copy.deepCopy(self.objectToMoreAbstractObject)
        copiedState.heap = copy.deepCopy(self.heap)
        copiedState.context =self.context
        copiedState.functionName = self.functionName
        return copiedState


    def mergeIn(self, newStates):
        ''' Merges the given states into the state.
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
                    self.heap.update(object)
                else:
                    self.heap = object

        # Here the magic happens. When we merge here, all the references above will also point to these objects
        for newState in newStates:
            for abstrObj in newState.mostAbstractObjectToObjects:
                concObjsSet = newState._getConcreteObj(abstrObj)
                for concObj in concObjsSet:
                    prevAbstrObj = self._getAbstractObject(concObj)
                    objsToMerge = concObjSet - self._getConcreteObjects(prevAbstrObj)
                    for objToMerge in objsToMerge:
                        self.mergeObjects(prevAbstrObj, objToMerge)
            self.mostAbstractObjectToObjects.update(abstrObj)


#TODO: Noch die aufsplittung beim Merge von Objekten in alt und neu!
