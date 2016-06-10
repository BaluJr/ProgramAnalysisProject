class CallgraphException(Exception):
    pass

class MappingException(Exception):
    pass

class HoleFoundException(Exception):
    def __init__(self, history):
        self.history = history

    def __str__(self):
        self.history