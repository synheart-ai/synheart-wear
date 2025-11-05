"""Tests for token storage functionality.

Note: These tests require moto for AWS mocking.
Run with: pytest tests/test_tokens.py
"""

from datetime import datetime, timezone

import pytest

from synheart_cloud_connector.exceptions import TokenError
from synheart_cloud_connector.tokens import TokenStore
from synheart_cloud_connector.vendor_types import OAuthTokens, TokenStatus, VendorType

# Import moto for mocking AWS services
try:
    from moto import mock_dynamodb, mock_kms
    import boto3

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_dynamodb = lambda: lambda f: f
    mock_kms = lambda: lambda f: f


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestTokenStore:
    """Tests for TokenStore class with mocked AWS."""

    @pytest.fixture
    def dynamodb_table(self):
        """Create mocked DynamoDB table."""
        with mock_dynamodb():
            # Create DynamoDB resource
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

            # Create table
            table = dynamodb.create_table(
                TableName="test_tokens",
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            yield table

    @pytest.fixture
    def token_store(self, dynamodb_table):
        """Create TokenStore instance with mocked table."""
        with mock_dynamodb():
            return TokenStore(
                table_name="test_tokens",
                kms_key_id=None,  # Skip KMS for testing
                region="us-east-1",
            )

    def test_save_tokens(self, token_store):
        """Test saving tokens to DynamoDB."""
        tokens = OAuthTokens(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_in=3600,
            scopes=["read:data", "write:data"],
        )

        record = token_store.save_tokens(
            vendor=VendorType.WHOOP,
            user_id="user123",
            tokens=tokens,
        )

        assert record.pk == "whoop:user123"
        assert record.access_token is not None  # Should be encrypted
        assert record.status == TokenStatus.ACTIVE

    def test_get_tokens(self, token_store):
        """Test retrieving tokens from DynamoDB."""
        # First save tokens
        original_tokens = OAuthTokens(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_in=3600,
            scopes=["read:data"],
        )

        token_store.save_tokens(
            vendor=VendorType.WHOOP,
            user_id="user123",
            tokens=original_tokens,
        )

        # Retrieve tokens
        retrieved = token_store.get_tokens(VendorType.WHOOP, "user123")

        assert retrieved is not None
        assert retrieved.access_token == "test_access_token"
        assert retrieved.refresh_token == "test_refresh_token"
        assert "read:data" in retrieved.scopes

    def test_get_tokens_not_found(self, token_store):
        """Test retrieving non-existent tokens."""
        tokens = token_store.get_tokens(VendorType.WHOOP, "nonexistent_user")
        assert tokens is None

    def test_revoke_tokens(self, token_store):
        """Test revoking tokens."""
        # Save tokens first
        tokens = OAuthTokens(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_in=3600,
        )

        token_store.save_tokens(VendorType.WHOOP, "user123", tokens)

        # Revoke tokens
        token_store.revoke_tokens(VendorType.WHOOP, "user123")

        # Should not retrieve revoked tokens
        retrieved = token_store.get_tokens(VendorType.WHOOP, "user123")
        assert retrieved is None  # Status is REVOKED

    def test_update_last_webhook(self, token_store):
        """Test updating webhook timestamp."""
        # Save tokens first
        tokens = OAuthTokens(
            access_token="test_token",
            expires_in=3600,
        )

        token_store.save_tokens(VendorType.WHOOP, "user123", tokens)

        # Update webhook timestamp
        token_store.update_last_webhook(VendorType.WHOOP, "user123")

        # Verify timestamp was updated (would need to query DynamoDB directly)
        # This is a basic test that it doesn't raise an error

    def test_update_last_pull(self, token_store):
        """Test updating pull timestamp."""
        tokens = OAuthTokens(
            access_token="test_token",
            expires_in=3600,
        )

        token_store.save_tokens(VendorType.WHOOP, "user123", tokens)

        # Update pull timestamp
        token_store.update_last_pull(VendorType.WHOOP, "user123")

        # Basic test that it doesn't raise an error


class TestTokenStoreWithoutMocks:
    """Tests that don't require AWS mocking."""

    def test_encrypt_decrypt_without_kms(self):
        """Test encryption/decryption without KMS (base64)."""
        store = TokenStore(table_name="test", kms_key_id=None)

        plaintext = "test_secret_token"
        encrypted = store._encrypt(plaintext)
        decrypted = store._decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Should be different

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt/decrypt are inverse operations."""
        store = TokenStore(table_name="test", kms_key_id=None)

        original = "my_secret_access_token_12345"
        encrypted = store._encrypt(original)
        decrypted = store._decrypt(encrypted)

        assert decrypted == original
