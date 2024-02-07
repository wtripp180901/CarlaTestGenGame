import carla
from assertion import Assertion
from tags import *

# client = carla.Client('localhost', 2000)
# world = client.get_world()

class TestActor:
    def __init__(self):
        self.pos = 0
    def getPos(self):
        return self.pos

def main():
    
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

def stoppingDistance(speed):
    # Stopping distance = thinking distance + braking distance
    # DVSA formulae: Thinking distance = 0.3 * speed, braking distance = 0.015 * speed^2
    return 0.3 * speed + speed * speed * 0.015

if __name__ == '__main__':
    main()
