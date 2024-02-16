import argparse

import carla
from assertion import Assertion
from tags import *
import random
import time
import test_setup
import numpy

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
    map = world.get_map()

    for i,s in enumerate(world.get_map().get_spawn_points()):
        world.debug.draw_string(s.location + carla.Vector3D(0,0,2),str(i),life_time=20)
    
    test_score = 0
    
    assertions = [
        Assertion(126,
                "Maintain a safe stopping distance",
                (lambda: any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()) + 5,world) for t in non_ego_vehicles)),
                (lambda: not any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()),world) for t in non_ego_vehicles))
                ),
        Assertion(124,
                "You must not exceed maximum speed limits",
                (lambda: ego_vehicle.get_speed_limit() != None),
                (lambda: ego_vehicle.get_velocity().length() <= ego_vehicle.get_speed_limit())
                ),
        Assertion(170,
                  "Give way to vehicles on major road",
                  lambda: junction_status == JunctionStates.T_ON_MINOR and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) for v in non_ego_vehicles),
                  lambda: not (junction_status == JunctionStates.T_ON_MINOR 
                               and any(vehicleInJunction(v,currentJunction(ego_vehicle,map)) and not performingSafeLeftTurn(ego_vehicle,v) for v in non_ego_vehicles)) 
                               or ego_vehicle.get_velocity().length() < 0.1
        )
    ]

    has_junction = False
    junction_status = JunctionStates.NONE
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
        if not has_junction and current_junction != None:
            has_junction = True
            junction_status = getJunctionStatus(ego_vehicle,current_junction)
            print(junction_status)

        score_change = assertionCheckTick(assertions)
        test_score += score_change
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

    assertions[:] = [x for x in assertions if not x.violated]
    return score_change

def performingSafeLeftTurn(ego_vehicle,vehicle):
    return ego_vehicle.get_control().steer < 0 and incomingVehicleAllowLeftTurn(ego_vehicle,vehicle)

# Returns true if oncoming vehicle is going right (assuming in right lane) or vehicle is parked at junction
def incomingVehicleAllowLeftTurn(ego_vehicle,vehicle):
    return ego_vehicle.get_transform().get_forward_vector().dot(vehicle.get_transform().get_forward_vector()) < 0 or vehicle.get_velocity().length() < 0
    

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

def currentJunction(ego,map):
    ego_waypoint = map.get_waypoint(ego.get_location())
    return ego_waypoint.get_junction()


def getJunctionStatus(ego,junction):
    
    waypoints = junction.get_waypoints(carla.LaneType.Driving)
    entrypoints = [t[0] for t in waypoints]
    distances = [(ego.get_transform().location - e.transform.location).length() for e in entrypoints]
    closestInd = numpy.argmin(distances)
    entrypoint = entrypoints[closestInd]

    straight_path = False
    #TODO: distinguish between left and right somehow
    other_path = False
    location = entrypoint.transform.location
    destinations_from_entrypoint = [w[1].transform.location for w in waypoints if (w[0].transform.location - location).length() < 0.01]
    direction_vector = location - entrypoint.previous(10)[0].transform.location
    direction_vector = direction_vector / direction_vector.length()
    for d in destinations_from_entrypoint:
        if (d - (location + direction_vector * (d - location).length())).length() < 1:
            straight_path = True
        else:
            other_path = True
    if straight_path and other_path:
        return JunctionStates.T_ON_MAJOR
    elif other_path:
        return JunctionStates.T_ON_MINOR
    else:
        return JunctionStates.UNKNOWN
        

            

if __name__ == '__main__':
    main()
