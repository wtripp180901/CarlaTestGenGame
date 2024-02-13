import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-s","--serverless",default=False)
args = parser.parse_args()

import carla
from assertion import Assertion
from tags import *
import random
import time
import test_setup

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

def main():
    
    ego_vehicle = None
    non_ego_actors = None
    non_ego_vehicles = None
    
    client = carla.Client('localhost', 2000)
    world = client.get_world()
    test_setup.setupForTest("stationaryCollision",world)
    
    test_score = 0
    
    assertions = [
        Assertion(126,
                "Maintain a safe stopping distance",
                (lambda: any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()) + 5,world) for t in non_ego_vehicles)),
                (lambda: not any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(ego_vehicle.get_velocity().length()),world) for t in non_ego_vehicles))
                )
    ]

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

if __name__ == '__main__':
    main()
