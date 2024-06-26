from typing import Callable
from validity_requirements import *

class Assertion:
    def __init__(self,ruleNumber: int,subcase: int,description: str,
                 preconditionOracle: Callable[[], bool],assertionOracle: Callable[[], bool],
                 validityRequirements: ValidityRequirement = None,previous_tick_precondition: bool = False):
        self.ruleNumber = ruleNumber
        self.subcase = subcase
        self.description = description
        self.preconditionOracle = preconditionOracle
        self.assertionOracle = assertionOracle
        self.previous_tick_precondition = previous_tick_precondition

        self.covered = False
        self.violated = False
        self.zero_value = False

        self.precondition_active_in_tick = False
        self.violated_in_tick = False

        # Tag constraints
        self.validityRequirements = validityRequirements
    
    def IsActive(self,coverage_state: List[Tuple[CoverageVariable,Enum]]):
        if self.validityRequirements == None:
            return True
        return self.validityRequirements.is_valid(coverage_state)

    def Check(self):
        precondition_active_last_tick = self.precondition_active_in_tick
        self.precondition_active_in_tick = False
        self.violated_in_tick = False
        
        if self.preconditionOracle():
            self.covered = True
            self.precondition_active_in_tick = True
        if not self.assertionOracle():
            self.violated = True
            self.violated_in_tick = True
            if (self.previous_tick_precondition and not precondition_active_last_tick) or (
                not self.previous_tick_precondition and not self.precondition_active_in_tick):
                self.zero_value = True
