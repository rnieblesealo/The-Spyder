import pygame
import sys
import os

from enum import Enum
from typing import List
from random import randint
from pygame import Surface, Rect
from pygame.math import Vector2

pygame.init()

DISPLAY_SIZE = (400, 500)
DISPLAY = pygame.display.set_mode(DISPLAY_SIZE)
CLOCK = pygame.time.Clock()

#TODO add scoring system
#TODO make road get faster as game progresses (use a score threshold to increase difficulty)
#TODO add a consequence when the player dies

def print_warning(n = "?"):
    """
    shorthand for printing out a warning message.
    """

    print("{S} {N}".format(S = "[!]", N = n))

def import_image(filepath: str, scale = 1) -> Surface:
    """
    imports an image as surface and applies a scale to it if specified.
    """
    
    if not os.path.exists(filepath):
        print_warning("image {F} not found!".format(F = filepath))
        return None

    img = pygame.image.load(filepath).convert_alpha()

    return pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))

def lerp(a = 0, b = 0, t = 0.125):
    """
    lerps without the need to use a vector2
    """

    return a + (t - 0) * (b - a) / (1 - 0)

player = import_image('assets/player.png', 3)
police = import_image('assets/police.png', 3)
car_g = import_image('assets/car_g.png', 3)
car_o = import_image('assets/car_o.png', 3)
car_r = import_image('assets/car_r.png', 3)
car_y = import_image('assets/car_y.png', 3)
road = import_image('assets/road.png', 4)
shadow = import_image('assets/shadow.png', 3)

font = pygame.font.Font('assets/font.ttf', 40)

shadow.set_alpha(50)

# --- Lanes & Obstacle Spawns ---

lane_spacing = 0.835

lane_c = Vector2(DISPLAY_SIZE[0] / 2, 400)
lane_l = Vector2(lane_c.x - (lane_c.x / 2) * lane_spacing, lane_c.y)
lane_r = Vector2(lane_c.x + (lane_c.x / 2) * lane_spacing, lane_c.y)

lanes = (lane_l, lane_c, lane_r)

spawn_c = Vector2(lane_c.x, 0)
spawn_l = Vector2(lane_l.x, 0)
spawn_r = Vector2(lane_r.x, 0)

#region input
class Direction(Enum):
    LEFT = -1
    RIGHT = 1
#endregion

#region player
class Player:
    """
    player controller; only one per game instance!
    """

    texture: Surface = None
    rect: Rect = None

    current_lane = 1
    last_direction: Direction = Direction.RIGHT
    
    pos: Vector2 = None
    rot = 0

    __pos: Vector2 = None
    __rot = 0

    __l_pressed = False
    __r_pressed = False

    def __init__(self, texture = player, start_lane = 1) -> None:
        self.texture = texture.copy()

        self.current_lane = start_lane
        self.pos = Vector2(lanes[self.current_lane])
        self.rot = 0

    def get_input(self) -> None:
        get_l = pygame.key.get_pressed()[pygame.K_a]
        get_r = pygame.key.get_pressed()[pygame.K_d]
        
        can_press_l = (self.current_lane > 0) and not self.__l_pressed
        can_press_r = (self.current_lane < len(lanes) - 1) and not self.__r_pressed

        #left button input
        if get_l and can_press_l: 
            self.current_lane -= 1
            self.last_direction = Direction.RIGHT
            
            self.__l_pressed = True
        
        elif not get_l:
            self.__l_pressed = False
        
        #right button input
        if get_r and can_press_r:
            self.current_lane += 1
            self.last_direction = Direction.LEFT
            
            self.__r_pressed = True

        elif not get_r:
            self.__r_pressed = False

    def update(self) -> None:        
        #position & rotate
        self.__rot = Vector2.magnitude(lanes[self.current_lane] - self.pos) * 0.75 * self.last_direction.value
        self.__pos = lanes[self.current_lane]
    
        self.rot = lerp(self.rot, self.__rot, 0.125 * DELTA_TIME * 60)
        self.pos = lerp(self.pos, self.__pos, 0.125 * DELTA_TIME * 60)

        #input
        self.get_input()
        
    def draw(self) -> None:
        #rotate dropshadow
        r_shadow = pygame.transform.rotate(shadow, self.rot) #NOTE --move shadow_r to classvar?
        
        #center rotated dropshadow rect
        r_shadow_rect = r_shadow.get_rect()
        r_shadow_rect.center = self.pos
        
        #rotate texture
        r_texture = pygame.transform.rotate(self.texture, self.rot) #NOTE --move texture_r to classvar?
        
        #center rotated texture rect
        r_texture_rect = r_texture.get_rect()
        r_texture_rect.center = self.pos

        # --- EXPERIMENTAL : OUTLINE ---
        mask = pygame.mask.from_surface(r_texture)
        mask_outline = mask.outline()
        mask_surf = pygame.Surface(r_texture.get_size())
        
        for pixel in mask_outline:
            mask_surf.set_at(pixel, (25, 25, 25))
        
        mask_surf.set_colorkey((0, 0, 0))
        mask_surf_pos = Vector2(r_texture_rect.topleft)

        DISPLAY.blit(mask_surf, (mask_surf_pos.x - 3, mask_surf_pos.y))
        DISPLAY.blit(mask_surf, (mask_surf_pos.x + 3, mask_surf_pos.y))
        DISPLAY.blit(mask_surf, (mask_surf_pos.x, mask_surf_pos.y - 3))
        DISPLAY.blit(mask_surf, (mask_surf_pos.x, mask_surf_pos.y + 3))

        #draw dropshadow
        DISPLAY.blit(r_shadow, r_shadow_rect)

        #draw texture
        DISPLAY.blit(r_texture, r_texture_rect)

