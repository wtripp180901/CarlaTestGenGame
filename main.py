import argparse

import carla
from assertion import Assertion
from tags import *
from coverage import *
import random
import time
import test_setup
import numpy as np
import score_writer
from world_state import WorldState

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--scenario",default="none")
    args = parser.parse_args()
    
    ego_vehicle = None
    non_ego_actors = None
    non_ego_vehicles = None
    
    client = carla.Client('localhost', 2000)
    client.set_timeout(10)
    world = test_setup.setupForTest(args.scenario,client)
    world_state = WorldState(world)
    map = world.get_map()

    for i,s in enumerate(world.get_map().get_spawn_points()):
        world.debug.draw_string(s.location + carla.Vector3D(0,0,2),str(i),life_time=60)
    
    active_assertions = [
        Assertion(126, 0,
                "Maintain a safe stopping distance",
                (lambda: any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()) + 5,world) for t in non_ego_vehicles)),
                (lambda: not any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()),world) for t in non_ego_vehicles))
                ),
        Assertion(124, 0,
                "You must not exceed maximum speed limits",
                (lambda: ego_vehicle.get_speed_limit() != None),
                (lambda: ego_vehicle.get_velocity().length() <= ego_vehicle.get_speed_limit())
                ),
        Assertion(170, 0,
                  "Give way to vehicles on major road",
                  lambda: junction_status == JunctionStates.T_ON_MINOR and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles),
                  lambda: not (junction_status == JunctionStates.T_ON_MINOR 
                               and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) and (not performingSafeLeftTurn(ego_vehicle,v) and not performingSafeRightTurn(ego_vehicle,v)) for v in non_ego_vehicles)) 
                               or ego_vehicle.get_velocity().length() < 0.1
                ),
        Assertion(170, 1,
                  "Give way to vehicles on major road (major case)",
                  lambda: junction_status == JunctionStates.T_ON_MAJOR and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles),
                  lambda: (not (junction_status == JunctionStates.T_ON_MAJOR and (any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles))) or straightOnAtJunction(ego_vehicle,junction_status))
                            or ego_vehicle.get_velocity().length() < 0.1
                )
    ]

    coverage = Coverage(active_assertions,world_state.coverage_space)

    has_junction = False
    junction_status = JunctionStates.NONE
    quads = None
    triggered_assertions = []
    while True:
        non_ego_actors = world.get_actors()
        non_ego_vehicles = non_ego_actors.filter('*vehicle*')

        for i in range(len(non_ego_actors)):
            if non_ego_actors[i].attributes.get('role_name') == 'hero':
                ego_vehicle = non_ego_actors[i]
                break
        if ego_vehicle == None:
            print("Couldn't find ego vehicle in",len(non_ego_vehicles),"vehicles searched")
            return -1
        
        non_ego_actors = [x for x in non_ego_actors if x.id != ego_vehicle.id]
        non_ego_vehicles = [x for x in non_ego_vehicles if x.id != ego_vehicle.id]

        current_junction = currentJunction(ego_vehicle,map)

        # Might cause issues for double junctions
        if current_junction == None and has_junction:
            has_junction = False
            junction_status = JunctionStates.NONE
            quads = None
        if not has_junction and current_junction != None:
            has_junction = True
            junction_status, quads = getJunctionStatus(ego_vehicle,current_junction)
            print(junction_status)

        if quads != None:
            print(quads.get_quadrant(ego_vehicle.get_transform().location))

        score_change, new_triggered_assertions = assertionCheckTick(active_assertions)
        if len(new_triggered_assertions) > 0:
            enumed_vars, quant_vars = world_state.get_coverage_state()
            coverage.add_covered(enumed_vars,quant_vars,new_triggered_assertions)
        triggered_assertions.extend(new_triggered_assertions)
        score_writer.add_and_update_scenario_score(score_change)
        time.sleep(0.1)

