import pygame
from random import uniform
from math import sqrt, pow, cos, sin, pow
from config import *

class Sprite:
    def __init__(self, image_path, target_width, *, velocity, coordinates, health = DEFAULT_HEALTH):
        self.x, self.y = coordinates #约定坐标为精灵中心
        self.load_image(image_path, target_width)
        self.vx, self.vy = velocity
    def get_velocity(self):
        return self.vx, self.vy
    def get_coordinates(self):
        return self.x, self.y
    def get_health(self):
            return self.health

    def load_image(self, image_path, target_width):
        image = pygame.image.load(image_path)
        width, height = image.get_size()
        target_height = height * (target_width / width)
        self.image = pygame.transform.smoothscale(image, (int(target_width), int(target_height)))
        self.width, self.height = self.image.get_size()

    def distance_to(self, other_sprite):
        x1, y1 = self.get_coordinates()
        x2, y2 = other_sprite.get_coordinates()
        distance = sqrt(pow(x1 - x2, 2) + pow(y1 - y2, 2))
        return distance
    def damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.health = 0

    def draw(self, surface):
        surface.blit(self.image, (self.x - self.width / 2, self.y - self.height / 2))
    def move(self):
        self.x += self.vx
        self.y += self.vy
        x, y = self.get_coordinates()
        x_sign, y_sign = 1, 1
        if x < 0:
            self.x = 0
            x_sign = -1
        elif x > GAME_WIDTH:
            self.x = GAME_WIDTH
            x_sign = -1
        if y < 0:
            self.y = 0
            y_sign = -1
        elif y > GAME_HEIGHT:
            self.y = GAME_HEIGHT  
            y_sign = -1
        return x_sign, y_sign

class Player(Sprite):
    def __init__(self):
        super().__init__(PLAYER_IMAGE_PATH, PLAYER_WIDTH, velocity=(PLAYER_ORIGINAL_SPEED_X, PLAYER_ORIGINAL_SPEED_Y), coordinates=(PLAYER_ORIGIN_X, PLAYER_ORIGIN_Y))
        self.health = PLAYER_HEALTH
    def calculate_bullet_velocity(angle = 90, speed = PLAYER_BULLET_SPEED):
        return round(cos(angle) * speed, 1), round(sin(angle) * speed, 1)

class Boss(Sprite):
    def __init__(self):
        super().__init__(BOSS_IMAGE_PATH, BOSS_WIDTH, velocity=(BOSS_ORIGINAL_SPEED_X, BOSS_ORIGINAL_SPEED_Y), coordinates=(BOSS_ORIGIN_X, BOSS_ORIGIN_Y))
        self.health = BOSS_HEALTH
    def calculate_bullet_velocity(angle = 90, speed = BOSS_BULLET_SPEED):
        return round(cos(angle) * speed, 1), round(sin(angle) * speed, 1)

    def move(self):
        x_sign, y_sign = super().move()
        self.vx *= x_sign
        self.vy *= y_sign

class Bullet(Sprite):
    def __init__(self, origin_image_path, collusion_image_path, target_width, *, velocity, coordinates, target_sprite, damage):
        super().__init__(origin_image_path, target_width, velocity=velocity, coordinates=coordinates)
        self.target_sprite = target_sprite
        self.collusion_image_path = collusion_image_path
        self.damage = damage

    def check_collision(self):
        return self.distance_to(self.target_sprite) > DISTANCE_MIN
    def check_out_of_screen(self):
        return self.x <= 0 or self.x >= GAME_WIDTH or self.y <= 0 or self.y >= GAME_HEIGHT
    
    def move(self):
        super().move()
        if self.check_collision():
            self.crash()
            self.health = 0
        if self.check_out_of_screen():
            self.health = 0
    def crash(self):
        self.load_image(self.collusion_image_path, self.width)
        self.target_sprite.damage(self.damage)

class Player_Bullet(Bullet):
    def __init__(self, *, velocity, coordinates, target_sprite):
        super().__init__(PLAYER_BULLET_PATH, PLAYER_BULLET_CRASH_PATH, PLAYER_BULLET_WIDTH, 
                         velocity=velocity, coordinates=coordinates, target_sprite=target_sprite, 
                         damage = PLAYER_BULLET_DAMAGE)
class Boss_Bullet(Bullet):
    def __init__(self, *, velocity, coordinates, target_sprite):
        super().__init__(BOSS_BULLET_PATH, BOSS_BULLET_CRASH_PATH, BOSS_BULLET_WIDTH, 
                         velocity=velocity, coordinates=coordinates, target_sprite=target_sprite, 
                         damage = BOSS_BULLET_DAMAGE)
        
class Game(Sprite):
    def __init__(self, player, boss):
        self.screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
        pygame.display.set_caption(GAME_NAME)
        self.icon = pygame.image.load(GAME_ICON_PATH)
        pygame.display.set_icon(self.icon)
        
        self.image = pygame.image.load(GAME_BG_IMAGE_PATH)
        super().__init__(self.image, GAME_WIDTH, velocity=(0, 0), coordinates=(GAME_WIDTH / 2, GAME_HEIGHT / 2))
        
        self.player = player
        self.boss = boss
        self.status = "running"

        self.player_bullets = []
        self.boss_bullets = []

    def move_and_update_all(self):
        self.boss.move()
        self.player.move()
        for bullet in self.player_bullets:
            bullet.move()
            if bullet.get_health() <= 0:
                self.player_bullets.remove(bullet)
    def shoot(self):
        self.player.shoot()
    def draw_all(self):
        self.draw()
        self.boss.draw(self.screen)
        self.player.draw(self.screen)
        for bullet in self.boss_bullets:
            bullet.draw(self.screen)
        for bullet in self.player_bullets:
            bullet.draw(self.screen)
        
    def update(self):
        self.move_and_update_all()
        self.shoot()
        self.draw_all()
        pygame.display.update()
    def draw(self):
        self.screen.blit(self.image, (0, 0))
    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.status = "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    self.player.vx = PLAYER_SPEED
                elif event.key == pygame.K_LEFT:
                    self.player.vx = -PLAYER_SPEED
            elif event.type == pygame.KEYUP:
                self.player.vx, self.player.vy = 0, 0
    
    def player_shoot(self, angle):
        self.player_bullets.append(Player_Bullet(velocity=self.player.calculate_angle(angle), 
                                   coordinates=self.player.get_coordinates(), 
                                   target_sprite=self.boss
                                   ))
    def boss_shoot(self, angle):
        self.boss_bullets.append(Boss_Bullet(velocity=self.boss.calculate_angle(angle), 
                                  coordinates=self.boss.get_coordinates(), 
                                  target_sprite=self.player
                                  ))

    def run(self):
        while self.status == "running":
            self.process_events()
            self.update()