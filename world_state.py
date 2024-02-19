import carla
from coverage import CoverageVariableSet, CoverageVariable
from tags import *
from typing import List, Tuple

class WorldState:
    def __init__(self,world: carla.World):
        self.world = world
        self.coverage_space = CoverageVariableSet([
            (CoverageVariable.RAIN,RainTags),
            (CoverageVariable.GROUND_WATER,RainTags)
        ],
        [
            (CoverageVariable.NUM_VEHICLES,50),
            (CoverageVariable.NUM_PEDESTRIANS,50)
        ]
        )

    def get_coverage_state(self):
        enumerated_vars = [
            (CoverageVariable.RAIN, getWeatherLevel(self.world.get_weather().precipitation)),
            (CoverageVariable.GROUND_WATER, getWeatherLevel(self.world.get_weather().precipitation_deposits))
        ]
        quantitative_vars = [
            (CoverageVariable.NUM_VEHICLES, len(self.world.get_actors().filter("*vehicle*"))),
            (CoverageVariable.NUM_PEDESTRIANS, len(self.world.get_actors().filter("*walker*")))
        ]
        return enumerated_vars, quantitative_vars

def getWeatherLevel(variable: float):
    if variable <= 0:
        return RainTags.NONE
    elif variable <= 25:
        return RainTags.VERY_LIGHT
    elif variable <= 50:
        return RainTags.LIGHT
    elif variable <= 75:
        return RainTags.MID
    else:
        return RainTags.HEAVY