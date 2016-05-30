class UnionFind: 
    def __init__(self): 
        self.objects = {} 
        self.count = 0 
        
    def insert_objects(self, objects): 
        for i in objects: 
            self.find(i) 
            
    def find(self, a): 
        if not a in self.objects: 
            self.objects[a] = {a:1}  # 1 because needs placeholder
            self.count += 1 
        return id(self.objects[a])  #Id is builtin
        
    def union(self, a, b): 
        if self.find(a) != self.find(b): 
            la = len(self.objects[a]) 
            lb = len(self.objects[b]) 
            if la > lb: 
                a, b = b, a 
            self.objects[b].update(self.objects[a])  # Update erweitert dictionary. 
            self.objects[a] = self.objects[b] 
            self.count -= 1 
                
    def __str__(self): 
        outp = {} 
        for i in self.objects.itervalues():
            outp[id(i)] = i 
            out = [] 
            for i in outp.values(): 
                out.append(str(i.keys())) 

            return ', '.join(out)




        # For parsing the old version of js_printer
        #    # In case it is the last log line take the part behind the "]"
        #    if not lines[i+1].startswith("I0510"):
        #        filtered_lines.add(line[line.find("]")+1:])
        #else:    


















##########################################################################################
# from Env
##########################################################################################
class Env(object):
    """ Models the variable environment of the execution
    Since we have a difference between global and local environment, this class is 
    used as an encapsulation of that logic.
    It overtakes functionality like firstly look onto the local environment and only afterwards looking onto the global one.
    """

    localEnvironment = {}

    globalEnvironment = {}



    def get(self, var):
        '''Looks for existance of a variable in environment
        Returns local one if exists. Else global one. Else None.
        Is the original object, which has been assigned. Afterwards
        the object might have to be looked up in the ObjectCollection
        too look for the currently most abstract one it is included in.

        Input:
            l_env:  The local environment at place where function called
            var:    The variable to look for

        Return:
            pts:    The abstract object, the variable points to
        '''

        if var in localEnvironment:
            return localEnvironment[var]
        elif var in globalEnvironment:
            return globalEnvironment[var]
        else:
            return None



    def createLocal (name):
        ''' Creates a variable in the local environment

        Input:
        name:   The name of the new variable
        '''
        localEnvironment[name] = None



    def set(self, var, val):
        ''' Sets a variable in the environment
        If it does not exist in the local environment, sets it within the 
        global object window.

        Input:
            var:    The variable to look for
            val:    The value to set the variable to.
        '''
        if var in localEnvironment:
            localEnvironment[var] = val
        else:
            globalEnvironment[var] = val



    def newEnvForSubfunction(self):
        ''' Returns a new environment
        It copies the global environment to the new Env-object 
        but discards the local one.
        '''

        newEnv = Env()
        newEnv.globalEnvironment = copy.deepCopy(self.globalEnvironment)
        return newEnv







        

##########################################################################################
# from ObjectCollection
##########################################################################################
# Die HistoryCollections sind fertig. Jetzt muss ich noch überlegen, wie ich das mit den ObjectCollections und Env mache.
# Die Sache ist, dass ich das zusammenmergen zu den komplexeren Objekten irgendwie regeln muss.
# OK habe DIE Strategie. Die mache ich heute auch noch fertig!!!

# Das merging passiert hier automatisch ohne dass es nach aussen auffällt. Muss es ja auch nicht, da die Env nicht geändert wird und die 
# Hist uach einfach die referenzen nimmt, die sie rein bekommt. Dh wir brauchen die folgenden Funktionen:
# heap_Add(obj, fiel, target): Fügt link hinzu. Wenn es das schon im Heap gibt, wird target und das vorherige Objekt automatisch gemerged
# heap_Get(obj, field): Gibt (sofort) das abstrakteste Objekt zurück
#
# env_Add(var, value):          Fügt variablen Wert zu. Ggf automatisches mergen wenn es die schon gibt.
# env_CreateLocal():            Legt variable in localer Environment an. Fehler, dass mehrfach anlegung wird nich behandelt
# env_Get(var):                 Gibt (sofort) das abstrakteste Objekt zurück.
# [env.prepareForSubfunction]:  siehe unten! 
#                                   
#
# newObject(class):             Gibt einen eindeutigen Namen für ein neues Objekt der Klasse zurück. Interner Counter für Nummerierung (Integer Overflow nicht behandelt)
# _getMostAbstractObject(obj):  Gibt für ein Objekt das abstrakteste zurück (Das ist nur intern da von aussen nicht gebraucht. Getter geben alle automatisch das abstrakteste aus
# _getConcreteObjects           Gibt für ein Objekt alle enthaltenen Konkreten zurück. (Das wird nur gebraucht (Braucht man auch nur intern)
# getAbstractToConcreteMapping: Das ist quasi die ausgabefunktion, die am ende noch ausgegeben wird und der Historybildung mit auf den Weg gegeben wird! :)
#
# copy():                       Kopiert alles um es in einem SwitchCase den versch. Cases mitzugeben
# prepareForSubfunction():      Resetted den lokalen Teil der Environment, da die Subfunktion ja in neuer Umgebung. Muss nur beim Übergeben in den PArameter angebeben werden. Gut ist, da das andere Listen sind und daher ByReference, reicht es wenn das in der Subfunktion in dem kopieren Objekt behandelt wird.  Dann ist es auch in dem originalen aktuell.
# merge(States[]):              Die schwierigste funktion. schaut was in den verschiedenen Strängen geändert wurde und merged objekte die sich nun überlappen.
#
# => Bam! Mehr braucht es nicht! Und dann ist auch direkt alles in einem Objekt drin!

