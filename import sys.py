import sys
import pygame

# Initialisatie van Pygame
pygame.init()

# Scherminstellingen
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(
    "Smart Traffic Rhythmic Action Game - Week 1 Prototype"
)

# Kleuren (RGB)
BLACK = (30, 30, 30)
WHITE = (255, 255, 255)
ROAD_GRAY = (80, 80, 80)
LINE_YELLOW = (255, 204, 0)
GREEN = (46, 204, 113)
RED = (231, 76, 60)

# Klok voor framerate
clock = pygame.time.Clock()
FPS = 60


def draw_intersection(surface):
  # Teken de achtergrond
  surface.fill((40, 120, 60))  

  # Horizontale weg
  pygame.draw.rect(
      surface,
      ROAD_GRAY,
      (0, SCREEN_HEIGHT // 2 - 100, SCREEN_WIDTH, 200),
  )
  # Verticale weg
  pygame.draw.rect(
      surface,
      ROAD_GRAY,
      (SCREEN_WIDTH // 2 - 100, 0, 200, SCREEN_HEIGHT),
  )

  # Wegmarkeringen (centrale kruispuntlijnen)
  pygame.draw.line(
      surface,
      LINE_YELLOW,
      (0, SCREEN_HEIGHT // 2),
      (SCREEN_WIDTH, SCREEN_HEIGHT // 2),
      2,
  )
  pygame.draw.line(
      surface,
      LINE_YELLOW,
      (SCREEN_WIDTH // 2, 0),
      (SCREEN_WIDTH // 2, SCREEN_HEIGHT),
      2,
  )

  # Indicatie verkeerslichten (placeholder locaties)
  pygame.draw.circle(
      surface, RED, (SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 - 120), 15
  )
  pygame.draw.circle(
      surface, GREEN, (SCREEN_WIDTH // 2 + 120, SCREEN_HEIGHT // 2 + 120), 15
  )


# --- Game Loop ---
running = True
while running:
  # Event handling
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False
    elif event.type == pygame.KEYDOWN:
      if event.key == pygame.K_ESCAPE:
        running = False

  # Teken logica
  screen.fill(BLACK)
  draw_intersection(screen)

  # Update display
  pygame.display.flip()
  clock.tick(FPS)

pygame.quit()
sys.exit()