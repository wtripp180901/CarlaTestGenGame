import carla

def stationaryCollision(world: carla.World):
    ego_bp = world.get_blueprint_library().filter("vehicle.audi.a2")[0]
    ego_bp.set_attribute('role_name', 'hero')
    ego = world.spawn_actor(ego_bp, world.get_map().get_spawn_points()[0])
    world.get_spectator().set_transform(ego.get_transform())
    world.spawn_actor(world.get_blueprint_library().filter("vehicle.audi.etron")[0], carla.Transform(ego.get_transform().location + carla.Vector3D(100,0,0),ego.get_transform().rotation))
    ego.apply_control(carla.VehicleControl(throttle=1.0))

test_scenarios = {
    "stationaryCollision" : stationaryCollision
}

def setupForTest(test_name: str,world: carla.World):
    test = test_scenarios.get(test_name)
    test(world)