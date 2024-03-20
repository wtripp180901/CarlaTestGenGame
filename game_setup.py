from typing import List
import pygame
import carla
from test_setup import reversed_spawn
from fnmatch import fnmatch

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
    spectator_pos = map.get_spawn_points()[76].location + carla.Vector3D(0,0,30)
    
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
        spectator_pos = spectator_pos + move_vec
        spectator.set_transform(carla.Transform(spectator_pos,spectator_rotation))

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
                            if fnmatch(vehicle_blueprint_ids[vehicle_index],"*police*"):
                                placed_vehicle.set_light_state(carla.VehicleLightState.Special1)
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
        render_instructions(screen,font,instructions,instruction_txts,instruction_txt_rects)
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

def render_instructions(screen,font,instructions,instruction_txts,instruction_txt_rects):
    for i in range(len(instruction_txts)):
        instruction_txts[i] = font.render(instructions[i],True,(0,0,0),None)
        screen.blit(instruction_txts[i],instruction_txt_rects[i])

def world_settings_loop(screen,client,current_world):
    font = pygame.font.SysFont("ComicSans.tff",32)
    instructions, instruction_txts, instruction_rects = set_instruction_texts(font,["Use up and down keys to select parameter",
                                                                                    "Use left and right keys to set value",
                                                                                    "Press ENTER to finish"])
    parameter_names = ["Map",
                       "Rain",
                       "Puddles",
                       "Time",
                       "Cloudiness"]
    parameter_display_values = [["Town","Urban"],
                                 ["None","Light","Medium","Heavy","Very Heavy"],
                                 ["None","Low","Medium","High","Very High"],
                                 ["Day","Sunrise","Sunset","Night"],
                                 ["None","Low","Medium","High","Very High"]
                                 ]
    parameter_values = [["Town01_Opt","Town10HD_Opt"],
                        [0,25,50,75,100],
                        [0,25,50,75,100],
                        [90,5,175,-90],
                        [0,25,50,75,100]
                        ]
    indices = [0,0,0,0,0]
    
    row = 0

    parameter_texts = [font.render("Map: Town",True,(255,0,0),None),
                       font.render("Rain: None",True,(0,0,0),None),
                       font.render("Puddles: None",True,(0,0,0),None),
                       font.render("Time: Day",True,(0,0,0),None),
                       font.render("Cloudiness: None",True,(0,0,0),None)]
    parameter_rects = []
    for i in range(len(parameter_texts)):
        parameter_rects.append(parameter_texts[i].get_rect())
        parameter_rects[i].center = (320,156 + 18 * i)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                parameter_texts[row] = font.render(parameter_names[row]+": "+str(parameter_display_values[row][indices[row]]),True,(0,0,0))
                
                if event.key == pygame.K_UP:
                    row -= 1
                    if row < 0:
                        row = len(parameter_names) - 1
                if event.key == pygame.K_DOWN:
                    row += 1
                    if row >= len(parameter_names):
                        row = 0
                if event.key == pygame.K_LEFT:
                    indices[row] -= 1
                    if indices[row] < 0:
                        indices[row] = len(parameter_values[row]) - 1
                if event.key == pygame.K_RIGHT:
                    indices[row] += 1
                    if indices[row] >= len(parameter_values[row]):
                        indices[row] = 0
                if event.key == pygame.K_RETURN:
                    running = False

                parameter_texts[row] = font.render(parameter_names[row]+": "+str(parameter_display_values[row][indices[row]]),True,(255,0,0))

        screen.fill((255,255,255))
        for i in range(len(instruction_txts)):
            screen.blit(instruction_txts[i],instruction_rects[i])
        for i in range(len(parameter_texts)):
            screen.blit(parameter_texts[i],parameter_rects[i])
        pygame.display.update()

    # Saves from long load
    world = None
    if "Carla/Maps/"+parameter_values[0][indices[0]] == current_world.get_map().name:
        world = current_world
    else:
        world = client.load_world(parameter_values[0][indices[0]])
        
    weather_params = carla.WeatherParameters(
        precipitation = parameter_values[1][indices[1]],
        precipitation_deposits = parameter_values[2][indices[2]],
        sun_altitude_angle = parameter_values[3][indices[3]],
        cloudiness = parameter_values[4][indices[4]]
    )
    world.set_weather(weather_params)
    return world
        