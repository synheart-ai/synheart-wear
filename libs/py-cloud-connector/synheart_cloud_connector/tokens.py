"""Token storage and management with DynamoDB and KMS encryption."""

import base64
from datetime import datetime, timezone
from typing import Any

# Lazy import boto3 - only import when actually needed
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    # Create dummy classes for type hints when boto3 is not available
    class ClientError(Exception):
        pass

from .exceptions import TokenError
from .vendor_types import OAuthTokens, TokenRecord, TokenStatus, VendorType


class TokenStore:
    """
    Manages OAuth token storage in DynamoDB with KMS encryption.

    Schema:
        pk: vendor:user_id
        sk: timestamp (ISO8601)
    """

    def __init__(
        self,
        table_name: str = "cloud_connector_tokens",
        kms_key_id: str | None = None,
        region: str = "us-east-1",
    ):
        self.table_name = table_name
        self.kms_key_id = kms_key_id
        self.region = region

        # Import boto3 only when actually instantiating (lazy import)
        if not HAS_BOTO3:
            raise ImportError(
                "boto3 is required for TokenStore. Install it with: pip install boto3\n"
                "For local development, use MockTokenStore instead."
            )
        import boto3  # Import here to ensure it's available
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.kms = boto3.client("kms", region_name=region)

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a string using KMS."""
        if not self.kms_key_id:
            # For dev/testing without KMS
            return base64.b64encode(plaintext.encode()).decode()

        try:
            response = self.kms.encrypt(
                KeyId=self.kms_key_id,
                Plaintext=plaintext.encode(),
            )
            return base64.b64encode(response["CiphertextBlob"]).decode()
        except ClientError as e:
            raise TokenError(f"KMS encryption failed: {e}") from e

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt a string using KMS."""
        if not self.kms_key_id:
            # For dev/testing without KMS
            return base64.b64decode(ciphertext.encode()).decode()

        try:
            response = self.kms.decrypt(
                CiphertextBlob=base64.b64decode(ciphertext.encode())
            )
            return response["Plaintext"].decode()
        except ClientError as e:
            raise TokenError(f"KMS decryption failed: {e}") from e

    def save_tokens(
        self,
        vendor: VendorType,
        user_id: str,
        tokens: OAuthTokens,
        vendor_meta: dict[str, Any] | None = None,
    ) -> TokenRecord:
        """
        Save encrypted tokens to DynamoDB.

        Args:
            vendor: Vendor type
            user_id: User identifier
            tokens: OAuth token set
            vendor_meta: Optional vendor-specific metadata

        Returns:
            TokenRecord with encrypted tokens
        """
        now = datetime.now(timezone.utc)
        expires_at = int(now.timestamp()) + tokens.expires_in

        # Encrypt tokens
        encrypted_access = self._encrypt(tokens.access_token)
        encrypted_refresh = (
            self._encrypt(tokens.refresh_token) if tokens.refresh_token else None
        )

        record = TokenRecord(
            pk=f"{vendor.value}:{user_id}",
            sk=now.isoformat(),
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_at=expires_at,
            scopes=tokens.scopes,
            status=TokenStatus.ACTIVE,
            vendor_meta=vendor_meta or {},
        )

        try:
            self.table.put_item(Item=record.model_dump())
            return record
        except ClientError as e:
            raise TokenError(
                f"Failed to save tokens for {vendor.value}:{user_id}",
                vendor=vendor.value,
            ) from e

    def get_tokens(self, vendor: VendorType, user_id: str) -> OAuthTokens | None:
        """
        Retrieve and decrypt tokens for a user.

        Args:
            vendor: Vendor type
            user_id: User identifier

        Returns:
            Decrypted OAuthTokens or None if not found
        """
        pk = f"{vendor.value}:{user_id}"

        try:
            # Query for the latest token record
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                ScanIndexForward=False,  # Most recent first
                Limit=1,
            )

            if not response.get("Items"):
                return None

            item = response["Items"][0]
            record = TokenRecord(**item)

            # Check if token is active
            if record.status != TokenStatus.ACTIVE:
                return None

            # Decrypt tokens
            access_token = self._decrypt(record.access_token)
            refresh_token = (
                self._decrypt(record.refresh_token) if record.refresh_token else None
            )

            expires_at = datetime.fromtimestamp(record.expires_at, tz=timezone.utc)
            expires_in = int((expires_at - datetime.now(timezone.utc)).total_seconds())

            return OAuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=max(0, expires_in),
                expires_at=expires_at,
                scopes=record.scopes,
            )

        except ClientError as e:
            raise TokenError(
                f"Failed to retrieve tokens for {vendor.value}:{user_id}",
                vendor=vendor.value,
            ) from e

    def update_last_webhook(self, vendor: VendorType, user_id: str) -> None:
        """Update the last_webhook_at timestamp."""
        pk = f"{vendor.value}:{user_id}"
        now = int(datetime.now(timezone.utc).timestamp())

        try:
            self.table.update_item(
                Key={"pk": pk},
                UpdateExpression="SET last_webhook_at = :ts",
                ExpressionAttributeValues={":ts": now},
            )
        except ClientError as e:
            raise TokenError(
                f"Failed to update webhook timestamp for {vendor.value}:{user_id}",
                vendor=vendor.value,
            ) from e

    def update_last_pull(self, vendor: VendorType, user_id: str) -> None:
        """Update the last_pull_at timestamp."""
        pk = f"{vendor.value}:{user_id}"
        now = int(datetime.now(timezone.utc).timestamp())

        try:
            self.table.update_item(
                Key={"pk": pk},
                UpdateExpression="SET last_pull_at = :ts",
                ExpressionAttributeValues={":ts": now},
            )
        except ClientError as e:
            raise TokenError(
                f"Failed to update pull timestamp for {vendor.value}:{user_id}",
                vendor=vendor.value,
            ) from e

    def revoke_tokens(self, vendor: VendorType, user_id: str) -> None:
        """
        Mark tokens as revoked (soft delete).

        Args:
            vendor: Vendor type
            user_id: User identifier
        """
        pk = f"{vendor.value}:{user_id}"

        try:
            self.table.update_item(
                Key={"pk": pk},
                UpdateExpression="SET #status = :revoked",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":revoked": TokenStatus.REVOKED.value},
            )
        except ClientError as e:
            raise TokenError(
                f"Failed to revoke tokens for {vendor.value}:{user_id}",
                vendor=vendor.value,
            ) from e

    def get_stale_users(self, vendor: VendorType, max_age_seconds: int) -> list[str]:
        """
        Find users who haven't synced data recently.

        Args:
            vendor: Vendor type
            max_age_seconds: Maximum age since last pull

        Returns:
            List of user IDs
        """
        cutoff = int(datetime.now(timezone.utc).timestamp()) - max_age_seconds

        try:
            # Query GSI2 (last_pull_at index)
            response = self.table.query(
                IndexName="GSI2-last-pull-index",
                KeyConditionExpression="vendor = :vendor AND last_pull_at < :cutoff",
                ExpressionAttributeValues={
                    ":vendor": vendor.value,
                    ":cutoff": cutoff,
                },
            )

            items = response.get("Items", [])
            return [item["pk"].split(":")[1] for item in items]

        except ClientError as e:
            raise TokenError(
                f"Failed to query stale users for {vendor.value}",
                vendor=vendor.value,
            ) from e
