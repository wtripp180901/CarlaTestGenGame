import carla
from coverage import CoverageVariableSet, CoverageVariable
from tags import *
from typing import List, Tuple
import numpy as np

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

class WorldState:
    def __init__(self,world: carla.World):
        self.world = world
        self.coverage_space = CoverageVariableSet([
            (CoverageVariable.RAIN,RainTags),
            (CoverageVariable.GROUND_WATER,RainTags),
            (CoverageVariable.BIKES_PRESENT,BooleanEnum),
            (CoverageVariable.CARS_PRESENT, BooleanEnum),
            (CoverageVariable.SPEED_LIMIT,SpeedLimits),
            (CoverageVariable.ROAD_GRAPH,RoadGraphs)
        ],
        [
            (CoverageVariable.NUM_VEHICLES,50),
            (CoverageVariable.NUM_PEDESTRIANS,50)
        ]
        )
        self._last_road_graph_string = "TTTT"

    def get_coverage_state(self,ego_vehicle,non_ego_vehicles,map):
        enumerated_speed_limit = None
        try:
            enumerated_speed_limit = SpeedLimits(int(ego_vehicle.get_speed_limit()))
        except:
            print("invalid speed limit: ",ego_vehicle.get_speed_limit())
            enumerated_speed_limit = SpeedLimits.SEVENTY
        self._last_road_graph_string = self.get_road_graph(map.get_waypoint(ego_vehicle.get_location()))

        enumerated_vars = [
            (CoverageVariable.RAIN, getWeatherLevel(self.world.get_weather().precipitation)),
            (CoverageVariable.GROUND_WATER, getWeatherLevel(self.world.get_weather().precipitation_deposits)),
            (CoverageVariable.BIKES_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 2 for v in non_ego_vehicles]))),
            (CoverageVariable.CARS_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 4 for v in non_ego_vehicles]))),
            (CoverageVariable.SPEED_LIMIT, enumerated_speed_limit),
            (CoverageVariable.ROAD_GRAPH, RoadGraphs[self._last_road_graph_string])
        ]
        quantitative_vars = [
            (CoverageVariable.NUM_VEHICLES, len(non_ego_vehicles)),
            (CoverageVariable.NUM_PEDESTRIANS, len(self.world.get_actors().filter("*walker*")))
        ]
        return enumerated_vars, quantitative_vars

    def get_road_graph(self,ego_waypoint: carla.Waypoint):
        junction = ego_waypoint.get_junction()

        up = False
        down = False
        left = False
        right = False

        glob_right = carla.Vector3D(1,0,0)
        glob_left = carla.Vector3D(-1,0,0)
        glob_down = carla.Vector3D(0,-1,0)
        glob_up = carla.Vector3D(0,1,0)
        threshold = 0.1

        if junction == None:
            road_direction = ego_waypoint.next(10)[0].transform.location - ego_waypoint.previous(10)[0].transform.location
            road_direction = road_direction / road_direction.length()
            directions = [glob_up,glob_down,glob_left,glob_right]
            direction_dots = [dot2d(road_direction,d) for d in directions]
            closest_direction = np.argmax(direction_dots)

            straight = 1 - direction_dots[closest_direction] < threshold

            if closest_direction == 0:
                down = True
                if straight:
                    up = True
                else:
                    if direction_dots[3] > 0:
                        right = True
                    else:
                        left = True
            elif closest_direction == 1:
                up = True
                if straight:
                    down = True
                else:
                    if direction_dots[3] > 0:
                        right = True
                    else:
                        left = True
            elif closest_direction == 2:
                right = True
                if straight:
                    left = True
                else:
                    if direction_dots[0] > 0:
                        up = True
                    else:
                        down = True
            elif closest_direction == 3:
                left = True
                if straight:
                    right = True
                else:
                    if direction_dots[0] > 0:
                        up = True
                    else:
                        down = True
        else:
            waypoints = junction.get_waypoints(carla.LaneType.Driving)
            entry = waypoints[0][0]
            road_waypoints = [x[1] for x in waypoints if (x[0].transform.location - entry.transform.location).length() < 0.1]
            road_waypoints.append(entry)
            
            relative_positions = [x.transform.location - junction.bounding_box.location for x in road_waypoints]
            
            for p in relative_positions:
                if p.y > p.x:
                    if p.y > -p.x:
                        up = True
                    else:
                        left = True
                else:
                    if p.y > -p.x:
                        right = True
                    else:
                        down = True

        output_string = ""
        for b in [up,down,left,right]:
            if b:
                output_string = output_string + "T"
            else:
                output_string = output_string + "F"
        if output_string == "FFFF":
            output_string = self._last_road_graph_string
        return output_string

def dot2d(v1,v2):
    return v1.x * v2.x + v1.y * v2.y

def vector_is_straight_in_direction(vec: carla.Vector3D,dir: carla.Vector3D):
    threshold = 0.1
    return (vec - dir).length() < threshold

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