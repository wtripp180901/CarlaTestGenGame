import carla

def stationaryCollision(client: carla.Client):
    world = client.get_world()
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, world.get_map().get_spawn_points()[0])
    world.get_spectator().set_transform(ego.get_transform())
    world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0], carla.Transform(ego.get_transform().location + carla.Vector3D(100,0,0),ego.get_transform().rotation))
    ego.apply_control(carla.VehicleControl(throttle=1.0))
    return world

def TJunctionMinor(client: carla.Client):
    return TJunction(client,0)

def TJunctionMajor(client: carla.Client):
    return TJunction(client,42)

def TJunction(client: carla.Client,spawnNumber: int):
    world = client.load_world("Town01")
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, world.get_map().get_spawn_points()[spawnNumber])
    ego.apply_control(carla.VehicleControl(throttle=0.5))
    world.get_spectator().set_transform(ego.get_transform())
    return world


test_scenarios = {
    "stationaryCollision" : stationaryCollision,
    "TJunctionMinorRoad": TJunctionMinor,
    "TJunctionMajorRoad": TJunctionMajor
}

def setupForTest(test_name: str,client: carla.Client) -> carla.World:
    test = test_scenarios.get(test_name)
    if test != None:
        return test(client)
    else:
        return client.get_world()