def assertionCheckTick(assertions):
    score_change = 0
    for i in range(len(assertions)):
        if assertions[i].IsActive(RainTags.NONE):
            assertions[i].Check()
            if assertions[i].violated:
                if assertions[i].vacuous:
                    print("Unfair test:",assertions[i].description,"-1")
                    score_change -= 1
                else:
                    print("Bug found:",assertions[i].description,"+1")
                    score_change += 1

    triggered_assertions = [x for x in assertions if x.violated]
    assertions[:] = [x for x in assertions if not x.violated]
    return score_change, triggered_assertions

def performingSafeLeftTurn(ego_vehicle,vehicle):
    return ego_vehicle.get_control().steer < 0 and incomingVehicleAllowsLeftTurn(ego_vehicle,vehicle)

def performingSafeRightTurn(ego_vehicle,vehicle):
    return ego_vehicle.get_control().steer > 0 and incomingVehicleAllowsRightTurn(ego_vehicle,vehicle)

# Returns true if oncoming vehicle is travelling in direction of right lane of major road or vehicle is parked at junction
def incomingVehicleAllowsLeftTurn(ego_vehicle,vehicle):
    return upcoming_travelling_to_right(ego_vehicle,vehicle) or vehicle.get_velocity().length() <= 0

# Returns true if oncoming vehicle is travelling in direction of left lane of major road and turning left or vehicle is parked at junction
def incomingVehicleAllowsRightTurn(ego_vehicle,vehicle):
    return (vehicle.get_control().steer < 0 and not upcoming_travelling_to_right(ego_vehicle,vehicle)) or vehicle.get_velocity().length() <= 0

def upcoming_travelling_to_right(forward_vehicle,upcoming):
    va = forward_vehicle.get_transform().get_right_vector()
    vb = upcoming.get_transform().get_forward_vector()
    return va.x * vb.x + va.y * vb.y > 0

def vehicleInJunction(vehicle: carla.Actor,junction: carla.Junction,extentMargins: carla.Vector3D = carla.Vector3D(0,0,5)):
    bb = junction.bounding_box
    nbb = carla.BoundingBox(carla.Vector3D(0,0,0),bb.extent + extentMargins)
    if nbb.contains(vehicle.get_transform().location + carla.Vector3D(0,0,extentMargins.z/2),carla.Transform(bb.location,bb.rotation)):
        return True
    return False

def locationWithinBoxInFrontOfVehicle(from_vehicle: carla.Actor,location: carla.Location,box_length: float,world):
    
    extents = from_vehicle.bounding_box.extent
    transform = from_vehicle.get_transform()
    centre = transform.location
    directionVector = transform.get_forward_vector()

    box = carla.BoundingBox(carla.Vector3D(0,0,0),
                            carla.Vector3D((box_length/2),extents.y,extents.z))
    world.debug.draw_box(carla.BoundingBox(centre + directionVector * (box_length/2),carla.Vector3D((box_length/2),extents.y,extents.z)),transform.rotation,life_time=0.1)
    return box.contains(location,carla.Transform(centre + directionVector * (box_length/2),transform.rotation))
                   

def stoppingDistance(speed):
    # Stopping distance = thinking distance + braking distance
    # DVSA formulae: Thinking distance = 0.3 * speed, braking distance = 0.015 * speed^2
    return 0.3 * speed + speed * speed * 0.015

class JunctionStates(Enum):
    T_ON_MAJOR = 0
    T_ON_MINOR = 1
    UNKNOWN = 2
    NONE = 3
    ROUNDABOUT = 4

def straightOnAtJunction(vehicle: carla.Vehicle,junction_status: JunctionStates):
    return vehicle.get_control().steer == 0 and junction_status == JunctionStates.T_ON_MAJOR

def currentJunction(ego,map):
    ego_waypoint = map.get_waypoint(ego.get_location())
    return ego_waypoint.get_junction()

class JunctionQuadrants(Enum):
    OUTER_BEFORE_TURNING = 0
    OUTER_AFTER_TURNING = 1
    INNER_BEFORE_TURNING = 2
    INNER_AFTER_TURNING = 3

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

if __name__ == '__main__':
    main()
