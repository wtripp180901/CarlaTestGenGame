import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-s","--serverless",default=False)
args = parser.parse_args()

if args.serverless:
    import carlaSpoofer as carla
else:
    import carla

from assertion import Assertion
from tags import *
import shapely.geometry
import random
import time

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

ego_vehicle = None
nonEgoActors = None
nonEgoVehicles = None

def main():
    
    client = carla.Client('localhost', 2000)
    world = client.get_world()
    setupForTest(world)
    nonEgoActors = world.get_actors()
    nonEgoVehicles = nonEgoActors.filter('*vehicle*')

    for i in range(len(nonEgoActors)):
        if nonEgoActors[i].attributes.get('role_name') == 'hero':
            ego_vehicle = nonEgoActors[i]
            break
    if ego_vehicle == None:
        print("Couldn't find ego vehicle in",len(nonEgoVehicles),"vehicles searched")
        return -1
    
    nonEgoActors = [x for x in nonEgoActors if x.id != ego_vehicle.id]
    nonEgoVehicles = [x for x in nonEgoVehicles if x.id != ego_vehicle.id]
    
    testScore = 0
    
    assertions = [
        Assertion(126,
                "Maintain a safe stopping distance",
                (lambda: any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(t.get_velocity().length()) + 10,world) for t in nonEgoVehicles)),
                (lambda: not any(locationWithinBoxInFrontOfVehicle(ego_vehicle,t.get_location(),stoppingDistance(t.get_velocity().length()),world) for t in nonEgoVehicles))
                )
    ]

    while True:
        scoreChange = assertionCheckTick(assertions)
        testScore += scoreChange
        time.sleep(0.1)


def setupForTest(world):
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, world.get_map().get_spawn_points()[0])
    world.get_spectator().set_transform(ego.get_transform())
    world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0], carla.Transform(ego.get_transform().location + carla.Vector3D(50,0,0),ego.get_transform().rotation))
    ego.apply_control(carla.VehicleControl(throttle=1.0))

def assertionCheckTick(assertions):
    scoreChange = 0
    for i in range(len(assertions)):
        if assertions[i].IsActive(RainTags.NONE):
            assertions[i].Check()
            if assertions[i].violated:
                if assertions[i].vacuous:
                    print("Unfair test:",assertions[i].description,"-1")
                    scoreChange -= 1
                else:
                    print("Bug found:",assertions[i].description,"+1")
                    scoreChange += 1

    assertions[:] = [x for x in assertions if not x.violated]
    return scoreChange

def locationWithinBoxInFrontOfVehicle(fromVehicle: carla.Actor,location: carla.Location,boxLength: float,world):
    
    extents = fromVehicle.bounding_box.extent
    transform = fromVehicle.get_transform()
    centre = transform.location
    #centre = carla.Vector3D(centre.x,centre.y,centre.z)

    directionVector = transform.get_forward_vector()
    #perpVector = transform.get_right_vector()

    # boxPoints = []
    # boxPoints.append(centre + extents.x * directionVector + extents.y * perpVector)
    # boxPoints.append(centre + extents.x * directionVector - extents.y * perpVector)
    # boxPoints.append(boxPoints[0] + directionVector * boxLength)
    # boxPoints.append(boxPoints[1] + directionVector * boxLength)
    # boxPoints = [(b.x,b.y) for b in boxPoints]

    # box = shapely.Polygon(boxPoints)
    # point = shapely.Point(location.x,location.z)
    # return box.contains(point)

    box = carla.BoundingBox(carla.Vector3D(0,0,0),
                            carla.Vector3D((boxLength/2),extents.y,extents.z))
    return box.contains(location,carla.Transform(centre + directionVector * (boxLength/2),transform.rotation))
                   

# def scalarToVector(scalar: float):
#     return carla.Vector3D(scalar,scalar,scalar)

def stoppingDistance(speed):
    # Stopping distance = thinking distance + braking distance
    # DVSA formulae: Thinking distance = 0.3 * speed, braking distance = 0.015 * speed^2
    return 0.3 * speed + speed * speed * 0.015

if __name__ == '__main__':
    main()
