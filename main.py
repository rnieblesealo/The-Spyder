import pygame
import sys
import os

from enum import Enum
from random import randint
from pygame import PixelArray, Surface, Rect
from pygame.math import Vector2

pygame.init()
pygame.mixer.init()

DISPLAY_SIZE = (400, 500)
DISPLAY = pygame.display.set_mode(DISPLAY_SIZE)
CLOCK = pygame.time.Clock()

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

# --- Asset Importing --- 

player = import_image('assets/player.png', 3)
police = import_image('assets/police.png', 3)
car_g = import_image('assets/car_g.png', 3)
car_o = import_image('assets/car_o.png', 3)
car_r = import_image('assets/car_r.png', 3)
car_y = import_image('assets/car_y.png', 3)
road = import_image('assets/road.png', 4)
shadow = import_image('assets/shadow.png', 3)
logo = import_image('assets/logo.png')
game_over = import_image('assets/game_over.png')

font = pygame.font.Font('assets/font.ttf', 32) #big version of font
font_s = pygame.font.Font('assets/font.ttf', 16) #small version of font

p_switch = pygame.mixer.Sound('assets/switch.wav')
p_crash = pygame.mixer.Sound('assets/crash.wav')

shadow.set_alpha(50)

# --- Secondary Initialization ----

pygame.display.set_caption('The Spyder')
pygame.display.set_icon(logo)

# --- Game Control ---

class GameState(Enum):
    IDLE = 0
    GAME_ON = 1
    GAME_OVER = 2

def get_highscore(in_int = False) -> int:
    """
    gets high score from save info (save.txt)
    score should be formatted as: h_score={HIGH SCORE}
    """
    
    if not os.path.exists('save.txt'):
        return None
    
    with open('save.txt', 'r') as save:
        for line in save:
            if 'h_score=' in line:
                data = line.split('=')
                return data[1] if not in_int else int(data[1])
        return None
                
state = GameState.IDLE

timer = 0 #NOTE timer is aggregate of deltatime used to count towards one tick
ticks = 0 #NOTE 1 tick == 0.5 second

high_score = get_highscore()

score = 0 #current score (base is 0)
score_incr = 10 #amt score given per score tick
score_ticks = 2 #amt of ticks before score tick
score_ticks_t = score_ticks #temp current tick goal for score incr

base_speed = 500
speed = base_speed #current speed
speed_incr = 75 #speed increased per speed tick
speed_ticks = 12 #amt of ticks before speed tick
speed_ticks_t = speed_ticks #temp current tick goal for speed incr

# --- Lanes & Obstacle Spawns ---

lane_spacing = 0.835

lane_c = Vector2(DISPLAY_SIZE[0] / 2, 400)
lane_l = Vector2(lane_c.x - (lane_c.x / 2) * lane_spacing, lane_c.y)
lane_r = Vector2(lane_c.x + (lane_c.x / 2) * lane_spacing, lane_c.y)

lanes = (lane_l, lane_c, lane_r)

spawn_c = Vector2(lane_c.x, 0)
spawn_l = Vector2(lane_l.x, 0)
spawn_r = Vector2(lane_r.x, 0)

# --- Input Definitions --- 

class Direction(Enum):
    LEFT = -1
    RIGHT = 1

# --- Road ---

road_rect_a = road.get_rect()
road_rect_b = road.get_rect()

road_pos_a = Vector2(DISPLAY_SIZE[0] / 2, DISPLAY_SIZE[1] / 2)
road_pos_b = road_pos_a - Vector2(0, road.get_height())

road_vel = speed #current road vel
road_dsp = road.get_height() * 2

# --- Obstacles ---

obstacle_assets = [police, car_g, car_o, car_r, car_y]
obstacle_spawns = [Vector2(lane_c.x, -50), Vector2(lane_l.x, -50), Vector2(lane_r.x, -50)] #NOTE we spawn at -20 so cars spawn offscreen
obstacles = []

spawn_ticks = 1 #amt of ticks before a vehicle spawns
spawn_ticks_t = spawn_ticks #temp current spawntick goal for next vehicle to spawn

class Obstacle:    
    texture: Surface = None
    rect: Rect = None
    
    pos: Vector2 = None
    speed = 300

    __drop_shadow_rect: Rect = None

    def __init__(self, texture: Surface, start_pos: Vector2) -> None:
        self.texture = texture.copy()
        self.rect = texture.get_rect()

        self.pos = Vector2(start_pos)

        self.__drop_shadow_rect = shadow.get_rect()

        #initialize rects --NOTE this prevents flickering when cars are instantiated!
        self.rect.center = self.pos
        self.__drop_shadow_rect.center = self.pos

    def update(self) -> None:
        #delete this obstacle if out of screen bounds (NOTE +100 is just for ensuring object doesn't die onscreen no matter the size)
        if self.pos.y >= DISPLAY_SIZE[1] + 100:
            global obstacles
            obstacles.remove(self)
            del self
            return
        
        #position (drop shadow)
        self.__drop_shadow_rect.center = self.pos
        
        #position (texture)
        self.pos.y += (self.speed + (speed - base_speed)) * DELTA_TIME #y pos vel increment is obstacle base speed (300) + the difference between current game speed and base game speed
        self.rect.center = self.pos

    def draw(self) -> None:        
        # #draw hitbox --NOTE for debugging
        # pygame.draw.rect(DISPLAY, (0, 0, 255), self.rect)
        
        #drawing (drop shadow)
        DISPLAY.blit(shadow, self.__drop_shadow_rect)

        #drawing (texture)
        DISPLAY.blit(self.texture, self.rect)

