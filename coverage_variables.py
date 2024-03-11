from enum import Enum

class CoverageVariable(Enum):
    RAIN = 0
    NUM_VEHICLES = 1
    NUM_PEDESTRIANS = 2
    GROUND_WATER = 3
    BIKES_PRESENT = 4
    CARS_PRESENT = 5
    SPEED_LIMIT = 6
    ROAD_GRAPH = 7

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

class RainTags(Enum):
    NONE = 1
    VERY_LIGHT = 2
    LIGHT = 3
    MID = 4
    HEAVY = 5

class RoadGraphs(Enum):
    FFFT = 0
    FFTF = 1
    FFTT = 2
    FTFF = 3
    FTFT = 4
    FTTF = 5
    FTTT = 6
    TFFF = 7
    TFFT = 8
    TFTF = 9
    TFTT = 10
    TTFF = 11
    TTFT = 12
    TTTF = 13
    TTTT = 14