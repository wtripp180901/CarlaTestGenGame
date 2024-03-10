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
        self._last_road_graph_string = "TTTT"

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

        if junction == None:
            possible_waypoints = [ego_waypoint.next(10)[0], ego_waypoint.previous(10)[0]]
            relative_positions = [x.transform.location - ego_waypoint.transform.location for x in possible_waypoints]
            relative_directions = [x/x.length() for x in relative_positions]
            other = []
            for i, w in enumerate(relative_directions):
                classified = False
                if vector_is_straight_in_direction(w,glob_up):
                    up = True
                    classified = True
                if vector_is_straight_in_direction(w,glob_down):
                    down = True
                    classified = True
                if vector_is_straight_in_direction(w,glob_right):
                    right = True
                    classified = True
                if vector_is_straight_in_direction(w,glob_left):
                    left = True
                    classified = True
                if not classified:
                    other.append(possible_waypoints[i])

            print(up,down,left,right)
            if up or down:
                for w in other:
                    if w.get_junction != None:
                        up = True
                        down = True
                    else:
                        if w.transform.location.y > 0:
                            right = True
                        else:
                            left = True
            elif left or right:
                for w in other:
                    if w.get_junction != None:
                        left = True
                        right = True
                    else:
                        if w.transform.location.x > 0:
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