def instantiate_obstacle() -> None:
    """
    creates a moving obstacle
    """

    obstacles.append(
        Obstacle(
            obstacle_assets[randint(0, len(obstacle_assets) - 1)],
            obstacle_spawns[randint(0, len(obstacle_spawns) - 1)], #TODO change this to spawnpoints!
        )
    )

# --- Player ---

class Player:
    """
    player controller; only one per game instance!
    """

    texture: Surface = None
    rect: Rect = None
    rect_fix = -15 #adjustment applied to rect w and h so its smaller/bigger

    current_lane = 1
    last_direction: Direction = Direction.RIGHT
    
    pos: Vector2 = None
    rot = 0

    outline_color = (50, 50, 50)
    outline_width = 3 #keep below 5

    __pos: Vector2 = None
    __rot = 0

    __l_pressed = False
    __r_pressed = False

    __outline: Surface = None

    def __init__(self, texture = player, start_lane = 1) -> None:
        self.texture = texture.copy()
        self.rect = Rect(0, 0, self.texture.get_width() + self.rect_fix, self.texture.get_height() + self.rect_fix)

        self.current_lane = start_lane
        self.pos = Vector2(lanes[self.current_lane])
        self.rot = 0

        #outline generation process
        
        #get binary bitmap surface of texture, convert it back to a surface 
        mask = pygame.mask.from_surface(self.texture)
        mask_surf = mask.to_surface() #--NOTE the result is a black & white surface where black represents transparent area and white represents filled area (of passed texture)
        
        #convert mask_surf into pixel data (numpy array) and replace white with desired color (this will be outline's color)
        mask_surf_pixels = PixelArray(mask_surf)
        mask_surf_pixels.replace((255, 255, 255), self.outline_color)
        
        self.__outline = mask_surf_pixels.make_surface()

    def reset_pos(self) -> None:
        """
        Resets the player's position and rotation to the central lane.
        """
        
        if self.current_lane == 1:
            return

        self.current_lane = 1
        
        self.pos = lanes[1]
        self.rot = 0
        
        self.__pos = lanes[1]
        self.__rot = 0

    def get_input(self) -> None:
        get_l = pygame.key.get_pressed()[pygame.K_a]
        get_r = pygame.key.get_pressed()[pygame.K_d]
        
        can_press_l = (self.current_lane > 0) and not self.__l_pressed
        can_press_r = (self.current_lane < len(lanes) - 1) and not self.__r_pressed

        global state
        if state == GameState.IDLE:
            #reset position to center lane when game is idle
            self.reset_pos()

            #start game if input is received
            if get_l or get_r:
                print_warning("Starting Game!")
                state = GameState.GAME_ON

        #get left button input
        if get_l and can_press_l: 
            self.current_lane -= 1
            self.last_direction = Direction.RIGHT
            p_switch.play()
            
            self.__l_pressed = True
        
        elif not get_l:
            self.__l_pressed = False
        
        #get right button input
        if get_r and can_press_r:
            self.current_lane += 1
            self.last_direction = Direction.LEFT
            p_switch.play()
            
            self.__r_pressed = True

        elif not get_r:
            self.__r_pressed = False

    def update(self) -> None:       
        #position & rotate
        self.__rot = Vector2.magnitude(lanes[self.current_lane] - self.pos) * 0.75 * self.last_direction.value
        self.__pos = lanes[self.current_lane]
    
        self.rot = lerp(self.rot, self.__rot, 0.125 * DELTA_TIME * 60)
        self.pos = lerp(self.pos, self.__pos, 0.125 * DELTA_TIME * 60)

        #update rect (NOTE this isn't used for drawing, it's used for collision!)
        self.rect.center = self.pos

        #check for collision & gameover event handle
        global state
        if state == GameState.GAME_ON:
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle.rect):
                    #write new highscore before changing gamestate if we beat our last highscore
                    if score > get_highscore(in_int=True):
                        with open('save.txt', 'w+') as save:
                            save.truncate(0)
                            save.write('h_score={H}'.format(H=score))
                            
                        #change global high score to new one
                        global high_score
                        high_score = get_highscore()
                    
                    state = GameState.GAME_OVER
                    
                    p_crash.play()

        #input
        self.get_input()
    
    #NOTE that drawing the outline is computationally expensive!
    def draw_outline(self, pos):
        #rotate outline surface
        r_outline = pygame.transform.rotate(self.__outline, self.rot)
        
        #set outline colorkey (must do this every time we modify it)
        r_outline.set_colorkey((0, 0, 0))
        
        #center rotated outline surface rect
        r_outline_pos = pos
        
        #draw outline (we shift it towards every direction to give outline effect)
        DISPLAY.blit(r_outline, (r_outline_pos[0] - self.outline_width, r_outline_pos[1]))
        DISPLAY.blit(r_outline, (r_outline_pos[0] + self.outline_width, r_outline_pos[1]))
        DISPLAY.blit(r_outline, (r_outline_pos[0], r_outline_pos[1] - self.outline_width))
        DISPLAY.blit(r_outline, (r_outline_pos[0], r_outline_pos[1] + self.outline_width))

    def draw(self) -> None:
        # #draw hitbox --NOTE for debugging
        # pygame.draw.rect(DISPLAY, (0, 255, 0), self.rect)
        
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

        #draw dropshadow
        DISPLAY.blit(r_shadow, r_shadow_rect)
        
        #draw outline
        self.draw_outline(r_texture_rect.topleft)

        #draw texture
        DISPLAY.blit(r_texture, r_texture_rect)

