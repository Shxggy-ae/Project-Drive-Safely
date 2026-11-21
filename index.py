import pygame
import sys
import random
import os

# --- CONFIGURATIE & CONSTANTEN ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
GAME_WIDTH = 800
FPS = 60

# Kleuren (Modern & Strak)
COLOR_BG = (46, 139, 87)       # Frisse zeegroene/gras kleur
COLOR_GRASS_DARK = (34, 115, 69) # Donkerdere tint voor grasdetails
COLOR_ROAD = (60, 64, 67)      # Modern asfaltgrijs
COLOR_CURB = (189, 195, 199)   # Stoeprand lichtgrijs
COLOR_SIDEBAR = (32, 34, 37)   # Discord-achtige donkere zijbalk
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (241, 196, 15)  # Wegmarkering geel
COLOR_RED = (231, 76, 60)
COLOR_GREEN = (46, 204, 113)
COLOR_BEAT = (243, 156, 18)    # Warme oranje/gouden beat kleur
COLOR_GOLD = (241, 196, 15)    # Highscore goud kleur
COLOR_OVERLAY = (0, 0, 0, 190)

ROAD_WIDTH = 130
CENTER_X = GAME_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2


class BeatManager:
    def __init__(self, bpm=100):
        self.bpm = bpm
        self.interval = (60 / self.bpm) * 1000
        self.last_beat_time = pygame.time.get_ticks()
        self.is_beat_frame = False

    def update(self, current_bpm=None):
        if current_bpm and current_bpm != self.bpm:
            self.bpm = current_bpm
            self.interval = (60 / self.bpm) * 1000

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
        self.rect = pygame.Rect(x - 14, y - 14, 28, 28)

    def toggle(self):
        self.is_green = not self.is_green

    def draw(self, surface):
        pygame.draw.rect(surface, (100, 100, 100), (self.x - 3, self.y - 3, 6, 30))
        pygame.draw.rect(surface, (40, 40, 40), pygame.Rect(self.x - 16, self.y - 16, 32, 32), border_radius=4)
        color = COLOR_GREEN if self.is_green else COLOR_RED
        pygame.draw.circle(surface, color, (self.x, self.y), 12)
        pygame.draw.circle(surface, (255, 255, 255), (self.x - 3, self.y - 3), 3)