class ObjectCollection(object):
    """ This class handles the mapping of the objects
    and the Heap. It is reasonable to do this within one file, since the merging always 
    concerns both parts.
    
    Handling arrays should work since it is rather improbable that objects are assigned to an 
    array in a loop.
    """

    # The mappings from an object to the one more abstract one
    objectToMoreAbstractObject = {}

    # Another mapping containing for each object a set of all concrete objects included in the abstraction (immetiatly to 
    abstractObjectToObjects = {}

    # The mapping of object/array fields to objects. Handles the references to the other objects.
    heap = {}

    #a
    #a.l = p
    #a.g = q
    #a.n = z

    #b 
    #b.m = p
    #b.n = v

    #z
    #z.r = a

    #v
    #v.r = p

    # Merging der Klassen hierüber: 
    # a mit b mergen -> temporaeres a&b
    # z mit v mergen -> temporaeres z&v
    # a>a&b mit r mergen -> temporaeres a&b&r
    # => Was am Ende bleibt: a&b&r + z&v + p + q

    # Strategie:
    # Zu erst herausfinden was gemerged werden muss -> Merging in 2. Schritt
    # Dictionary von alten Objekten zu neuen objects
    # und Liste mit Tupeln aus (objects-name, sets mit den Mergings)
    # 
    # Dann die liste der Sets durchgehen und diese Objekte mergen
    # -> Erst in Heap (Liste an Mergings durchgehen, Zu Setname aus allen objekten die Fields nehmen und setname rein schreiben, der aus dem Dict 
    #    genommen werden kann
    # -> Dann die MappingsTabelle anpassen indem man die mappings aus dem Dictionary zu setname hinzufügt.
     
    def mergeObjects(self, obj1, obj2): 
        """ Merges two objects to a new abstract one. 
        Does it for the mappings as well as for the heap. By adding the new mapping to the 
        objects dictionary, the recursive search of the most abstract version in getAbstractObject 
        ends up finding the new abstract object for a concrete object, without having to alter the 
        existing references. Therfore the environment does not have to be altered.
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


    def getAbstractObject(obj):
        """ Returns the name of the class, the object 
        has been finaly merged to. 
        """
        while (obj in self.objects):
            obj = self.objects[obj]
        return obj

    
    def getConcreteObjects(obj):
        """ Returns the list ob concrete objects, abstracted by the 
        given abstract object 
        
        Input:
        obj:            The abstract object for which the abstracted objects 

        Output:
        concreteObjs:   List of the concrete objects, abstracted by this 
                        object
        """
        if obj in abstractObjectToObjects:
            return abstractObjectToObjects[obj]
        else:
            # The object is not abstract
            return obj



    ########################################################################
    # From HEAP    
    def add(self, obj, field, target):
        """ Adds a field to the designated object.
        It always leads to adding, since we are flow insensitive 
        and a target is never removed. 

        Input: 
        obj:        The object whose filed is assigned to
        field:      The field that is assigned to
        target:     The object, that is assigned to the field
        """
        if not obj in objects:
            objects[obj] = {}
        if not field in objects[obj]:
            objects[obj][field] = set()
        #nee! HAlt! Das führt sofort zu einem merge! Ah das ist genau was wir bei dem dereferencing hatten. 
        
        objects[obj][field].add(target)


    def get(obj, field):
        """ Returns the current set referen
        It always leads to adding, since we are flow insensitive 
        and a target is never removed. 

        Input: 
        object:     The object whose filed is assigned to
        field:      The field that is assigned to
        target:     The object, that is assigned to the field
        """
        pass   

        
        # Add to the local dictionary of objects
        heap[newObj] = {}

    def merge(heap):
        """ Merge with another heap """        
        pass




#### Also merging Gründe:
## A) (Das ist kein Merginggrund sondern das anlegen einer Referenz)
## B) a = b -> 2 Objekte werden knallhart zusammen gelegt
## C) Dereferencing Read 
## D) Dereferencing Write

## Kann ich mit Object Mapping zusammen packen!

#class Heap(object):
#    """ The mapping of object/array fields to objects
#    Handles the references to the other objects. Also handles the merging when objects are merged.
    
