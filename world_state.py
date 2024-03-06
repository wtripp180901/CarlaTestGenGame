import carla
from coverage import CoverageVariableSet, CoverageVariable
from tags import *
from typing import List, Tuple

class BooleanEnum(Enum):
    TRUE = 0
    FALSE = 1

class SpeedLimits(Enum):
    FIVE = 5
    TEN = 10
    TWENTY = 20
    THIRTY = 30
    FOURTY = 40
    FIFTY = 50
    SIXTY = 60
    SEVENTY = 70
    EIGHT = 80
    NINETY = 90
    HUNDRED = 100

class WorldState:
    def __init__(self,world: carla.World):
        self.world = world
        self.coverage_space = CoverageVariableSet([
            (CoverageVariable.RAIN,RainTags),
            (CoverageVariable.GROUND_WATER,RainTags),
            (CoverageVariable.BIKES_PRESENT,BooleanEnum),
            (CoverageVariable.CARS_PRESENT, BooleanEnum),
            (CoverageVariable.SPEED_LIMIT,SpeedLimits)
        ],
        [
            (CoverageVariable.NUM_VEHICLES,50),
            (CoverageVariable.NUM_PEDESTRIANS,50)
        ]
        )

    def get_coverage_state(self,ego_vehicle,non_ego_vehicles):
        enumerated_speed_limit = None
        try:
            enumerated_speed_limit = SpeedLimits(int(ego_vehicle.get_speed_limit()))
        except:
            print("invalid speed limit: ",ego_vehicle.get_speed_limit())
            enumerated_speed_limit = SpeedLimits.SEVENTY
        enumerated_vars = [
            (CoverageVariable.RAIN, getWeatherLevel(self.world.get_weather().precipitation)),
            (CoverageVariable.GROUND_WATER, getWeatherLevel(self.world.get_weather().precipitation_deposits)),
            (CoverageVariable.BIKES_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 2 for v in non_ego_vehicles]))),
            (CoverageVariable.CARS_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 4 for v in non_ego_vehicles]))),
            (CoverageVariable.SPEED_LIMIT, enumerated_speed_limit)
        ]
        quantitative_vars = [
            (CoverageVariable.NUM_VEHICLES, len(non_ego_vehicles)),
            (CoverageVariable.NUM_PEDESTRIANS, len(self.world.get_actors().filter("*walker*")))
        ]
        return enumerated_vars, quantitative_vars

def boolToEnum(bool):
    if bool:
        return BooleanEnum.TRUE
    else:
        return BooleanEnum.FALSE

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