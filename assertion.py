from typing import Callable
from tags import *

class Assertion:
    def __init__(self,ruleNumber: int,subcase: int,description: str,
                 preconditionOracle: Callable[[], bool],assertionOracle: Callable[[], bool],
                 raininess: TagSet = ANY_TAGSET):
        self.ruleNumber = ruleNumber
        self.subcase = subcase
        self.description = description
        self.preconditionOracle = preconditionOracle
        self.assertionOracle = assertionOracle

        self.covered = False
        self.violated = False
        self.zero_value = False

        self.precondition_active_in_tick = False
        self.violated_in_tick = False

        # Tag constraints
        self.raininess = raininess
    
    def IsActive(self,raininess: TagSet):
        return requiredTagsPresent(self.raininess,raininess)

    def Check(self):
        self.precondition_active_in_tick = False
        self.violated_in_tick = False
        
        if self.preconditionOracle():
            self.covered = True
            self.precondition_active_in_tick = True
        if not self.assertionOracle():
            self.violated = True
            self.violated_in_tick = True
            if not self.precondition_active_in_tick:
                self.zero_value = True

def requiredTagsPresent(myTags: TagSet,envTags: TagSet):
        return (myTags.Any or 
                (myTags.allRequired and set(myTags.tags).issubset(envTags.tags)) or 
                (not myTags.allRequired and not set(myTags.tags).isdisjoint(envTags.tags)))
