from array import array
from dataclasses import dataclass
import math
import random
import statistics

import pygame

SAMPLE_RATE = 22050
WINDOW_SECONDS = 0.02
MAX_TRAFFIC_BPM = 160


@dataclass(frozen=True)
class BeatEvent:
    time: float
    intensity: float
    queue_size: int = 1
    hold_id: int | None = None
    hold_end: float | None = None


@dataclass(frozen=True)
class TrafficForecast:
    cars_per_beat: int
    patience_beats: int


def analyze_upcoming_section(events, elapsed, bpm, horizon=30):
    upcoming = [
        event for event in events
        if elapsed <= event.time < elapsed + horizon
    ]
    beat_rate = len(upcoming) / horizon if upcoming else bpm / 60
    mean_intensity = (
        statistics.mean(event.intensity for event in upcoming)
        if upcoming else 0.45
    )

    cars_per_beat = 2 if mean_intensity >= 0.65 else 1

    patience_beats = round(10 / max(0.75, beat_rate))
    patience_beats = max(6, min(14, patience_beats))
    return TrafficForecast(cars_per_beat, patience_beats)


def make_preset_sound(bpm, seed):
    beat_count = round(bpm)
    frames_per_beat = round(SAMPLE_RATE * 60 / bpm)
    samples = array("h", [0]) * (beat_count * frames_per_beat)
    rng = random.Random(seed)
    melody = (0, 3, 7, 10, 7, 3, 5, 12)

    for beat in range(beat_count):
        start = beat * frames_per_beat
        phrase_beat = beat % 32
        if 16 <= phrase_beat < 24:
            if phrase_beat == 16:
                hold_frames = 8 * frames_per_beat
                hold_hz = 220 * (2 ** (7 / 12))
                for offset in range(hold_frames):
                    time = offset / SAMPLE_RATE
                    hold_time = hold_frames / SAMPLE_RATE
                    envelope = min(1.0, time / 0.1, (hold_time - time) / 0.35)
                    tone = (
                        math.sin(2 * math.pi * hold_hz * time)
                        + 0.45 * math.sin(2 * math.pi * hold_hz * 1.5 * time)
                    )
                    samples[start + offset] = int(2800 * max(0.0, envelope) * tone)
            continue

        note_hz = 220 * (2 ** (melody[beat % len(melody)] / 12))
        tone_length = min(frames_per_beat, int(SAMPLE_RATE * 0.22))

        for offset in range(tone_length):
            time = offset / SAMPLE_RATE
            tone = math.sin(2 * math.pi * note_hz * time) * math.exp(-time * 9)
            sample = 2200 * tone

            if beat % 4 == 0:
                kick_hz = 90 - 45 * min(time / 0.16, 1)
                sample += 6500 * math.sin(2 * math.pi * kick_hz * time) * math.exp(-time * 22)
            elif beat % 4 == 2:
                noise = rng.uniform(-1, 1)
                sample += 2600 * noise * math.exp(-time * 24)

            index = start + offset
            samples[index] = max(-32768, min(32767, samples[index] + int(sample)))

    return pygame.mixer.Sound(buffer=samples.tobytes())


