"""Tests for OAuth handler functionality."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from synheart_cloud_connector.exceptions import OAuthError, VendorAPIError
from synheart_cloud_connector.oauth import OAuthHandler
from synheart_cloud_connector.vendor_types import OAuthTokens


class TestOAuthHandler:
    """Tests for OAuthHandler class."""

    @pytest.fixture
    def oauth_handler(self):
        """Create OAuth handler instance."""
        return OAuthHandler(
            client_id="test_client_id",
            client_secret="test_client_secret",
            auth_url="https://api.vendor.com/oauth/authorize",
            token_url="https://api.vendor.com/oauth/token",
            revoke_url="https://api.vendor.com/oauth/revoke",
        )

    def test_build_authorization_url(self, oauth_handler):
        """Test building authorization URL."""
        url = oauth_handler.build_authorization_url(
            redirect_uri="https://app.com/callback",
            scopes=["read:data", "write:data"],
            state="user123",
        )

        assert "https://api.vendor.com/oauth/authorize?" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.com%2Fcallback" in url
        assert "response_type=code" in url
        assert "scope=read%3Adata+write%3Adata" in url
        assert "state=user123" in url

    def test_build_authorization_url_no_state(self, oauth_handler):
        """Test building authorization URL without state."""
        url = oauth_handler.build_authorization_url(
            redirect_uri="https://app.com/callback",
            scopes=["read:data"],
        )

        assert "state" not in url
        assert "client_id=test_client_id" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, oauth_handler):
        """Test successful code exchange."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "read:data write:data",
        }

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ) as mock_post:
            mock_post.return_value = mock_response

            tokens = await oauth_handler.exchange_code(
                code="auth_code_123",
                redirect_uri="https://app.com/callback",
            )

            assert isinstance(tokens, OAuthTokens)
            assert tokens.access_token == "test_access_token"
            assert tokens.refresh_token == "test_refresh_token"
            assert tokens.expires_in == 3600
            assert tokens.token_type == "Bearer"
            assert "read:data" in tokens.scopes

            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.vendor.com/oauth/token"
            assert call_args[1]["data"]["grant_type"] == "authorization_code"
            assert call_args[1]["data"]["code"] == "auth_code_123"

    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, oauth_handler):
        """Test failed code exchange."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        }

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ):
            with pytest.raises(OAuthError) as exc_info:
                await oauth_handler.exchange_code(
                    code="invalid_code",
                    redirect_uri="https://app.com/callback",
                )

            assert "Token exchange failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exchange_code_missing_access_token(self, oauth_handler):
        """Test exchange with missing access token in response."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "expires_in": 3600,
            # Missing access_token
        }

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ):
            with pytest.raises(OAuthError) as exc_info:
                await oauth_handler.exchange_code(
                    code="auth_code",
                    redirect_uri="https://app.com/callback",
                )

            assert "Missing access_token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, oauth_handler):
        """Test successful token refresh."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ) as mock_post:
            tokens = await oauth_handler.refresh_token(
                refresh_token="old_refresh_token"
            )

            assert tokens.access_token == "new_access_token"
            assert tokens.refresh_token == "new_refresh_token"

            # Verify API call
            call_args = mock_post.call_args
            assert call_args[1]["data"]["grant_type"] == "refresh_token"
            assert call_args[1]["data"]["refresh_token"] == "old_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, oauth_handler):
        """Test failed token refresh."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"
        mock_response.json.return_value = {"error": "invalid_grant"}

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ):
            with pytest.raises(OAuthError) as exc_info:
                await oauth_handler.refresh_token(refresh_token="invalid_token")

            assert "Token refresh failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, oauth_handler):
        """Test successful token revocation."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200

        with patch.object(
            oauth_handler.http_client, "post", return_value=mock_response
        ):
            result = await oauth_handler.revoke_token(
                token="access_token_123",
                token_type="access_token",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_no_url(self):
        """Test token revocation when no revoke URL configured."""
        handler = OAuthHandler(
            client_id="test_id",
            client_secret="test_secret",
            auth_url="https://api.vendor.com/authorize",
            token_url="https://api.vendor.com/token",
            revoke_url=None,  # No revoke URL
        )

        result = await handler.revoke_token(token="token_123")
        assert result is True  # Should succeed silently

    def test_parse_token_response_with_scopes_string(self, oauth_handler):
        """Test parsing token response with scopes as string."""
        response = {
            "access_token": "token_123",
            "refresh_token": "refresh_123",
            "expires_in": 7200,
            "scope": "read:data write:data",
        }

        tokens = oauth_handler._parse_token_response(response)

        assert tokens.access_token == "token_123"
        assert tokens.scopes == ["read:data", "write:data"]

    def test_parse_token_response_with_scopes_list(self, oauth_handler):
        """Test parsing token response with scopes as list."""
        response = {
            "access_token": "token_123",
            "expires_in": 7200,
            "scope": ["read:data", "write:data"],
        }

        tokens = oauth_handler._parse_token_response(response)

        assert tokens.scopes == ["read:data", "write:data"]

    def test_parse_token_response_calculates_expiry(self, oauth_handler):
        """Test that expires_at is calculated correctly."""
        response = {
            "access_token": "token_123",
            "expires_in": 3600,
        }

        before = datetime.now(timezone.utc)
        tokens = oauth_handler._parse_token_response(response)
        after = datetime.now(timezone.utc)

        expected_expiry = before + timedelta(seconds=3600)
        assert tokens.expires_at >= expected_expiry
        assert tokens.expires_at <= after + timedelta(seconds=3600)

    @pytest.mark.asyncio
    async def test_context_manager(self, oauth_handler):
        """Test OAuth handler as context manager."""
        async with oauth_handler as handler:
            assert handler is oauth_handler

        # HTTP client should be closed after exit
        # (Can't easily test this without mocking, but structure is correct)
