from enum import Enum
from fnmatch import fnmatch
import carla
import numpy as np
from world_state import get_emergency_vehicle_status, dot2d

class PartitionedJunction:
    def __init__(self,cross_point: carla.Vector3D,right_lane_alignment_vector: carla.Vector3D,past_turning_alignment_vector: carla.Vector3D):
        self.cross_point = carla.Vector2D(cross_point.x,cross_point.y)
        self._lane_separation_vector = carla.Vector2D(right_lane_alignment_vector.x,right_lane_alignment_vector.y)
        self._turning_separation_vector = carla.Vector2D(past_turning_alignment_vector.x,past_turning_alignment_vector.y)

    def get_quadrant(self,location: carla.Location):
        location = carla.Vector2D(location.x,location.y)
        relative_vector = location - self.cross_point
        relative_vector = relative_vector / relative_vector.length()
        lane_dot = relative_vector.x * self._lane_separation_vector.x + relative_vector.y * self._lane_separation_vector.y
        turning_dot = relative_vector.x * self._turning_separation_vector.x + relative_vector.y * self._turning_separation_vector.y
        in_right_lane = lane_dot > 0
        past_turning_point = turning_dot > 0
        if in_right_lane:
            if past_turning_point:
                return JunctionQuadrants.INNER_AFTER_TURNING
            else:
                return JunctionQuadrants.INNER_BEFORE_TURNING
        else:
            if past_turning_point:
                return JunctionQuadrants.OUTER_AFTER_TURNING
            else:
                return JunctionQuadrants.OUTER_BEFORE_TURNING
    
    def inner_lane(self,location: carla.Location):
        quad = self.get_quadrant(location)
        return quad == JunctionQuadrants.INNER_AFTER_TURNING or quad == JunctionQuadrants.INNER_BEFORE_TURNING
    
    def past_turning(self,location: carla.Location):
        quad = self.get_quadrant(location)
        return quad == JunctionQuadrants.INNER_AFTER_TURNING or quad == JunctionQuadrants.OUTER_AFTER_TURNING

class JunctionQuadrants(Enum):
    OUTER_BEFORE_TURNING = 0
    OUTER_AFTER_TURNING = 1
    INNER_BEFORE_TURNING = 2
    INNER_AFTER_TURNING = 3

class JunctionStates(Enum):
    T_ON_MAJOR = 0
    T_ON_MINOR = 1
    UNKNOWN = 2
    NONE = 3
    ROUNDABOUT = 4

# Returns true if faster than other vehicle, within sensible range and pther vehicle is to the left
def vehicle_in_overtake_range(ego_vehicle,other_vehicle):
    vec_to_other = other_vehicle.get_location() - ego_vehicle.get_location()
    return (ego_vehicle.get_velocity().length() > other_vehicle.get_velocity().length() and 
            vec_to_other.length() < ego_vehicle.bounding_box.extent.y * 7 and
            dot2d(vec_to_other,ego_vehicle.get_transform().get_right_vector()) < 0
    )

def vehicle_or_pedestrian(actor):
    return fnmatch(actor.type_id,"*vehicle*") or fnmatch(actor.type_id,"*walker*")

def parked_left(ego_vehicle,map):
    ego_loc = ego_vehicle.get_location()
    ego_wp = map.get_waypoint(ego_vehicle.get_location())
    vec_to_ego = ego_loc - ego_wp.transform.location
    if ego_vehicle.get_velocity().length() <= 0 and dot2d(vec_to_ego,ego_wp.transform.get_right_vector()) < 0 and vec_to_ego.length() >= ego_wp.lane_width/8:
        return True
    else:
        return False
    
def active_emergency_vehicle_within_distance(ego_vehicle,world,distance):
    _, active_evs = get_emergency_vehicle_status(world)
    return any([(e.get_location() - ego_vehicle.get_location()).length() < distance for e in active_evs])

def vehicleInJunction(vehicle: carla.Actor,junction: carla.Junction,extentMargins: carla.Vector3D = carla.Vector3D(0,0,5)):
    if junction == None:
        return False
    bb = junction.bounding_box
    nbb = carla.BoundingBox(carla.Vector3D(0,0,0),bb.extent + extentMargins)
    if nbb.contains(vehicle.get_transform().location + carla.Vector3D(0,0,extentMargins.z/2),carla.Transform(bb.location,bb.rotation)):
        return True
    return False

# Returns a tuple indicating if the vehicle would be at a traffic light if it was driving on the right and if the light is green
def american_traffic_light_status(ego_vehicle,map,world):
    ego_loc = ego_vehicle.get_location()
    ego_wp = map.get_waypoint(ego_loc)
    right_lane_wp = map.get_waypoint(ego_loc + ego_vehicle.get_transform().get_right_vector() * ego_wp.lane_width)
    lights = world.get_traffic_lights_from_waypoint(right_lane_wp,10)
    if len(lights) > 0:
        return (True, lights[0].get_state() == carla.TrafficLightState.Green)
    else:
        return (False, False)
    
def locationWithinBoxInFrontOfVehicle(from_vehicle: carla.Actor,location: carla.Location,box_length: float,world):
    
    extents = from_vehicle.bounding_box.extent
    transform = from_vehicle.get_transform()
    centre = transform.location
    directionVector = transform.get_forward_vector()

    box = carla.BoundingBox(carla.Vector3D(0,0,0),
                            carla.Vector3D((box_length/2),extents.y,2 * extents.z))
    world.debug.draw_box(carla.BoundingBox(centre + directionVector * (extents.x + box_length/2),carla.Vector3D((box_length/2),extents.y,2 * extents.z)),transform.rotation,life_time=0.1)
    return box.contains(location,carla.Transform(centre + directionVector * (extents.x + box_length/2),transform.rotation))

