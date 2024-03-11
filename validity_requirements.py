from enum import Enum
from typing import *
from coverage_variables import CoverageVariable, RoadGraphs

class ValidityRequirement:
    def __init__(self,present_variables: Dict[CoverageVariable,List[Enum]],absent_variables: Dict[CoverageVariable,List[Enum]],all_present_required: bool):
        self.present_variables = present_variables
        self.absent_variables = absent_variables
        self.all_present_required = all_present_required

    def is_valid(self,variable_value_pairs: List[Tuple[CoverageVariable,Enum]]):
        if self.present_variables == None and self.absent_variables == None:
            return True
        
        if self.absent_variables != None:
            for v in variable_value_pairs:
                if v[0] in self.absent_variables and v[1] in self.absent_variables[v[0]]:
                    return False
            
        if self.present_variables != None:
            given_variable_names = [v[0] for v in variable_value_pairs]
            for v in self.present_variables:
                try:
                    i = given_variable_names.index(v)
                    if variable_value_pairs[i][1] in self.present_variables[v]:
                        if not self.all_present_required:
                            return True
                    else:
                        if self.all_present_required:
                            return False
                except:
                    if self.all_present_required:
                        return False
        return True

IN_JUNCTION_REQUIREMENTS = validityRequirements=ValidityRequirement(
    {CoverageVariable.ROAD_GRAPH: [RoadGraphs.TTTF,RoadGraphs.TTFT,RoadGraphs.TFTT,RoadGraphs.FTTT,RoadGraphs.TTTT]},
    None,
    True)