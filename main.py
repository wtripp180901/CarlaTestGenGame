import argparse

import carla
from assertion import Assertion
from validity_requirements import *
from coverage import *
import assertion
import time
import test_setup
import numpy as np
import score_writer
from world_state import WorldState, dot2d, get_emergency_vehicle_status
from fnmatch import fnmatch

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

off_road_event_flag = False
static_collision_event_flag = False
no_stopping_line_event_flag = False

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--scenario",default="none")
    args = parser.parse_args()

    has_junction = False
    junction_status = JunctionStates.NONE
    quads = None
    
    client = carla.Client('localhost', 2000)
    client.set_timeout(10)
    world = test_setup.setupForTest(args.scenario,client)
    world_state = WorldState(world)
    map = world.get_map()

    ego_vehicle = None
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
    other_vehicles_and_pedestrians = [x for x in non_ego_actors if vehicle_or_pedestrian(x)]
    non_ego_vehicles = [x for x in non_ego_vehicles if x.id != ego_vehicle.id]

    global off_road_event_flag
    global no_stopping_line_event_flag
    off_road_event_flag = False
    li_blueprint = world.get_blueprint_library().find('sensor.other.lane_invasion')
    lane_invasion_sensor = world.spawn_actor(li_blueprint,carla.Transform(carla.Location(0,0,0)),attach_to=ego_vehicle)
    lane_invasion_sensor.listen(lane_callback)

    global static_collision_event_flag
    static_collision_event_flag = False
    collision_blueprint = world.get_blueprint_library().find('sensor.other.collision')
    collision_sensor = world.spawn_actor(collision_blueprint,carla.Transform(carla.Location(0,0,0)),attach_to=ego_vehicle)
    collision_sensor.listen(collision_callback)

    for i,s in enumerate(world.get_map().get_spawn_points()):
        world.debug.draw_string(s.location + carla.Vector3D(0,0,2),str(i),life_time=60)

    traffic_light_status = (False,False)
    
    active_assertions = [
        Assertion(126, 0,
                "Maintain a safe stopping distance",
                (lambda: any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()) + 5,world) for t in other_vehicles_and_pedestrians)),
                (lambda: not any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()),world) for t in other_vehicles_and_pedestrians))
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
                               and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) and (not performingSafeLeftTurn(ego_vehicle,v,quads,junction_status) and not performingSafeRightTurn(ego_vehicle,v,quads,junction_status)) for v in non_ego_vehicles)) 
                               or ego_vehicle.get_velocity().length() < 0.1,
                  validityRequirements=IN_JUNCTION_REQUIREMENTS
                ),
        Assertion(170, 1,
                  "Give way to vehicles on major road (major case)",
                  lambda: junction_status == JunctionStates.T_ON_MAJOR and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles),
                  lambda: (not (junction_status == JunctionStates.T_ON_MAJOR and (any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles))) or straightOnAtJunction(ego_vehicle,junction_status))
                            or ego_vehicle.get_velocity().length() < 0.1,
                  validityRequirements=IN_JUNCTION_REQUIREMENTS
                ),
        Assertion(103,0,
                  "Give signals before manoeuvering",
                  lambda: junction_status != JunctionStates.NONE,
                  lambda: ((ego_vehicle.get_light_state() == carla.VehicleLightState.RightBlinker or not ego_vehicle.get_control().steer > 0) and (ego_vehicle.get_light_state() == carla.VehicleLightState.LeftBlinker or not ego_vehicle.get_control().steer < 0)) or not junction_status != JunctionStates.NONE,
                ),
        Assertion(219,0,
                  "Stop to let emergency service vehicles pass",
                  lambda: active_emergency_vehicle_within_distance(ego_vehicle,world,50),
                  lambda: parked_left(ego_vehicle,map) or not active_emergency_vehicle_within_distance(ego_vehicle,world,30),
                  validityRequirements=ValidityRequirement({CoverageVariable.EMERGENCY_VEHICLE_STATUS: [EmergencyVehicleStatus.PRESENT,EmergencyVehicleStatus.SIREN]},None,False)
                  ),
        Assertion(238,0,
                  "No waiting or parking on yellow or red lines",
                  lambda: not active_emergency_vehicle_within_distance(ego_vehicle,world,50),
                  lambda: not (parked_left(ego_vehicle,map) and no_stopping_line_event_flag)
                  ),
        Assertion(0,0,
                  "Must stop at traffic lights",
                  lambda: traffic_light_status[0],
                  lambda: (ego_vehicle.get_velocity().length() <= 0 or ego_vehicle.get_control().brake > ego_vehicle.get_control().throttle) or not (traffic_light_status[0] and not traffic_light_status[1])
                  ),
        Assertion(0,1,
                  "Stay on road",
                  lambda: True,
                  lambda: not off_road_event_flag),
        Assertion(0,2,
                  "Collision with terrain",
                  lambda: True,
                  lambda: not static_collision_event_flag)
    ]

    coverage = Coverage(active_assertions,world_state.coverage_space)

    while True:

        traffic_light_status = american_traffic_light_status(ego_vehicle,map,world)
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

        qual_vars = world_state.get_coverage_state(ego_vehicle,non_ego_vehicles,map)
        score_change, triggered_assertions, covered_assertions, valid_assertions = assertionCheckTick(active_assertions,qual_vars)
        coverage.try_cover(qual_vars,triggered_assertions,covered_assertions,valid_assertions)

        # world.debug.draw_line(ego_wp.transform.location,ego_wp.transform.location + carla.Vector3D(0,0,5),life_time=0.1)
        # for w in ego_wp.next(10):
        #     world.debug.draw_line(w.transform.location,w.transform.location + carla.Vector3D(0,0,5),color=carla.Color(0,255,0),life_time=0.1)
        # for w in ego_wp.previous(10):
        #     world.debug.draw_line(w.transform.location,w.transform.location + carla.Vector3D(0,0,5),color=carla.Color(0,0,255),life_time=0.1)

        if score_change != 0:
            score_writer.add_and_update_scenario_score(score_change)

        off_road_event_flag = False
        static_collision_event_flag = False
        no_stopping_line_event_flag = False
        time.sleep(0.1)

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

