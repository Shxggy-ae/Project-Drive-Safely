import pygame
import sys
import random
import math
import os
import tkinter as tk
from array import array
from tkinter import filedialog

from music import (
    MAX_TRAFFIC_BPM,
    SAMPLE_RATE,
    analyze_upcoming_section,
    analyze_track,
    extract_waveform,
    make_preset_events,
    make_rhythm_events,
    make_preset_sound,
)

# --- CONFIGURATIE & CONSTANTEN ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GAME_WIDTH = 800
FPS = 60
BEAT_INPUT_WINDOW_MS = 400
MAX_RHYTHM_BPM = MAX_TRAFFIC_BPM
ON_BEAT_SCORE = 100
OFF_BEAT_SCORE = 50
COMPLETION_BONUS = 1000
MIN_GREEN_BEATS = 3
GREEN_CLEARANCE_BUFFER_MS = 300
HIGH_SCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "highscore.txt",
)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "leaderboard.txt",
)

# Kleuren
COLOR_BG = (10, 7, 19)
COLOR_GRASS_DARK = (38, 16, 52)
COLOR_ROAD = (22, 21, 29)
COLOR_CURB = (170, 166, 178)
COLOR_SIDEBAR = (8, 7, 14)
COLOR_WHITE = (238, 234, 242)
COLOR_BLACK = (7, 6, 11)
COLOR_PURPLE = (139, 67, 170)
COLOR_PINK = (224, 76, 157)
COLOR_YELLOW = (221, 188, 67)
COLOR_RED = (185, 55, 64)
COLOR_GREEN = (62, 157, 104)
COLOR_BEAT = (221, 188, 67)
COLOR_OVERLAY = (6, 5, 10, 215)
COLOR_PALETTE = (
    (224, 76, 157),
    (139, 67, 170),
    (221, 188, 67),
    (238, 234, 242),
    (92, 58, 196),
)

ROAD_WIDTH = 130
CENTER_X = GAME_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2
DIRECTIONS = ("N", "E", "S", "W")
TRACK_VOLUME = 0.80
METRONOME_VOLUME = min(1.0, round(TRACK_VOLUME * 1.20, 2))

PRESET_LEVELS = (
    {"name": "Story", "song": "Story", "bpm": 140, "difficulty": "normal", "seed": 21},
    {
        "name": "Shotta's",
        "song": "Shotta's",
        "file": os.path.join(PROJECT_DIR, "presets", "shottas.mp3"),
        "bpm": 125,
        "difficulty": "hard",
    },
    {
        "name": "Wait a Minute",
        "song": "Wait a Minute!",
        "file": os.path.join(PROJECT_DIR, "presets", "wait-a-minute.mp3"),
        "bpm": 103,
        "difficulty": "normal",
    },
    {
        "name": "Neon Guts",
        "song": "Lil Uzi Vert - Neon Guts",
        "file": os.path.join(PROJECT_DIR, "presets", "neon-guts.mp3"),
        "bpm": 120,
        "difficulty": "hard",
    },
)


