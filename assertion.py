from typing import Callable
from tags import *

class Assertion:
    def __init__(self,ruleNumber: int,description: str,
                 preconditionOracle: Callable[[], bool],assertionOracle: Callable[[], bool],
                 raininess: TagSet = ANY_TAGSET):
        self.ruleNumber = ruleNumber
        self.description = description
        self.preconditionOracle = preconditionOracle
        self.assertionOracle = assertionOracle

        self.covered = False
        self.violated = False
        self.vacuous = False

        # Tag constraints
        self.raininess = raininess
    
    def IsActive(self,raininess: TagSet):
        return requiredTagsPresent(self.raininess,raininess)

    def Check(self):
        if self.preconditionOracle():
            self.covered = True
        if not self.assertionOracle():
            self.violated = True
            if not self.preconditionOracle():
                self.vacuous = True

def requiredTagsPresent(myTags: TagSet,envTags: TagSet):
        return (myTags.Any or 
                (myTags.allRequired and set(myTags.tags).issubset(envTags.tags)) or 
                (not myTags.allRequired and not set(myTags.tags).isdisjoint(envTags.tags)))