player = Player()

# GAME LOOP ----------------------------------------------------------------------------------------------------------------------------------------------------------------------

#temp, delete || move later
s_text = str(score)
s_last_text = None

st_outl_width = 5

st: Surface = None
st_outl: Surface = None
st_rect: Rect = None

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
    
    #move road if game not over
    if state != GameState.GAME_OVER:
        road_vel = speed
        
        road_pos_a.y += road_vel * DELTA_TIME
        road_pos_b.y += road_vel * DELTA_TIME
    
    if road_rect_a.y >= DISPLAY_SIZE[1]:
        road_pos_a.y -= road_dsp

    if road_rect_b.y >= DISPLAY_SIZE[1]:
        road_pos_b.y -= road_dsp

    DISPLAY.blit(road, road_rect_a)
    DISPLAY.blit(road, road_rect_b)

    #if game not over, update player and draw obstacles
    if state != GameState.GAME_OVER:
        player.update()

    #always draw obstacles in obstacles list
    for obstacle in obstacles:
        obstacle.draw()
    
    #always draw player
    player.draw()
    
    if state == GameState.IDLE:            
        #clear obstacles list when idle
        if len(obstacles) != 0:
            obstacles.clear()

        #draw logo
        logo_rect = logo.get_rect()
        logo_rect.center = (DISPLAY_SIZE[0] / 2, 150)
        
        DISPLAY.blit(logo, logo_rect)

        #show highscore if we have one
        if high_score != None:
            hs_text = font_s.render('High Score: {H}'.format(H=high_score), False, (197, 197, 197))
            hs_text_rect = hs_text.get_rect()
            hs_text_rect.center = (DISPLAY_SIZE[0] / 2, 310)

            DISPLAY.blit(hs_text, hs_text_rect)

    if state == GameState.GAME_ON:
        #update obstacles
        for obstacle in obstacles:
            obstacle.update()
        
        #update score txt
        s_text = str(score)

        #remake score txt graphic if score txt changed
        if s_text != s_last_text:
            s_last_text = s_text

            #make score txt
            st = font.render(s_text, False, (255, 255, 255))

            #make score txt outline
            st_outl = font.render(s_text, False, (25, 25, 25))
            
            #maek score txt rect
            st_rect = st.get_rect()
            st_rect.center = (DISPLAY_SIZE[0] / 2, 65)
            st_pos = st_rect.topleft
        
        #draw score txt outline
        DISPLAY.blit(st_outl, (st_pos[0] - st_outl_width, st_pos[1]))
        DISPLAY.blit(st_outl, (st_pos[0] + st_outl_width, st_pos[1]))
        DISPLAY.blit(st_outl, (st_pos[0], st_pos[1] - st_outl_width))
        DISPLAY.blit(st_outl, (st_pos[0], st_pos[1] + st_outl_width))

        #draw score txt
        DISPLAY.blit(st, st_rect)
    
        #update ticks
        if timer < 0.5:
            timer += DELTA_TIME

        else:
            ticks += 1
            timer = 0

        #spawn obstacles
        if ticks == spawn_ticks_t:
            instantiate_obstacle()
            spawn_ticks_t += spawn_ticks

        #give score
        if ticks == score_ticks_t:
            score += score_incr
            score_ticks_t += score_ticks

        #speed up road
        if ticks == speed_ticks_t:
            speed += speed_incr
            speed_ticks_t += speed_ticks

    #reset values after death
    else:
        ticks = 0
        score = 0
        speed = base_speed
        spawn_ticks_t = spawn_ticks
        score_ticks_t = score_ticks
        speed_ticks_t = speed_ticks

    if state == GameState.GAME_OVER:
        #draw game over
        go_rect = game_over.get_rect()
        go_rect.center = (DISPLAY_SIZE[0] / 2, 150)
        
        DISPLAY.blit(game_over, go_rect)

    #NOTE FOR DEBUGGING --switch gamestate to idle if press I
    if pygame.key.get_pressed()[pygame.K_i]:
        state = GameState.IDLE

    #pygame closing
    pygame.display.update()