def stoppingDistance(speed):
    # Stopping distance = thinking distance + braking distance
    speed = speed / 3.6
    return 0.675 * speed + speed * speed * (1/12.96)

def straightOnAtJunction(vehicle: carla.Vehicle,junction_status: JunctionStates):
    return vehicle.get_control().steer == 0 and junction_status == JunctionStates.T_ON_MAJOR

def currentJunction(ego,map):
    ego_waypoint = map.get_waypoint(ego.get_location())
    return ego_waypoint.get_junction()

def getJunctionStatus(ego,junction):
    
    waypoints = junction.get_waypoints(carla.LaneType.Driving)
    entrypoints = [t[0] for t in waypoints]
    dist_sorted = sorted(entrypoints,key = lambda x: [(ego.get_transform().location - x.transform.location).length()])
    entrypoint = dist_sorted[0]

    straight_path = False
    other_path = False
    location = entrypoint.transform.location
    destinations_from_entrypoint = [w[1] for w in waypoints if (w[0].transform.location - location).length() < 0.01]
    direction_vector = location - entrypoint.previous(10)[0].transform.location
    direction_vector = direction_vector / direction_vector.length()
    right_direction_vector = direction_vector.cross(carla.Vector3D(0,0,1))
    
    roundabout = True
    for d in destinations_from_entrypoint:
        possible_next_junction = d.next(10)[0].get_junction()
        if possible_next_junction == None or possible_next_junction.id == junction.id:
            roundabout = False

        if (d.transform.location - (location + direction_vector * (d.transform.location - location).length())).length() < 1:
            straight_path = True
        else:
            other_path = True

    sorted_other_entrances = sorted(
        [e for e in entrypoints if (e.transform.location - entrypoint.transform.location).length() > 0.1],
        key=(lambda x: (x.transform.location - location).length())
    )

    if roundabout:
        return JunctionStates.ROUNDABOUT, None
    if straight_path and other_path:
        assert len(sorted_other_entrances) > 0
        closest_other_entrance = sorted_other_entrances[0]
        cross_point = get_vector_intersection(entrypoint.transform.location - right_direction_vector * (entrypoint.lane_width),
                                direction_vector,
                                closest_other_entrance.transform.location - direction_vector * (closest_other_entrance.lane_width/2),
                                right_direction_vector)
        return JunctionStates.T_ON_MAJOR, PartitionedJunction(cross_point,-1 * right_direction_vector,direction_vector)
    elif other_path:
        assert len(sorted_other_entrances) > 0
        closest_other_entrance = sorted_other_entrances[0]
        cross_point = get_vector_intersection(entrypoint.transform.location + right_direction_vector * (entrypoint.lane_width),
                                direction_vector,
                                closest_other_entrance.transform.location + direction_vector * (closest_other_entrance.lane_width/2),
                                right_direction_vector)
        return JunctionStates.T_ON_MINOR, PartitionedJunction(cross_point,-1 * direction_vector,-1 * right_direction_vector)
    else:
        return JunctionStates.UNKNOWN, None
    
def get_vector_intersection(b1,v1,b2,v2):
    return (np.matrix([[v1.x,-v2.x],[v1.y,-v2.y]]).I @ np.matrix([[b2.x-b1.x],[b2.y-b1.x]])).getA()[0][0] * v2 + b2

def debugJunction(current_junction,world):
    if current_junction != None:
        for x in current_junction.get_waypoints(carla.LaneType.Driving):
            world.debug.draw_line(x[0].transform.location,x[0].transform.location + carla.Vector3D(0,0,5),life_time=0.1)
            world.debug.draw_line(x[1].transform.location,x[1].transform.location + carla.Vector3D(0,0,5),life_time=0.1,color=carla.Color(0,255,0))
            world.debug.draw_line(x[1].next(10)[0].transform.location,x[1].next(10)[0].transform.location + carla.Vector3D(0,0,5),life_time=0.1,color=carla.Color(0,0,255))

def performingSafeLeftTurn(ego_vehicle,vehicle,partitioned_junction: PartitionedJunction,junction_status):
    if junction_status == JunctionStates.T_ON_MINOR:
        return (ego_vehicle.get_control().steer < 0 and partitioned_junction.get_quadrant(vehicle.get_transform().location) != JunctionQuadrants.INNER_AFTER_TURNING) or vehicle.get_velocity().length() <= 0.1
    elif junction_status == JunctionStates.T_ON_MAJOR:
        return ego_vehicle.get_control().steer < 0
    else:
        print("Warning: undefined safe left")
        return False

def performingSafeRightTurn(ego_vehicle,vehicle,paritioned_junction: PartitionedJunction,junction_status):
    if junction_status == JunctionStates.T_ON_MINOR:
        return (ego_vehicle.get_control().steer > 0 and paritioned_junction.get_quadrant(vehicle.get_transform().location) == JunctionQuadrants.INNER_AFTER_TURNING and vehicle.get_control().steer < 0) or vehicle.get_velocity().length() <= 0.1
    elif junction_status == JunctionStates.T_ON_MAJOR:
        return (ego_vehicle.get_control().steer > 0 and paritioned_junction.get_quadrant(vehicle.get_transform().location) != JunctionQuadrants.INNER_AFTER_TURNING) or vehicle.get_velocity().length() <= 0.1
    else:
        print("Warning: undefined safe right")
        return False
    