#    Handling arrays should work since it is rather improbable that objects are assigned to an 
#    array in a loop.
#    """

#    heap = {}

#    def add(self, obj, field, target):
#        """ Adds a field to the designated object.
#        It always leads to adding, since we are flow insensitive 
#        and a target is never removed. 

#        Input: 
#        obj:        The object whose filed is assigned to
#        field:      The field that is assigned to
#        target:     The object, that is assigned to the field
#        """
#        if not obj in objects:
#            objects[obj] = {}
#        if not field in objects[obj]:
#            objects[obj][field] = set()
#        #nee! HAlt! Das führt sofort zu einem merge! Ah das ist genau was wir bei dem dereferencing hatten. 
        
#        objects[obj][field].add(target)


#    def get(obj, field):
#        """ Returns the current set referen
#        It always leads to adding, since we are flow insensitive 
#        and a target is never removed. 

#        Input: 
#        object:     The object whose filed is assigned to
#        field:      The field that is assigned to
#        target:     The object, that is assigned to the field
#        """
#        pass   

#    def mergeObjects(obj1, obj2, newObj):
#        """ Input are always already the labels of the most abstract previous objects. """
        
#        # Create the new objects with all heap entries
#        newObj = {}
#        for field in objects[obj1]:
#            newObj = {field: objects[obj1][field]}
#        for field in objects[obj2]:
#            if  not field in objects[newObj]
#                newObj = {field: objects[obj2][field]}
#            else
#                # When same field existed in the merged objects -> merge again!

        
#        # Add to the local dictionary of objects
#        heap[newObj] = {}

#    def merge(heap):
#        """ Merge with another heap
        
#        pass






