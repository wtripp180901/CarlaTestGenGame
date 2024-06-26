import carla
from coverage import CoverageVariableSet, CoverageVariable
from validity_requirements import *
from typing import List, Tuple
import numpy as np
from coverage_variables import *
from fnmatch import fnmatch

class WorldState:
    def __init__(self,world: carla.World):
        self.world = world
        self.coverage_space = CoverageVariableSet([
            (CoverageVariable.RAIN,Levels),
            (CoverageVariable.GROUND_WATER,Levels),
            (CoverageVariable.BIKES_PRESENT,BooleanEnum),
            (CoverageVariable.CARS_PRESENT, BooleanEnum),
            (CoverageVariable.SPEED_LIMIT,SpeedLimits),
            (CoverageVariable.ROAD_GRAPH,RoadGraphs),
            (CoverageVariable.PEDESTRIAN_DENSITY,Levels),
            (CoverageVariable.VEHICLE_DENSITY,Levels),
            (CoverageVariable.EMERGENCY_VEHICLE_STATUS,EmergencyVehicleStatus),
            (CoverageVariable.CLOUD, Levels),
            (CoverageVariable.TIME_OF_DAY,TimesOfDay)
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
        emergency_vehicle_status, _ = get_emergency_vehicle_status(self.world)

        enumerated_vars = [
            (CoverageVariable.RAIN, getWeatherLevel(self.world.get_weather().precipitation)),
            (CoverageVariable.GROUND_WATER, getWeatherLevel(self.world.get_weather().precipitation_deposits)),
            (CoverageVariable.BIKES_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 2 for v in non_ego_vehicles]))),
            (CoverageVariable.CARS_PRESENT, boolToEnum(any([v.attributes["number_of_wheels"] == 4 for v in non_ego_vehicles]))),
            (CoverageVariable.SPEED_LIMIT, enumerated_speed_limit),
            (CoverageVariable.ROAD_GRAPH, RoadGraphs[self._last_road_graph_string]),
            (CoverageVariable.VEHICLE_DENSITY, get_density_level(get_actor_density(non_ego_vehicles,ego_vehicle.get_location(),25))),
            (CoverageVariable.PEDESTRIAN_DENSITY, get_density_level(get_actor_density(self.world.get_actors().filter("*walker*"),ego_vehicle.get_location(),25))),
            (CoverageVariable.EMERGENCY_VEHICLE_STATUS,emergency_vehicle_status),
            (CoverageVariable.CLOUD,getWeatherLevel(self.world.get_weather().cloudiness)),
            (CoverageVariable.TIME_OF_DAY,get_time_of_day(self.world))
        ]
        return enumerated_vars

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
            nextlist = ego_waypoint.next(10)
            prevlist = ego_waypoint.previous(10)
            has_two_points = False
            has_one_point = False
            if len(nextlist) == 0 and len(prevlist) != 0:
                road_direction = prevlist[0].transform.location - ego_waypoint.transform.location
                has_one_point = True
            elif len(nextlist) != 0 and len(prevlist) == 0:
                road_direction = nextlist[0].transform.location - ego_waypoint.transform.location
                has_one_point = True
            elif len(nextlist) != 0 and len(prevlist) != 0:   
                road_direction = nextlist[0].transform.location - prevlist[0].transform.location
                has_two_points = True
            else:
                return self._last_road_graph_string
            
            road_direction = road_direction / road_direction.length()
            directions = [glob_up,glob_down,glob_left,glob_right]
            direction_dots = [dot2d(road_direction,d) for d in directions]
            closest_direction = np.argmax(direction_dots)

            if has_one_point:
                if closest_direction == 0:
                    up = True
                if closest_direction == 1:
                    down = True
                if closest_direction == 2:
                    left = True
                if closest_direction == 3:
                    right = True

            if has_two_points:

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

# Returns if an emergency vehicle is present and if their siren is on + the vehicles with their sirens on
def get_emergency_vehicle_status(world):
    emergency_vehicles = [x for x in world.get_actors() if fnmatch(x.type_id,"*ambulance*") or fnmatch(x.type_id,"*police*") or fnmatch(x.type_id,"*firetruck*")]
    if len(emergency_vehicles) > 0:
        sirens_on = [v for v in emergency_vehicles if v.get_light_state() == carla.VehicleLightState.Special1 or v.get_light_state() == carla.VehicleLightState.Special2]
        if len(sirens_on) > 0:
            return EmergencyVehicleStatus.SIREN, sirens_on
        return EmergencyVehicleStatus.PRESENT, []
    else:
        return EmergencyVehicleStatus.ABSENT, []

def get_time_of_day(world):
    sun_angle = world.get_weather().sun_altitude_angle
    if sun_angle > -10 and sun_angle <= 20:
        return TimesOfDay.SUNRISE
    elif sun_angle > 10 and sun_angle < 160:
        return TimesOfDay.DAY
    elif sun_angle >= 160 and sun_angle < 190:
        return TimesOfDay.SUNSET
    else:
        return TimesOfDay.NIGHT

def get_actor_density(full_actor_list,ego_pos,distance):
    return len([e for e in full_actor_list if (e.get_location() - ego_pos).length() < distance])/(3.14 * distance * distance)

def get_density_level(density):
    if density <= 0:
        return Levels.NONE
    elif density <= 0.003:
        return Levels.LOW
    elif density <= 0.008:
        return Levels.MEDIUM
    elif density <= 0.013:
        return Levels.HIGH
    else:
        return Levels.VERY_HIGH

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
        return Levels.NONE
    elif variable <= 25:
        return Levels.LOW
    elif variable <= 50:
        return Levels.MEDIUM
    elif variable <= 75:
        return Levels.HIGH
    else:
        return Levels.VERY_HIGH