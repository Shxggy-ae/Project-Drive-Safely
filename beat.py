import pygame
import sys
import random

# --- CONFIGURATIE & CONSTANTEN ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Kleuren
COLOR_BG = (34, 139, 34)
COLOR_ROAD = (50, 50, 50)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 20, 60)
COLOR_GREEN = (50, 205, 50)
COLOR_CAR = (30, 144, 255)
COLOR_BEAT = (255, 215, 0)

ROAD_WIDTH = 120
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2


class BeatManager:
    def __init__(self, bpm=100):
        self.bpm = bpm
        self.interval = (60 / self.bpm) * 1000
        self.last_beat_time = pygame.time.get_ticks()
        self.is_beat_frame = False

    def update(self):
        current_time = pygame.time.get_ticks()
        self.is_beat_frame = False
        if current_time - self.last_beat_time >= self.interval:
            self.last_beat_time = current_time
            self.is_beat_frame = True

    def get_pulse_factor(self):
        current_time = pygame.time.get_ticks()
        elapsed = (current_time - self.last_beat_time) % self.interval
        return max(0.0, 1.0 - (elapsed / (self.interval * 0.5)))


class TrafficLight:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.is_green = False
        self.rect = pygame.Rect(x - 15, y - 15, 30, 30)

    def toggle(self):
        self.is_green = not self.is_green

    def draw(self, surface):
        color = COLOR_GREEN if self.is_green else COLOR_RED
        pygame.draw.circle(surface, color, (self.x, self.y), 15)
        pygame.draw.circle(surface, COLOR_WHITE, (self.x, self.y), 15, 2)


