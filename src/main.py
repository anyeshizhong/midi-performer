import pygame
from performer import MidiPerformer

def main():
    pygame.init()
    performer = MidiPerformer()
    performer.run()

if __name__ == "__main__":
    main()