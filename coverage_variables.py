from enum import Enum

class CoverageVariable(Enum):
    RAIN = 0
    VEHICLE_DENSITY = 1
    PEDESTRIAN_DENSITY = 2
    GROUND_WATER = 3
    BIKES_PRESENT = 4
    CARS_PRESENT = 5
    SPEED_LIMIT = 6
    ROAD_GRAPH = 7
    EMERGENCY_VEHICLE_STATUS = 8
    CLOUD = 9
    TIME_OF_DAY = 10

class TimesOfDay(Enum):
    NIGHT = 0
    SUNRISE = 1
    DAY = 2
    SUNSET = 3

class EmergencyVehicleStatus(Enum):
    ABSENT = 0
    PRESENT = 1
    SIREN = 2

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

class Levels(Enum):
    NONE = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

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
    