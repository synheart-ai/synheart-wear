"""Job queue management using AWS SQS."""

import json
import uuid
from datetime import datetime, timezone

# Lazy import boto3 - only import when actually needed (not during module import)
# This allows local dev mode to work without boto3 installed
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    # Create dummy classes for type hints when boto3 is not available
    class ClientError(Exception):
        pass

from .exceptions import EnqueueError
from .vendor_types import SQSMessage, VendorType, WebhookEvent


class JobQueue:
    """
    Manages job enqueueing and processing with AWS SQS.

    Features:
    - Idempotency via message deduplication
    - Exponential backoff retry logic
    - Dead letter queue for failed jobs
    """

    def __init__(
        self,
        queue_url: str | None = None,
        queue_name: str = "cloud-connector-events",
        region: str = "us-east-1",
    ):
        if not HAS_BOTO3:
            raise ImportError(
                "boto3 is required for JobQueue. Install it with: pip install boto3\n"
                "For local development, use MockJobQueue instead."
            )
        self.queue_name = queue_name
        self.region = region

        # Import boto3 only when actually instantiating (lazy import)
        import boto3  # Import here to ensure it's available
        self.sqs = boto3.client("sqs", region_name=region)

        # Get queue URL if not provided
        if queue_url:
            self.queue_url = queue_url
        else:
            try:
                response = self.sqs.get_queue_url(QueueName=queue_name)
                self.queue_url = response["QueueUrl"]
            except ClientError as e:
                raise EnqueueError(f"Failed to get queue URL for {queue_name}") from e

    def enqueue_event(
        self,
        event: WebhookEvent,
        delay_seconds: int = 0,
    ) -> str:
        """
        Enqueue a webhook event for processing.

        Args:
            event: Parsed webhook event
            delay_seconds: Optional delay before message becomes visible

        Returns:
            SQS message ID
        """
        message = SQSMessage(
            vendor=event.vendor,
            event_type=event.event_type,
            user_id=event.user_id,
            resource_id=event.resource_id,
            trace_id=event.trace_id,
            received_at=event.received_at,
            retries=0,
            payload=event.payload,
        )

        return self._send_message(message, delay_seconds)

    def enqueue_backfill(
        self,
        vendor: VendorType,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """
        Enqueue a backfill job for a date range.

        Args:
            vendor: Vendor type
            user_id: User identifier
            start_date: Start of date range
            end_date: End of date range

        Returns:
            SQS message ID
        """
        message = SQSMessage(
            vendor=vendor,
            event_type="backfill.requested",
            user_id=user_id,
            resource_id=None,
            trace_id=str(uuid.uuid4()),
            received_at=datetime.now(timezone.utc),
            retries=0,
            payload={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        return self._send_message(message)

    def _send_message(
        self,
        message: SQSMessage,
        delay_seconds: int = 0,
    ) -> str:
        """
        Send a message to SQS.

        Args:
            message: Message to send
            delay_seconds: Optional delay

        Returns:
            SQS message ID
        """
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message.model_dump_json(),
                DelaySeconds=delay_seconds,
                MessageAttributes={
                    "vendor": {
                        "StringValue": message.vendor.value,
                        "DataType": "String",
                    },
                    "event_type": {
                        "StringValue": message.event_type,
                        "DataType": "String",
                    },
                    "trace_id": {
                        "StringValue": message.trace_id,
                        "DataType": "String",
                    },
                },
                # Use trace_id for deduplication (FIFO queues)
                MessageDeduplicationId=message.trace_id,
                MessageGroupId=f"{message.vendor.value}:{message.user_id}",
            )

            return response["MessageId"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle non-FIFO queues (no deduplication)
            if error_code == "InvalidParameterValue":
                try:
                    response = self.sqs.send_message(
                        QueueUrl=self.queue_url,
                        MessageBody=message.model_dump_json(),
                        DelaySeconds=delay_seconds,
                        MessageAttributes={
                            "vendor": {
                                "StringValue": message.vendor.value,
                                "DataType": "String",
                            },
                            "event_type": {
                                "StringValue": message.event_type,
                                "DataType": "String",
                            },
                            "trace_id": {
                                "StringValue": message.trace_id,
                                "DataType": "String",
                            },
                        },
                    )
                    return response["MessageId"]
                except ClientError as retry_error:
                    raise EnqueueError(
                        f"Failed to enqueue message: {retry_error}",
                        vendor=message.vendor.value,
                        trace_id=message.trace_id,
                    ) from retry_error

            raise EnqueueError(
                f"Failed to enqueue message: {e}",
                vendor=message.vendor.value,
                trace_id=message.trace_id,
            ) from e

    def requeue_with_backoff(
        self,
        message: SQSMessage,
        receipt_handle: str,
    ) -> str:
        """
        Requeue a failed message with exponential backoff.

        Args:
            message: Original message
            receipt_handle: SQS receipt handle for deletion

        Returns:
            New SQS message ID
        """
        # Increment retry count
        message.retries += 1

        # Calculate backoff delay (exponential: 60s, 120s, 240s, 480s, 960s)
        max_retries = 5
        if message.retries > max_retries:
            raise EnqueueError(
                f"Message exceeded max retries ({max_retries})",
                vendor=message.vendor.value,
                trace_id=message.trace_id,
            )

        delay_seconds = min(60 * (2 ** (message.retries - 1)), 900)  # Max 15 min

        # Delete original message
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except ClientError as e:
            # Log but don't fail - message will eventually be reprocessed
            print(f"Warning: Failed to delete message {message.trace_id}: {e}")

        # Send new message with delay
        return self._send_message(message, delay_seconds)

    def receive_messages(
        self,
        max_messages: int = 10,
        wait_time_seconds: int = 20,
    ) -> list[dict]:
        """
        Receive messages from the queue (long polling).

        Args:
            max_messages: Maximum number of messages to receive
            wait_time_seconds: Long polling wait time

        Returns:
            List of message dictionaries with Body and ReceiptHandle
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])

            # Parse message bodies
            parsed_messages = []
            for msg in messages:
                try:
                    body = json.loads(msg["Body"])
                    parsed_messages.append(
                        {
                            "message": SQSMessage(**body),
                            "receipt_handle": msg["ReceiptHandle"],
                            "attributes": msg.get("MessageAttributes", {}),
                        }
                    )
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Warning: Failed to parse message: {e}")
                    continue

            return parsed_messages

        except ClientError as e:
            raise EnqueueError(f"Failed to receive messages: {e}") from e

    def delete_message(self, receipt_handle: str) -> None:
        """
        Delete a successfully processed message.

        Args:
            receipt_handle: SQS receipt handle
        """
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except ClientError as e:
            raise EnqueueError(f"Failed to delete message: {e}") from e