##########################################################################################
# from HistoryCollection
##########################################################################################

    # Die HistoryCollections sind fertig. Jetzt muss ich noch ueberlegen, wie ich das mit den ObjectCollections und Env mache.
    # Die Sache ist, dass ich das zusammenmergen zu den komplexeren Objekten irgendwie regeln muss.
    # OK habe DIE Strategie. Die mache ich heute auch noch fertig!!!
    # Das merging passiert hier automatisch ohne dass es nach aussen auffällt. Muss es ja auch nicht, da die Env nicht geändert wird und die
    # Hist uach einfach die referenzen nimmt, die sie rein bekommt. Dh wir brauchen die folgenden Funktionen:
    #
    # newObject(class):             Gibt einen eindeutigen Namen für ein neues Objekt der Klasse zurück. Interner Counter für Nummerierung (Integer Overflow nicht behandelt)
    # getAbstractObject(obj):  Gibt für ein Objekt das abstrakteste zurück (Das ist nur intern da von aussen nicht gebraucht. Getter geben alle automatisch das abstrakteste aus
    # getConcreteObjects           Gibt für ein Objekt alle enthaltenen Konkreten zurück. (Das wird nur gebraucht (Braucht man auch nur intern)
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




    def addEventToHistory (self, obj, methodSignature, position, contextFunction):
        ''' Adds an event of an object to the history.
        Used within the nodes, where something is executed.
        The contextFunction is necessary to handle return statements- 
        Special-tag  and loopDepth for the event are later determined by setting this value for the whole historyCollection
        
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

        #if obj in self.histories:
        #    for hist in self.histories[obj]:
        #        if not (hist[-1][1] == context and hist[-1][0] == ret):
        #            hist.append((position, methodSignature, 0, "-")) 
        #            #Für mehere Events käme hier extend(events)
        #else:
        #    self.histories[obj] = [[methodSignature]]
        self.histories.append((obj,methodSignature, position, contextFunction))


    def addHistoryCollection (self, historyCollection):
        """ Adds another historyCollection to the histories of the calling one.
        If there are multiple histories for the same object do the 
        union, what means doing the crossproduct between the histories.
        Take care that deep copyies.

        Input: 
        historyCollection:  The other HistoryCollection, whose traces shall be 
                            appended to the own ones.
        """

        #for id, newHistories in enumerate(historyCollection.getHistories()):
        #    if self.histories[id]:
        #        tmp = self.histories["id"]
        #        self.histories[id] = []
        #        for ownHist in tmp:
        #            for newHist in newHistories:
        #                cpOwnHist = copy.deepcopy(ownHist)
        #                extendedHist.extend(newHist)
        #                self.histories[id].append(extendedHist);
        #    else:
        #        self.histories[id] = histories

        if historyCollection != None:
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
        #oldHistories = self.histories
        #selfHistories = {}

        #for historyCollection in historyCollections:            
        #    for id, newHistories in enumerate(historyCollection.getHistories()):
        #        if self.histories[id]:
        #            tmp = copy.deepcopy(self.histories["id"])
        #            for ownHist in tmp:
        #                for newHist in newHistories:
        #                    cpOwnHist = copy.deepcopy(ownHist)
        #                    extendedHist.extend(newHist)
        #                    self.histories[id].append(extendedHist);
        #        else:
        #            self.histories[id] = histories

        ## In the end take care, that histories, which were not expanded are kept
        #for key in oldHistories:
        #    if not selfHistories[key]:
        #        selfHistoriesoldHistories[key]

        self.histories.append(historyCollections)


    def tagAsSpecialNode(self, tag):
        ''' 
        Tags all elements of this HistoryCollection with a special.
        Usecase is for example the expression inside an if-condition
        
        Input: 
        tag: string - the special tag ("fh", "wc", "ic", "sc")
        '''
        #for key in histories:
        #    for history in histories[key]:
                #for word in history:
                #    word[4] = tag
        self.specialTag = tag

    def markAsLoopBody(self):
        ''' 
        Marks this history as a loopBody. This causes all contained events to 
        # have a by one increased by loopingDepth property. 
        '''
        #for key in histories:
        #    for history in histories[key]:
        #        for word in history:
        #            word[3] = word[3] + 1   
        self.loopBody = True






##########################################################################################
# from STATE
##########################################################################################


# THE OLD MERGING FUNCTION
    # if obj1 == None or obj2 == None:
    #     return
    #
    # # A) DETERMINE WHICH MERGES ARE NECESSARY
    # # Do the merging locally and only save final merging results in the class fields
    # mappings = {obj1: obj1+obj2, obj2: obj1+obj2}
    # mergings = {"obj1+obj2": set(obj1,obj2)}
    #
    # # Determine which
    # newMergings = [set([obj1, obj2])]
    # # Go through all new mergings
    # while newMergings:
    #
    #     for newMerging in newMergings:                                          # Go through the merging sets
    #         fieldValues = {}                                                    # Mark which fieds are there
    #         for obj in newMerging:                                              # For each object in mergingset go through each field
    #             for field in self.heap[obj]:
    #                 if not field in fieldValues:                                # For each field add the most abstract object pointing to to the set
    #                     fieldValues[field] = set([self.heap_get(obj, field)])
    #                 else:
    #                     fieldValues[field].add(self.heap_get(obj,field))
    #
    #         # When again overlapping obejects another merge necessary
    #         for field in fieldValues:
    #             if len(fieldValues[field]) > 1:
    #                 newObj = ''.join(fieldValues[field])
    #                 mergings[newObj] = field
    #                 mapping
    #                 veryNewMergings.append(fieldValues[field])
    #
    #         # Add the mapping and merging for the
    #
    #     # Now check which elements have to be overall merged by analysing these new mergings caused by the previous mergings
    #
    #     newMergings = []
    #
    #
    # # B) DO THE MERGING
    # for merging in mergings:
    #     newObj = {}
    #     for prevObj in merging[1]:
    #         for field in self.heap[prevObj]:
    #             if prevObj[field] in mappings:
    #                 target = mappings[prevObj[field]]
    #             else:
    #                 target = prevObj[field]
    #             newObj["field"] = target
    #     self.abstractObjectToObjects[merging[0]] = merging[1]
    # # Remember the new mappings in the official mapping list
    # for moreConcreteObj in mappings:
    #     self.objectToMoreAbstractObject[moreConcreteObj] = mappings[moreConcreteObj]
    #     if moreConcreteObj in self.mostAbstractObjects:
    #         self.mostAbstractObjects.remove(moreConcreteObj)
    #     self.mostAbstractObjects.add(mappings[moreConcreteObj])