player = Player()

# --- Road ---

road_rect_a = road.get_rect()
road_rect_b = road.get_rect()

road_pos_a = Vector2(DISPLAY_SIZE[0] / 2, DISPLAY_SIZE[1] / 2)
road_pos_b = road_pos_a - Vector2(0, road.get_height())

road_vel = Vector2(0, 600)
road_dsp = Vector2(0, road.get_height() * 2)

# --- Obstacles ---

class Obstacle:    
    texture: Surface = None
    rect: Rect = None
    
    pos: Vector2 = None
    vel: Vector2 = None

    __drop_shadow_rect: Rect = None

    def __init__(self, texture: Surface, start_pos: Vector2, vel: Vector2) -> None:
        self.texture = texture.copy()
        self.rect = texture.get_rect()

        self.pos = Vector2(start_pos)
        self.vel = Vector2(vel)

        self.__drop_shadow_rect = shadow.get_rect()

    def update(self) -> None:
        #position (drop shadow)
        self.__drop_shadow_rect.center = self.pos
        
        #position
        self.pos += self.vel * DELTA_TIME
        self.rect.center = self.pos

    def draw(self) -> None:
        #drawing (drop shadow)
        DISPLAY.blit(shadow, self.__drop_shadow_rect)

        #drawing
        DISPLAY.blit(self.texture, self.rect)

obstacle_assets = [police, car_g, car_o, car_r, car_y]
obstacle_spawns = [Vector2(lane_c.x, -20), Vector2(lane_l.x, -20), Vector2(lane_r.x, -20)] #NOTE we spawn at -20 so cars spawn offscreen; it looks nicer
obstacles: List[Obstacle] = []

timer = 0 #NOTE timer is aggregate of deltatime used to count towards one tick
ticks = 0 #NOTE 1 tick == 1 second

def instantiate_obstacle() -> None:
    """
    creates a moving obstacle
    """

    obstacles.append(
        Obstacle(
            obstacle_assets[randint(0, len(obstacle_assets) - 1)],
            obstacle_spawns[randint(0, len(obstacle_spawns) - 1)], #TODO change this to spawnpoints!
            Vector2(0, 300)
        )
    )

while True:
    #pygame opening
    if pygame.key.get_pressed()[pygame.K_ESCAPE]:
        sys.exit()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    DELTA_TIME = CLOCK.tick() / 1000
    DISPLAY.fill((0, 0, 0))
    
    #draw road
    road_rect_a.center = road_pos_a
    road_rect_b.center = road_pos_b
    
    road_pos_a += road_vel * DELTA_TIME
    road_pos_b += road_vel * DELTA_TIME
    
    if road_rect_a.y >= DISPLAY_SIZE[1]:
        road_pos_a -= road_dsp

    if road_rect_b.y >= DISPLAY_SIZE[1]:
        road_pos_b -= road_dsp

    DISPLAY.blit(road, road_rect_a)
    DISPLAY.blit(road, road_rect_b)

    player.update()
    player.draw()

    #draw score
    score_text = font.render('941', True, (255, 255, 255))
    score_text_rect = score_text.get_rect()
    score_text_rect.center = (DISPLAY_SIZE[0] / 2, 65)
    DISPLAY.blit(score_text, score_text_rect)

    # #draw lane positons --NOTE debug
    # pygame.draw.circle(DISPLAY, (255, 255, 255), lane_c, 5)
    # pygame.draw.circle(DISPLAY, (255, 255, 255), lane_l, 5)
    # pygame.draw.circle(DISPLAY, (255, 255, 255), lane_r, 5)

    # #draw vehicle spawns --NOTE debug
    # pygame.draw.circle(DISPLAY, (255, 0, 0), spawn_c, 5)
    # pygame.draw.circle(DISPLAY, (255, 0, 0), spawn_l, 5)
    # pygame.draw.circle(DISPLAY, (255, 0, 0), spawn_r, 5)
    
    #input

    #update ticks
    if timer < 1:
        timer += DELTA_TIME

    else:
        ticks += 1
        timer = 0

    #spawn obstacles
    if ticks == 1:
        instantiate_obstacle()
        ticks = 0

    #update obstacles
    for obstacle in obstacles:
        obstacle.update()
        obstacle.draw()

    #pygame closing
    pygame.display.update()

    #debugging
    #print(pygame.mouse.get_pos())