class Vehicle:
    def __init__(self, direction):
        self.direction = direction
        self.speed = 3
        self.width = 34
        self.height = 20
        self.body_color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))

        if direction == 'W':
            self.x = -self.width
            self.y = CENTER_Y + 16
            self.stop_x = CENTER_X - (ROAD_WIDTH // 2) - 25
        elif direction == 'E':
            self.x = GAME_WIDTH + self.width
            self.y = CENTER_Y - 36
            self.stop_x = CENTER_X + (ROAD_WIDTH // 2) + 25
        elif direction == 'N':
            self.x = CENTER_X + 16
            self.y = -self.height
            self.stop_y = CENTER_Y - (ROAD_WIDTH // 2) - 25
        elif direction == 'S':
            self.x = CENTER_X - 36
            self.y = SCREEN_HEIGHT + self.height
            self.stop_y = CENTER_Y + (ROAD_WIDTH // 2) + 25

    def get_rect(self):
        if self.direction in ('W', 'E'):
            return pygame.Rect(self.x, self.y, self.width, self.height)
        else:
            return pygame.Rect(self.x, self.y, self.height, self.width)

    def update(self, light_is_green):
        should_stop = False

        if self.direction in ('W', 'E'):
            if not light_is_green:
                if self.direction == 'W' and 0 < (self.stop_x - self.x) <= 12:
                    should_stop = True
                elif self.direction == 'E' and 0 < (self.x - self.stop_x) <= 12:
                    should_stop = True

            if not should_stop:
                if self.direction == 'W':
                    self.x += self.speed
                elif self.direction == 'E':
                    self.x -= self.speed
        else:
            if not light_is_green:
                if self.direction == 'N' and 0 < (self.stop_y - self.y) <= 12:
                    should_stop = True
                elif self.direction == 'S' and 0 < (self.y - self.stop_y) <= 12:
                    should_stop = True

            if not should_stop:
                if self.direction == 'N':
                    self.y += self.speed
                elif self.direction == 'S':
                    self.y -= self.speed

    def draw(self, surface):
        rect = self.get_rect()
        pygame.draw.rect(surface, self.body_color, rect, border_radius=5)
        pygame.draw.rect(surface, (20, 20, 20), rect, 1, border_radius=5)

        if self.direction == 'W':
            pygame.draw.rect(surface, (200, 220, 240), (self.x + 18, self.y + 3, 8, 14), border_radius=2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + self.width - 2, self.y + 4), 2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + self.width - 2, self.y + self.height - 4), 2)
        elif self.direction == 'E':
            pygame.draw.rect(surface, (200, 220, 240), (self.x + 8, self.y + 3, 8, 14), border_radius=2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + 2, self.y + 4), 2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + 2, self.y + self.height - 4), 2)
        elif self.direction == 'N':
            pygame.draw.rect(surface, (200, 220, 240), (self.x + 3, self.y + 18, 14, 8), border_radius=2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + 4, self.y + self.height - 2), 2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + self.width - 4, self.y + self.height - 2), 2)
        elif self.direction == 'S':
            pygame.draw.rect(surface, (200, 220, 240), (self.x + 3, self.y + 8, 14, 8), border_radius=2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + 4, self.y + 2), 2)
            pygame.draw.circle(surface, (255, 255, 200), (self.x + self.width - 4, self.y + 2), 2)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Traffic Beat: Gridlock Hero - Deluxe Edition met Highscore")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_score = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_large = pygame.font.SysFont("Arial", 28, bold=True)

        self.state = 'START'
        self.score = 0
        self.high_score = self.load_highscore()
        
        self.game_duration = 60
        self.time_left = self.game_duration
        self.start_ticks = 0

        self.beat_manager = BeatManager(bpm=100)

        self.lights = {
            'N': TrafficLight(CENTER_X + 35, CENTER_Y - (ROAD_WIDTH // 2) - 25, 'N'),
            'S': TrafficLight(CENTER_X - 35, CENTER_Y + (ROAD_WIDTH // 2) + 25, 'S'),
            'W': TrafficLight(CENTER_X - (ROAD_WIDTH // 2) - 25, CENTER_Y + 35, 'W'),
            'E': TrafficLight(CENTER_X + (ROAD_WIDTH // 2) + 25, CENTER_Y - 35, 'E'),
        }

        self.vehicles = []
        self.restart_button = pygame.Rect(820, 500, 160, 45)
        self.start_button = pygame.Rect(350, 380, 300, 50)

    def load_highscore(self):
        """Leest de highscore uit een lokaal bestandje."""
        try:
            if os.path.exists("highscore.txt"):
                with open("highscore.txt", "r") as f:
                    return int(f.read().strip())
        except:
            pass
        return 0

    def save_highscore(self):
        """Slaat de highscore op in een lokaal bestandje."""
        try:
            with open("highscore.txt", "w") as f:
                f.write(str(self.high_score))
        except:
            pass

    def reset_game(self):
        self.score = 0
        self.vehicles = []
        self.time_left = self.game_duration
        self.start_ticks = pygame.time.get_ticks()
        self.beat_manager = BeatManager(bpm=100)
        self.lights = {
            'N': TrafficLight(CENTER_X + 35, CENTER_Y - (ROAD_WIDTH // 2) - 25, 'N'),
            'S': TrafficLight(CENTER_X - 35, CENTER_Y + (ROAD_WIDTH // 2) + 25, 'S'),
            'W': TrafficLight(CENTER_X - (ROAD_WIDTH // 2) - 25, CENTER_Y + 35, 'W'),
            'E': TrafficLight(CENTER_X + (ROAD_WIDTH // 2) + 25, CENTER_Y - 35, 'E'),
        }
        self.state = 'PLAYING'

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == 'START':
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        self.reset_game()
                elif self.state == 'PLAYING':
                    if event.key == pygame.K_SPACE:
                        self.state = 'PAUSED'
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.toggle_light_with_score('W')
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.toggle_light_with_score('E')
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.toggle_light_with_score('N')
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.toggle_light_with_score('S')
                elif self.state == 'PAUSED':
                    if event.key == pygame.K_SPACE:
                        self.state = 'PLAYING'
                elif self.state == 'GAMEOVER':
                    if event.key == pygame.K_r:
                        self.reset_game()

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.state == 'START':
                    if self.start_button.collidepoint(pos):
                        self.reset_game()
                elif self.state == 'GAMEOVER':
                    if self.restart_button.collidepoint(pos):
                        self.reset_game()
                elif self.state == 'PLAYING':
                    for key, light in self.lights.items():
                        if light.rect.collidepoint(pos):
                            self.toggle_light_with_score(key)

        return True

    def toggle_light_with_score(self, direction):
        self.lights[direction].toggle()
        pulse = self.beat_manager.get_pulse_factor()
        if pulse > 0.6:
            self.score += 50
        else:
            self.score = max(0, self.score - 10)
        
        # Check direct highscore tijdens het spel
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_highscore()

    def check_collisions(self):
        collided = set()
        for i in range(len(self.vehicles)):
            for j in range(i + 1, len(self.vehicles)):
                if self.vehicles[i].get_rect().colliderect(self.vehicles[j].get_rect()):
                    collided.add(i)
                    collided.add(j)

        if collided:
            self.score = max(0, self.score - 50)
            self.vehicles = [v for idx, v in enumerate(self.vehicles) if idx not in collided]

    def update(self):
        if self.state != 'PLAYING':
            return

        elapsed_seconds = (pygame.time.get_ticks() - self.start_ticks) / 1000
        self.time_left = max(0, self.game_duration - int(elapsed_seconds))

        if self.time_left == 0:
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_highscore()
            self.state = 'GAMEOVER'
            return

        current_bpm = 100 + (elapsed_seconds // 15) * 15
        self.beat_manager.update(current_bpm)

        spawn_chance = 0.35 + (elapsed_seconds / 150)
        if self.beat_manager.is_beat_frame:
            if random.random() < spawn_chance:
                direction = random.choice(['N', 'S', 'W', 'E'])
                self.vehicles.append(Vehicle(direction))

        for v in self.vehicles[:]:
            light_is_green = self.lights[v.direction].is_green
            v.update(light_is_green)

            if v.x < -150 or v.x > GAME_WIDTH + 150 or v.y < -150 or v.y > SCREEN_HEIGHT + 150:
                self.vehicles.remove(v)
                self.score += 20

        # Highscore check na punten toevoeging
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_highscore()

        self.check_collisions()

    def draw(self):
        # 1. Achtergrond & Omgeving (Gras + Boompjes in de hoeken)
        self.screen.fill(COLOR_BG)
        
        tree_radius = 28
        tree_positions = [
            (90, 90), (GAME_WIDTH - 90, 90),
            (90, SCREEN_HEIGHT - 90), (GAME_WIDTH - 90, SCREEN_HEIGHT - 90)
        ]
        for tx, ty in tree_positions:
            pygame.draw.circle(self.screen, COLOR_GRASS_DARK, (tx, ty), tree_radius)
            pygame.draw.circle(self.screen, (40, 140, 80), (tx, ty), tree_radius - 6)

        # 2. Asfalt Wegen & Stoepranden
        h_road_rect = pygame.Rect(0, CENTER_Y - (ROAD_WIDTH // 2), GAME_WIDTH, ROAD_WIDTH)
        v_road_rect = pygame.Rect(CENTER_X - (ROAD_WIDTH // 2), 0, ROAD_WIDTH, SCREEN_HEIGHT)

        curb_size = 6
        pygame.draw.rect(self.screen, COLOR_CURB, h_road_rect.inflate(0, curb_size * 2))
        pygame.draw.rect(self.screen, COLOR_CURB, v_road_rect.inflate(curb_size * 2, 0))

        pygame.draw.rect(self.screen, COLOR_ROAD, h_road_rect)
        pygame.draw.rect(self.screen, COLOR_ROAD, v_road_rect)

        # 3. Wegmarkeringen & Zebrapaden
        pygame.draw.line(self.screen, COLOR_YELLOW, (0, CENTER_Y), (GAME_WIDTH, CENTER_Y), 2)
        pygame.draw.line(self.screen, COLOR_YELLOW, (CENTER_X, 0), (CENTER_X, SCREEN_HEIGHT), 2)

        stripe_color = (240, 240, 240)
        for offset in range(-40, 40, 12):
            pygame.draw.rect(self.screen, stripe_color, (CENTER_X - (ROAD_WIDTH // 2) - 8, CENTER_Y + offset, 4, 8))
        for offset in range(-40, 40, 12):
            pygame.draw.rect(self.screen, stripe_color, (CENTER_X + (ROAD_WIDTH // 2) + 4, CENTER_Y + offset, 4, 8))

        # 4. Verkeerslichten & Voertuigen tekenen
        for light in self.lights.values():
            light.draw(self.screen)

        for v in self.vehicles:
            v.draw(self.screen)

        # 5. Rechter Zijbalk (Strak Dashboard met HIGHSCORE en SCORE bovenaan)
        sidebar_rect = pygame.Rect(GAME_WIDTH, 0, SCREEN_WIDTH - GAME_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_SIDEBAR, sidebar_rect)
        pygame.draw.line(self.screen, (60, 64, 67), (GAME_WIDTH, 0), (GAME_WIDTH, SCREEN_HEIGHT), 4)

        # --- HIGHSCORE BOX ---
        hs_box_rect = pygame.Rect(815, 15, 170, 50)
        pygame.draw.rect(self.screen, (45, 48, 54), hs_box_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_GOLD, hs_box_rect, 2, border_radius=6)
        hs_title = self.font.render("HIGHSCORE", True, COLOR_GOLD)
        hs_val = self.font_score.render(str(self.high_score), True, COLOR_WHITE)
        self.screen.blit(hs_title, (825, 20))
        self.screen.blit(hs_val, (900, 20))

        # --- SCORE BOX ---
        score_box_rect = pygame.Rect(815, 75, 170, 50)
        pygame.draw.rect(self.screen, (45, 48, 54), score_box_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BEAT, score_box_rect, 2, border_radius=6)
        score_title = self.font.render("SCORE", True, COLOR_BEAT)
        score_val = self.font_score.render(str(self.score), True, COLOR_WHITE)
        self.screen.blit(score_title, (825, 80))
        self.screen.blit(score_val, (900, 80))

        # Beat Metronoom Cirkel
        pulse = self.beat_manager.get_pulse_factor()
        radius = int(20 + (pulse * 10))
        pygame.draw.circle(self.screen, (60, 64, 67), (900, 180), 32)
        pygame.draw.circle(self.screen, COLOR_BEAT, (900, 180), radius)
        beat_label = self.font.render("BEAT", True, (255, 255, 255))
        self.screen.blit(beat_label, (881, 172))

        # Overige Stats (Tijd en Tempo)
        timer_surf = self.font.render(f"Tijd over: {self.time_left}s", True, COLOR_WHITE)
        bpm_surf = self.font.render(f"Tempo: {int(self.beat_manager.bpm)} BPM", True, COLOR_WHITE)

        self.screen.blit(timer_surf, (820, 230))
        self.screen.blit(bpm_surf, (820, 260))

        # Besturingskader onderaan in de zijbalk
        pygame.draw.rect(self.screen, (45, 48, 54), pygame.Rect(815, 310, 170, 150), border_radius=6)
        instr_title = self.font.render("Besturing:", True, COLOR_BEAT)
        instr_1 = self.font.render("W / A / S / D", True, COLOR_WHITE)
        instr_2 = self.font.render("of Pijltjestoetsen", True, COLOR_WHITE)
        instr_3 = self.font.render("= Licht bedienen", True, COLOR_WHITE)
        instr_4 = self.font.render("SPACE = Pauze", True, COLOR_WHITE)

        self.screen.blit(instr_title, (830, 320))
        self.screen.blit(instr_1, (830, 350))
        self.screen.blit(instr_2, (830, 370))
        self.screen.blit(instr_3, (830, 390))
        self.screen.blit(instr_4, (830, 415))

        # --- START SCHERM ---
        if self.state == 'START':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))

            title = self.font_large.render("TRAFFIC BEAT: GRIDLOCK HERO", True, COLOR_WHITE)
            sub = self.font.render("Regel het verkeer op de beat, voorkom botsingen!", True, COLOR_WHITE)
            
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 80)))
            self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30)))

            pygame.draw.rect(self.screen, (46, 204, 113), self.start_button, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_WHITE, self.start_button, 2, border_radius=6)
            btn_text = self.font.render("START GAME", True, COLOR_WHITE)
            self.screen.blit(btn_text, btn_text.get_rect(center=self.start_button.center))

        # --- PAUZE SCHERM ---
        elif self.state == 'PAUSED':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))

            pause_text = self.font_large.render("SPEL GEPAUZEERD", True, COLOR_WHITE)
            resume_text = self.font.render("Druk op SPACE om verder te gaan", True, COLOR_WHITE)

            self.screen.blit(pause_text, pause_text.get_rect(center=(GAME_WIDTH//2, SCREEN_HEIGHT//2 - 30)))
            self.screen.blit(resume_text, resume_text.get_rect(center=(GAME_WIDTH//2, SCREEN_HEIGHT//2 + 20)))

        # --- GAME OVER SCHERM ---
        elif self.state == 'GAMEOVER':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))

            over_text = self.font_large.render("TIJD OP! EINDSTAND", True, COLOR_WHITE)
            final_score = self.font_score.render(f"Jouw Score: {self.score}", True, COLOR_BEAT)
            hs_text = self.font_score.render(f"Highscore: {self.high_score}", True, COLOR_GOLD)

            self.screen.blit(over_text, over_text.get_rect(center=(GAME_WIDTH//2, SCREEN_HEIGHT//2 - 80)))
            self.screen.blit(final_score, final_score.get_rect(center=(GAME_WIDTH//2, SCREEN_HEIGHT//2 - 35)))
            self.screen.blit(hs_text, hs_text.get_rect(center=(GAME_WIDTH//2, SCREEN_HEIGHT//2 - 5)))

            pygame.draw.rect(self.screen, (70, 70, 70), self.restart_button, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_WHITE, self.restart_button, 2, border_radius=6)
            restart_text = self.font.render("OPNIEUW (R)", True, COLOR_WHITE)
            self.screen.blit(restart_text, restart_text.get_rect(center=self.restart_button.center))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()