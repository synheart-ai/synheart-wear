"""Normalization functions to convert vendor data to Synheart schema."""

from datetime import datetime
from typing import Any

from .schema import DataSource, SampleType, SynheartSample


def normalize_to_synheart(
    vendor_data: dict[str, Any],
    source: DataSource,
    sample_type: SampleType,
) -> SynheartSample:
    """
    Normalize vendor-specific data to Synheart schema.

    This function dispatches to vendor-specific normalizers.

    Args:
        vendor_data: Raw data from vendor API
        source: Data source vendor
        sample_type: Type of measurement

    Returns:
        Normalized SynheartSample
    """
    normalizers = {
        DataSource.WHOOP: normalize_whoop,
        DataSource.GARMIN: normalize_garmin,
        DataSource.FITBIT: normalize_fitbit,
        DataSource.POLAR: normalize_polar,
        DataSource.OURA: normalize_oura,
    }

    normalizer = normalizers.get(source)
    if not normalizer:
        raise ValueError(f"No normalizer for source: {source}")

    return normalizer(vendor_data, sample_type)


def normalize_whoop(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """
    Normalize WHOOP data to Synheart schema.

    WHOOP provides:
    - Recovery data (HRV, resting HR, recovery score)
    - Sleep data (stages, quality, duration)
    - Workout data (strain, calories, HR zones)
    """
    timestamp = vendor_data.get("created_at") or vendor_data.get("start")

    if sample_type == SampleType.RECOVERY:
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.WHOOP,
            sample_type=SampleType.RECOVERY,
            hrv_rmssd_ms=vendor_data.get("score", {}).get("hrv_rmssd_milli"),
            resting_hr=vendor_data.get("score", {}).get("resting_heart_rate"),
            recovery_score=vendor_data.get("score", {}).get("recovery_score"),
            meta={
                "whoop_recovery_id": vendor_data.get("id"),
                "user_calibrating": vendor_data.get("score", {}).get("user_calibrating"),
            },
        )

    if sample_type == SampleType.SLEEP:
        sleep_data = vendor_data.get("score", {})
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.WHOOP,
            sample_type=SampleType.SLEEP,
            sleep_score=sleep_data.get("stage_summary", {}).get("total_sleep_time_milli"),
            hrv_rmssd_ms=sleep_data.get("hrv_rmssd_milli"),
            resting_hr=sleep_data.get("average_heart_rate"),
            meta={
                "whoop_sleep_id": vendor_data.get("id"),
                "sleep_stages": sleep_data.get("stage_summary"),
                "sleep_efficiency": sleep_data.get("sleep_efficiency_percentage"),
            },
        )

    if sample_type == SampleType.WORKOUT:
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.WHOOP,
            sample_type=SampleType.WORKOUT,
            hr_bpm=vendor_data.get("score", {}).get("average_heart_rate"),
            calories=vendor_data.get("score", {}).get("kilojoule"),
            meta={
                "whoop_workout_id": vendor_data.get("id"),
                "strain": vendor_data.get("score", {}).get("strain"),
                "zone_duration": vendor_data.get("score", {}).get("zone_duration"),
            },
        )

    raise ValueError(f"Unsupported WHOOP sample type: {sample_type}")


