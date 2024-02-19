from enum import Enum

class RainTags(Enum):
    NONE = 1
    VERY_LIGHT = 2
    LIGHT = 3
    MID = 4
    HEAVY = 5

class TagSet:
    def __init__(self,tags,allRequired: bool):
        self.Any = False
        self.tags = tags
        self.allRequired = allRequired

ANY_TAGSET = TagSet([],False)
ANY_TAGSET.Any = True