def make_preset_events(bpm, duration, difficulty):
    bpm = min(bpm, MAX_TRAFFIC_BPM)
    beat_interval = 60 / bpm
    event_count = math.ceil(duration / beat_interval)
    events = []

    for beat in range(event_count):
        phrase_position = beat % 32
        is_hold = 16 <= phrase_position < 24
        hold_id = (beat // 32) % 4 if is_hold else None
        hold_end = ((beat // 32) * 32 + 24) * beat_interval if is_hold else None
        intensity = 0.7 if is_hold else 0.45
        if difficulty == "hard" and beat % 4 == 3:
            intensity = 0.8
        queue_size = 2 if intensity >= 0.75 else 1
        events.append(
            BeatEvent(
                beat * beat_interval,
                intensity,
                queue_size,
                hold_id=hold_id,
                hold_end=hold_end,
            )
        )

    return events


def make_rhythm_events(bpm, duration):
    beat_interval = 60 / bpm
    return [
        BeatEvent(beat * beat_interval, 0.5)
        for beat in range(math.ceil(duration / beat_interval))
    ]


def extract_waveform(sound, point_count=400):
    mixer_format = pygame.mixer.get_init()
    if mixer_format is None:
        raise RuntimeError("De Pygame-audiomixer is niet gestart.")

    _, sample_format, channels = mixer_format
    if sample_format != -16:
        raise RuntimeError("De audiomixer moet 16-bit-audio gebruiken voor waveformanalyse.")

    samples = array("h")
    samples.frombytes(sound.get_raw())
    frame_count = len(samples) // channels
    if frame_count == 0:
        return []

    point_count = max(1, min(point_count, frame_count))
    frames_per_point = math.ceil(frame_count / point_count)
    peaks = []
    for first_frame in range(0, frame_count, frames_per_point):
        first_sample = first_frame * channels
        last_sample = min(frame_count, first_frame + frames_per_point) * channels
        samples_in_point = samples[first_sample:last_sample]
        peak = max(max(samples_in_point), -min(samples_in_point))
        peaks.append(peak)

    highest_peak = max(peaks, default=0)
    if highest_peak == 0:
        return [0.0] * len(peaks)
    return [peak / highest_peak for peak in peaks]


def _estimate_bpm_and_offset(peak_times, duration):
    if len(peak_times) < 2:
        return 120.0, 0.0

    normalized_intervals = []
    for index in range(1, len(peak_times)):
        interval = peak_times[index] - peak_times[index - 1]
        if interval <= 0.08:
            continue
        while interval > 0.75:
            interval /= 2.0
        while interval < 0.35:
            interval *= 2.0
        normalized_intervals.append(interval)

    if not normalized_intervals:
        return 120.0, 0.0

    beat_interval = statistics.median(normalized_intervals)
    bpm = max(70.0, min(MAX_TRAFFIC_BPM, 60.0 / beat_interval))
    beat_interval = 60.0 / bpm

    best_offset = 0.0
    best_score = -1.0
    for step in range(100):
        offset = (step / 100) * beat_interval
        score = 0.0
        for peak_time in peak_times:
            if peak_time < offset or peak_time >= duration:
                continue
            grid_position = (peak_time - offset) / beat_interval
            distance = abs(grid_position - round(grid_position)) * beat_interval
            if distance < 0.045:
                score += 1.0 - distance / 0.045
        if score > best_score:
            best_score = score
            best_offset = offset

    return round(bpm), best_offset


def analyze_track(sound, subdivision=1, min_intensity=0.32):
    mixer_format = pygame.mixer.get_init()
    if mixer_format is None:
        raise RuntimeError("De Pygame-audiomixer is niet gestart.")

    sample_rate, sample_format, channels = mixer_format
    if sample_format != -16:
        raise RuntimeError("De audiomixer moet 16-bit-audio gebruiken voor beat-analyse.")

    samples = array("h")
    samples.frombytes(sound.get_raw())
    frame_count = len(samples) // channels
    if frame_count == 0:
        raise ValueError("Dit MP3-bestand bevat geen leesbare audio.")

    window_frames = max(1, round(sample_rate * WINDOW_SECONDS))
    energies = []
    for first_frame in range(0, frame_count, window_frames):
        last_frame = min(frame_count, first_frame + window_frames)
        square_sum = 0
        sample_count = 0
        for frame in range(first_frame, last_frame):
            for channel in range(channels):
                sample = samples[frame * channels + channel]
                square_sum += sample * sample
                sample_count += 1
        energies.append(math.sqrt(square_sum / sample_count))

    if not energies or max(energies) < 1:
        raise ValueError("Dit MP3-bestand bevat geen hoorbare audio.")

    flux = []
    for index, energy in enumerate(energies):
        prior = energies[max(0, index - 3):index]
        baseline = statistics.mean(prior) if prior else 0.0
        flux.append(max(0, energy - baseline))

    max_flux = max(flux)
    if max_flux <= 0:
        raise ValueError("Dit MP3-bestand bevat geen hoorbare audio.")

    flux_threshold = max(statistics.mean(flux) * 1.15, max_flux * 0.12)
    peak_indices = []
    last_peak_time = -1.0
    window_duration = window_frames / sample_rate

    for index in range(1, len(flux) - 1):
        value = flux[index]
        event_time = index * window_duration
        if (
            value >= flux_threshold
            and value >= flux[index - 1]
            and value > flux[index + 1]
            and event_time - last_peak_time >= 0.12
        ):
            peak_indices.append(index)
            last_peak_time = event_time

    duration = sound.get_length()
    raw_peak_times = [
        index * window_duration
        for index in peak_indices
        if index * window_duration < duration
    ]
    used_fallback = len(raw_peak_times) < 4
    if used_fallback:
        bpm = 120
        offset = 0.0
    else:
        bpm, offset = _estimate_bpm_and_offset(raw_peak_times, duration)

    subdivision = max(1, int(subdivision))
    min_intensity = min(1.0, max(0.0, float(min_intensity)))
    beat_interval = 60.0 / bpm
    step_interval = beat_interval / subdivision
    sustained_sections = _find_sustained_sections(energies, window_duration)

    grid_best = {}
    for index in peak_indices:
        raw_time = index * window_duration
        if raw_time >= duration:
            continue
        intensity = min(1.0, flux[index] / max_flux)
        step_index = max(0, round((raw_time - offset) / step_interval))
        snapped_time = offset + step_index * step_interval
        if snapped_time >= duration:
            continue
        if step_index not in grid_best or intensity > grid_best[step_index].intensity:
            grid_best[step_index] = BeatEvent(snapped_time, intensity)

    if used_fallback:
        total_steps = math.ceil((duration - offset) / step_interval)
        for step_index in range(max(0, total_steps)):
            snapped_time = offset + step_index * step_interval
            if snapped_time < duration:
                grid_best[step_index] = BeatEvent(snapped_time, 0.55)

    full_tempo_events = [grid_best[index] for index in sorted(grid_best)]
    filtered_events = [
        event for event in full_tempo_events
        if event.intensity >= min_intensity
    ]
    source_events = filtered_events

    if len(source_events) / max(duration, 1e-9) * 60 > MAX_TRAFFIC_BPM:
        traffic_tempo_events = []
        source_index = 0
        for time in _regular_beat_times(duration, MAX_TRAFFIC_BPM):
            while (
                source_index + 1 < len(source_events)
                and abs(source_events[source_index + 1].time - time)
                < abs(source_events[source_index].time - time)
            ):
                source_index += 1
            traffic_tempo_events.append(
                BeatEvent(time, source_events[source_index].intensity)
            )
    else:
        traffic_tempo_events = source_events

    events = []
    for event in traffic_tempo_events:
        queue_size = 2 if event.intensity >= 0.85 else 1
        hold_id = None
        hold_end = None
        for section_index, (start, end) in enumerate(sustained_sections):
            if start <= event.time < end:
                hold_id = section_index % 4
                hold_end = end
                break
        events.append(
            BeatEvent(
                event.time,
                event.intensity,
                queue_size=queue_size,
                hold_id=hold_id,
                hold_end=hold_end,
            )
        )

    traffic_intervals = [
        events[index].time - events[index - 1].time
        for index in range(1, len(events))
        if events[index].time > events[index - 1].time
    ]
    traffic_bpm = (
        round(60 / statistics.median(traffic_intervals))
        if traffic_intervals
        else bpm * subdivision
    )
    traffic_bpm = max(30, min(MAX_TRAFFIC_BPM, traffic_bpm))
    return events, traffic_bpm, used_fallback, source_events, bpm


def _regular_beat_times(duration, bpm):
    interval = 60 / bpm
    return [beat * interval for beat in range(math.ceil(duration / interval))]


def _find_sustained_sections(energies, window_duration):
    smoothing_frames = max(1, round(0.7 / window_duration))
    prefix_sums = [0.0]
    for energy in energies:
        prefix_sums.append(prefix_sums[-1] + energy)

    smoothed = []
    for index in range(len(energies)):
        first = max(0, index - smoothing_frames // 2)
        last = min(len(energies), index + smoothing_frames // 2 + 1)
        smoothed.append((prefix_sums[last] - prefix_sums[first]) / (last - first))

    if len(smoothed) < round(1.2 / window_duration):
        return []

    ordered = sorted(smoothed)
    median_energy = statistics.median(ordered)
    upper_energy = ordered[int((len(ordered) - 1) * 0.85)]
    if upper_energy - median_energy < max(5, upper_energy * 0.08):
        return []

    threshold = median_energy + (upper_energy - median_energy) * 0.45
    active = [energy >= threshold for energy in smoothed]
    sections = []
    first_active = None
    for index, is_active in enumerate(active + [False]):
        if is_active and first_active is None:
            first_active = index
        elif not is_active and first_active is not None:
            start = first_active * window_duration
            end = index * window_duration
            if end - start >= 1.2:
                sections.append((start, end))
            first_active = None
    return sections