def lane_callback(li_event):
    global off_road_event_flag
    global no_stopping_line_event_flag
    crossed_markings = [l.type for l in li_event.crossed_lane_markings]
    colors = [l.color for l in li_event.crossed_lane_markings]
    if any([c in [carla.LaneMarkingType.Grass,carla.LaneMarkingType.Curb,carla.LaneMarkingType.NONE] for c in crossed_markings]):
        off_road_event_flag = True
    if any([c in [carla.LaneMarkingColor.Red,carla.LaneMarkingColor.Yellow] for c in colors]):
        no_stopping_line_event_flag = True

def collision_callback(col_event):
    global static_collision_event_flag
    if not vehicle_or_pedestrian(col_event.other_actor):
        static_collision_event_flag = True

def assertionCheckTick(assertions: List[assertion.Assertion],qualitative_coverage_state: List[Tuple[CoverageVariable,Enum]]):
    score_change = 0
    valid_assertions = []
    covered_assertions = []
    triggered_assertions = []

    for i in range(len(assertions)):
        if assertions[i].IsActive(qualitative_coverage_state):
            valid_assertions.append(assertions[i])
            violated_before_tick = assertions[i].violated
            assertions[i].Check()
            if assertions[i].precondition_active_in_tick:
                covered_assertions.append(assertions[i])
                if assertions[i].violated_in_tick:
                    triggered_assertions.append(assertions[i])
            if assertions[i].violated and not violated_before_tick:
                if assertions[i].zero_value:
                    print("Unfair test:",assertions[i].description,"+0")
                else:
                    print("Bug found:",assertions[i].description,"+1")
                    score_change += 1

    return score_change, triggered_assertions, covered_assertions, valid_assertions


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

if __name__ == '__main__':
    main()
