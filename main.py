import pygame
from sprite import *

def running_game():
    pygame.init()
    player = Player()
    boss = Boss()
    game = Game(player, boss)
    game.run()


if __name__ == "__main__":
    running_game()