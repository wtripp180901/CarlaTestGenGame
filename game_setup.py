import pygame
import carla
from test_setup import reversed_spawn

def game_setup_loop(screen,spectator,world,map):
    setting_up_scenario = True
    ego_vehicle_placed = False
    last_placed_vehicle = None
    current_bp_id = "vehicle.audi.etron"
    camera_speed = 0.25
    spectator_rotation = carla.Rotation(pitch=-90)
    spectator.set_transform(carla.Transform(map.get_spawn_points()[0].location + carla.Vector3D(0,0,50),spectator_rotation))
    
    vehicle_paths = []
    current_path = []
    
    while setting_up_scenario:
        
        keys_pressed = pygame.key.get_pressed()
        move_vec = carla.Vector3D(0,0,0)
        if keys_pressed[pygame.K_UP]:
            move_vec.x = 1 * camera_speed
        if keys_pressed[pygame.K_DOWN]:
            move_vec.x = -1 * camera_speed
        if keys_pressed[pygame.K_LEFT]:
            move_vec.y = -1 * camera_speed
        if keys_pressed[pygame.K_RIGHT]:
            move_vec.y = 1 * camera_speed
        spectator.set_transform(carla.Transform(spectator.get_location() + move_vec,spectator_rotation))

        cursor_location = spectator.get_location()
        cursor_location.z = 1
        

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if ego_vehicle_placed:
                        placed_vehicle = place_vehicle(current_bp_id,cursor_location,world,map)
                        if placed_vehicle != None:
                            if last_placed_vehicle != None:
                                current_path.insert(0,last_placed_vehicle.get_location())
                                vehicle_paths.append((last_placed_vehicle,current_path))
                            last_placed_vehicle = placed_vehicle
                            current_path = []
                    else:
                        place_vehicle("vehicle.tesla.cybertruck",cursor_location,world,map,is_ego=True)
                        ego_vehicle_placed = True
                if event.key == pygame.K_w and last_placed_vehicle != None:
                    current_path.append(cursor_location)
                    world.debug.draw_point(cursor_location,life_time=0)
                if event.key == pygame.K_RETURN:
                    current_path.insert(0,last_placed_vehicle.get_location())
                    vehicle_paths.append((last_placed_vehicle,current_path))
                    setting_up_scenario = False

        pygame.display.flip()

    for i in range(len(vehicle_paths)):
        for j in range(len(vehicle_paths[i][1])):
            vehicle_paths[i][1][j].z = 0

    return vehicle_paths
        
def place_vehicle(blueprint_id,location,world,map,is_ego=False):
    bp = world.get_blueprint_library().filter(blueprint_id)[0]
    if is_ego:
        bp.set_attribute('role_name','hero')
    return world.try_spawn_actor(bp,
                                reversed_spawn(carla.Transform(location,map.get_waypoint(location).transform.rotation))
                                )