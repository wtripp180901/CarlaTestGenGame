from enum import Enum

class RainTags(Enum):
    NONE = 1
    LIGHT = 2
    MID = 3
    HEAVY = 4

class TagSet:
    def __init__(self,tags,allRequired: bool):
        self.Any = False
        self.tags = tags
        self.allRequired = allRequired

ANY_TAGSET = TagSet([],False)
ANY_TAGSET.Any = True