class BeatManager:
    def __init__(self, bpm=100, beat_events=None, start_ticks=None):
        self.bpm = bpm
        self.interval = (60 / self.bpm) * 1000
        self.start_ticks = pygame.time.get_ticks() if start_ticks is None else start_ticks
        self.last_beat_time = self.start_ticks
        self.is_beat_frame = False
        self.beat_events = beat_events
        self.next_event_index = 0
        self.current_event = None
        self.happened_events = []
        self.happened_event_indices = []
        self.beat_count = 0

    def update(self, current_bpm=None):
        if current_bpm and current_bpm != self.bpm:
            self.bpm = current_bpm
            self.interval = (60 / self.bpm) * 1000

        current_time = pygame.time.get_ticks()
        self.is_beat_frame = False
        self.current_event = None
        self.happened_events = []
        self.happened_event_indices = []

        if self.beat_events is not None:
            elapsed = (current_time - self.start_ticks) / 1000
            while (
                self.next_event_index < len(self.beat_events)
                and self.beat_events[self.next_event_index].time <= elapsed
            ):
                event = self.beat_events[self.next_event_index]
                event_index = self.next_event_index
                self.current_event = event
                self.last_beat_time = self.start_ticks + round(event.time * 1000)
                self.next_event_index += 1
                self.beat_count += 1
                self.is_beat_frame = True
                self.happened_events.append(event)
                self.happened_event_indices.append(event_index)

                if self.next_event_index < len(self.beat_events):
                    next_event = self.beat_events[self.next_event_index]
                    self.interval = max(1, (next_event.time - event.time) * 1000)
            return

        if current_time - self.last_beat_time >= self.interval:
            self.last_beat_time = current_time
            self.is_beat_frame = True
            self.beat_count += 1

    def get_pulse_factor(self):
        current_time = pygame.time.get_ticks()
        if self.beat_events and self.next_event_index == 0:
            first_beat_time = (
                self.start_ticks + round(self.beat_events[0].time * 1000)
            )
            first_interval = max(1, first_beat_time - self.start_ticks)
            progress = min(
                1.0,
                max(0.0, (current_time - self.start_ticks) / first_interval),
            )
            return (1 - math.cos(math.pi * progress)) / 2

        elapsed = (current_time - self.last_beat_time) % self.interval
        return (1 + math.cos(2 * math.pi * elapsed / self.interval)) / 2

    def next_beat_time(self, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()
        if (
            self.beat_events
            and self.next_event_index < len(self.beat_events)
        ):
            next_event = self.beat_events[self.next_event_index]
            return self.start_ticks + round(next_event.time * 1000)

        interval = max(1, self.interval)
        elapsed = max(0, current_time - self.last_beat_time)
        intervals_until_next = math.floor(elapsed / interval) + 1
        return round(self.last_beat_time + intervals_until_next * interval)

    def nearest_beat_time(self, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()
        if self.beat_events:
            scheduled_beats = []
            if self.next_event_index > 0:
                previous_event = self.beat_events[self.next_event_index - 1]
                scheduled_beats.append(
                    self.start_ticks + round(previous_event.time * 1000)
                )
            if self.next_event_index < len(self.beat_events):
                next_event = self.beat_events[self.next_event_index]
                scheduled_beats.append(
                    self.start_ticks + round(next_event.time * 1000)
                )
            else:
                scheduled_beats.append(self.next_beat_time(current_time))
            return min(scheduled_beats, key=lambda beat: abs(current_time - beat))

        elapsed = (current_time - self.last_beat_time) % self.interval
        if elapsed <= self.interval / 2:
            return current_time - elapsed
        return current_time + self.interval - elapsed

    def beat_offsets(self, current_time=None, lookahead_ms=900):
        if current_time is None:
            current_time = pygame.time.get_ticks()
        lookahead_ms = max(1, lookahead_ms)

        if self.beat_events is not None:
            elapsed = (current_time - self.start_ticks) / 1000
            offsets = []
            index = min(self.next_event_index, len(self.beat_events)) - 1
            while index >= 0:
                event = self.beat_events[index]
                offset = round(event.time * 1000) - round(elapsed * 1000)
                if offset < -lookahead_ms:
                    break
                offsets.append(offset)
                index -= 1

            index = max(0, self.next_event_index)
            while index < len(self.beat_events):
                event = self.beat_events[index]
                offset = round(event.time * 1000) - round(elapsed * 1000)
                if offset > lookahead_ms:
                    break
                offsets.append(offset)
                index += 1
            return sorted(offsets)

        interval = max(1, round(self.interval))
        next_beat = self.next_beat_time(current_time)
        offsets = []
        beat_time = next_beat
        while beat_time - current_time <= lookahead_ms:
            offsets.append(beat_time - current_time)
            beat_time += interval
        beat_time = next_beat - interval
        while current_time - beat_time <= lookahead_ms:
            offsets.append(beat_time - current_time)
            beat_time -= interval
        return sorted(offsets)

    def input_window_ms(self, beat_time=None):
        if beat_time is None:
            beat_time = self.nearest_beat_time()

        interval = max(1, self.interval)
        if self.beat_events:
            first_index = max(0, self.next_event_index - 2)
            last_index = min(len(self.beat_events), self.next_event_index + 2)
            nearby_indices = range(first_index, last_index)
            nearest_index = min(
                nearby_indices,
                key=lambda index: abs(
                    beat_time
                    - (
                        self.start_ticks
                        + round(self.beat_events[index].time * 1000)
                    )
                ),
            )
            adjacent_intervals = []
            if nearest_index > 0:
                previous = self.beat_events[nearest_index - 1]
                current = self.beat_events[nearest_index]
                adjacent_intervals.append((current.time - previous.time) * 1000)
            else:
                adjacent_intervals.append(60_000 / self.bpm)
            if nearest_index + 1 < len(self.beat_events):
                current = self.beat_events[nearest_index]
                following = self.beat_events[nearest_index + 1]
                adjacent_intervals.append((following.time - current.time) * 1000)
            else:
                adjacent_intervals.append(interval)
            interval = max(1, min(adjacent_intervals))

        return min(BEAT_INPUT_WINDOW_MS, max(1, round(interval * 0.45)))

    def is_on_beat(self, window_ms=None):
        current_time = pygame.time.get_ticks()
        beat_time = self.nearest_beat_time(current_time)
        if window_ms is None:
            window_ms = self.input_window_ms(beat_time)
        return abs(current_time - beat_time) <= window_ms


class TrafficLight:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.is_green = False
        self.state = "RED"
        self.yellow_until = 0
        self.green_until = 0
        self.rect = pygame.Rect(x - 18, y - 34, 36, 68)

    def toggle(self):
        self.is_green = not self.is_green
        self.state = "GREEN" if self.is_green else "RED"

    def set_green(self, duration_ms=420):
        self.is_green = True
        self.state = "GREEN"
        self.yellow_until = 0
        self.green_until = pygame.time.get_ticks() + duration_ms

    def set_yellow(self, yellow_ms=700):
        self.is_green = False
        self.state = "YELLOW"
        self.yellow_until = pygame.time.get_ticks() + yellow_ms

    def update(self):
        if self.state == "GREEN" and pygame.time.get_ticks() >= self.green_until:
            self.set_yellow(700)
        if self.state == "YELLOW" and pygame.time.get_ticks() >= self.yellow_until:
            self.state = "RED"
            self.is_green = False

    def draw(self, surface):
        housing = pygame.Rect(self.x - 15, self.y - 31, 30, 62)
        pygame.draw.rect(surface, (27, 29, 30), housing, border_radius=8)
        pygame.draw.rect(surface, (104, 108, 108), housing, 2, border_radius=8)
        active_color = {
            "RED": COLOR_RED,
            "YELLOW": COLOR_YELLOW,
            "GREEN": COLOR_GREEN,
        }[self.state]
        inactive_colors = {
            "RED": (77, 29, 28),
            "YELLOW": (75, 62, 24),
            "GREEN": (24, 67, 44),
        }
        for index, state in enumerate(("RED", "YELLOW", "GREEN")):
            center = (self.x, self.y - 20 + index * 20)
            color = active_color if self.state == state else inactive_colors[state]
            pygame.draw.circle(surface, color, center, 7)
            pygame.draw.circle(surface, (76, 79, 79), center, 7, 1)
            if self.state == state:
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (center[0] - 2, center[1] - 2),
                    2,
                )
        pygame.draw.rect(
            surface,
            (100, 100, 100),
            (self.x - 3, self.y + 30, 6, 11),
        )


class Vehicle:
    LEFT_TURNS = {'N': 'W', 'E': 'N', 'S': 'E', 'W': 'S'}
    RIGHT_TURNS = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}
    HEADINGS = {'W': 0, 'N': 90, 'E': 180, 'S': 270}

    def __init__(self, direction, queue_position=0, turn=None):
        self.direction = direction
        self.approach_direction = direction
        self.turn = turn or random.choice(("straight", "left", "right"))
        self.speed = 7
        self.width = 34
        self.height = 20
        self.body_color = random.choice(COLOR_PALETTE)
        self.has_collided = False
        self.passed_stop_line = False
        self.inside_intersection = False
        self.stopped = False
        self.turn_curve = None
        self.turn_progress = 0.0
        self.heading_angle = self.HEADINGS[direction]
        queue_offset = queue_position * 48

        if direction == 'W':
            self.x = -self.width - queue_offset
            self.y = CENTER_Y - 36
            self.stop_x = CENTER_X - (ROAD_WIDTH // 2) - 25
        elif direction == 'E':
            self.x = GAME_WIDTH + self.width + queue_offset
            self.y = CENTER_Y + 16
            self.stop_x = CENTER_X + (ROAD_WIDTH // 2) + 25
        elif direction == 'N':
            self.x = CENTER_X + 16
            self.y = -self.height - queue_offset
            self.stop_y = CENTER_Y - (ROAD_WIDTH // 2) - 25
        elif direction == 'S':
            self.x = CENTER_X - 36
            self.y = SCREEN_HEIGHT + queue_offset
            self.stop_y = CENTER_Y + (ROAD_WIDTH // 2) + 25

    def get_rect(self):
        if self.direction in ('W', 'E'):
            return pygame.Rect(self.x, self.y, self.width, self.height)
        else:
            return pygame.Rect(self.x, self.y, self.height, self.width)

    def get_collision_corners(self):
        center = self.get_rect().center
        angle = math.radians(self.heading_angle)
        forward = (math.cos(angle), math.sin(angle))
        side = (-forward[1], forward[0])
        corners = []
        for forward_sign, side_sign in (
            (-1, -1),
            (-1, 1),
            (1, 1),
            (1, -1),
        ):
            corners.append(
                (
                    center[0]
                    + forward[0] * self.width / 2 * forward_sign
                    + side[0] * self.height / 2 * side_sign,
                    center[1]
                    + forward[1] * self.width / 2 * forward_sign
                    + side[1] * self.height / 2 * side_sign,
                )
            )
        return corners

    def collides_with(self, other):
        first_corners = self.get_collision_corners()
        second_corners = other.get_collision_corners()
        for vehicle in (self, other):
            angle = math.radians(vehicle.heading_angle)
            for axis in (
                (math.cos(angle), math.sin(angle)),
                (-math.sin(angle), math.cos(angle)),
            ):
                first_projection = [
                    corner[0] * axis[0] + corner[1] * axis[1]
                    for corner in first_corners
                ]
                second_projection = [
                    corner[0] * axis[0] + corner[1] * axis[1]
                    for corner in second_corners
                ]
                if (
                    max(first_projection) <= min(second_projection)
                    or max(second_projection) <= min(first_projection)
                ):
                    return False
        return True

    def set_center(self, center, direction=None):
        direction = direction or self.direction
        if direction in ('W', 'E'):
            self.x = center[0] - self.width / 2
            self.y = center[1] - self.height / 2
        else:
            self.x = center[0] - self.height / 2
            self.y = center[1] - self.width / 2

    def start_turn(self):
        if self.turn == "straight":
            return

        target = (
            self.LEFT_TURNS[self.approach_direction]
            if self.turn == "left"
            else self.RIGHT_TURNS[self.approach_direction]
        )
        starts = {'N': (0, 1), 'E': (-1, 0), 'S': (0, -1), 'W': (1, 0)}
        ends = {'W': (1, 0), 'N': (0, 1), 'E': (-1, 0), 'S': (0, -1)}
        exit_centers = {
            'W': (CENTER_X + ROAD_WIDTH // 2 + self.width + 20, CENTER_Y - 26),
            'E': (CENTER_X - ROAD_WIDTH // 2 - self.width - 20, CENTER_Y + 26),
            'N': (CENTER_X + 26, CENTER_Y + ROAD_WIDTH // 2 + self.width + 20),
            'S': (CENTER_X - 26, CENTER_Y - ROAD_WIDTH // 2 - self.width - 20),
        }

        start = self.get_rect().center
        end = exit_centers[target]
        start_vector = starts[self.approach_direction]
        end_vector = ends[target]
        control_distance = ROAD_WIDTH // 2
        first_control = (
            start[0] + start_vector[0] * control_distance,
            start[1] + start_vector[1] * control_distance,
        )
        second_control = (
            end[0] - end_vector[0] * control_distance,
            end[1] - end_vector[1] * control_distance,
        )
        path_length = sum(
            math.hypot(second[0] - first[0], second[1] - first[1])
            for first, second in (
                (start, first_control),
                (first_control, second_control),
                (second_control, end),
            )
        )
        self.turn_curve = (
            start,
            first_control,
            second_control,
            end,
            target,
            path_length,
        )
        self.turn_progress = 0.0

    def advance_turn(self, step):
        start, first, second, end, target, path_length = self.turn_curve
        self.turn_progress = min(1.0, self.turn_progress + step / path_length)
        t = self.turn_progress
        inverse = 1 - t
        x = (
            inverse ** 3 * start[0]
            + 3 * inverse ** 2 * t * first[0]
            + 3 * inverse * t ** 2 * second[0]
            + t ** 3 * end[0]
        )
        y = (
            inverse ** 3 * start[1]
            + 3 * inverse ** 2 * t * first[1]
            + 3 * inverse * t ** 2 * second[1]
            + t ** 3 * end[1]
        )
        dx = (
            3 * inverse ** 2 * (first[0] - start[0])
            + 6 * inverse * t * (second[0] - first[0])
            + 3 * t ** 2 * (end[0] - second[0])
        )
        dy = (
            3 * inverse ** 2 * (first[1] - start[1])
            + 6 * inverse * t * (second[1] - first[1])
            + 3 * t ** 2 * (end[1] - second[1])
        )
        self.heading_angle = math.degrees(math.atan2(dy, dx)) % 360
        self.set_center((x, y))

        if self.turn_progress >= 1:
            self.direction = target
            self.heading_angle = self.HEADINGS[target]
            self.set_center(end, target)
            self.turn_curve = None
            self.inside_intersection = False

    def update(
        self,
        light_state="RED",
        move_on_beat=False,
        blocked=False,
        speed_scale=1.0,
    ):
        if self.turn_curve is not None:
            step = self.speed * (2 if move_on_beat else 1) * speed_scale
            self.advance_turn(step)
            self.stopped = False
            return

        if blocked:
            self.stopped = True
            return

        if self.passed_stop_line:
            step = self.speed * (2 if move_on_beat else 1) * speed_scale
        elif light_state == "GREEN":
            step = self.speed * (2 if move_on_beat else 1) * speed_scale
        elif light_state == "YELLOW":
            step = max(2, self.speed // 2) * speed_scale
        else:
            step = self.speed * speed_scale

        if self.direction == 'W':
            if light_state != "GREEN" and not self.passed_stop_line:
                if self.x + self.width >= self.stop_x:
                    self.stopped = True
                    return
                if self.x + self.width + step >= self.stop_x:
                    self.x = self.stop_x - self.width
                    self.stopped = True
                    return
            self.x += step
        elif self.direction == 'E':
            if light_state != "GREEN" and not self.passed_stop_line:
                if self.x <= self.stop_x:
                    self.stopped = True
                    return
                if self.x - step <= self.stop_x:
                    self.x = self.stop_x
                    self.stopped = True
                    return
            self.x -= step
        elif self.direction == 'N':
            if light_state != "GREEN" and not self.passed_stop_line:
                if self.y + self.height >= self.stop_y:
                    self.stopped = True
                    return
                if self.y + self.height + step >= self.stop_y:
                    self.y = self.stop_y - self.height
                    self.stopped = True
                    return
            self.y += step
        elif self.direction == 'S':
            if light_state != "GREEN" and not self.passed_stop_line:
                if self.y <= self.stop_y:
                    self.stopped = True
                    return
                if self.y - step <= self.stop_y:
                    self.y = self.stop_y
                    self.stopped = True
                    return
            self.y -= step

        if not self.passed_stop_line:
            crossed_line = (
                self.direction == 'W' and self.x + self.width > self.stop_x
                or self.direction == 'E' and self.x < self.stop_x
                or self.direction == 'N' and self.y + self.height > self.stop_y
                or self.direction == 'S' and self.y < self.stop_y
            )
            if crossed_line:
                self.passed_stop_line = True
                self.inside_intersection = True
                self.start_turn()
        elif self.inside_intersection and self.turn_curve is None:
            cleared_intersection = (
                self.direction == 'W' and self.x >= CENTER_X + ROAD_WIDTH // 2
                or self.direction == 'E' and self.x + self.width <= CENTER_X - ROAD_WIDTH // 2
                or self.direction == 'N' and self.y >= CENTER_Y + ROAD_WIDTH // 2
                or self.direction == 'S' and self.y + self.height <= CENTER_Y - ROAD_WIDTH // 2
            )
            if cleared_intersection:
                self.inside_intersection = False
        self.stopped = False

    def draw(self, surface, glowing=False):
        rect = self.get_rect()
        if glowing:
            pygame.draw.rect(
                surface,
                (205, 177, 82),
                rect.inflate(10, 10),
                3,
                border_radius=8,
            )
        car = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(
            car,
            self.body_color,
            pygame.Rect(0, 0, self.width, self.height),
            border_radius=5,
        )
        outline = COLOR_RED if self.has_collided else (20, 20, 20)
        pygame.draw.rect(
            car,
            outline,
            pygame.Rect(0, 0, self.width, self.height),
            2 if self.has_collided else 1,
            border_radius=5,
        )
        pygame.draw.rect(
            car,
            (142, 151, 166),
            pygame.Rect(self.width // 2 - 4, 3, 9, self.height - 6),
            border_radius=2,
        )
        if not self.passed_stop_line:
            route_arrows = {
                "left": ((17, 14), (17, 6), (14, 9), (17, 6), (20, 9)),
                "right": ((17, 6), (17, 14), (14, 11), (17, 14), (20, 11)),
                "straight": ((13, 10), (22, 10), (19, 7), (22, 10), (19, 13)),
            }
            route_color = COLOR_YELLOW if self.turn != "straight" else COLOR_GREEN
            pygame.draw.lines(
                car,
                route_color,
                False,
                route_arrows[self.turn],
                2,
            )
        pygame.draw.circle(car, (215, 210, 176), (self.width - 2, 4), 2)
        pygame.draw.circle(car, (215, 210, 176), (self.width - 2, self.height - 4), 2)

        rotated_car = pygame.transform.rotate(car, -self.heading_angle)
        self_rect = rotated_car.get_rect(center=self.get_rect().center)
        surface.blit(rotated_car, self_rect)


class Game:
    def __init__(self):
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Traffic Beat")
        self.clock = pygame.time.Clock()
        retro_font = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "PressStart2P-Regular.ttf",
        )
        self.font = pygame.font.Font(retro_font, 11)
        self.font_score = pygame.font.Font(retro_font, 14)
        self.font_large = pygame.font.Font(retro_font, 20)
        self.font_title = pygame.font.Font(retro_font, 28)
        self.font_card_title = pygame.font.Font(retro_font, 10)
        self.font_card_small = pygame.font.Font(retro_font, 7)

        self.state = 'START'
        self.metronome_enabled = True
        self.metronome_tick = self.make_tone_sound(1500, 0.045, 5000)
        self.metronome_accent = self.make_tone_sound(2100, 0.06, 6500)

        self.game_duration = 60
        self.time_left = self.game_duration
        self.start_ticks = 0
        self.beat_manager = BeatManager(bpm=100)
        self.rhythm_manager = BeatManager(bpm=100)
        self.track_sound = None
        self.track_channel = None
        self.track_waveform = []
        self.waveform_layer = None
        self.preview_sound = None
        self.preview_channel = None
        self.track_events = None
        self.track_bpm = 100
        self.rhythm_events = None
        self.rhythm_bpm = 100
        self.track_name = "Selecteer een track"
        self.track_is_custom = False
        self.track_fading_out = False
        self.game_over_reason = None
        self.score = 0
        self.mistakes = 0
        self.on_beat_streak = 0
        self.score_saved = False
        self.rhythm_feedback = ""
        self.rhythm_feedback_until = 0
        self.score_popup = ""
        self.score_popup_until = 0
        self.score_popup = ""
        self.score_popup_until = 0
        self.pause_started_ticks = 0
        self.active_hold_direction = None
        self.active_hold_until = 0
        self.control_direction = None
        self.served_lanes = set()
        self.on_beat_served_lanes = set()
        self.lane_start_offset = 0
        self.lane_patience = {direction: 0 for direction in DIRECTIONS}
        self.lane_wait_beats = {direction: 0 for direction in DIRECTIONS}
        self.traffic_forecast = analyze_upcoming_section([], 0, self.track_bpm)
        self.patience_limit_beats = self.traffic_forecast.patience_beats * 2
        self.traffic_lane_counts = {direction: 0 for direction in DIRECTIONS}
        self.traffic_preview = []
        self.status_message = ""
        self.status_until = 0
        self.high_score_file = HIGH_SCORE_FILE
        self.high_score = self.load_high_score()
        self.leaderboard_file = LEADERBOARD_FILE
        self.leaderboard = self.load_leaderboard()
        self.player_name = "PLAY"
        self.score_saved = False
        self.start_menu_index = 0
        self.pending_load = None
        self.loading_started_ticks = 0
        self.loading_message = "LOADING TRACK..."

        self.city_buildings = self.make_city_buildings()
        self.lights = self.make_lights()
        self.vehicles = []
        self.restart_button = pygame.Rect(220, 500, 160, 45)
        self.menu_button = pygame.Rect(420, 500, 160, 45)
        self.new_game_button = pygame.Rect(250, 355, 300, 52)
        self.custom_mode_button = pygame.Rect(250, 423, 300, 52)
        self.leaderboard_button = pygame.Rect(250, 491, 300, 52)
        self.selected_level_index = 0
        self.level_buttons = [
            pygame.Rect(20 + index * 194, 245, 175, 180)
            for index in range(len(PRESET_LEVELS))
        ]
        self.back_button = pygame.Rect(28, 520, 135, 42)

    @staticmethod
    def make_tone_sound(frequency, duration, volume, end_frequency=None):
        frame_count = round(SAMPLE_RATE * duration)
        final_frequency = frequency if end_frequency is None else end_frequency
        samples = array("h")
        phase = 0
        for frame in range(frame_count):
            progress = frame / max(1, frame_count - 1)
            current_frequency = frequency + (
                final_frequency - frequency
            ) * progress
            phase += 2 * math.pi * current_frequency / SAMPLE_RATE
            envelope = math.exp(-frame / (SAMPLE_RATE * duration / 4))
            samples.append(round(volume * envelope * math.sin(phase)))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def load_high_score(self):
        try:
            with open(self.high_score_file, "r", encoding="utf-8") as score_file:
                return max(0, int(score_file.read().strip()))
        except FileNotFoundError:
            return 0
        except (OSError, ValueError) as error:
            self.show_status(f"High score kon niet worden geladen: {error}")
            return 0

    def save_high_score(self):
        if self.score <= self.high_score:
            return

        self.high_score = self.score
        try:
            with open(self.high_score_file, "w", encoding="utf-8") as score_file:
                score_file.write(f"{self.high_score}\n")
        except OSError as error:
            self.show_status(f"High score kon niet worden opgeslagen: {error}")

    def load_leaderboard(self):
        entries = []
        try:
            with open(self.leaderboard_file, "r", encoding="utf-8") as score_file:
                for line in score_file:
                    parts = line.strip().split("|", 2)
                    if len(parts) == 3:
                        name = parts[0][:5].upper() or "PLAYER"
                        try:
                            score = max(0, int(parts[1]))
                        except ValueError:
                            continue
                        entries.append((name, score, parts[2][:24]))
        except FileNotFoundError:
            pass
        except OSError as error:
            self.show_status(f"Leaderboard kon niet worden geladen: {error}")
        return sorted(entries, key=lambda entry: entry[1], reverse=True)[:10]

    def save_leaderboard_entry(self):
        if getattr(self, "score_saved", False):
            return
        name = getattr(self, "player_name", "PLAYER").strip().upper()
        name = "".join(character for character in name if character.isalnum())[:5]
        if not name:
            name = "PLAYER"
        entries = list(getattr(self, "leaderboard", []))
        entries.append((name, max(0, self.score), self.track_name[:24]))
        entries.sort(key=lambda entry: entry[1], reverse=True)
        self.leaderboard = entries[:10]
        try:
            with open(self.leaderboard_file, "w", encoding="utf-8") as score_file:
                for entry_name, entry_score, entry_track in self.leaderboard:
                    score_file.write(f"{entry_name}|{entry_score}|{entry_track}\n")
        except OSError as error:
            self.show_status(f"Leaderboard kon niet worden opgeslagen: {error}")
        self.score_saved = True

    def finish_game(self, reason):
        if self.state == "GAMEOVER":
            return
        self.state = "GAMEOVER"
        self.game_over_reason = reason
        track_channel = getattr(self, "track_channel", None)
        if track_channel is not None:
            track_channel.stop()
        if hasattr(self, "high_score"):
            self.save_high_score()

    def play_metronome_tick(self):
        if not self.metronome_enabled:
            return
        metronome_tick = getattr(self, "metronome_tick", None)
        metronome_accent = getattr(self, "metronome_accent", None)
        if metronome_tick is not None and hasattr(metronome_tick, "set_volume"):
            metronome_tick.set_volume(METRONOME_VOLUME)
        if metronome_accent is not None and hasattr(metronome_accent, "set_volume"):
            metronome_accent.set_volume(METRONOME_VOLUME)
        if self.rhythm_manager.beat_count % 4 == 1:
            self.metronome_accent.play()
        else:
            self.metronome_tick.play()

    @staticmethod
    def make_lights():
        return {
            'N': TrafficLight(CENTER_X + 35, CENTER_Y - (ROAD_WIDTH // 2) - 25, 'N'),
            'S': TrafficLight(CENTER_X - 35, CENTER_Y + (ROAD_WIDTH // 2) + 25, 'S'),
            'W': TrafficLight(CENTER_X - (ROAD_WIDTH // 2) - 25, CENTER_Y + 35, 'W'),
            'E': TrafficLight(CENTER_X + (ROAD_WIDTH // 2) + 25, CENTER_Y - 35, 'E'),
        }

    @staticmethod
    def make_city_buildings():
        buildings = []
        heights = (112, 148, 92, 130, 165, 105, 142, 118)
        x_positions = (8, 92, 176, 478, 562, 646, 730)
        for index, x in enumerate(x_positions):
            width = 70 if x != 730 else 64
            height = heights[index]
            color = (70 + index * 3, 78 + index * 2, 82 + index * 2)
            buildings.append((x, 18, width, height, color))
            buildings.append((x, SCREEN_HEIGHT - height - 18, width, height, color))
        return buildings

    def show_status(self, message, duration=5):
        self.status_message = message
        self.status_until = pygame.time.get_ticks() + duration * 1000

    def normalize_track_timing(self, bpm, rhythm_events, duration):
        normalized_bpm = min(MAX_RHYTHM_BPM, max(60, round(bpm)))
        if normalized_bpm != bpm:
            rhythm_events = make_rhythm_events(normalized_bpm, duration)
        return normalized_bpm, rhythm_events

    def start_loading(self, message):
        self.loading_message = message
        self.loading_started_ticks = pygame.time.get_ticks()
        self.state = "LOADING"

    def select_preset(self, index):
        self.stop_preview()
        level = PRESET_LEVELS[index]
        self.loading_message = f"LOADING {level['song'].upper()}..."
        self.pending_load = ("preset", index)
        self.start_loading(self.loading_message)

    def stop_preview(self):
        preview_channel = getattr(self, "preview_channel", None)
        if preview_channel is not None:
            preview_channel.stop()
        self.preview_channel = None
        self.preview_sound = None

    def preview_selected_level(self):
        index = getattr(self, "selected_level_index", 0)
        level = PRESET_LEVELS[index]
        self.stop_preview()
        try:
            if "file" in level:
                self.preview_sound = pygame.mixer.Sound(level["file"])
            else:
                self.preview_sound = make_preset_sound(
                    level["bpm"],
                    level["seed"],
                )
            self.preview_channel = self.preview_sound.play(maxtime=10_000)
            if self.preview_channel is None:
                self.show_status("De trackpreview kon niet worden afgespeeld.")
            else:
                self.preview_channel.set_volume(TRACK_VOLUME)
                self.show_status(f"PREVIEW: {level['song']} (10 SEC)")
        except (pygame.error, OSError, RuntimeError, ValueError) as error:
            self.stop_preview()
            self.show_status(f"Trackpreview mislukt: {error}")

    def process_pending_load(self):
        if self.pending_load is None:
            return
        elapsed = pygame.time.get_ticks() - self.loading_started_ticks
        if elapsed < 450:
            return

        pending_load = self.pending_load
        self.pending_load = None
        if pending_load[0] == "preset":
            self.load_preset(pending_load[1])
        elif pending_load[0] == "custom":
            self.load_custom_track(pending_load[1])

    def load_preset(self, index):
        level = PRESET_LEVELS[index]
        try:
            if "file" in level:
                preset_sound = pygame.mixer.Sound(level["file"])
                waveform = extract_waveform(preset_sound)
                (
                    events,
                    bpm,
                    used_fallback,
                    rhythm_events,
                    rhythm_bpm,
                ) = analyze_track(preset_sound, subdivision=1)
                if not events:
                    self.state = "LEVEL_SELECT"
                    self.show_status("Er konden geen beats in dit presetbestand worden gevonden.")
                    return
                rhythm_bpm, rhythm_events = self.normalize_track_timing(
                    rhythm_bpm,
                    rhythm_events,
                    preset_sound.get_length(),
                )
                bpm = min(MAX_TRAFFIC_BPM, round(bpm))
                self.track_sound = preset_sound
                self.track_events = events
                self.track_bpm = bpm
                self.rhythm_events = rhythm_events
                self.rhythm_bpm = rhythm_bpm
                self.game_duration = max(1.0, preset_sound.get_length())
                if used_fallback:
                    self.show_status("Geen duidelijke beats gevonden; scorebeat op 100 BPM.")
            else:
                self.track_sound = make_preset_sound(level["bpm"], level["seed"])
                waveform = extract_waveform(self.track_sound)
                self.track_bpm = min(MAX_TRAFFIC_BPM, level["bpm"])
                self.game_duration = 60
                self.track_events = make_preset_events(
                    level["bpm"], self.game_duration, level["difficulty"]
                )
                self.rhythm_events = make_rhythm_events(
                    level["bpm"], self.game_duration
                )
                self.rhythm_bpm = level["bpm"]

        except (pygame.error, OSError, RuntimeError, ValueError, OverflowError) as error:
            self.state = "LEVEL_SELECT"
            self.show_status(f"Preset laden is mislukt: {error}")
            return

        self.track_waveform = waveform
        self.waveform_layer = self.make_waveform_layer(waveform)
        self.track_name = level["song"]
        self.track_is_custom = False
        self.reset_game()

    def choose_custom_track(self):
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                path = filedialog.askopenfilename(
                    title="Kies een MP3-bestand",
                    filetypes=(("MP3-bestanden", "*.mp3"), ("Alle bestanden", "*.*")),
                )
            finally:
                root.destroy()
        except tk.TclError as error:
            self.show_status(f"Bestandskiezer kon niet worden geopend: {error}")
            return

        if not path:
            return
        self.stop_preview()
        self.pending_load = ("custom", path)
        self.start_loading("ANALYZING MP3...")

    def load_custom_track(self, path):
        try:
            sound = pygame.mixer.Sound(path)
            waveform = extract_waveform(sound)
            events, bpm, used_fallback, rhythm_events, rhythm_bpm = analyze_track(
                sound,
                subdivision=1,
            )
            duration = max(1.0, sound.get_length())
            rhythm_bpm, rhythm_events = self.normalize_track_timing(
                rhythm_bpm,
                rhythm_events,
                duration,
            )
            bpm = min(MAX_TRAFFIC_BPM, round(bpm))
        except (pygame.error, OSError, RuntimeError, ValueError, OverflowError) as error:
            self.state = "START"
            self.pending_load = None
            self.show_status(f"MP3 laden is mislukt: {error}")
            return

        if not events:
            self.state = "START"
            self.pending_load = None
            self.show_status("Er konden geen beats in dit MP3-bestand worden gevonden.")
            return

        self.stop_preview()
        if self.track_channel is not None:
            self.track_channel.stop()
        self.track_sound = sound
        self.track_waveform = waveform
        self.waveform_layer = self.make_waveform_layer(waveform)
        self.track_events = events
        self.track_bpm = bpm
        self.rhythm_events = rhythm_events
        self.rhythm_bpm = rhythm_bpm
        self.track_name = os.path.basename(path)
        self.game_duration = max(1.0, sound.get_length())
        self.track_is_custom = True
        self.reset_game()
        if used_fallback:
            self.show_status("Geen duidelijke beats gevonden; scorebeat op 100 BPM.")

    def reset_game(self):
        self.stop_preview()
        if self.track_channel is not None:
            self.track_channel.stop()
        self.track_channel = None
        self.vehicles = []
        self.lights = self.make_lights()
        self.pause_started_ticks = 0
        self.active_hold_direction = None
        self.active_hold_until = 0
        self.control_direction = None
        self.served_lanes = set()
        self.on_beat_served_lanes = set()
        self.lane_start_offset = random.randrange(len(DIRECTIONS))
        self.game_over_reason = None
        self.score = 0
        self.mistakes = 0
        self.on_beat_streak = 0
        self.score_saved = False
        self.rhythm_feedback = ""
        self.rhythm_feedback_until = 0
        self.score_popup = ""
        self.score_popup_until = 0
        self.track_fading_out = False
        self.lane_patience = {direction: 0 for direction in DIRECTIONS}
        self.lane_wait_beats = {direction: 0 for direction in DIRECTIONS}
        self.state = 'PLAYING'
        if self.track_sound is not None:
            self.track_channel = self.track_sound.play(loops=0)
            if self.track_channel is None:
                self.show_status("De muziek kon niet worden afgespeeld.")
            elif hasattr(self.track_channel, "set_volume"):
                self.track_channel.set_volume(TRACK_VOLUME)
        self.start_ticks = pygame.time.get_ticks()
        self.time_left = math.ceil(self.game_duration)
        self.beat_manager = BeatManager(
            bpm=self.track_bpm,
            beat_events=self.track_events,
            start_ticks=self.start_ticks,
        )
        self.rhythm_manager = BeatManager(
            bpm=self.rhythm_bpm,
            beat_events=self.rhythm_events,
            start_ticks=self.start_ticks,
        )
        self.traffic_forecast = analyze_upcoming_section(
            self.track_events or [],
            0,
            self.track_bpm,
            horizon=60,
        )
        self.patience_limit_beats = self.traffic_forecast.patience_beats * 2
        self.update_traffic_preview(0)

    @staticmethod
    def make_waveform_layer(waveform):
        layer = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        if len(waveform) < 2:
            return layer

        baseline = SCREEN_HEIGHT // 2
        color = (*COLOR_PINK, 26)
        upper = []
        lower = []
        for index, amplitude in enumerate(waveform):
            x = round(index * (GAME_WIDTH - 1) / (len(waveform) - 1))
            height = round(amplitude * 82)
            upper.append((x, baseline - height))
            lower.append((x, baseline + height))
        pygame.draw.lines(layer, color, False, upper)
        pygame.draw.lines(layer, color, False, lower)
        return layer

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == 'START':
                    if event.key in (
                        pygame.K_UP,
                        pygame.K_DOWN,
                        pygame.K_w,
                        pygame.K_s,
                        pygame.K_LEFT,
                        pygame.K_RIGHT,
                        pygame.K_a,
                        pygame.K_d,
                    ):
                        self.start_menu_index = (
                            self.start_menu_index + 1
                        ) % 3
                    elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        if getattr(self, "start_menu_index", 0) == 1:
                            self.choose_custom_track()
                        elif getattr(self, "start_menu_index", 0) == 2:
                            self.state = "LEADERBOARD"
                        else:
                            self.state = 'LEVEL_SELECT'
                    elif event.key == pygame.K_c:
                        self.choose_custom_track()
                    elif event.key == pygame.K_l:
                        self.state = "LEADERBOARD"
                elif self.state == 'LEVEL_SELECT':
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        self.stop_preview()
                        self.state = 'START'
                    elif event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
                        self.stop_preview()
                        self.selected_level_index = (
                            self.selected_level_index - 1
                        ) % len(PRESET_LEVELS)
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
                        self.stop_preview()
                        self.selected_level_index = (
                            self.selected_level_index + 1
                        ) % len(PRESET_LEVELS)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.select_preset(self.selected_level_index)
                    elif event.key == pygame.K_p:
                        self.preview_selected_level()
                    elif event.key in (
                        pygame.K_1,
                        pygame.K_2,
                        pygame.K_3,
                        pygame.K_4,
                    ):
                        self.stop_preview()
                        self.selected_level_index = (
                            event.key - pygame.K_1
                        )
                        self.select_preset(self.selected_level_index)
                elif self.state == 'LEADERBOARD':
                    if event.key in (
                        pygame.K_ESCAPE,
                        pygame.K_BACKSPACE,
                        pygame.K_m,
                    ):
                        self.state = 'START'
                elif self.state == 'PLAYING':
                    if event.key == pygame.K_m:
                        self.metronome_enabled = not self.metronome_enabled
                        setting = "aan" if self.metronome_enabled else "uit"
                        self.show_status(f"Metronoom {setting}.")
                    elif event.key == pygame.K_SPACE:
                        self.state = 'PAUSED'
                        self.pause_started_ticks = pygame.time.get_ticks()
                        for light in self.lights.values():
                            light.is_green = False
                            if light.state == "GREEN":
                                light.set_yellow()
                        if self.track_channel is not None:
                            self.track_channel.pause()
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.press_light('W')
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.press_light('E')
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.press_light('N')
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.press_light('S')
                elif self.state == 'PAUSED':
                    if event.key == pygame.K_SPACE:
                        paused_for = pygame.time.get_ticks() - self.pause_started_ticks
                        self.start_ticks += paused_for
                        self.beat_manager.start_ticks += paused_for
                        self.beat_manager.last_beat_time += paused_for
                        self.rhythm_manager.start_ticks += paused_for
                        self.rhythm_manager.last_beat_time += paused_for
                        if self.track_channel is not None:
                            self.track_channel.unpause()
                        self.pause_started_ticks = 0
                        self.state = 'PLAYING'
                elif self.state == 'GAMEOVER':
                    if event.key == pygame.K_RETURN:
                        self.save_leaderboard_entry()
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.save_leaderboard_entry()
                        self.state = 'START'
                    elif (
                        event.unicode.isascii()
                        and event.unicode.isalnum()
                        and len(self.player_name) < 5
                    ):
                        self.player_name = (
                            self.player_name + event.unicode
                        ).upper()[:5]
                    elif event.key == pygame.K_m:
                        if self.track_channel is not None:
                            self.track_channel.stop()
                        self.state = 'START'

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.state == 'START':
                    if self.new_game_button.collidepoint(pos):
                        self.state = 'LEVEL_SELECT'
                    elif self.custom_mode_button.collidepoint(pos):
                        self.choose_custom_track()
                    elif self.leaderboard_button.collidepoint(pos):
                        self.state = 'LEADERBOARD'
                elif self.state == 'LEVEL_SELECT':
                    if self.back_button.collidepoint(pos):
                        self.stop_preview()
                        self.state = 'START'
                    else:
                        for index, button in enumerate(self.level_buttons):
                            if button.collidepoint(pos):
                                self.selected_level_index = index
                                self.select_preset(index)
                                break
                elif self.state == 'GAMEOVER':
                    if self.restart_button.collidepoint(pos):
                        self.reset_game()
                    elif self.menu_button.collidepoint(pos):
                        self.save_leaderboard_entry()
                        self.state = 'START'
                elif self.state == 'PLAYING':
                    for key, light in self.lights.items():
                        if light.rect.collidepoint(pos):
                            self.press_light(key)

        return True

    def press_light(self, direction):
        current_time = pygame.time.get_ticks()
        beat_time = self.rhythm_manager.nearest_beat_time(current_time)
        offset_ms = current_time - beat_time
        window_ms = self.rhythm_manager.input_window_ms(beat_time)
        on_beat = abs(offset_ms) <= window_ms
        points = ON_BEAT_SCORE if on_beat else OFF_BEAT_SCORE
        self.score += points
        self.score_popup = f"+{points}"
        self.score_popup_until = current_time + 1200
        if on_beat:
            self.on_beat_streak = getattr(self, "on_beat_streak", 0) + 1
            self.rhythm_feedback = (
                f"+{ON_BEAT_SCORE} ON BEAT  STREAK x{self.on_beat_streak}"
            )
        else:
            self.on_beat_streak = 0
            self.rhythm_feedback = f"+{OFF_BEAT_SCORE} OFF BEAT"
        self.rhythm_feedback_until = (
            current_time + 1200
        )

        self.activate_lane(direction)
        if on_beat:
            on_beat_lanes = getattr(self, "on_beat_served_lanes", set())
            on_beat_lanes.add(direction)
            self.on_beat_served_lanes = on_beat_lanes

    def activate_lane(self, direction):
        self.served_lanes.add(direction)
        self.control_direction = direction
        for other_direction, other_light in self.lights.items():
            if other_direction != direction and other_light.state == "GREEN":
                other_light.set_yellow()
        light = self.lights[direction]
        light.set_green(self.lane_green_duration_ms(direction))

    def lane_green_duration_ms(self, direction):
        queued_vehicles = [
            vehicle
            for vehicle in self.vehicles
            if vehicle.approach_direction == direction
            and not vehicle.passed_stop_line
        ]
        minimum_duration = max(
            1800,
            math.ceil(MIN_GREEN_BEATS * self.beat_manager.interval),
        )
        if not queued_vehicles:
            return minimum_duration

        def distance_to_stop_line(vehicle):
            if direction == "W":
                return max(0, vehicle.stop_x - vehicle.x - vehicle.width)
            if direction == "E":
                return max(0, vehicle.x - vehicle.stop_x)
            if direction == "N":
                return max(0, vehicle.stop_y - vehicle.y - vehicle.height)
            return max(0, vehicle.y - vehicle.stop_y)

        farthest_car = max(queued_vehicles, key=distance_to_stop_line)
        distance_to_clear = (
            distance_to_stop_line(farthest_car)
            + ROAD_WIDTH * 2
            + farthest_car.width
        )
        speed = farthest_car.speed * FPS * self.vehicle_speed_scale()
        clearance_duration = math.ceil(distance_to_clear / speed * 1000)
        return max(
            minimum_duration,
            clearance_duration + GREEN_CLEARANCE_BUFFER_MS,
        )

    def check_collisions(self):
        for i in range(len(self.vehicles)):
            for j in range(i + 1, len(self.vehicles)):
                first = self.vehicles[i]
                second = self.vehicles[j]
                if (
                    first.inside_intersection
                    and second.inside_intersection
                    and first.passed_stop_line
                    and second.passed_stop_line
                    and first.approach_direction != second.approach_direction
                    and first.direction != second.direction
                    and first.collides_with(second)
                    and not first.has_collided
                    and not second.has_collided
                ):
                    first.has_collided = True
                    second.has_collided = True
                    self.finish_game("COLLISION")

    def vehicle_is_blocked_by_queue(self, vehicle):
        if vehicle.passed_stop_line:
            return False

        for other in self.vehicles:
            if (
                other is vehicle
                or other.approach_direction != vehicle.approach_direction
                or other.passed_stop_line
                or not other.stopped
            ):
                continue
            if vehicle.approach_direction == 'W':
                if other.x > vehicle.x and other.x - vehicle.x < 42:
                    return True
            elif vehicle.approach_direction == 'E':
                if other.x < vehicle.x and vehicle.x - other.x < 42:
                    return True
            elif vehicle.approach_direction == 'N':
                if other.y > vehicle.y and other.y - vehicle.y < 42:
                    return True
            elif vehicle.approach_direction == 'S':
                if other.y < vehicle.y and vehicle.y - other.y < 42:
                    return True
        return False

    def update_lane_patience(self, beat_happened):
        served_lanes = getattr(self, "served_lanes", set())
        queued_by_lane = {
            direction: [
                vehicle
                for vehicle in self.vehicles
                if vehicle.approach_direction == direction
                and not vehicle.passed_stop_line
            ]
            for direction in DIRECTIONS
        }
        for direction, queued_vehicles in queued_by_lane.items():
            if not queued_vehicles:
                self.lane_wait_beats[direction] = 0
                self.lane_patience[direction] = 0
                served_lanes.discard(direction)
                getattr(self, "on_beat_served_lanes", set()).discard(direction)

        if not beat_happened:
            return

        for direction in DIRECTIONS:
            if not queued_by_lane[direction]:
                continue
            waiting = False
            for vehicle in queued_by_lane[direction]:
                if vehicle.stopped:
                    waiting = True
                    break

            if direction in served_lanes:
                relief = 4 if direction in getattr(
                    self,
                    "on_beat_served_lanes",
                    set(),
                ) else 2
                self.lane_wait_beats[direction] = max(
                    0,
                    self.lane_wait_beats[direction] - relief,
                )
            elif (
                self.control_direction == direction
                and self.lights[direction].is_green
            ):
                self.lane_wait_beats[direction] = max(
                    0,
                    self.lane_wait_beats[direction] - 2,
                )
            elif waiting:
                self.lane_wait_beats[direction] += 1
            else:
                self.lane_wait_beats[direction] = max(
                    0,
                    self.lane_wait_beats[direction] - 1,
                )

            self.lane_patience[direction] = min(
                100,
                round(
                    self.lane_wait_beats[direction]
                    * 100
                    / self.patience_limit_beats
                ),
            )
            light = self.lights[direction]
            if self.lane_patience[direction] >= 90 and light.state == "RED":
                light.set_yellow(max(700, round(self.beat_manager.interval)))
            if self.lane_patience[direction] >= 100:
                self.finish_game("PATIENCE")

        served_lanes.clear()
        getattr(self, "on_beat_served_lanes", set()).clear()
        most_patient_lane = max(DIRECTIONS, key=lambda lane: self.lane_patience[lane])
        if self.lane_patience[most_patient_lane] > 0:
            self.control_direction = most_patient_lane
        else:
            queued_counts = {
                direction: len(queued_by_lane[direction])
                for direction in DIRECTIONS
            }
            busiest_lane = max(queued_counts, key=queued_counts.get)
            self.control_direction = (
                busiest_lane if queued_counts[busiest_lane] else None
            )

    def spawn_beat_queue(self, event, event_index=None):
        if event.hold_id is not None:
            spawn_direction = DIRECTIONS[
                (self.lane_start_offset + event.hold_id) % len(DIRECTIONS)
            ]
            self.active_hold_direction = spawn_direction
            self.active_hold_until = (
                self.start_ticks + round(event.hold_end * 1000)
                if event.hold_end is not None
                else 0
            )
        else:
            sequence_index = (
                self.beat_manager.beat_count - 1
                if event_index is None
                else event_index
            )
            spawn_direction = DIRECTIONS[
                (
                    self.lane_start_offset
                    + sequence_index
                )
                % len(DIRECTIONS)
            ]
        most_patient_lane = max(
            DIRECTIONS,
            key=lambda lane: self.lane_patience[lane],
        )
        self.control_direction = (
            most_patient_lane
            if self.lane_patience[most_patient_lane] > 0
            else spawn_direction
        )

        cars_to_spawn = max(
            event.queue_size,
            self.traffic_forecast.cars_per_beat,
        )
        for _ in range(cars_to_spawn):
            queued = sum(
                1 for vehicle in self.vehicles
                if vehicle.approach_direction == spawn_direction and not vehicle.passed_stop_line
            )
            self.vehicles.append(Vehicle(spawn_direction, queued))

    def update_traffic_preview(self, elapsed, horizon=60, preview_limit=3):
        self.traffic_lane_counts = {direction: 0 for direction in DIRECTIONS}
        self.traffic_preview = []
        if not self.track_events:
            return

        first_event_index = self.beat_manager.next_event_index
        for event_index in range(first_event_index, len(self.track_events)):
            event = self.track_events[event_index]
            if event.time >= elapsed + horizon:
                break
            if event.time < elapsed:
                continue

            if event.hold_id is not None:
                direction = DIRECTIONS[
                    (self.lane_start_offset + event.hold_id) % len(DIRECTIONS)
                ]
            else:
                direction = DIRECTIONS[
                    (self.lane_start_offset + event_index) % len(DIRECTIONS)
                ]
            cars_to_spawn = max(
                event.queue_size,
                self.traffic_forecast.cars_per_beat,
            )
            self.traffic_lane_counts[direction] += cars_to_spawn
            if len(self.traffic_preview) < preview_limit:
                self.traffic_preview.append(
                    (direction, cars_to_spawn, event.time - elapsed)
                )

    def update(self):
        if self.state == "LOADING":
            self.process_pending_load()
            return
        if self.state != 'PLAYING':
            return

        current_ticks = pygame.time.get_ticks()
        elapsed_seconds = (current_ticks - self.start_ticks) / 1000
        self.traffic_forecast = analyze_upcoming_section(
            self.track_events or [],
            elapsed_seconds,
            self.track_bpm,
            horizon=60,
        )
        self.patience_limit_beats = self.traffic_forecast.patience_beats * 2
        self.update_traffic_preview(elapsed_seconds)
        if self.active_hold_direction is not None and current_ticks >= self.active_hold_until:
            self.active_hold_direction = None
            if self.control_direction in self.lights:
                most_patient_lane = max(
                    DIRECTIONS,
                    key=lambda lane: self.lane_patience[lane],
                )
                if self.lane_patience[most_patient_lane] > 0:
                    self.control_direction = most_patient_lane
                else:
                    queued_counts = {
                        direction: sum(
                            1 for vehicle in self.vehicles
                            if vehicle.approach_direction == direction
                        )
                        for direction in DIRECTIONS
                    }
                    self.control_direction = max(
                        queued_counts,
                        key=queued_counts.get,
                    )
        remaining_seconds = self.game_duration - elapsed_seconds
        self.time_left = max(0, math.ceil(remaining_seconds))
        if (
            0 < remaining_seconds <= 2
            and self.track_channel is not None
            and not self.track_fading_out
        ):
            self.track_channel.fadeout(round(remaining_seconds * 1000))
            self.track_fading_out = True

        if remaining_seconds <= 0:
            self.score += COMPLETION_BONUS
            self.finish_game("TIME")
            return

        self.beat_manager.update()
        self.rhythm_manager.update()
        if (
            self.rhythm_manager.happened_events
            and getattr(self, "metronome_enabled", False)
        ):
            self.play_metronome_tick()
        for event, event_index in zip(
            self.beat_manager.happened_events,
            self.beat_manager.happened_event_indices,
        ):
            self.spawn_beat_queue(event, event_index)
        for light in self.lights.values():
            light.update()

        for v in self.vehicles[:]:
            light_state = self.lights[v.approach_direction].state
            blocked = self.vehicle_is_blocked_by_queue(v)
            v.update(
                light_state,
                move_on_beat=self.beat_manager.is_beat_frame,
                blocked=blocked,
                speed_scale=self.vehicle_speed_scale(),
            )

            has_exited = (
                v.direction == 'W' and v.x > GAME_WIDTH + v.width
                or v.direction == 'E' and v.x < -v.width
                or v.direction == 'N' and v.y > SCREEN_HEIGHT + v.height
                or v.direction == 'S' and v.y < -v.height
            )
            if has_exited:
                self.vehicles.remove(v)

        self.check_collisions()
        self.update_lane_patience(self.beat_manager.is_beat_frame)
        if self.state == 'GAMEOVER' and self.track_channel is not None:
            self.track_channel.stop()

    def vehicle_speed_scale(self):
        highest_patience = max(self.lane_patience.values())
        return max(0.65, 1 - max(0, highest_patience - 65) * 0.01)

    def draw_city(self):
        self.screen.fill(COLOR_BG)
        for x, y, width, height, color in self.city_buildings:
            building = pygame.Rect(x, y, width, height)
            pygame.draw.rect(
                self.screen,
                (24, 76, 48),
                building.move(5, 6),
                border_radius=5,
            )
            pygame.draw.rect(self.screen, color, building, border_radius=4)
            pygame.draw.rect(self.screen, (105, 110, 112), building, 1, border_radius=4)
            pygame.draw.rect(self.screen, (50, 56, 59), (x + 8, y + 6, width - 16, 5))
            for window_y in range(y + 12, y + height - 8, 20):
                for window_x in range(x + 10, x + width - 6, 18):
                    window_color = (164, 151, 105) if (window_x // 18 + window_y // 20) % 3 else (92, 111, 102)
                    pygame.draw.rect(
                        self.screen,
                        window_color,
                        (window_x, window_y, 7, 9),
                        border_radius=2,
                    )
            pygame.draw.rect(
                self.screen,
                (52, 48, 42),
                (x + width // 2 - 7, y + height - 22, 14, 22),
                border_radius=2,
            )

        trees = (
            (42, 205, 15), (270, 165, 13), (748, 202, 16),
            (74, 405, 15), (272, 435, 14), (748, 395, 17),
        )
        for x, y, size in trees:
            pygame.draw.ellipse(
                self.screen,
                (25, 99, 52),
                (x - size - 5, y + size - 1, size * 2 + 10, 9),
            )
            pygame.draw.rect(
                self.screen,
                (103, 76, 47),
                (x - 3, y + 4, 6, size + 8),
                border_radius=2,
            )
            pygame.draw.circle(self.screen, (23, 94, 44), (x, y), size + 3)
            pygame.draw.circle(self.screen, (43, 139, 62), (x - 3, y - 3), size)
            pygame.draw.circle(
                self.screen,
                (83, 169, 75),
                (x - size // 3, y - size // 2),
                max(3, size // 3),
            )

    def draw_button(self, rect, label, fill_color):
        pygame.draw.rect(self.screen, fill_color, rect, border_radius=9)
        pygame.draw.rect(self.screen, COLOR_CURB, rect, 2, border_radius=9)
        text = self.font_score.render(label, True, COLOR_WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_lane_highlights(self):
        hit_window = self.rhythm_manager.is_on_beat()
        glow = COLOR_PINK if hit_window else COLOR_PURPLE
        glow_surface = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        lane_edges = (
            ((CENTER_X - ROAD_WIDTH // 2, 0),
             (CENTER_X - ROAD_WIDTH // 2, CENTER_Y - ROAD_WIDTH // 2 - 12)),
            ((CENTER_X + ROAD_WIDTH // 2, 0),
             (CENTER_X + ROAD_WIDTH // 2, CENTER_Y - ROAD_WIDTH // 2 - 12)),
            ((0, CENTER_Y - ROAD_WIDTH // 2),
             (CENTER_X - ROAD_WIDTH // 2 - 12, CENTER_Y - ROAD_WIDTH // 2)),
            ((0, CENTER_Y + ROAD_WIDTH // 2),
             (CENTER_X - ROAD_WIDTH // 2 - 12, CENTER_Y + ROAD_WIDTH // 2)),
            ((CENTER_X - ROAD_WIDTH // 2, CENTER_Y + ROAD_WIDTH // 2 + 12),
             (CENTER_X - ROAD_WIDTH // 2, SCREEN_HEIGHT)),
            ((CENTER_X + ROAD_WIDTH // 2, CENTER_Y + ROAD_WIDTH // 2 + 12),
             (CENTER_X + ROAD_WIDTH // 2, SCREEN_HEIGHT)),
            ((CENTER_X + ROAD_WIDTH // 2 + 12, CENTER_Y - ROAD_WIDTH // 2),
             (GAME_WIDTH, CENTER_Y - ROAD_WIDTH // 2)),
            ((CENTER_X + ROAD_WIDTH // 2 + 12, CENTER_Y + ROAD_WIDTH // 2),
             (GAME_WIDTH, CENTER_Y + ROAD_WIDTH // 2)),
        )
        for first, second in lane_edges:
            glow_layers = (
                ((12, 12), (7, 22), (3, 60))
                if not hit_window
                else ((14, 35), (9, 90), (3, 220))
            )
            for width, alpha in glow_layers:
                pygame.draw.line(
                    glow_surface,
                    (*glow, alpha),
                    first,
                    second,
                    width,
                )
        self.screen.blit(glow_surface, (0, 0))

    def draw_lane_guides(self):
        labels = (
            ("W", "A  WEST", pygame.Rect(12, 201, 92, 26)),
            ("E", "D  EAST", pygame.Rect(GAME_WIDTH - 104, 201, 92, 26)),
            ("N", "W  NORTH", pygame.Rect(CENTER_X + 77, 110, 92, 26)),
            ("S", "S  SOUTH", pygame.Rect(CENTER_X - 169, 464, 92, 26)),
        )
        for direction, label, rect in labels:
            active = direction == self.control_direction
            color = COLOR_YELLOW if active else COLOR_WHITE
            fill = (61, 68, 55) if active else (38, 42, 45)
            pygame.draw.rect(self.screen, fill, rect, border_radius=6)
            pygame.draw.rect(self.screen, color, rect, 2 if active else 1, border_radius=6)
            text = self.font.render(label, True, color)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_driver_warnings(self):
        for direction in DIRECTIONS:
            patience = self.lane_patience[direction]
            if patience < 50:
                continue
            waiting = [
                vehicle
                for vehicle in self.vehicles
                if vehicle.approach_direction == direction
                and vehicle.stopped
                and not vehicle.passed_stop_line
                and vehicle.get_rect().colliderect(self.screen.get_rect())
            ]
            if not waiting:
                continue
            vehicle = max(
                waiting,
                key=lambda car: (
                    car.x if direction == "W"
                    else -car.x if direction == "E"
                    else car.y if direction == "N"
                    else -car.y
                ),
            )
            speech = (
                ("HONK!", "HEY!", "MOVE!")
                if patience < 70
                else ("MOVE!", "NOW!", "WAITING!")
                if patience < 90
                else ("HELP!", "OPEN!", "AGAIN!")
            )
            text = speech[
                (pygame.time.get_ticks() // 700 + int(direction in ("E", "S")))
                % len(speech)
            ]
            color = COLOR_RED if patience >= 90 else (160, 48, 38)
            car_rect = vehicle.get_rect()
            bubble_rect = pygame.Rect(
                car_rect.centerx - 31,
                car_rect.top - 28,
                62,
                22,
            )
            bubble_rect.clamp_ip(self.screen.get_rect())
            pygame.draw.polygon(
                self.screen,
                COLOR_WHITE,
                (
                    (bubble_rect.centerx - 4, bubble_rect.bottom - 1),
                    (bubble_rect.centerx + 5, bubble_rect.bottom - 1),
                    (car_rect.centerx, car_rect.top + 1),
                ),
            )
            pygame.draw.rect(self.screen, COLOR_WHITE, bubble_rect, border_radius=6)
            pygame.draw.rect(self.screen, color, bubble_rect, 2, border_radius=6)
            text_surface = self.font.render(text, True, color)
            self.screen.blit(text_surface, text_surface.get_rect(center=bubble_rect.center))

    def draw_pressure_warning(self):
        direction = max(
            DIRECTIONS,
            key=lambda lane: self.lane_patience[lane],
        )
        patience = self.lane_patience[direction]
        if patience < 75:
            return

        lane_names = {"N": "NORTH", "E": "EAST", "S": "SOUTH", "W": "WEST"}
        pulse = (math.sin(pygame.time.get_ticks() / 100) + 1) / 2
        fill = (75 + round(pulse * 65), 25, 30)
        warning_rect = pygame.Rect(128, 12, 544, 48)
        pygame.draw.rect(self.screen, fill, warning_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_RED, warning_rect, 3, border_radius=8)
        message = (
            f"DANGER: {lane_names[direction]} {patience}% - "
            f"OPTIONAL: OPEN {lane_names[direction]}"
        )
        warning_text = self.font.render(message, True, COLOR_WHITE)
        self.screen.blit(
            warning_text,
            warning_text.get_rect(center=warning_rect.center),
        )

    def draw_compact_hud(self):
        current_time = pygame.time.get_ticks()

        pygame.draw.rect(
            self.screen,
            (8, 7, 12),
            pygame.Rect(0, 0, GAME_WIDTH, 48),
        )
        pygame.draw.line(
            self.screen,
            COLOR_PURPLE,
            (0, 47),
            (GAME_WIDTH, 47),
            2,
        )

        track_text = self.font.render(
            f"{self.track_name[:24]}  |  {int(self.rhythm_manager.bpm)} BPM",
            True,
            COLOR_YELLOW,
        )
        self.screen.blit(track_text, (18, 15))

        lookahead_ms = 900
        hit_line_x = 500
        pixels_per_side = 100
        rhythm_track = pygame.Rect(390, 13, 220, 18)
        pygame.draw.rect(self.screen, COLOR_BLACK, rhythm_track, border_radius=9)
        pygame.draw.rect(self.screen, COLOR_PURPLE, rhythm_track, 2, border_radius=9)
        on_beat = self.rhythm_manager.is_on_beat()
        hit_line_color = COLOR_GREEN if on_beat else COLOR_PINK
        zone_width = max(
            3,
            round(
                min(
                    lookahead_ms,
                    self.rhythm_manager.input_window_ms(),
                )
                / lookahead_ms
                * pixels_per_side
            ),
        )
        zone_surface = pygame.Surface(
            (zone_width * 2 + 1, rhythm_track.height),
            pygame.SRCALPHA,
        )
        zone_surface.fill((*hit_line_color, 100 if on_beat else 45))
        self.screen.blit(
            zone_surface,
            (hit_line_x - zone_width, rhythm_track.y),
        )
        pygame.draw.line(
            self.screen,
            hit_line_color,
            (hit_line_x, 7),
            (hit_line_x, 38),
            3,
        )
        for bracket_x in (hit_line_x - zone_width, hit_line_x + zone_width):
            pygame.draw.line(
                self.screen,
                hit_line_color,
                (bracket_x, 9),
                (bracket_x, 35),
                2 if on_beat else 1,
            )

        for offset in self.rhythm_manager.beat_offsets(
            current_time,
            lookahead_ms,
        ):
            marker_x = round(
                hit_line_x + offset / lookahead_ms * pixels_per_side
            )
            marker_color = (
                COLOR_YELLOW if abs(offset) <= 120 else COLOR_PURPLE
            )
            pygame.draw.circle(self.screen, marker_color, (marker_x, 22), 5)

        time_text = self.font.render(
            f"{self.time_left}s  |  M:{'ON' if self.metronome_enabled else 'OFF'}",
            True,
            COLOR_WHITE,
        )
        self.screen.blit(time_text, time_text.get_rect(top=15, right=782))

        pygame.draw.rect(
            self.screen,
            (8, 7, 12),
            pygame.Rect(0, SCREEN_HEIGHT - 42, GAME_WIDTH, 42),
        )

        score_surface = self.font_large.render(
            f"SCORE  {self.score}",
            True,
            COLOR_WHITE,
        )
        self.screen.blit(score_surface, (18, 563))

        best_surface = self.font.render(
            f"BEST  {getattr(self, 'high_score', 0)}",
            True,
            COLOR_YELLOW,
        )
        self.screen.blit(best_surface, best_surface.get_rect(top=570, right=782))

        if current_time < getattr(self, "score_popup_until", 0):
            remaining = (
                getattr(self, "score_popup_until", current_time) - current_time
            ) / 1200
            alpha = max(0, min(255, round(remaining * 255)))
            popup = self.font_score.render(
                getattr(self, "score_popup", ""),
                True,
                COLOR_PINK,
            )
            popup.set_alpha(alpha)
            popup_x = 20
            popup_y = 530 - round((1 - remaining) * 18)
            self.screen.blit(popup, (popup_x, popup_y))

        control_keys = {"N": "W", "E": "D", "S": "S", "W": "A"}
        lane_names = {"N": "N", "E": "E", "S": "S", "W": "W"}
        start_x = 340
        for index, direction in enumerate(DIRECTIONS):
            patience = self.lane_patience[direction]
            active = direction == self.control_direction
            label_x = start_x + index * 82
            label_color = COLOR_YELLOW if active else COLOR_WHITE
            label = self.font.render(
                f"{lane_names[direction]}-{control_keys[direction]}  {patience}%",
                True,
                label_color,
            )
            self.screen.blit(label, (label_x, 566))
            bar = pygame.Rect(label_x, 585, 66, 5)
            pygame.draw.rect(self.screen, (70, 40, 82), bar, border_radius=2)
            if patience:
                fill = pygame.Rect(
                    bar.x,
                    bar.y,
                    round(bar.width * min(100, patience) / 100),
                    bar.height,
                )
                pygame.draw.rect(
                    self.screen,
                    COLOR_PINK if patience >= 90 else COLOR_PURPLE,
                    fill,
                    border_radius=2,
                )

        if current_time < getattr(self, "rhythm_feedback_until", 0):
            feedback = self.font.render(
                self.rhythm_feedback,
                True,
                COLOR_PINK if self.rhythm_feedback.startswith("-") else COLOR_YELLOW,
            )
            self.screen.blit(feedback, feedback.get_rect(center=(500, 535)))

    def draw(self):
        self.draw_city()

        # Wegen en stoepranden
        h_road_rect = pygame.Rect(0, CENTER_Y - (ROAD_WIDTH // 2), GAME_WIDTH, ROAD_WIDTH)
        v_road_rect = pygame.Rect(CENTER_X - (ROAD_WIDTH // 2), 0, ROAD_WIDTH, SCREEN_HEIGHT)

        curb_size = 6
        pygame.draw.rect(self.screen, COLOR_CURB, h_road_rect.inflate(0, curb_size * 2))
        pygame.draw.rect(self.screen, COLOR_CURB, v_road_rect.inflate(curb_size * 2, 0))

        pygame.draw.rect(self.screen, COLOR_ROAD, h_road_rect)
        pygame.draw.rect(self.screen, COLOR_ROAD, v_road_rect)

        # Dashed center lines keep the intersection open for turning traffic.
        stripe_color = (172, 169, 155)
        intersection_start = CENTER_X - ROAD_WIDTH // 2
        intersection_end = CENTER_X + ROAD_WIDTH // 2
        for first in range(0, intersection_start - 22, 30):
            pygame.draw.line(
                self.screen,
                COLOR_YELLOW,
                (first, CENTER_Y),
                (first + 16, CENTER_Y),
                3,
            )
        for first in range(intersection_end + 8, GAME_WIDTH, 30):
            pygame.draw.line(
                self.screen,
                COLOR_YELLOW,
                (first, CENTER_Y),
                (first + 16, CENTER_Y),
                3,
            )
        for first in range(0, CENTER_Y - ROAD_WIDTH // 2 - 22, 30):
            pygame.draw.line(
                self.screen,
                COLOR_YELLOW,
                (CENTER_X, first),
                (CENTER_X, first + 16),
                3,
            )
        for first in range(CENTER_Y + ROAD_WIDTH // 2 + 8, SCREEN_HEIGHT, 30):
            pygame.draw.line(
                self.screen,
                COLOR_YELLOW,
                (CENTER_X, first),
                (CENTER_X, first + 16),
                3,
            )

        for offset in range(0, ROAD_WIDTH, 12):
            pygame.draw.rect(
                self.screen,
                stripe_color,
                (intersection_start + offset, CENTER_Y - ROAD_WIDTH // 2 - 8, 6, 8),
            )
            pygame.draw.rect(
                self.screen,
                stripe_color,
                (intersection_start + offset, CENTER_Y + ROAD_WIDTH // 2, 6, 8),
            )
            pygame.draw.rect(
                self.screen,
                stripe_color,
                (intersection_start - 8, CENTER_Y - ROAD_WIDTH // 2 + offset, 8, 6),
            )
            pygame.draw.rect(
                self.screen,
                stripe_color,
                (intersection_end, CENTER_Y - ROAD_WIDTH // 2 + offset, 8, 6),
            )

        pygame.draw.line(
            self.screen,
            COLOR_WHITE,
            (CENTER_X - ROAD_WIDTH // 2, CENTER_Y - ROAD_WIDTH // 2 - 25),
            (CENTER_X, CENTER_Y - ROAD_WIDTH // 2 - 25),
            3,
        )
        pygame.draw.line(
            self.screen,
            COLOR_WHITE,
            (CENTER_X, CENTER_Y + ROAD_WIDTH // 2 + 25),
            (CENTER_X + ROAD_WIDTH // 2, CENTER_Y + ROAD_WIDTH // 2 + 25),
            3,
        )
        pygame.draw.line(
            self.screen,
            COLOR_WHITE,
            (CENTER_X - ROAD_WIDTH // 2 - 25, CENTER_Y - ROAD_WIDTH // 2),
            (CENTER_X - ROAD_WIDTH // 2 - 25, CENTER_Y),
            3,
        )
        pygame.draw.line(
            self.screen,
            COLOR_WHITE,
            (CENTER_X + ROAD_WIDTH // 2 + 25, CENTER_Y),
            (CENTER_X + ROAD_WIDTH // 2 + 25, CENTER_Y + ROAD_WIDTH // 2),
            3,
        )

        self.draw_lane_highlights()
        self.draw_lane_guides()

        # Verkeerslichten en voertuigen
        for light in self.lights.values():
            light.draw(self.screen)

        for vehicle in self.vehicles:
            vehicle.draw(
                self.screen,
                glowing=self.lights[vehicle.approach_direction].state == "GREEN",
            )
        self.draw_driver_warnings()
        if self.state in ('PLAYING', 'PAUSED') and self.waveform_layer is not None:
            self.screen.blit(self.waveform_layer, (0, 0))

        self.draw_compact_hud()
        self.draw_pressure_warning()

        if self.state == 'START':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            title = self.font_title.render("TRAFFIC BEAT", True, COLOR_WHITE)
            subtitle = self.font_score.render(
                "TRAFFIC CONTROL + RHYTHM SCORE",
                True,
                COLOR_YELLOW,
            )
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 190)))
            self.screen.blit(subtitle, subtitle.get_rect(center=(GAME_WIDTH // 2, 232)))
            first_time_guide = (
                "1. Open any traffic lane with A/D/W/S or click its light.",
                "2. Keep traffic moving to prevent patience game overs and crashes.",
                "3. Time lane presses to the beat for bonus points.",
            )
            for index, line in enumerate(first_time_guide):
                guide_text = self.font.render(line, True, COLOR_WHITE)
                self.screen.blit(
                    guide_text,
                    guide_text.get_rect(center=(GAME_WIDTH // 2, 282 + index * 23)),
                )
            start_buttons = (
                (self.new_game_button, "NEW GAME", 0),
                (self.custom_mode_button, "CUSTOM MP3", 1),
                (self.leaderboard_button, "LEADERBOARD", 2),
            )
            for button, label, index in start_buttons:
                selected = getattr(self, "start_menu_index", 0) == index
                fill = (102, 48, 126) if selected else (48, 42, 58)
                border = COLOR_PINK if selected else COLOR_CURB
                pygame.draw.rect(self.screen, fill, button, border_radius=9)
                pygame.draw.rect(self.screen, border, button, 2, border_radius=9)
                text = self.font_score.render(label, True, COLOR_WHITE)
                self.screen.blit(text, text.get_rect(center=button.center))
            controls = self.font_card_small.render(
                "ARROWS / W A S D  +  ENTER", True, COLOR_YELLOW
            )
            self.screen.blit(controls, controls.get_rect(center=(GAME_WIDTH // 2, 568)))

        elif self.state == 'LOADING':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            title = self.font_title.render("LOADING", True, COLOR_PINK)
            message = self.font_score.render(
                getattr(self, "loading_message", "PLEASE WAIT"),
                True,
                COLOR_WHITE,
            )
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 265)))
            self.screen.blit(message, message.get_rect(center=(GAME_WIDTH // 2, 310)))
            dots = "." * (1 + ((pygame.time.get_ticks() // 350) % 3))
            dots_text = self.font_score.render(dots, True, COLOR_YELLOW)
            self.screen.blit(dots_text, dots_text.get_rect(center=(GAME_WIDTH // 2, 350)))

        elif self.state == 'LEADERBOARD':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            title = self.font_title.render("HIGHSCORES", True, COLOR_YELLOW)
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 110)))
            entries = getattr(self, "leaderboard", [])
            if not entries:
                empty = self.font_score.render("NO SCORES YET", True, COLOR_WHITE)
                self.screen.blit(empty, empty.get_rect(center=(GAME_WIDTH // 2, 230)))
            else:
                for index, (name, score, track) in enumerate(entries):
                    rank = self.font_card_small.render(
                        f"{index + 1:02d}",
                        True,
                        COLOR_PINK,
                    )
                    details = self.font_card_small.render(
                        f"{name}   {score}   {track}",
                        True,
                        COLOR_WHITE,
                    )
                    row_y = 180 + index * 32
                    self.screen.blit(rank, (180, row_y))
                    self.screen.blit(details, (230, row_y))
            back = self.font_score.render("ESC / M / BACKSPACE", True, COLOR_YELLOW)
            self.screen.blit(back, back.get_rect(center=(GAME_WIDTH // 2, 520)))

        elif self.state == 'LEVEL_SELECT':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            title = self.font_title.render("KIES JE LEVEL", True, COLOR_WHITE)
            self.screen.blit(title, title.get_rect(center=(GAME_WIDTH // 2, 150)))
            selection_hint = self.font.render(
                "P = PREVIEW SONG  |  CLICK / ENTER = PLAY",
                True,
                COLOR_WHITE,
            )
            self.screen.blit(
                selection_hint,
                selection_hint.get_rect(center=(GAME_WIDTH // 2, 198)),
            )

            card_colors = ((61, 84, 66), (69, 82, 72), (67, 76, 80), (82, 78, 66))
            for index, (level, button) in enumerate(zip(PRESET_LEVELS, self.level_buttons)):
                pygame.draw.rect(self.screen, card_colors[index], button, border_radius=12)
                selected = index == self.selected_level_index
                border = COLOR_YELLOW if selected else COLOR_CURB
                pygame.draw.rect(
                    self.screen,
                    border,
                    button,
                    3 if selected else 2,
                    border_radius=12,
                )
                name = self.font_card_title.render(level["name"], True, COLOR_WHITE)
                song = self.font_card_small.render(level["song"], True, COLOR_YELLOW)
                tempo_text = f'{min(MAX_TRAFFIC_BPM, level["bpm"])} BPM'
                tempo = self.font_card_small.render(tempo_text, True, COLOR_WHITE)
                difficulty = self.font_card_small.render(level["difficulty"].upper(), True, COLOR_BEAT)
                name_rect = name.get_rect(center=(button.centerx, button.y + 38))
                song_rect = song.get_rect(center=(button.centerx, button.y + 72))
                tempo_rect = tempo.get_rect(center=(button.centerx, button.y + 104))
                difficulty_rect = difficulty.get_rect(center=(button.centerx, button.y + 133))
                if name_rect.width > button.width - 18:
                    name = self.font_card_small.render(level["name"], True, COLOR_WHITE)
                    name_rect = name.get_rect(center=(button.centerx, button.y + 38))
                self.screen.blit(name, name_rect)
                self.screen.blit(song, song_rect)
                self.screen.blit(tempo, tempo_rect)
                self.screen.blit(
                    difficulty,
                    difficulty_rect,
                )
                self.draw_button(
                    pygame.Rect(button.x + 22, button.bottom - 38, button.width - 44, 30),
                    "PLAY",
                    (53, 69, 57),
                )
            self.draw_button(self.back_button, "BACK", (62, 69, 64))

        elif self.state == 'PAUSED':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            pause_text = self.font_large.render("PAUSED", True, COLOR_WHITE)
            resume_text = self.font.render("Druk op SPACE om verder te gaan", True, COLOR_WHITE)
            self.screen.blit(
                pause_text,
                pause_text.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)),
            )
            self.screen.blit(
                resume_text,
                resume_text.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)),
            )

        elif self.state == 'GAMEOVER':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill(COLOR_OVERLAY)
            self.screen.blit(overlay, (0, 0))
            if self.game_over_reason == "PATIENCE":
                over_label = "GAME OVER: PATIENCE"
            elif self.game_over_reason == "COLLISION":
                over_label = "GAME OVER: COLLISION"
            elif self.game_over_reason == "TIME":
                over_label = "TRACK COMPLETE: TIME (+1000)"
            else:
                over_label = "TRACK COMPLETE"
            over_text = self.font_large.render(over_label, True, COLOR_RED)
            song_text = self.font.render(self.track_name[:35], True, COLOR_WHITE)
            self.screen.blit(
                over_text,
                over_text.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 - 45)),
            )
            self.screen.blit(
                song_text,
                song_text.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2)),
            )
            result_text = self.font_score.render(
                f"Score: {self.score}",
                True,
                COLOR_WHITE,
            )
            self.screen.blit(
                result_text,
                result_text.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT // 2 + 42)),
            )
            name_label = self.font_card_small.render("NAME", True, COLOR_PINK)
            name_value = self.font_score.render(
                getattr(self, "player_name", "PLAYER"),
                True,
                COLOR_YELLOW,
            )
            self.screen.blit(name_label, name_label.get_rect(center=(GAME_WIDTH // 2 - 80, 392)))
            name_box = pygame.Rect(GAME_WIDTH // 2 - 35, 375, 170, 34)
            pygame.draw.rect(self.screen, (30, 20, 38), name_box, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_PINK, name_box, 2, border_radius=4)
            self.screen.blit(name_value, name_value.get_rect(center=name_box.center))
            enter_hint = self.font_card_small.render(
                "TYPE UP TO 5 CHARS  ENTER = SAVE",
                True,
                COLOR_WHITE,
            )
            self.screen.blit(enter_hint, enter_hint.get_rect(center=(GAME_WIDTH // 2, 452)))
            pygame.draw.rect(self.screen, (70, 70, 70), self.restart_button, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_WHITE, self.restart_button, 2, border_radius=6)
            restart_text = self.font.render("RETRY", True, COLOR_WHITE)
            self.screen.blit(restart_text, restart_text.get_rect(center=self.restart_button.center))
            pygame.draw.rect(self.screen, (48, 42, 58), self.menu_button, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_PINK, self.menu_button, 2, border_radius=6)
            menu_text = self.font.render("MENU (ESC)", True, COLOR_YELLOW)
            self.screen.blit(
                menu_text,
                menu_text.get_rect(center=self.menu_button.center),
            )

        if self.status_message and pygame.time.get_ticks() < self.status_until:
            status = self.font.render(self.status_message[:78], True, COLOR_YELLOW)
            self.screen.blit(status, status.get_rect(center=(GAME_WIDTH // 2, SCREEN_HEIGHT - 18)))
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