"""Dummy Lambda handler for shared infrastructure deployment.

Shared infrastructure utilities (placeholder for future use).
The actual infrastructure (DynamoDB, KMS) is created independently.
"""

def app(event, context):
    """Dummy handler - never actually invoked."""
    return {
        "statusCode": 200,
        "body": "Shared infrastructure deployment"
    }

