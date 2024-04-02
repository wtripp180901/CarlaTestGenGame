from enum import Enum
from typing import *
from coverage_variables import CoverageVariable, RoadGraphs

class ValidityRequirement:
    def __init__(self,required_variables: Dict[CoverageVariable,List[Enum]]):
        self.required_variables = required_variables

    def is_valid(self,variable_value_pairs: List[Tuple[CoverageVariable,Enum]]):
        if self.required_variables == None:
            return True
        else:
            given_variable_names = [v[0] for v in variable_value_pairs]
            for v in self.required_variables:
                i = given_variable_names.index(v)
                if not (variable_value_pairs[i][1] in self.required_variables[v]):
                    return False
        return True

IN_JUNCTION_REQUIREMENTS = validityRequirements=ValidityRequirement(
    {CoverageVariable.ROAD_GRAPH: [RoadGraphs.TTTF,RoadGraphs.TTFT,RoadGraphs.TFTT,RoadGraphs.FTTT,RoadGraphs.TTTT]})