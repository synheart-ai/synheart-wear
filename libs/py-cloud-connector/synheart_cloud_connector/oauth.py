"""OAuth 2.0 utilities for token exchange and refresh."""

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from .exceptions import OAuthError, VendorAPIError
from .vendor_types import OAuthTokens


class OAuthHandler:
    """
    Handles OAuth 2.0 authorization code flow and token management.

    Supports:
    - Authorization URL generation
    - Code exchange for tokens
    - Token refresh
    - Token revocation
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
        revoke_url: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.revoke_url = revoke_url

        self.http_client = httpx.AsyncClient(timeout=30.0)

    def build_authorization_url(
        self,
        redirect_uri: str,
        scopes: list[str],
        state: str | None = None,
        **extra_params: Any,
    ) -> str:
        """
        Build OAuth authorization URL.

        Args:
            redirect_uri: Callback URL
            scopes: List of OAuth scopes
            state: Optional state parameter for CSRF protection
            **extra_params: Additional vendor-specific parameters

        Returns:
            Full authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            **extra_params,
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        **extra_params: Any,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from vendor
            redirect_uri: Must match the one used in authorization
            **extra_params: Additional vendor-specific parameters

        Returns:
            OAuthTokens with access and refresh tokens

        Raises:
            OAuthError: If exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            **extra_params,
        }

        try:
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error_description", response.text)
                raise OAuthError(f"Token exchange failed: {error_msg}")

            token_data = response.json()
            return self._parse_token_response(token_data)

        except httpx.RequestError as e:
            raise VendorAPIError(f"Network error during token exchange: {e}") from e

    async def refresh_token(
        self,
        refresh_token: str,
        **extra_params: Any,
    ) -> OAuthTokens:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous exchange
            **extra_params: Additional vendor-specific parameters

        Returns:
            OAuthTokens with new access token

        Raises:
            OAuthError: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            **extra_params,
        }

        try:
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error_description", response.text)
                raise OAuthError(f"Token refresh failed: {error_msg}")

            token_data = response.json()
            return self._parse_token_response(token_data)

        except httpx.RequestError as e:
            raise VendorAPIError(f"Network error during token refresh: {e}") from e

    async def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """
        Revoke an access or refresh token.

        Args:
            token: Token to revoke
            token_type: Type of token (access_token or refresh_token)

        Returns:
            True if revocation succeeded

        Raises:
            OAuthError: If revocation fails
        """
        if not self.revoke_url:
            # Some vendors don't provide revocation endpoint
            return True

        data = {
            "token": token,
            "token_type_hint": token_type,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = await self.http_client.post(
                self.revoke_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # RFC 7009: successful revocations return 200
            return response.status_code == 200

        except httpx.RequestError as e:
            raise VendorAPIError(f"Network error during token revocation: {e}") from e

    def _parse_token_response(self, data: dict[str, Any]) -> OAuthTokens:
        """
        Parse vendor token response into OAuthTokens.

        Args:
            data: Token response from vendor

        Returns:
            OAuthTokens object
        """
        access_token = data.get("access_token")
        if not access_token:
            raise OAuthError("Missing access_token in response")

        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)  # Default 1 hour

        # Calculate absolute expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Parse scopes (can be string or list)
        scope = data.get("scope", "")
        scopes = scope.split(" ") if isinstance(scope, str) else scope

        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
            scopes=scopes,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def __aenter__(self) -> "OAuthHandler":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        await self.close()
