from array import array
import math
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from index import BeatManager, Game, PRESET_LEVELS, Vehicle
from music import (
    BeatEvent,
    _estimate_bpm_and_offset,
    _fill_traffic_gaps,
    analyze_track,
    analyze_upcoming_section,
    extract_waveform,
    make_preset_events,
    make_preset_sound,
    make_rhythm_events,
)


class RhythmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_track_tempo_is_capped_at_160_bpm(self):
        game = Game.__new__(Game)
        rhythm_events = make_rhythm_events(220, 20)
        bpm, normalized_events = game.normalize_track_timing(
            220,
            rhythm_events,
            20,
        )
        self.assertEqual(bpm, 160)
        self.assertAlmostEqual(
            normalized_events[1].time - normalized_events[0].time,
            60 / 160,
        )

    def test_leaderboard_saves_a_five_letter_name(self):
        game = Game.__new__(Game)
        game.score_saved = False
        game.player_name = "AB12Z"
        game.score = 1250
        game.track_name = "Test"
        game.leaderboard = []
        with tempfile.TemporaryDirectory() as directory:
            game.leaderboard_file = os.path.join(directory, "leaderboard.txt")
            game.save_leaderboard_entry()
            with open(game.leaderboard_file, "r", encoding="utf-8") as score_file:
                self.assertEqual(score_file.read().strip(), "AB12Z|1250|Test")

    def test_leaderboard_save_failure_preserves_file_and_can_be_retried(self):
        game = Game.__new__(Game)
        game.score_saved = False
        game.player_name = "NEW"
        game.score = 1000
        game.track_name = "New track"
        game.leaderboard = [("OLD", 500, "Old track")]
        statuses = []
        game.show_status = statuses.append

        with tempfile.TemporaryDirectory() as directory:
            game.leaderboard_file = os.path.join(directory, "leaderboard.txt")
            with open(game.leaderboard_file, "w", encoding="utf-8") as score_file:
                score_file.write("OLD|500|Old track\n")

            with patch("index.os.replace", side_effect=OSError("file is locked")):
                game.save_leaderboard_entry()

            self.assertFalse(game.score_saved)
            self.assertEqual(game.leaderboard, [("OLD", 500, "Old track")])
            with open(game.leaderboard_file, "r", encoding="utf-8") as score_file:
                self.assertEqual(score_file.read(), "OLD|500|Old track\n")
            self.assertEqual(os.listdir(directory), ["leaderboard.txt"])
            self.assertTrue(statuses)

            game.save_leaderboard_entry()

            with open(game.leaderboard_file, "r", encoding="utf-8") as score_file:
                self.assertEqual(
                    score_file.read(),
                    "NEW|1000|New track\nOLD|500|Old track\n",
                )
            self.assertTrue(game.score_saved)

    def test_story_preset_uses_full_tempo_and_has_a_hold_section(self):
        events = make_preset_events(140, 30, "normal")
        self.assertAlmostEqual(events[1].time - events[0].time, 60 / 140)
        rhythm_events = make_rhythm_events(140, 30)
        self.assertAlmostEqual(
            rhythm_events[1].time - rhythm_events[0].time,
            60 / 140,
        )
        hold_events = [event for event in events if event.hold_id == 0]
        self.assertEqual(len(hold_events), 8)
        self.assertTrue(all(event.hold_end is not None for event in hold_events))

    def test_preset_traffic_rate_is_capped_at_160_bpm(self):
        events = make_preset_events(220, 2, "normal")

        self.assertAlmostEqual(events[1].time - events[0].time, 60 / 160)

    def test_detected_traffic_rate_is_capped_at_160_bpm(self):
        sample_rate = 22050
        duration = 8
        samples = array("h", [0]) * (sample_rate * duration)
        interval = 60 / 220
        for beat in range(math.ceil(duration / interval)):
            start = round(beat * interval * sample_rate)
            for offset in range(round(sample_rate * 0.06)):
                samples[start + offset] = int(
                    10000 * math.sin(2 * math.pi * 900 * offset / sample_rate)
                )

        events, bpm, _, _, _ = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes()),
            subdivision=2,
        )

        self.assertEqual(bpm, 160)
        self.assertAlmostEqual(events[1].time - events[0].time, 60 / 160, delta=0.01)

    def test_sparse_traffic_events_are_filled_on_the_estimated_bpm_grid(self):
        detected_events = [
            BeatEvent(0.1, 0.8, queue_size=2),
            BeatEvent(1.6, 0.9, queue_size=2),
        ]

        events = _fill_traffic_gaps(detected_events, 120, 0.1, 2.2)

        self.assertEqual(
            [event.time for event in events],
            [0.1, 0.6, 1.1, 1.6],
        )
        self.assertIs(events[0], detected_events[0])
        self.assertIs(events[-1], detected_events[-1])
        self.assertEqual([event.intensity for event in events[1:3]], [0.55, 0.55])

        close_events = [BeatEvent(0.1, 0.8), BeatEvent(0.6, 0.9)]
        short_gap = _fill_traffic_gaps(close_events, 120, 0.1, 1.1)
        self.assertEqual(short_gap, close_events)

    def test_detected_events_at_point_eight_intensity_use_two_car_queues(self):
        sample_rate = 22050
        duration = 6
        samples = array("h", [0]) * (sample_rate * duration)
        for beat in range(12):
            start = round(beat * 0.5 * sample_rate)
            amplitude = 10_000 if beat % 2 == 0 else 8_000
            for offset in range(round(sample_rate * 0.05)):
                samples[start + offset] = int(
                    amplitude * math.sin(2 * math.pi * 900 * offset / sample_rate)
                )

        events, _, _, _, _ = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes())
        )

        self.assertTrue(
            any(
                0.75 <= event.intensity < 0.85 and event.queue_size == 2
                for event in events
            )
        )

    def test_bpm_estimation_aligns_the_beat_grid_to_peak_phase(self):
        bpm, offset = _estimate_bpm_and_offset(
            [0.12, 0.62, 1.12, 1.62, 2.12],
            3,
        )

        self.assertEqual(bpm, 120)
        self.assertAlmostEqual(offset, 0.12, delta=0.01)

    def test_analysis_defaults_to_quarter_note_cues_on_the_quantized_grid(self):
        sample_rate = 22050
        duration = 6
        samples = array("h", [0]) * (sample_rate * duration)
        step_interval = 60 / 140 / 2
        for step in range(math.ceil(duration / step_interval)):
            start = round(step * step_interval * sample_rate)
            for offset in range(round(sample_rate * 0.04)):
                samples[start + offset] = int(
                    10000 * math.sin(2 * math.pi * 900 * offset / sample_rate)
                )

        events, traffic_bpm, used_fallback, rhythm_events, bpm = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes())
        )

        self.assertFalse(used_fallback)
        self.assertAlmostEqual(bpm, 140, delta=5)
        self.assertEqual(traffic_bpm, bpm)
        self.assertAlmostEqual(
            rhythm_events[1].time - rhythm_events[0].time,
            60 / bpm,
            delta=0.03,
        )
        self.assertAlmostEqual(events[1].time - events[0].time, 60 / bpm)

    def test_analysis_filters_weak_transients_from_rhythm_cues(self):
        sample_rate = 22050
        samples = array("h", [0]) * (sample_rate * 6)
        interval = 0.5
        for beat in range(12):
            start = round(beat * interval * sample_rate)
            amplitude = 10_000 if beat % 3 == 0 else 2_500
            for offset in range(round(sample_rate * 0.05)):
                samples[start + offset] = int(
                    amplitude * math.sin(2 * math.pi * 900 * offset / sample_rate)
                )

        _, _, used_fallback, rhythm_events, _ = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes())
        )

        self.assertFalse(used_fallback)
        self.assertGreater(len(rhythm_events), 0)
        self.assertLess(len(rhythm_events), 12)
        self.assertTrue(all(event.intensity >= 0.32 for event in rhythm_events))

    def test_story_preset_audio_matches_the_level_length(self):
        sound = make_preset_sound(140, 21)
        self.assertAlmostEqual(sound.get_length(), 60, delta=0.1)

    def test_each_song_start_randomizes_the_first_lane(self):
        game = Game.__new__(Game)
        game.track_channel = None
        game.track_bpm = 140
        game.track_events = []
        game.rhythm_bpm = 140
        game.rhythm_events = make_rhythm_events(140, 60)
        game.game_duration = 60
        game.track_sound = None
        game.track_is_custom = False
        game.score_saved = True

        for offset, expected_direction in enumerate(("N", "E", "S", "W")):
            with patch("index.random.randrange", return_value=offset):
                game.reset_game()
            self.assertFalse(game.score_saved)
            self.assertEqual(game.beat_manager.bpm, 140)
            self.assertEqual(game.rhythm_manager.bpm, 140)
            self.assertAlmostEqual(game.beat_manager.interval, 60 / 140 * 1000)
            self.assertAlmostEqual(game.rhythm_manager.interval, 60 / 140 * 1000)
            game.beat_manager.beat_count = 1
            game.spawn_beat_queue(BeatEvent(0, 0.5))
            self.assertEqual(game.vehicles[0].approach_direction, expected_direction)

    def test_control_target_follows_the_most_impatient_lane(self):
        game = Game.__new__(Game)
        game.lane_start_offset = 0
        game.lane_patience = {"N": 35, "E": 70, "S": 20, "W": 0}
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.traffic_forecast = type("Forecast", (), {"cars_per_beat": 1})()
        game.vehicles = []
        game.start_ticks = pygame.time.get_ticks()
        game.spawn_beat_queue(BeatEvent(0, 0.5, hold_id=0, hold_end=4))
        self.assertEqual(game.control_direction, "E")

    def test_level_select_accepts_keyboard_navigation_and_selection(self):
        game = Game.__new__(Game)
        game.state = "LEVEL_SELECT"
        game.selected_level_index = 0
        selected_levels = []
        game.select_preset = selected_levels.append

        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
            ],
        ):
            game.handle_events()
        self.assertEqual(game.selected_level_index, 1)

        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
            ],
        ):
            game.handle_events()
        self.assertEqual(selected_levels, [1])

        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)
            ],
        ):
            game.handle_events()
        self.assertEqual(selected_levels, [1, 2])

    def test_level_select_mouse_click_selects_the_clicked_song(self):
        game = Game.__new__(Game)
        game.state = "LEVEL_SELECT"
        game.back_button = pygame.Rect(0, 0, 10, 10)
        game.level_buttons = [
            pygame.Rect(index * 20, 20, 10, 10) for index in range(4)
        ]
        selected_levels = []
        game.select_preset = selected_levels.append
        clicked_song = game.level_buttons[2].center

        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=clicked_song,
                )
            ],
        ):
            game.handle_events()

        self.assertEqual(game.selected_level_index, 2)
        self.assertEqual(selected_levels, [2])

    def test_selected_song_preview_is_limited_to_ten_seconds(self):
        class FakeChannel:
            def __init__(self):
                self.volume = None

            def set_volume(self, volume):
                self.volume = volume

            def stop(self):
                pass

        class FakeSound:
            def __init__(self):
                self.channel = FakeChannel()
                self.play_options = None

            def play(self, **options):
                self.play_options = options
                return self.channel

        game = Game.__new__(Game)
        game.selected_level_index = 1
        game.preview_channel = None
        fake_sound = FakeSound()
        game.show_status = lambda message: None

        with patch("index.pygame.mixer.Sound", return_value=fake_sound) as sound_loader:
            game.preview_selected_level()

        sound_loader.assert_called_once_with(PRESET_LEVELS[1]["file"])
        self.assertEqual(fake_sound.play_options, {"maxtime": 10_000})
        self.assertEqual(game.preview_channel, fake_sound.channel)
        self.assertEqual(fake_sound.channel.volume, 0.8)

    def test_custom_track_decode_error_returns_to_start_menu(self):
        game = Game.__new__(Game)
        game.state = "LOADING"
        game.pending_load = ("custom", "unreadable.mp3")
        status_messages = []
        game.show_status = status_messages.append

        with patch(
            "index.pygame.mixer.Sound",
            side_effect=pygame.error("unsupported MP3"),
        ):
            game.load_custom_track("unreadable.mp3")

        self.assertEqual(game.state, "START")
        self.assertIsNone(game.pending_load)
        self.assertIn("MP3 laden is mislukt", status_messages[0])

    def test_game_over_name_accepts_r_without_restarting(self):
        game = Game.__new__(Game)
        game.state = "GAMEOVER"
        game.player_name = "PLAY"
        game.reset_game = lambda: self.fail("R should be entered as a name character")
        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(
                    pygame.KEYDOWN,
                    key=pygame.K_r,
                    unicode="r",
                )
            ],
        ):
            game.handle_events()

        self.assertEqual(game.player_name, "PLAYR")

    def test_driver_warning_animation_handles_east_lane(self):
        game = Game.__new__(Game)
        game.screen = pygame.Surface((800, 600))
        game.font = pygame.font.SysFont("Arial", 12)
        game.lane_patience = {"N": 0, "E": 80, "S": 0, "W": 0}
        vehicle = Vehicle("E")
        vehicle.stopped = True
        game.vehicles = [vehicle]

        with patch("index.pygame.time.get_ticks", return_value=0):
            game.draw_driver_warnings()

    def test_game_over_menu_button_returns_to_start(self):
        game = Game.__new__(Game)
        game.state = "GAMEOVER"
        game.restart_button = pygame.Rect(0, 0, 10, 10)
        game.menu_button = pygame.Rect(20, 0, 10, 10)
        game.save_leaderboard_entry = lambda: None

        with patch(
            "index.pygame.event.get",
            return_value=[
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=game.menu_button.center,
                )
            ],
        ):
            game.handle_events()

        self.assertEqual(game.state, "START")

    def test_lane_input_does_not_show_on_or_off_beat_status_text(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = None
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []
        game.status_message = ""

        with patch(
            "index.pygame.time.get_ticks",
            return_value=game.beat_manager.last_beat_time,
        ):
            game.press_light("N")

        self.assertEqual(game.status_message, "")
        self.assertEqual(game.score, 100)

    def test_on_beat_window_accepts_a_late_tap(self):
        manager = BeatManager(70, [], pygame.time.get_ticks())
        beat_time = manager.last_beat_time

        with patch("index.pygame.time.get_ticks", return_value=beat_time + 380):
            self.assertTrue(manager.is_on_beat())
        with patch("index.pygame.time.get_ticks", return_value=beat_time + 420):
            self.assertFalse(manager.is_on_beat())

    def test_metronome_uses_accented_ticks_and_can_be_muted(self):
        class FakeSound:
            def __init__(self):
                self.play_count = 0

            def play(self):
                self.play_count += 1

        game = Game.__new__(Game)
        game.metronome_enabled = True
        game.rhythm_manager = BeatManager(120, [], start_ticks=0)
        game.metronome_tick = FakeSound()
        game.metronome_accent = FakeSound()

        game.play_metronome_tick()
        game.rhythm_manager.beat_count = 1
        game.play_metronome_tick()
        game.metronome_enabled = False
        game.play_metronome_tick()

        self.assertEqual(game.metronome_tick.play_count, 1)
        self.assertEqual(game.metronome_accent.play_count, 1)

    def test_high_score_is_loaded_and_only_replaced_by_a_new_record(self):
        game = Game.__new__(Game)
        with tempfile.TemporaryDirectory() as directory:
            game.high_score_file = os.path.join(directory, "highscore.txt")
            with open(game.high_score_file, "w", encoding="utf-8") as score_file:
                score_file.write("780\n")

            game.high_score = game.load_high_score()
            game.score = 700
            game.save_high_score()
            with open(game.high_score_file, "r", encoding="utf-8") as score_file:
                self.assertEqual(score_file.read().strip(), "780")

            game.score = 900
            game.save_high_score()
            with open(game.high_score_file, "r", encoding="utf-8") as score_file:
                self.assertEqual(score_file.read().strip(), "900")
            self.assertEqual(game.high_score, 900)

    def test_charted_first_beat_drives_countdown_and_pulse(self):
        manager = BeatManager(
            70,
            [BeatEvent(0.5, 0.5), BeatEvent(1.3, 0.5)],
            start_ticks=1000,
        )

        with patch("index.pygame.time.get_ticks", return_value=1200):
            self.assertEqual(manager.next_beat_time(), 1500)
            self.assertEqual(manager.nearest_beat_time(), 1500)
            self.assertAlmostEqual(manager.get_pulse_factor(), 0.3455, places=3)

        with patch("index.pygame.time.get_ticks", return_value=1230):
            self.assertTrue(manager.is_on_beat())

        with patch("index.pygame.time.get_ticks", return_value=1000):
            self.assertAlmostEqual(manager.get_pulse_factor(), 0)
        with patch("index.pygame.time.get_ticks", return_value=1500):
            self.assertAlmostEqual(manager.get_pulse_factor(), 1)

        with patch("index.pygame.time.get_ticks", return_value=1500):
            manager.update()
        with patch("index.pygame.time.get_ticks", return_value=1600):
            self.assertEqual(manager.next_beat_time(), 2300)
            self.assertEqual(manager.nearest_beat_time(), 1500)

    def test_beat_rail_offsets_follow_irregular_chart_and_fallback_timing(self):
        events = [
            BeatEvent(0, 0.5),
            BeatEvent(0.4, 0.5),
            BeatEvent(1.0, 0.5),
            BeatEvent(1.4, 0.5),
        ]
        charted = BeatManager(100, events, start_ticks=0)

        with patch("index.pygame.time.get_ticks", return_value=500):
            charted.update()
        self.assertEqual(charted.beat_offsets(500), [-500, -100, 500, 900])

        regular = BeatManager(120, start_ticks=0)
        self.assertEqual(regular.beat_offsets(1000), [-500, 0, 500])

    def test_waveform_extracts_normalized_audio_peaks(self):
        sample_rate = 22050
        samples = array("h", [0]) * sample_rate
        for index in range(sample_rate // 4, sample_rate // 2):
            samples[index] = 10000 if index % 2 else -10000
        waveform = extract_waveform(
            pygame.mixer.Sound(buffer=samples.tobytes()),
            point_count=20,
        )

        self.assertEqual(len(waveform), 20)
        self.assertAlmostEqual(max(waveform), 1.0)
        self.assertEqual(min(waveform), 0.0)

    def test_bundled_preset_paths_do_not_depend_on_the_launch_directory(self):
        self.assertTrue(
            all(
                os.path.isabs(level["file"]) and os.path.isfile(level["file"])
                for level in PRESET_LEVELS
                if "file" in level
            )
        )

    def test_bundled_mp3_presets_load_from_another_working_directory(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as working_directory:
            os.chdir(working_directory)
            try:
                for index, level in enumerate(PRESET_LEVELS):
                    if "file" not in level:
                        continue
                    game = Game.__new__(Game)
                    game.track_channel = None
                    game.state = "LEVEL_SELECT"
                    game.show_status = lambda message: None
                    game.reset_game = lambda: None
                    game.load_preset(index)

                    self.assertEqual(game.track_name, level["song"])
                    self.assertEqual(game.rhythm_bpm, level["bpm"])
                    self.assertTrue(game.track_events)
                    self.assertTrue(game.track_waveform)
            finally:
                os.chdir(original_directory)

    def test_waveform_layer_uses_ten_percent_opacity(self):
        layer = Game.make_waveform_layer([0, 1, 0])

        self.assertEqual(layer.get_at((399, 218)).a, 26)

    def test_fast_tempo_timing_window_does_not_cover_the_entire_beat(self):
        manager = BeatManager(140, [], start_ticks=0)

        self.assertEqual(manager.input_window_ms(), 193)
        with patch("index.pygame.time.get_ticks", return_value=214):
            self.assertFalse(manager.is_on_beat())

    def test_story_input_score_uses_full_tempo_not_traffic_tempo(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.start_ticks = 1000
        game.beat_manager = BeatManager(140, [], game.start_ticks)
        game.rhythm_manager = BeatManager(
            140,
            make_rhythm_events(140, 2),
            game.start_ticks,
        )
        game.control_direction = None
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []

        with patch("index.pygame.time.get_ticks", return_value=1000):
            game.press_light("N")
        with patch("index.pygame.time.get_ticks", return_value=1214):
            game.press_light("E")

        self.assertEqual(game.score, 150)
        self.assertEqual(game.mistakes, 0)
        self.assertEqual(game.beat_manager.bpm, 140)
        self.assertEqual(game.rhythm_manager.bpm, 140)

    def test_beat_pulse_tracks_the_full_interval_smoothly(self):
        manager = BeatManager(70, [], pygame.time.get_ticks())
        beat_time = manager.last_beat_time
        interval = manager.interval

        with patch(
            "index.pygame.time.get_ticks",
            return_value=round(beat_time + interval / 4),
        ):
            self.assertAlmostEqual(manager.get_pulse_factor(), 0.5, places=2)
        with patch(
            "index.pygame.time.get_ticks",
            return_value=round(beat_time + interval / 2),
        ):
            self.assertAlmostEqual(manager.get_pulse_factor(), 0, places=2)

    def test_beat_manager_keeps_all_events_due_after_a_slow_frame(self):
        events = [BeatEvent(0.1, 0.4), BeatEvent(0.2, 0.6), BeatEvent(0.3, 0.8)]
        manager = BeatManager(70, events, start_ticks=0)

        with patch("index.pygame.time.get_ticks", return_value=350):
            manager.update()

        self.assertEqual(manager.happened_events, events)
        self.assertEqual(manager.happened_event_indices, [0, 1, 2])
        self.assertEqual(manager.beat_count, 3)

    def test_audio_analysis_uses_full_beat_rate_for_traffic(self):
        sample_rate = 22050
        samples = array("h", [0]) * (sample_rate * 8)
        interval = 60 / 140
        for beat in range(18):
            start = round(beat * interval * sample_rate)
            for offset in range(round(sample_rate * 0.07)):
                samples[start + offset] = int(
                    10000 * math.sin(2 * math.pi * 900 * offset / sample_rate)
                )

        events, bpm, used_fallback, rhythm_events, rhythm_bpm = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes())
        )

        self.assertGreaterEqual(len(events), 8)
        self.assertAlmostEqual(bpm, 140, delta=5)
        self.assertAlmostEqual(rhythm_bpm, 140, delta=5)
        self.assertTrue(any(event.time > rhythm_events[-1].time for event in events))
        self.assertFalse(used_fallback)

    def test_audio_analysis_marks_a_sustained_section(self):
        sample_rate = 22050
        samples = array("h", [0]) * (sample_rate * 6)
        for index in range(sample_rate * 2, sample_rate * 4):
            samples[index] = int(
                8000 * math.sin(2 * math.pi * 220 * index / sample_rate)
            )

        events, bpm, used_fallback, rhythm_events, rhythm_bpm = analyze_track(
            pygame.mixer.Sound(buffer=samples.tobytes())
        )

        self.assertEqual(bpm, 120)
        self.assertEqual(rhythm_bpm, 120)
        self.assertEqual(len(rhythm_events), len(events))
        self.assertAlmostEqual(
            rhythm_events[1].time - rhythm_events[0].time,
            60 / 120,
        )
        self.assertTrue(used_fallback)
        self.assertTrue(any(event.hold_id is not None for event in events))

    def test_queued_or_nonintersecting_cars_do_not_end_the_game(self):
        game = Game.__new__(Game)
        queued_car = Vehicle("W", 8)
        game.state = "PLAYING"
        game.start_ticks = pygame.time.get_ticks()
        game.game_duration = 60
        game.time_left = 60
        game.active_hold_direction = None
        game.active_hold_until = 0
        game.control_direction = "W"
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.lane_wait_beats = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.patience_limit_beats = 10
        game.track_events = []
        game.track_bpm = 70
        game.rhythm_events = []
        game.rhythm_bpm = 70
        game.track_channel = None
        game.beat_manager = BeatManager(70, [], game.start_ticks)
        game.rhythm_manager = BeatManager(70, [], game.start_ticks)
        game.lights = Game.make_lights()
        game.vehicles = [queued_car]
        game.served_lanes = set()
        game.update()
        self.assertIn(queued_car, game.vehicles)
        self.assertLess(queued_car.x, -150)

        first, second = Vehicle("N"), Vehicle("W")
        first.x, first.y = 400, 290
        second.x, second.y = 390, 300
        game.vehicles = [first, second]
        game.check_collisions()
        self.assertEqual(len(game.vehicles), 2)
        self.assertFalse(first.has_collided or second.has_collided)
        self.assertEqual(game.state, "PLAYING")

        first.inside_intersection = True
        first.passed_stop_line = True
        game.check_collisions()
        self.assertEqual(game.state, "PLAYING")
        self.assertFalse(first.has_collided or second.has_collided)

    def test_overlapping_cars_from_the_same_lane_do_not_end_the_game(self):
        game = Game.__new__(Game)
        first, second = Vehicle("W"), Vehicle("W")
        first.set_center((300, 300))
        second.set_center((300, 300))
        first.inside_intersection = second.inside_intersection = True
        first.passed_stop_line = second.passed_stop_line = True
        game.state = "PLAYING"
        game.vehicles = [first, second]

        game.check_collisions()

        self.assertEqual(game.state, "PLAYING")
        self.assertFalse(first.has_collided or second.has_collided)

        second.approach_direction = "N"
        second.direction = "N"
        game.check_collisions()
        self.assertEqual(game.state, "GAMEOVER")
        self.assertTrue(first.has_collided and second.has_collided)

    def test_rotated_car_shapes_do_not_crash_when_only_their_bounds_overlap(self):
        game = Game.__new__(Game)
        first = Vehicle("W", turn="right")
        second = Vehicle("W", turn="right")
        first.set_center((300, 300))
        second.set_center((285, 315))
        first.heading_angle = second.heading_angle = 45
        first.inside_intersection = second.inside_intersection = True
        first.passed_stop_line = second.passed_stop_line = True
        game.state = "PLAYING"
        game.vehicles = [first, second]

        self.assertTrue(first.get_rect().colliderect(second.get_rect()))
        self.assertFalse(first.collides_with(second))
        game.check_collisions()
        self.assertEqual(game.state, "PLAYING")

    def test_suriname_left_lane_positions(self):
        westbound = Vehicle("W")
        eastbound = Vehicle("E")
        northbound = Vehicle("N")
        southbound = Vehicle("S")
        self.assertLess(westbound.y, 300)
        self.assertGreater(eastbound.y, 300)
        self.assertGreater(northbound.x, 400)
        self.assertLess(southbound.x, 400)

    def test_green_light_moves_continuously_and_red_light_stops_at_line(self):
        westbound = Vehicle("W")
        westbound.x = 200
        westbound.update("GREEN", move_on_beat=False)
        self.assertGreater(westbound.x, 200)

        westbound.x = westbound.stop_x - 40
        westbound.update("RED", move_on_beat=False)
        stopped_at = westbound.x
        westbound.update("RED", move_on_beat=False)
        self.assertEqual(westbound.x, stopped_at)

    def test_car_that_cleared_stop_line_does_not_stop_when_light_changes(self):
        for direction in ("N", "E", "S", "W"):
            vehicle = Vehicle(direction, turn="straight")
            if direction == "W":
                vehicle.x = vehicle.stop_x - vehicle.width - 1
                position_axis, movement = "x", vehicle.speed
            elif direction == "E":
                vehicle.x = vehicle.stop_x + 1
                position_axis, movement = "x", -vehicle.speed
            elif direction == "N":
                vehicle.y = vehicle.stop_y - vehicle.height - 1
                position_axis, movement = "y", vehicle.speed
            else:
                vehicle.y = vehicle.stop_y + 1
                position_axis, movement = "y", -vehicle.speed

            vehicle.update("GREEN")
            self.assertTrue(vehicle.passed_stop_line, direction)
            crossed_at = getattr(vehicle, position_axis)
            vehicle.update("YELLOW")
            self.assertEqual(
                getattr(vehicle, position_axis),
                crossed_at + movement,
                direction,
            )
            crossed_at = getattr(vehicle, position_axis)
            vehicle.update("RED")
            self.assertEqual(
                getattr(vehicle, position_axis),
                crossed_at + movement,
                direction,
            )

    def test_random_left_and_right_turn_routes_exit_in_the_correct_direction(self):
        for approach in ("N", "E", "S", "W"):
            for turn, routes in (
                ("left", Vehicle.LEFT_TURNS),
                ("right", Vehicle.RIGHT_TURNS),
            ):
                vehicle = Vehicle(approach, turn=turn)
                if approach == "W":
                    vehicle.x = vehicle.stop_x - vehicle.width - 1
                elif approach == "E":
                    vehicle.x = vehicle.stop_x + 1
                elif approach == "N":
                    vehicle.y = vehicle.stop_y - vehicle.height - 1
                else:
                    vehicle.y = vehicle.stop_y + 1

                vehicle.update("GREEN")
                for _ in range(60):
                    if vehicle.direction != approach:
                        break
                    vehicle.update("RED")

                self.assertEqual(vehicle.direction, routes[approach])
                self.assertFalse(vehicle.inside_intersection)

    def test_conflicting_lanes_can_enter_the_intersection_together(self):
        westbound = Vehicle("W", turn="straight")
        northbound = Vehicle("N", turn="straight")
        westbound.x = westbound.stop_x - westbound.width - 1
        northbound.y = northbound.stop_y - northbound.height - 1

        westbound.update("GREEN")
        northbound.update("GREEN")

        self.assertTrue(westbound.passed_stop_line)
        self.assertTrue(northbound.passed_stop_line)

    def test_conflicting_crossing_traffic_can_cause_a_collision(self):
        eastbound = Vehicle("E", turn="straight")
        northbound = Vehicle("N", turn="straight")
        eastbound.x = eastbound.stop_x + 1
        northbound.y = northbound.stop_y - northbound.height - 1
        game = Game.__new__(Game)
        game.state = "PLAYING"
        game.vehicles = [eastbound, northbound]

        for _ in range(30):
            eastbound.update("GREEN")
            northbound.update("GREEN")
            game.check_collisions()
            if game.state == "GAMEOVER":
                break

        self.assertEqual(game.state, "GAMEOVER")
        self.assertEqual(game.game_over_reason, "COLLISION")

    def test_patience_forecast_changes_with_upcoming_song_section(self):
        quiet_events = [
            BeatEvent(time, 0.3)
            for time in (1, 8, 15, 22)
        ]
        busy_events = [
            BeatEvent(time, 0.9, 2)
            for time in range(30)
        ]
        quiet = analyze_upcoming_section(quiet_events, 0, 60)
        busy = analyze_upcoming_section(busy_events, 0, 90)
        self.assertGreater(quiet.patience_beats, busy.patience_beats)
        self.assertGreater(busy.cars_per_beat, quiet.cars_per_beat)
        self.assertEqual(busy.cars_per_beat, 2)

    def test_game_doubles_forecast_patience_to_slow_pressure_by_half(self):
        game = Game.__new__(Game)
        game.state = "PLAYING"
        game.start_ticks = pygame.time.get_ticks()
        game.game_duration = 60
        game.track_events = []
        game.track_bpm = 70
        game.rhythm_events = []
        game.rhythm_bpm = 70
        game.track_channel = None
        game.active_hold_direction = None
        game.active_hold_until = 0
        game.control_direction = None
        game.lane_wait_beats = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.patience_limit_beats = 10
        game.traffic_forecast = analyze_upcoming_section([], 0, game.track_bpm)
        game.beat_manager = BeatManager(70, [], game.start_ticks)
        game.rhythm_manager = BeatManager(70, [], game.start_ticks)
        game.lights = Game.make_lights()
        game.vehicles = []
        game.served_lanes = set()
        game.time_left = 60

        game.update()

        self.assertEqual(
            game.patience_limit_beats,
            game.traffic_forecast.patience_beats * 2,
        )

    def test_traffic_preview_shows_lane_counts_and_next_arrivals_for_one_minute(self):
        game = Game.__new__(Game)
        game.track_events = [
            BeatEvent(0.5, 0.4),
            BeatEvent(1, 0.8, queue_size=3),
            BeatEvent(2, 0.5, hold_id=2),
            BeatEvent(61, 0.5),
        ]
        game.beat_manager = BeatManager(70, game.track_events, pygame.time.get_ticks())
        game.lane_start_offset = 1
        game.traffic_forecast = type(
            "Forecast",
            (),
            {"cars_per_beat": 2},
        )()

        game.update_traffic_preview(0)

        self.assertEqual(game.traffic_lane_counts, {"N": 0, "E": 2, "S": 3, "W": 2})
        self.assertEqual(
            game.traffic_preview,
            [("E", 2, 0.5), ("S", 3, 1), ("W", 2, 2)],
        )

    def test_game_fades_and_ends_the_track_at_its_exact_duration(self):
        class FakeChannel:
            def __init__(self):
                self.fadeout_calls = []
                self.stop_calls = 0

            def fadeout(self, duration):
                self.fadeout_calls.append(duration)

            def stop(self):
                self.stop_calls += 1

        game = Game.__new__(Game)
        game.state = "PLAYING"
        game.game_duration = 60.0
        game.score = 75
        game.start_ticks = pygame.time.get_ticks() - 58_000
        game.time_left = 2
        game.track_events = []
        game.track_bpm = 70
        game.rhythm_events = []
        game.rhythm_bpm = 70
        game.track_channel = FakeChannel()
        game.track_fading_out = False
        game.active_hold_direction = None
        game.active_hold_until = 0
        game.control_direction = None
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.lane_wait_beats = {direction: 0 for direction in ("N", "E", "S", "W")}
        game.patience_limit_beats = 20
        game.beat_manager = BeatManager(70, [], game.start_ticks)
        game.rhythm_manager = BeatManager(70, [], game.start_ticks)
        game.lights = Game.make_lights()
        game.vehicles = []

        with patch(
            "index.pygame.time.get_ticks",
            return_value=game.start_ticks + 58_000,
        ):
            game.update()
            game.update()
        self.assertEqual(game.track_channel.fadeout_calls, [2000])

        with patch(
            "index.pygame.time.get_ticks",
            return_value=game.start_ticks + 60_000,
        ):
            game.update()
        self.assertEqual(game.state, "GAMEOVER")
        self.assertEqual(game.game_over_reason, "TIME")
        self.assertEqual(game.score, 1075)
        self.assertEqual(game.track_channel.stop_calls, 1)

    def test_reset_plays_the_track_once_before_starting_the_game_clock(self):
        events = []

        class FakeChannel:
            pass

        class FakeSound:
            def __init__(self):
                self.loops = None

            def play(self, loops):
                events.append("play")
                self.loops = loops
                return FakeChannel()

        game = Game.__new__(Game)
        game.track_channel = None
        game.track_sound = FakeSound()
        game.track_events = []
        game.track_bpm = 70
        game.rhythm_events = []
        game.rhythm_bpm = 70
        game.track_is_custom = False
        game.track_name = "Test"
        game.game_duration = 5.2
        game.vehicles = []
        game.start_ticks = 0
        game.time_left = 0
        game.state = "START"
        game.score = 700
        game.mistakes = 3

        def clock_ticks():
            events.append("clock")
            return 1234

        with patch("index.pygame.time.get_ticks", side_effect=clock_ticks):
            game.reset_game()

        self.assertEqual(game.track_sound.loops, 0)
        self.assertLess(events.index("play"), events.index("clock"))
        self.assertEqual(game.start_ticks, 1234)
        self.assertEqual(game.beat_manager.start_ticks, 1234)
        self.assertEqual(game.rhythm_manager.start_ticks, 1234)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.mistakes, 0)

    def test_patience_only_advances_on_song_beats_and_warns_at_90_percent(self):
        game = Game.__new__(Game)
        game.state = "PLAYING"
        game.vehicles = [Vehicle("W")]
        waiting_car = game.vehicles[0]
        waiting_car.x = waiting_car.stop_x - waiting_car.width
        waiting_car.stopped = True
        game.lights = Game.make_lights()
        game.control_direction = "E"
        game.lane_wait_beats = {direction: 8 for direction in ("N", "E", "S", "W")}
        game.lane_patience = {direction: 80 for direction in ("N", "E", "S", "W")}
        game.patience_limit_beats = 10
        game.served_lanes = set()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.update_lane_patience(False)
        self.assertEqual(game.lane_wait_beats["W"], 8)
        game.update_lane_patience(True)
        self.assertEqual(game.lane_patience["W"], 90)
        self.assertEqual(game.lights["W"].state, "YELLOW")
        game.update_lane_patience(True)
        self.assertEqual(game.lane_patience["W"], 100)
        self.assertEqual(game.state, "GAMEOVER")

    def test_patience_resets_immediately_when_lane_queue_is_empty(self):
        game = Game.__new__(Game)
        game.vehicles = []
        game.lane_wait_beats = {direction: 8 for direction in ("N", "E", "S", "W")}
        game.lane_patience = {direction: 80 for direction in ("N", "E", "S", "W")}

        game.update_lane_patience(False)

        self.assertEqual(game.lane_wait_beats, {direction: 0 for direction in ("N", "E", "S", "W")})
        self.assertEqual(game.lane_patience, {direction: 0 for direction in ("N", "E", "S", "W")})

    def test_only_a_stopped_queue_ahead_can_block_an_approaching_car(self):
        game = Game.__new__(Game)
        leading = Vehicle("W")
        following = Vehicle("W")
        leading.x = 240
        leading.stopped = True
        following.x = 200
        game.vehicles = [leading, following]
        self.assertTrue(game.vehicle_is_blocked_by_queue(following))

        leading.passed_stop_line = True
        self.assertFalse(game.vehicle_is_blocked_by_queue(following))

    def test_tapping_light_stays_green_for_at_least_one_beat(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = "W"
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        beat_time = game.beat_manager.last_beat_time

        with patch("index.pygame.time.get_ticks", return_value=beat_time):
            game.press_light("W")
        self.assertTrue(game.lights["W"].is_green)
        self.assertEqual(game.lights["W"].state, "GREEN")
        self.assertEqual(
            game.lights["W"].green_until,
            beat_time + game.lane_green_duration_ms("W"),
        )
        self.assertGreaterEqual(
            game.lights["W"].green_until - beat_time,
            3 * game.beat_manager.interval,
        )
        with patch(
            "index.pygame.time.get_ticks",
            return_value=game.lights["W"].green_until - 1,
        ):
            game.lights["W"].update()
        self.assertEqual(game.lights["W"].state, "GREEN")
        with patch(
            "index.pygame.time.get_ticks",
            return_value=game.lights["W"].green_until,
        ):
            game.lights["W"].update()
        self.assertEqual(game.lights["W"].state, "YELLOW")

    def test_long_queue_keeps_lane_green_longer_to_clear_the_approach(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], start_ticks=1000)
        game.control_direction = None
        game.served_lanes = set()
        game.vehicles = [Vehicle("W", queue_position=10)]
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}

        with patch("index.pygame.time.get_ticks", return_value=1000):
            game.activate_lane("W")

        green_duration = game.lights["W"].green_until - 1000
        self.assertGreater(
            green_duration,
            3 * game.beat_manager.interval,
        )

    def test_off_beat_lane_input_works_immediately(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = None
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        beat_time = game.beat_manager.last_beat_time

        with patch(
            "index.pygame.time.get_ticks",
            return_value=round(beat_time + 400),
        ):
            game.press_light("E")
        self.assertEqual(game.lights["E"].state, "GREEN")
        self.assertEqual(game.control_direction, "E")
        self.assertEqual(game.score, 50)
        self.assertEqual(game.mistakes, 0)
        self.assertEqual(game.rhythm_feedback, "+50 OFF BEAT")
        self.assertIn("E", game.served_lanes)

    def test_multiple_lane_inputs_work_in_one_beat_and_off_beat(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = "W"
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        beat_time = game.beat_manager.last_beat_time
        game.lights["W"].set_green()

        with patch("index.pygame.time.get_ticks", return_value=beat_time):
            game.press_light("E")
            game.press_light("W")
        self.assertEqual(game.lights["E"].state, "YELLOW")
        self.assertEqual(game.lights["W"].state, "GREEN")
        self.assertEqual(game.control_direction, "W")
        self.assertEqual(game.score, 200)

        with patch(
            "index.pygame.time.get_ticks",
            return_value=round(beat_time + 400),
        ):
            game.press_light("N")
        self.assertEqual(game.lights["N"].state, "GREEN")
        self.assertEqual(game.score, 250)
        self.assertEqual(game.mistakes, 0)

    def test_off_beat_inputs_never_cause_penalties_or_game_over(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = None
        game.score = 0
        game.mistakes = 0
        game.state = "PLAYING"
        game.track_channel = None
        game.served_lanes = set()
        game.vehicles = []
        game.lane_patience = {direction: 0 for direction in ("N", "E", "S", "W")}
        off_beat_time = round(game.beat_manager.last_beat_time + 400)

        with patch("index.pygame.time.get_ticks", return_value=off_beat_time):
            for direction in ("N", "E", "S", "W") * 3:
                game.press_light(direction)

        self.assertEqual(game.mistakes, 0)
        self.assertEqual(game.score, 600)
        self.assertEqual(game.state, "PLAYING")
        self.assertTrue(all(light.state in ("GREEN", "YELLOW") for light in game.lights.values()))

    def test_on_beat_lane_switch_relieves_that_lane_even_after_green_ends(self):
        game = Game.__new__(Game)
        game.lights = Game.make_lights()
        game.beat_manager = BeatManager(70, [], pygame.time.get_ticks())
        game.rhythm_manager = game.beat_manager
        game.control_direction = "W"
        game.score = 0
        game.mistakes = 0
        game.track_channel = None
        game.served_lanes = set()
        game.lane_wait_beats = {"N": 0, "E": 8, "S": 0, "W": 0}
        game.lane_patience = {"N": 0, "E": 80, "S": 0, "W": 0}
        game.patience_limit_beats = 10
        waiting_car = Vehicle("E")
        waiting_car.stopped = True
        game.vehicles = [waiting_car]
        game.state = "PLAYING"

        with patch("index.pygame.time.get_ticks", return_value=game.beat_manager.last_beat_time):
            game.press_light("E")
        self.assertEqual(game.score, 100)
        self.assertEqual(game.on_beat_streak, 1)
        game.lights["E"].state = "RED"
        game.lights["E"].is_green = False
        game.update_lane_patience(True)

        self.assertEqual(game.lane_wait_beats["E"], 4)
        self.assertEqual(game.lane_patience["E"], 40)

    def test_high_patience_slows_vehicle_motion(self):
        regular = Vehicle("W")
        slowed = Vehicle("W")
        regular.x = slowed.x = 100

        regular.update("RED")
        slowed.update("RED", speed_scale=0.65)

        self.assertLess(slowed.x - 100, regular.x - 100)


    def test_real_mp3_presets_are_bundled(self):
        for relative_path in (
            "presets/shottas.mp3",
            "presets/wait-a-minute.mp3",
            "presets/neon-guts.mp3",
        ):
            self.assertTrue(os.path.exists(relative_path), relative_path)


if __name__ == "__main__":
    unittest.main()
