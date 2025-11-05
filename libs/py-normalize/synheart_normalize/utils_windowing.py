"""Windowing utilities for HRV and RR interval processing."""

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .schema import SynheartSample


def calculate_rmssd(rr_intervals_ms: list[float]) -> float:
    """
    Calculate RMSSD (Root Mean Square of Successive Differences) from RR intervals.

    RMSSD is a time-domain measure of HRV.

    Args:
        rr_intervals_ms: List of RR intervals in milliseconds

    Returns:
        RMSSD in milliseconds
    """
    if len(rr_intervals_ms) < 2:
        raise ValueError("Need at least 2 RR intervals to calculate RMSSD")

    # Calculate successive differences
    rr_array = np.array(rr_intervals_ms)
    successive_diffs = np.diff(rr_array)

    # Square the differences
    squared_diffs = successive_diffs**2

    # Mean of squared differences
    mean_squared = np.mean(squared_diffs)

    # Root of the mean
    rmssd = np.sqrt(mean_squared)

    return float(rmssd)


def window_samples(
    samples: list[SynheartSample],
    window_size_minutes: int = 5,
) -> list[dict[str, Any]]:
    """
    Group samples into time windows and calculate aggregate metrics.

    Args:
        samples: List of SynheartSample objects
        window_size_minutes: Size of time window in minutes

    Returns:
        List of windowed aggregates
    """
    if not samples:
        return []

    # Sort samples by timestamp
    sorted_samples = sorted(samples, key=lambda s: s.timestamp_utc)

    windows = []
    current_window_start = sorted_samples[0].timestamp_utc
    current_window_samples: list[SynheartSample] = []

    window_delta = timedelta(minutes=window_size_minutes)

    for sample in sorted_samples:
        # Check if sample belongs to current window
        if sample.timestamp_utc < current_window_start + window_delta:
            current_window_samples.append(sample)
        else:
            # Process current window
            if current_window_samples:
                windows.append(_aggregate_window(current_window_samples, current_window_start))

            # Start new window
            current_window_start = sample.timestamp_utc
            current_window_samples = [sample]

    # Process final window
    if current_window_samples:
        windows.append(_aggregate_window(current_window_samples, current_window_start))

    return windows


def _aggregate_window(
    samples: list[SynheartSample],
    window_start: datetime,
) -> dict[str, Any]:
    """
    Aggregate metrics for a single time window.

    Args:
        samples: Samples in this window
        window_start: Start timestamp of window

    Returns:
        Aggregated metrics
    """
    hr_values = [s.hr_bpm for s in samples if s.hr_bpm is not None]
    hrv_values = [s.hrv_rmssd_ms for s in samples if s.hrv_rmssd_ms is not None]
    rr_intervals: list[float] = []

    for s in samples:
        if s.rr_intervals_ms:
            rr_intervals.extend(s.rr_intervals_ms)

    aggregate = {
        "window_start": window_start,
        "window_end": samples[-1].timestamp_utc,
        "sample_count": len(samples),
        "source": samples[0].source.value,
    }

    # Heart rate statistics
    if hr_values:
        aggregate["hr_avg"] = float(np.mean(hr_values))
        aggregate["hr_min"] = float(np.min(hr_values))
        aggregate["hr_max"] = float(np.max(hr_values))
        aggregate["hr_std"] = float(np.std(hr_values))

    # HRV statistics
    if hrv_values:
        aggregate["hrv_avg"] = float(np.mean(hrv_values))
        aggregate["hrv_min"] = float(np.min(hrv_values))
        aggregate["hrv_max"] = float(np.max(hrv_values))
        aggregate["hrv_std"] = float(np.std(hrv_values))

    # Calculate RMSSD from RR intervals if available
    if len(rr_intervals) >= 2:
        try:
            aggregate["hrv_rmssd_calculated"] = calculate_rmssd(rr_intervals)
        except ValueError:
            pass

    return aggregate


def detect_outliers(
    samples: list[SynheartSample],
    metric: str = "hr_bpm",
    std_threshold: float = 3.0,
) -> list[SynheartSample]:
    """
    Detect and remove outliers using standard deviation method.

    Args:
        samples: List of samples
        metric: Metric to check for outliers
        std_threshold: Number of standard deviations for outlier threshold

    Returns:
        Filtered list without outliers
    """
    if not samples:
        return []

    # Extract metric values
    values = []
    for sample in samples:
        value = getattr(sample, metric, None)
        if value is not None:
            values.append(value)

    if len(values) < 3:
        # Not enough data for outlier detection
        return samples

    # Calculate mean and std
    mean = np.mean(values)
    std = np.std(values)

    # Filter outliers
    filtered = []
    for sample in samples:
        value = getattr(sample, metric, None)
        if value is None:
            # Keep samples without this metric
            filtered.append(sample)
        else:
            # Check if within threshold
            if abs(value - mean) <= std_threshold * std:
                filtered.append(sample)

    return filtered


def interpolate_missing_samples(
    samples: list[SynheartSample],
    interval_seconds: int = 60,
) -> list[SynheartSample]:
    """
    Interpolate missing samples at regular intervals.

    Args:
        samples: List of samples (must be sorted by timestamp)
        interval_seconds: Expected interval between samples

    Returns:
        List with interpolated samples
    """
    if len(samples) < 2:
        return samples

    result = []
    interval_delta = timedelta(seconds=interval_seconds)

    for i in range(len(samples) - 1):
        current = samples[i]
        next_sample = samples[i + 1]

        result.append(current)

        # Check if there's a gap
        expected_next = current.timestamp_utc + interval_delta
        time_diff = (next_sample.timestamp_utc - current.timestamp_utc).total_seconds()

        if time_diff > interval_seconds * 1.5:
            # Gap detected - interpolate
            num_missing = int(time_diff // interval_seconds) - 1

            for j in range(1, num_missing + 1):
                interpolated_time = current.timestamp_utc + (interval_delta * j)

                # Linear interpolation of HR if available
                interpolated_hr = None
                if current.hr_bpm is not None and next_sample.hr_bpm is not None:
                    ratio = j / (num_missing + 1)
                    interpolated_hr = current.hr_bpm + (
                        next_sample.hr_bpm - current.hr_bpm
                    ) * ratio

                # Create interpolated sample
                interpolated = SynheartSample(
                    timestamp_utc=interpolated_time,
                    source=current.source,
                    sample_type=current.sample_type,
                    hr_bpm=interpolated_hr,
                    meta={"interpolated": True},
                )
                result.append(interpolated)

    # Add the last sample
    result.append(samples[-1])

    return result