class Vehicle:
    def __init__(self, direction):
        self.direction = direction
        self.speed = 3
        self.width = 30
        self.height = 18
        self.color = (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))

        if direction == 'W':
            self.x = -self.width
            self.y = CENTER_Y + 15
            self.stop_x = CENTER_X - (ROAD_WIDTH // 2) - 20
        elif direction == 'E':
            self.x = SCREEN_WIDTH + self.width
            self.y = CENTER_Y - 35
            self.stop_x = CENTER_X + (ROAD_WIDTH // 2) + 20
        elif direction == 'N':
            self.x = CENTER_X + 15
            self.y = -self.height
            self.stop_y = CENTER_Y - (ROAD_WIDTH // 2) - 20
        elif direction == 'S':
            self.x = CENTER_X - 35
            self.y = SCREEN_HEIGHT + self.height
            self.stop_y = CENTER_Y + (ROAD_WIDTH // 2) + 20

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self, light_is_green):
        should_stop = False

        if self.direction in ('W', 'E'):
            if not light_is_green:
                if self.direction == 'W' and 0 < (self.stop_x - self.x) <= 10:
                    should_stop = True
                elif self.direction == 'E' and 0 < (self.x - self.stop_x) <= 10:
                    should_stop = True

            if not should_stop:
                if self.direction == 'W':
                    self.x += self.speed
                elif self.direction == 'E':
                    self.x -= self.speed

        else:
            if not light_is_green:
                if self.direction == 'N' and 0 < (self.stop_y - self.y) <= 10:
                    should_stop = True
                elif self.direction == 'S' and 0 < (self.y - self.stop_y) <= 10:
                    should_stop = True

            if not should_stop:
                if self.direction == 'N':
                    self.y += self.speed
                elif self.direction == 'S':
                    self.y -= self.speed

    def draw(self, surface):
        rect = self.get_rect()
        pygame.draw.rect(surface, self.color, rect, border_radius=4)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Traffic Beat: Gridlock Hero - Prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18, bold=True)

        self.beat_manager = BeatManager(bpm=100)
        self.score = 0

        self.lights = {
            'N': TrafficLight(CENTER_X + 30, CENTER_Y - (ROAD_WIDTH // 2) - 25, 'N'),
            'S': TrafficLight(CENTER_X - 30, CENTER_Y + (ROAD_WIDTH // 2) + 25, 'S'),
            'W': TrafficLight(CENTER_X - (ROAD_WIDTH // 2) - 25, CENTER_Y + 30, 'W'),
            'E': TrafficLight(CENTER_X + (ROAD_WIDTH // 2) + 25, CENTER_Y - 30, 'E'),
        }

        self.vehicles = []
        self.game_over = False
        self.restart_button = pygame.Rect(300, 360, 200, 60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    continue

                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.toggle_light_with_score('W')
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.toggle_light_with_score('E')
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.toggle_light_with_score('N')
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.toggle_light_with_score('S')

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.game_over and self.restart_button.collidepoint(pos):
                    self.reset_game()
                    continue

                for key, light in self.lights.items():
                    if light.rect.collidepoint(pos):
                        self.toggle_light_with_score(key)

        return True

    def reset_game(self):
        self.score = 0
        self.vehicles = []
        self.game_over = False
        self.beat_manager = BeatManager(bpm=100)
        self.lights = {
            'N': TrafficLight(CENTER_X + 30, CENTER_Y - (ROAD_WIDTH // 2) - 25, 'N'),
            'S': TrafficLight(CENTER_X - 30, CENTER_Y + (ROAD_WIDTH // 2) + 25, 'S'),
            'W': TrafficLight(CENTER_X - (ROAD_WIDTH // 2) - 25, CENTER_Y + 30, 'W'),
            'E': TrafficLight(CENTER_X + (ROAD_WIDTH // 2) + 25, CENTER_Y - 30, 'E'),
        }

    def toggle_light_with_score(self, direction):
        self.lights[direction].toggle()
        pulse = self.beat_manager.get_pulse_factor()
        if pulse > 0.6:
            self.score += 50
        else:
            self.score = max(0, self.score - 10)

    def check_collisions(self):
        collided = set()
        for i in range(len(self.vehicles)):
            for j in range(i + 1, len(self.vehicles)):
                if self.vehicles[i].get_rect().colliderect(self.vehicles[j].get_rect()):
                    collided.add(i)
                    collided.add(j)

        if collided:
            self.game_over = True
            self.score = max(0, self.score - 30)
            self.vehicles = [vehicle for index, vehicle in enumerate(self.vehicles) if index not in collided]

    def update(self):
        self.beat_manager.update()

        if self.beat_manager.is_beat_frame:
            if random.random() < 0.45:
                direction = random.choice(['N', 'S', 'W', 'E'])
                self.vehicles.append(Vehicle(direction))

        for v in self.vehicles[:]:
            light_is_green = self.lights[v.direction].is_green
            v.update(light_is_green)

            if v.x < -150 or v.x > SCREEN_WIDTH + 150 or v.y < -150 or v.y > SCREEN_HEIGHT + 150:
                self.vehicles.remove(v)
                self.score += 20

        self.check_collisions()

    def draw(self):
        self.screen.fill(COLOR_BG)

        pygame.draw.rect(self.screen, COLOR_ROAD, (0, CENTER_Y - (ROAD_WIDTH // 2), SCREEN_WIDTH, ROAD_WIDTH))
        pygame.draw.rect(self.screen, COLOR_ROAD, (CENTER_X - (ROAD_WIDTH // 2), 0, ROAD_WIDTH, SCREEN_HEIGHT))

        pygame.draw.line(self.screen, COLOR_WHITE, (0, CENTER_Y), (SCREEN_WIDTH, CENTER_Y), 2)
        pygame.draw.line(self.screen, COLOR_WHITE, (CENTER_X, 0), (CENTER_X, SCREEN_HEIGHT), 2)

        for light in self.lights.values():
            light.draw(self.screen)

        for v in self.vehicles:
            v.draw(self.screen)

        pulse = self.beat_manager.get_pulse_factor()
        radius = int(15 + (pulse * 15))
        pygame.draw.circle(self.screen, COLOR_BEAT, (750, 50), radius)
        beat_text = self.font.render("BEAT", True, (0, 0, 0))
        self.screen.blit(beat_text, (733, 42))

        score_surface = self.font.render(f"Score: {self.score}", True, COLOR_WHITE)
        instructions = self.font.render("A/D/W/S of pijlen: schakelen van N/S/W/E", True, COLOR_WHITE)
        self.screen.blit(score_surface, (20, 20))
        self.screen.blit(instructions, (20, 560))

        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            game_over_text = self.font.render("GAME OVER", True, (255, 255, 255))
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
            self.screen.blit(game_over_text, game_over_rect)

            pygame.draw.rect(self.screen, (70, 70, 70), self.restart_button)
            pygame.draw.rect(self.screen, COLOR_WHITE, self.restart_button, 3)
            restart_text = self.font.render("RESTART", True, COLOR_WHITE)
            restart_rect = restart_text.get_rect(center=self.restart_button.center)
            self.screen.blit(restart_text, restart_rect)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            if not self.game_over:
                self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()