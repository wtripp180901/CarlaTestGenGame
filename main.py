import argparse
import random
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
import pygame
from game import Game
from os import linesep
import game_setup
from checker_utils import *

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

off_road_event_flag = False
static_collision_event_flag = False
no_stopping_line_event_flag = False
no_overtaking_event_flag = False
crossing_into_right_lane_event_flag = False

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--scenario",default="none")
    args = parser.parse_args()

    has_junction = False
    junction_status = JunctionStates.NONE
    quads = None
    
    client = carla.Client('localhost', 2000)
    client.set_timeout(25)
    world, is_test_scenario = test_setup.setupForTest(args.scenario,client)

    pygame.init()
    screen = pygame.display.set_mode((640,480))

    if not is_test_scenario:
        kill_list = [a for a in world.get_actors() if fnmatch(a.type_id,"*walker*") or fnmatch(a.type_id,"*vehicle*") or fnmatch(a.type_id,"*sensor*")]
        for a in kill_list:
            a.destroy()
        world = game_setup.world_settings_loop(screen,client,world)

    world_state = WorldState(world)
    map = world.get_map()
    spectator = world.get_spectator()

    vehicle_paths = []
    if not is_test_scenario:
        vehicle_paths = game_setup.game_setup_loop(screen,spectator,world,map)

    ego_vehicle = None
    non_ego_actors = [x for x in world.get_actors()]
    non_ego_vehicles = [x for x in world.get_actors().filter('*vehicle*')]

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
    global no_overtaking_event_flag
    global no_stopping_line_event_flag
    global crossing_into_right_lane_event_flag
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
                (lambda: any(within_box_in_front_of_vehicle(ego_vehicle,t,stoppingDistance(ego_vehicle.get_velocity().length()) + 5,world) for t in other_vehicles_and_pedestrians)),
                (lambda: not any(within_box_in_front_of_vehicle(ego_vehicle,t,stoppingDistance(ego_vehicle.get_velocity().length()),world) for t in other_vehicles_and_pedestrians))
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
                  validityRequirements=ValidityRequirement({CoverageVariable.EMERGENCY_VEHICLE_STATUS: [EmergencyVehicleStatus.PRESENT,EmergencyVehicleStatus.SIREN]})
                  ),
        Assertion(238,0,
                  "No waiting or parking on yellow or red lines",
                  lambda: not active_emergency_vehicle_within_distance(ego_vehicle,world,50),
                  lambda: not (parked_left(ego_vehicle,map) and no_stopping_line_event_flag)
                  ),
        Assertion(129,0,
                  "Must not cross solid road markings",
                  lambda: True,
                  lambda: not no_overtaking_event_flag),
        Assertion(160,
                  0,
                  "Stay in the left lane unless safely overtaking",
                  lambda: True,
                  lambda: not (not_in_left_lane(ego_vehicle,map,junction_status) and not any([vehicle_in_overtake_range(ego_vehicle,v) for v in non_ego_vehicles]))
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

    session_timestamp = time.strftime("%d-%m-%Y_%H-%M-%S",time.localtime())

    global_coverage = Coverage("out/global_coverage.csv",active_assertions,world_state.coverage_space)
    session_coverage = Coverage("out/coverage_"+session_timestamp+".csv",active_assertions,world_state.coverage_space)
    scorer = score_writer.ScoreWriter("out/score_"+session_timestamp+".csv")

    clock = pygame.time.Clock()
    game = Game(screen)
    new_covered_cases_in_session = 0
    
    while True:

        if not is_test_scenario:
            execute_vehicle_behaviour(vehicle_paths,world)
            execute_ego_behaviour(ego_vehicle)

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
        score_change, triggered_assertions, covered_assertions, valid_assertions, bug_descriptions = assertionCheckTick(active_assertions,qual_vars)
        new_covered_cases_in_session += global_coverage.try_cover(qual_vars,triggered_assertions,covered_assertions,valid_assertions)
        session_coverage.try_cover(qual_vars,triggered_assertions,covered_assertions,valid_assertions)

        # world.debug.draw_line(ego_wp.transform.location,ego_wp.transform.location + carla.Vector3D(0,0,5),life_time=0.1)
        # for w in ego_wp.next(10):
        #     world.debug.draw_line(w.transform.location,w.transform.location + carla.Vector3D(0,0,5),color=carla.Color(0,255,0),life_time=0.1)
        # for w in ego_wp.previous(10):
        #     world.debug.draw_line(w.transform.location,w.transform.location + carla.Vector3D(0,0,5),color=carla.Color(0,0,255),life_time=0.1)

        if score_change != 0:
            scorer.add_and_update_scenario_score(score_change)

        off_road_event_flag = False
        static_collision_event_flag = False
        no_stopping_line_event_flag = False
        no_overtaking_event_flag = False
        crossing_into_right_lane_event_flag = False

        game.update_score_text(str(scorer.score),str(new_covered_cases_in_session),bug_descriptions)
        global_max, _, global_covered = global_coverage.get_num_cases()
        game.update_global_coverage_progress(global_covered,global_max)
        game.handle_input()
        game.render()
        if (spectator.get_location() - ego_vehicle.get_location()).length() > 32:
            spec_trans = spectator.get_transform()
            ego_loc = ego_vehicle.get_location()
            spectator.set_transform(carla.Transform(carla.Location(ego_loc.x,ego_loc.y,spec_trans.location.z),spec_trans.rotation))
        clock.tick(10)

def execute_vehicle_behaviour(vehicle_paths: List[Tuple[carla.Actor,List[carla.Location]]],world):
    vehicles = [v[0] for v in vehicle_paths]
    paths = [p[1] for p in vehicle_paths]
    threshold = 4

    for i in range(len(vehicles)):
        is_vehicle = fnmatch(vehicles[i].type_id,"*vehicle*")
        loc_vec_2d = vehicles[i].get_location()
        loc_vec_2d.z = 0
        if len(paths[i]) > 0 and (loc_vec_2d - paths[i][0]).length() < threshold:
            del paths[i][0]
        if len(paths[i]) > 0:
            forward_vec = vehicles[i].get_transform().get_forward_vector()
            # print(vehicles[i].get_location())
            dir_to_point = paths[i][0] - loc_vec_2d
            if is_vehicle:
                forward_vec.z = 0
                dir_to_point.z = 0
                dir_to_point = dir_to_point / dir_to_point.length()
                steer = (1 - dot2d(forward_vec,dir_to_point))
                if dot2d(vehicles[i].get_transform().get_right_vector(),dir_to_point) < 0:
                    steer *= -1
                vehicles[i].apply_control(carla.VehicleControl(throttle=0.6,steer=steer))
            else:
                vehicles[i].apply_control(carla.WalkerControl(direction=dir_to_point,speed=0.1))
        else:
            if is_vehicle:
                vehicles[i].apply_control(carla.VehicleControl(brake=1))
            else:
                vehicles[i].apply_control(carla.WalkerControl())

def execute_ego_behaviour(ego_vehicle):
    ego_vehicle.apply_control(carla.VehicleControl(throttle=random.uniform(0,1),steer=random.uniform(-1,1)))

def not_in_left_lane(ego_vehicle,map,junction_status):
    global crossing_into_right_lane_event_flag
    ego_loc = ego_vehicle.get_location()
    ego_wp = map.get_waypoint(ego_loc)
    return junction_status == JunctionStates.NONE and (crossing_into_right_lane_event_flag or
                                                        (ego_wp.transform.location - map.get_waypoint(ego_loc + ego_vehicle.get_transform().get_right_vector() * ego_wp.lane_width).transform.location).length() < 0.1)

def lane_callback(li_event):
    global off_road_event_flag
    global no_stopping_line_event_flag
    global no_overtaking_event_flag
    global crossing_into_right_lane_event_flag
    crossed_markings = [l.type for l in li_event.crossed_lane_markings]
    colors = [l.color for l in li_event.crossed_lane_markings]
    if any([c in [carla.LaneMarkingType.Grass,carla.LaneMarkingType.Curb,carla.LaneMarkingType.NONE] for c in crossed_markings]):
        off_road_event_flag = True
    if any([c in [carla.LaneMarkingType.SolidSolid,carla.LaneMarkingType.SolidBroken] for c in crossed_markings]):
        no_overtaking_event_flag = True
    if any([c in [carla.LaneMarkingType.SolidSolid,carla.LaneMarkingType.SolidBroken,carla.LaneMarkingType.Broken,carla.LaneMarkingType.BrokenSolid,carla.LaneMarkingType.BrokenBroken] for c in crossed_markings]):
        crossing_into_right_lane_event_flag = True
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
    triggered_descriptions = []

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
                    triggered_descriptions.append("- Unfair test: "+assertions[i].description)
                else:
                    triggered_descriptions.append("+ "+assertions[i].description)
                    score_change += 1

    return score_change, triggered_assertions, covered_assertions, valid_assertions, triggered_descriptions
                   
if __name__ == '__main__':
    main()
