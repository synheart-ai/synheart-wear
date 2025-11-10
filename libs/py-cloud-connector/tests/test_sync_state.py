"""Tests for sync state management."""

import os
from datetime import datetime, timezone

import pytest

from synheart_cloud_connector.sync_state import SyncState, SyncCursor
from synheart_cloud_connector.vendor_types import VendorType


@pytest.fixture
def sync_state():
    """Create SyncState in local mode for testing."""
    os.environ["LOCAL_MODE"] = "true"
    return SyncState()


def test_get_cursor_not_exists(sync_state):
    """Test getting cursor that doesn't exist."""
    cursor = sync_state.get_cursor(VendorType.WHOOP, "user123")
    assert cursor is None


def test_update_cursor_new(sync_state):
    """Test creating new cursor."""
    now = datetime.now(timezone.utc).isoformat()

    cursor = sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
        records_synced=10,
    )

    assert cursor.vendor == "whoop"
    assert cursor.user_id == "user123"
    assert cursor.last_sync_ts == now
    assert cursor.records_synced == 10
    assert cursor.created_at is not None
    assert cursor.updated_at is not None


def test_get_cursor_exists(sync_state):
    """Test getting cursor that exists."""
    now = datetime.now(timezone.utc).isoformat()

    # Create cursor
    sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
        records_synced=10,
    )

    # Get cursor
    cursor = sync_state.get_cursor(VendorType.WHOOP, "user123")

    assert cursor is not None
    assert cursor.vendor == "whoop"
    assert cursor.user_id == "user123"
    assert cursor.last_sync_ts == now
    assert cursor.records_synced == 10


def test_update_cursor_incremental(sync_state):
    """Test incrementing records_synced."""
    now = datetime.now(timezone.utc).isoformat()

    # First sync: 10 records
    sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
        records_synced=10,
    )

    # Second sync: 5 more records
    later = datetime.now(timezone.utc).isoformat()
    cursor = sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=later,
        records_synced=5,
    )

    assert cursor.records_synced == 15  # 10 + 5
    assert cursor.last_sync_ts == later


def test_reset_cursor(sync_state):
    """Test resetting cursor."""
    now = datetime.now(timezone.utc).isoformat()

    # Create cursor
    sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
        records_synced=10,
    )

    # Reset cursor
    sync_state.reset_cursor(VendorType.WHOOP, "user123")

    # Verify it's gone
    cursor = sync_state.get_cursor(VendorType.WHOOP, "user123")
    assert cursor is None


def test_get_last_sync_timestamp(sync_state):
    """Test convenience method for getting timestamp."""
    now = datetime.now(timezone.utc).isoformat()

    # No cursor exists
    ts = sync_state.get_last_sync_timestamp(VendorType.WHOOP, "user123")
    assert ts is None

    # Create cursor
    sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
    )

    # Get timestamp
    ts = sync_state.get_last_sync_timestamp(VendorType.WHOOP, "user123")
    assert ts == now


def test_has_synced_before(sync_state):
    """Test checking if user has synced."""
    # Never synced
    assert not sync_state.has_synced_before(VendorType.WHOOP, "user123")

    # Create cursor
    now = datetime.now(timezone.utc).isoformat()
    sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
    )

    # Now has synced
    assert sync_state.has_synced_before(VendorType.WHOOP, "user123")


def test_list_cursors(sync_state):
    """Test listing cursors."""
    now = datetime.now(timezone.utc).isoformat()

    # Create cursors for different vendors
    sync_state.update_cursor(VendorType.WHOOP, "user1", now, 10)
    sync_state.update_cursor(VendorType.WHOOP, "user2", now, 20)
    sync_state.update_cursor(VendorType.GARMIN, "user3", now, 30)

    # List all
    cursors = sync_state.list_cursors()
    assert len(cursors) == 3

    # List WHOOP only
    cursors = sync_state.list_cursors(vendor=VendorType.WHOOP)
    assert len(cursors) == 2
    assert all(c.vendor == "whoop" for c in cursors)

    # List GARMIN only
    cursors = sync_state.list_cursors(vendor=VendorType.GARMIN)
    assert len(cursors) == 1
    assert cursors[0].vendor == "garmin"


def test_multiple_vendors_same_user(sync_state):
    """Test same user ID across different vendors."""
    now = datetime.now(timezone.utc).isoformat()

    # Same user, different vendors
    sync_state.update_cursor(VendorType.WHOOP, "user123", now, 10)
    sync_state.update_cursor(VendorType.GARMIN, "user123", now, 20)

    # Each should be independent
    whoop_cursor = sync_state.get_cursor(VendorType.WHOOP, "user123")
    garmin_cursor = sync_state.get_cursor(VendorType.GARMIN, "user123")

    assert whoop_cursor.records_synced == 10
    assert garmin_cursor.records_synced == 20


def test_last_resource_id(sync_state):
    """Test storing last resource ID for pagination."""
    now = datetime.now(timezone.utc).isoformat()

    cursor = sync_state.update_cursor(
        VendorType.WHOOP,
        "user123",
        last_sync_ts=now,
        records_synced=10,
        last_resource_id="resource_abc123",
    )

    assert cursor.last_resource_id == "resource_abc123"

    # Verify it persists
    cursor2 = sync_state.get_cursor(VendorType.WHOOP, "user123")
    assert cursor2.last_resource_id == "resource_abc123"
