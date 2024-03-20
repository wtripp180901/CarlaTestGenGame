from typing import List
import pygame
import carla
from test_setup import reversed_spawn

def game_setup_loop(screen,spectator,world,map):
    
    font = pygame.font.SysFont("ComicSans.tff",32)
    vehicle_font = pygame.font.SysFont("ComicSans.tff",48)
    instructions, instruction_txts, instruction_txt_rects = set_instruction_texts(font,["Move cursor with arrow keys","Press SPACE to place the vehicle under test"])
    vehicle_display_names = ["Audi Etron","Chevrolet Impala","Pedestrian","Motorbike","Police Car","Ford Mustang","Delivery Truck","Citreon C3","Bike"]
    vehicle_blueprint_ids = ["vehicle.audi.etron",
                             "vehicle.chevrolet.impala",
                             "walker.pedestrian.0001",
                             "vehicle.harley-davidson.low_rider",
                             "vehicle.dodge.charger_police",
                             "vehicle.ford.mustang",
                             "vehicle.carlamotors.carlacola",
                             "vehicle.citroen.c3",
                             "vehicle.diamondback.century"
                             ]
    vehicle_index = 0
    vehicle_display_txt = vehicle_font.render(vehicle_display_names[0],True,(255,0,0),None)
    vehicle_display_rect = vehicle_display_txt.get_rect()
    vehicle_display_rect.center = (320,240)
    
    setting_up_scenario = True
    ego_vehicle_placed = False
    last_placed_vehicle = None
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
        world.debug.draw_point(cursor_location,life_time=0.017)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if ego_vehicle_placed:
                        placed_vehicle = place_vehicle(vehicle_blueprint_ids[vehicle_index],cursor_location,world,map)
                        if placed_vehicle != None:
                            if last_placed_vehicle != None:
                                current_path.insert(0,last_placed_vehicle.get_location())
                                vehicle_paths.append((last_placed_vehicle,current_path))
                            last_placed_vehicle = placed_vehicle
                            current_path = []
                    else:
                        place_vehicle("vehicle.tesla.cybertruck",cursor_location,world,map,is_ego=True)
                        ego_vehicle_placed = True
                        instructions, instruction_txts, instruction_txt_rects = set_instruction_texts(font,["Move cursor with arrow keys",
                                        "Press SPACE to place the vehicle under test",
                                        "Press W to place waypoints the actor will travel through",
                                        "Use A and D to choose an actor to place",
                                        "Press ENTER to begin test"])
                if event.key == pygame.K_w and last_placed_vehicle != None:
                    current_path.append(cursor_location)
                if event.key == pygame.K_d:
                    vehicle_index += 1
                    if vehicle_index >= len(vehicle_blueprint_ids):
                        vehicle_index = 0
                    vehicle_display_txt = vehicle_font.render(vehicle_display_names[vehicle_index],True,(255,0,0),None)
                if event.key == pygame.K_a:
                    vehicle_index -= 1
                    if vehicle_index < 0:
                        vehicle_index = len(vehicle_blueprint_ids) - 1
                    vehicle_display_txt = vehicle_font.render(vehicle_display_names[vehicle_index],True,(255,0,0),None)
                if event.key == pygame.K_RETURN:
                    current_path.insert(0,last_placed_vehicle.get_location())
                    vehicle_paths.append((last_placed_vehicle,current_path))
                    setting_up_scenario = False

        for p in current_path:
            world.debug.draw_line(p,p + carla.Vector3D(0,0,5),thickness=0.5,color=carla.Color(0,0,255),life_time=0.02)

        screen.fill((255,255,255))
        for i in range(len(instruction_txts)):
            instruction_txts[i] = font.render(instructions[i],True,(0,0,0),None)
            screen.blit(instruction_txts[i],instruction_txt_rects[i])
        if ego_vehicle_placed:
            vehicle_display_rect.center = (320,240)
            screen.blit(vehicle_display_txt,vehicle_display_rect)
        pygame.display.update()
        pygame.time.Clock().tick(60)

    for i in range(len(vehicle_paths)):
        for j in range(len(vehicle_paths[i][1])):
            vehicle_paths[i][1][j].z = 0

    return vehicle_paths

def set_instruction_texts(font, instructions: List[str]):
    instruction_txts = [font.render(instr,True,(0,0,0),None) for instr in instructions]
    instruction_txt_rects = [instr.get_rect() for instr in instruction_txts]
    for i in range(len(instruction_txts)):
        instruction_txt_rects[i].center = (320,48 + i * 18)
    return instructions, instruction_txts, instruction_txt_rects

def place_vehicle(blueprint_id,location,world,map,is_ego=False):
    bp = world.get_blueprint_library().filter(blueprint_id)[0]
    if is_ego:
        bp.set_attribute('role_name','hero')
    return world.try_spawn_actor(bp,
                                reversed_spawn(carla.Transform(location,map.get_waypoint(location).transform.rotation))
                                )