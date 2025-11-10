"""Unified schema for Synheart wearable data."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DataSource(str, Enum):
    """Supported data sources."""

    WHOOP = "whoop"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    POLAR = "polar"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"


class SampleType(str, Enum):
    """Type of sample data."""

    HEART_RATE = "heart_rate"
    HRV = "hrv"
    RR_INTERVALS = "rr_intervals"
    SLEEP = "sleep"
    RECOVERY = "recovery"
    WORKOUT = "workout"
    ACTIVITY = "activity"


class SynheartSample(BaseModel):
    """
    Unified data sample from wearable devices.

    This is the canonical schema that all vendor data is normalized to.
    """

    # Identifiers
    timestamp_utc: datetime = Field(
        ...,
        description="UTC timestamp of the measurement",
    )
    source: DataSource = Field(
        ...,
        description="Data source (vendor)",
    )
    sample_type: SampleType = Field(
        ...,
        description="Type of measurement",
    )

    # Biometric data
    hr_bpm: float | None = Field(
        None,
        description="Heart rate in beats per minute",
        ge=20,
        le=300,
    )
    hrv_rmssd_ms: float | None = Field(
        None,
        description="HRV RMSSD in milliseconds",
        ge=0,
        le=500,
    )
    rr_intervals_ms: list[float] | None = Field(
        None,
        description="RR intervals in milliseconds",
    )

    # Sleep metrics
    sleep_stage: str | None = Field(
        None,
        description="Sleep stage (light, deep, rem, awake)",
    )
    sleep_score: float | None = Field(
        None,
        description="Sleep quality score (0-100)",
        ge=0,
        le=100,
    )

    # Recovery metrics
    recovery_score: float | None = Field(
        None,
        description="Recovery score (0-100)",
        ge=0,
        le=100,
    )
    resting_hr: float | None = Field(
        None,
        description="Resting heart rate",
        ge=20,
        le=200,
    )

    # Activity metrics
    calories: float | None = Field(
        None,
        description="Calories burned",
        ge=0,
    )
    steps: int | None = Field(
        None,
        description="Step count",
        ge=0,
    )
    distance_meters: float | None = Field(
        None,
        description="Distance in meters",
        ge=0,
    )

    # Metadata
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Vendor-specific metadata and additional fields",
    )

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            from dateutil import parser

            return parser.parse(v)
        if isinstance(v, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(v)
        raise ValueError(f"Invalid timestamp format: {v}")

    @field_validator("rr_intervals_ms")
    @classmethod
    def validate_rr_intervals(cls, v: list[float] | None) -> list[float] | None:
        """Validate RR intervals are in reasonable range."""
        if v is None:
            return v

        # RR intervals should be between 200ms and 3000ms (20-300 BPM)
        for interval in v:
            if interval < 200 or interval > 3000:
                raise ValueError(f"RR interval {interval}ms out of range (200-3000ms)")

        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json()


class SampleBatch(BaseModel):
    """Batch of samples from a vendor."""

    source: DataSource
    samples: list[SynheartSample]
    total_count: int
    start_time: datetime
    end_time: datetime
    meta: dict[str, Any] = Field(default_factory=dict)