def normalize_garmin(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """
    Normalize Garmin Health API data to Synheart schema.

    Garmin provides:
    - Daily summaries (steps, calories, HR, stress)
    - Sleep tracking (stages, quality, duration)
    - Activity data (workouts, sports)
    - Heart rate data
    - Stress levels
    """
    # Garmin uses various timestamp fields
    timestamp = (
        vendor_data.get("calendarDate")
        or vendor_data.get("startTimeInSeconds")
        or vendor_data.get("summaryId")
    )

    if sample_type == SampleType.ACTIVITY:
        # Daily summary data
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.GARMIN,
            sample_type=SampleType.ACTIVITY,
            hr_bpm=vendor_data.get("restingHeartRateInBeatsPerMinute"),
            steps=vendor_data.get("totalSteps"),
            calories=vendor_data.get("activeKilocalories"),
            distance_meters=vendor_data.get("totalDistanceInMeters"),
            meta={
                "garmin_summary_id": vendor_data.get("summaryId"),
                "calendar_date": vendor_data.get("calendarDate"),
                "moderate_intensity_minutes": vendor_data.get("moderateIntensityDurationInSeconds"),
                "vigorous_intensity_minutes": vendor_data.get("vigorousIntensityDurationInSeconds"),
                "floors_climbed": vendor_data.get("floorsClimbed"),
            },
        )

    if sample_type == SampleType.SLEEP:
        sleep_levels = vendor_data.get("sleepLevelsMap", {})
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.GARMIN,
            sample_type=SampleType.SLEEP,
            sleep_score=vendor_data.get("sleepScores", {}).get("overall", {}).get("value"),
            resting_hr=vendor_data.get("averageHeartRateInBeatsPerMinute"),
            hrv_rmssd_ms=vendor_data.get("avgOvernightHrvValue"),
            meta={
                "garmin_sleep_id": vendor_data.get("dailySleepDTO", {}).get("id"),
                "sleep_start": vendor_data.get("sleepStartTimestampGMT"),
                "sleep_end": vendor_data.get("sleepEndTimestampGMT"),
                "deep_sleep_seconds": sleep_levels.get("DEEP", {}).get("seconds"),
                "light_sleep_seconds": sleep_levels.get("LIGHT", {}).get("seconds"),
                "rem_sleep_seconds": sleep_levels.get("REM", {}).get("seconds"),
                "awake_seconds": sleep_levels.get("AWAKE", {}).get("seconds"),
                "avg_respiration": vendor_data.get("averageRespirationValue"),
                "avg_spo2": vendor_data.get("averageSpo2Value"),
            },
        )

    if sample_type == SampleType.HEART_RATE:
        # Heart rate data point
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.GARMIN,
            sample_type=SampleType.HEART_RATE,
            hr_bpm=vendor_data.get("heartRate") or vendor_data.get("value"),
            meta={
                "garmin_timestamp": vendor_data.get("timestampInSeconds"),
            },
        )

    if sample_type == SampleType.HRV:
        # Stress/HRV data
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.GARMIN,
            sample_type=SampleType.HRV,
            hrv_rmssd_ms=vendor_data.get("hrvValue"),
            meta={
                "garmin_summary_id": vendor_data.get("summaryId"),
                "stress_level": vendor_data.get("bodyBatteryMostRecentValue"),
                "max_stress": vendor_data.get("maxStressLevel"),
                "avg_stress": vendor_data.get("avgStressLevel"),
                "rest_stress": vendor_data.get("restStressLevel"),
            },
        )

    if sample_type == SampleType.WORKOUT:
        # Activity/workout data
        return SynheartSample(
            timestamp_utc=timestamp,
            source=DataSource.GARMIN,
            sample_type=SampleType.WORKOUT,
            hr_bpm=vendor_data.get("averageHeartRateInBeatsPerMinute"),
            calories=vendor_data.get("activeKilocalories"),
            distance_meters=vendor_data.get("distanceInMeters"),
            meta={
                "garmin_activity_id": vendor_data.get("activityId"),
                "activity_type": vendor_data.get("activityType"),
                "duration_seconds": vendor_data.get("durationInSeconds"),
                "avg_pace": vendor_data.get("averagePaceInMinutesPerKilometer"),
                "max_hr": vendor_data.get("maxHeartRateInBeatsPerMinute"),
                "elevation_gain": vendor_data.get("elevationGainInMeters"),
            },
        )

    raise ValueError(f"Unsupported Garmin sample type: {sample_type}")


def normalize_fitbit(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """Normalize Fitbit data to Synheart schema."""
    # TODO: Implement Fitbit normalization
    raise NotImplementedError("Fitbit normalization not yet implemented")


def normalize_polar(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """Normalize Polar data to Synheart schema."""
    # TODO: Implement Polar normalization
    raise NotImplementedError("Polar normalization not yet implemented")


def normalize_oura(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """Normalize Oura data to Synheart schema."""
    # TODO: Implement Oura normalization
    raise NotImplementedError("Oura normalization not yet implemented")
