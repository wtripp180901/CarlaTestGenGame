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

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

def main():
    
    client = carla.Client('localhost', 2000)
    world = client.get_world()
    if args.serverless:
        setupForTest(world)
    actors = world.get_actors()
    vehicles = actors.filter('*vehicle*')

    ego_vehicle = None
    for i in range(len(vehicles)):
        if vehicles[i].attributes['role_name'] == 'ego':
            ego_vehicle = vehicles[i]
            break
    if ego_vehicle == None:
        print("Couldn't find ego vehicle in",len(vehicles),"vehicles searched")
        return -1
    
    testScore = 0
    
    x = TestActor()
    y = TestActor()
    y.pos = 30
    
    assertions = [
        Assertion(126,
                "Maintain a safe stopping distance",
                (lambda: x.getPos()-y.getPos() < stoppingDistance(30) + 10),
                (lambda: x.getPos()-y.getPos() > stoppingDistance(30))
                )
    ]

    for i in range(30):
        x.pos += 1
        scoreChange = assertionCheckTick(assertions)
        testScore += scoreChange
    print("done")


def setupForTest(world):
    ego = carla.Actor("vehicle.audi.a2",carla.Location(0,0,0))
    ego.attributes["role_name"] = "ego"
    world.actors.append(ego)
    world.actors.append(carla.Actor("vehicle.audi.etron",carla.Location(0,0,5)))

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

def locationWithinBoxInFrontOfVehicle(fromVehicle: carla.Actor,location: carla.Location,boxLength: float):
    extents = fromVehicle.bounding_box.extent
    centre = fromVehicle.get_location
    centre = carla.Vector3D(centre.x,centre.y,centre.z)
    velocityLength = fromVehicle.get_velocity().length()
    if velocityLength < 0.00001:
        return False
    directionVector = fromVehicle.get_velocity() / scalarToVector(velocityLength)
    perpVector = directionVector.cross(carla.Vector3D(0,1,0))
    boxPoints = []
    boxPoints.append(centre + scalarToVector(extents.z) * directionVector + scalarToVector(extents.x) * perpVector)
    boxPoints.append(centre + scalarToVector(extents.z) * directionVector - scalarToVector(extents.x) * perpVector)
    boxPoints.append(boxPoints[0] + directionVector * scalarToVector(boxLength))
    boxPoints.append(boxPoints[1] + directionVector * scalarToVector(boxLength))
    boxPoints = [(b.x,b.z) for b in boxPoints]

    box = shapely.Polygon(boxPoints)
    point = shapely.Point(location.x,location.z)
    return box.contains(point)
                   

def scalarToVector(scalar: float):
    return carla.Vector3D(scalar,scalar,scalar)

def stoppingDistance(speed):
    # Stopping distance = thinking distance + braking distance
    # DVSA formulae: Thinking distance = 0.3 * speed, braking distance = 0.015 * speed^2
    return 0.3 * speed + speed * speed * 0.015

if __name__ == '__main__':
    main()
