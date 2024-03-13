import carla
import time

def stationaryCollision(client: carla.Client,other_actor_bp: str):
    world = client.get_world()
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, world.get_map().get_spawn_points()[0])
    world.get_spectator().set_transform(ego.get_transform())
    world.spawn_actor(world.get_blueprint_library().filter(other_actor_bp)[0], carla.Transform(ego.get_transform().location + carla.Vector3D(100,0,0),ego.get_transform().rotation))
    ego.apply_control(carla.VehicleControl(throttle=1.0))
    return world

def stationaryVehicleCollision(client: carla.Client):
    return stationaryCollision(client,"vehicle.audi.etron")

def stationaryPedestrianCollision(client: carla.Client):
    return stationaryCollision(client,"walker.pedestrian.0001")

# Left turn with vehicle in left lane
def TJunctionMinorUnsafe(client: carla.Client):
    ego, world = TJunction(client,244)
    major_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[43]))
    major_vehicle.apply_control(carla.VehicleControl(throttle=0.95))
    time.sleep(2.5)
    ego.apply_control(carla.VehicleControl(throttle=0.85,steer=-0.05))
    print("Checking starting now")
    return world

# Left right turn with vehicle in left lane of major road turning left in junction
def TJunctionMinorSafeRight(client: carla.Client):
    ego, world = TJunction(client,244)
    major_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[78]))
    major_vehicle.apply_control(carla.VehicleControl(throttle=0.775,steer=-0.14))
    ego.set_light_state(carla.VehicleLightState(carla.VehicleLightState.RightBlinker))
    time.sleep(2.5)
    ego.apply_control(carla.VehicleControl(throttle=0.85,steer=0.05))
    print("Checking starting now")
    return world

# Left turn with vehicle in right lane
def TJunctionMinorSafe(client: carla.Client):
    ego, world = TJunction(client,244)
    major_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[47]))
    major_vehicle.apply_control(carla.VehicleControl(throttle=0.95))
    ego.set_light_state(carla.VehicleLightState(carla.VehicleLightState.LeftBlinker))
    time.sleep(2.5)
    ego.apply_control(carla.VehicleControl(throttle=0.85,steer=-0.05))
    print("Checking starting now")
    return world

# Right turn with vehicle in right lane
def TJunctionMinorRight(client: carla.Client):
    ego, world = TJunction(client,244)
    major_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[47]))
    major_vehicle.apply_control(carla.VehicleControl(throttle=0.95))
    time.sleep(2.5)
    ego.apply_control(carla.VehicleControl(throttle=0.85,steer=0.04))
    print("Checking starting now")
    return world

def TJunctionMajor(client: carla.Client,opposite_steering: float):
    ego, world = TJunction(client,125)
    major_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[78]))
    major_vehicle.apply_control(carla.VehicleControl(throttle=0.6))
    ego.apply_control(carla.VehicleControl(throttle=0.9,steer=opposite_steering))
    return world

def TJunctionMajorStraightOn(client: carla.Client):
    return TJunctionMajor(client,0)

def TJunctionMajorUnsafeRight(client: carla.Client):
    return TJunctionMajor(client,0.15)

def TJunction(client: carla.Client,spawnNumber: int):
    world = client.load_world("Town01")
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.tt")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, reversed_spawn(world.get_map().get_spawn_points()[spawnNumber]))
    ego.apply_control(carla.VehicleControl(throttle=0.85))
    world.get_spectator().set_transform(ego.get_transform())
    return ego, world

def Roundabout(client: carla.Client):
    world = client.load_world("Town03_Opt")
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, reversed_spawn(world.get_map().get_spawn_points()[245]))
    priority_vehicle = world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0],reversed_spawn(world.get_map().get_spawn_points()[81]))
    ego.apply_control(carla.VehicleControl(throttle=0.5))
    priority_vehicle.apply_control(carla.VehicleControl(throttle=0.5))
    world.get_spectator().set_transform(ego.get_transform())
    return world


def reversed_spawn(spawn_point: carla.Transform):
    return carla.Transform(spawn_point.location, carla.Rotation(spawn_point.rotation.pitch,spawn_point.rotation.yaw + 180,spawn_point.rotation.roll))

test_scenarios = {
    "StationaryCollision" : stationaryVehicleCollision,
    "TJunctionMinorRoad": TJunctionMinorUnsafe,
    "TJunctionSafeLeft": TJunctionMinorSafe,
    "TJunctionSafeRight": TJunctionMinorSafeRight,
    "TJunctionMajorRight": TJunctionMajorUnsafeRight,
    "TJunctionMajorStraight": TJunctionMajorStraightOn,
    "TJunctionRight": TJunctionMinorRight,
    "Roundabout": Roundabout,
    "PedestrianCollision": stationaryPedestrianCollision
}

def setupForTest(test_name: str,client: carla.Client) -> carla.World:
    test = test_scenarios.get(test_name)
    if test != None:
        return test(client)
    else:
        return client.get_world()