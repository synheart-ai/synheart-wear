#!/bin/bash
# Helper script to set SQS queue URLs and KMS key ID after deployment
# Usage: ./setup-env.sh <stage> [region]
# Example: ./setup-env.sh dev eu-west-1

set -e

STAGE=${1:-dev}
REGION=${2:-eu-west-1}

if [ -z "$STAGE" ]; then
    echo "Usage: $0 <stage> [region]"
    echo "Example: $0 dev eu-west-1"
    exit 1
fi

echo "🔧 Setting up environment variables for synheart-wear-service ($STAGE)"

# Get WHOOP queue URL
WHOOP_QUEUE_NAME="cloud-connector-events-whoop-${STAGE}"
echo "📬 Resolving WHOOP SQS queue URL: $WHOOP_QUEUE_NAME"

WHOOP_QUEUE_URL=$(aws sqs get-queue-url \
    --queue-name "$WHOOP_QUEUE_NAME" \
    --region "$REGION" \
    --query 'QueueUrl' \
    --output text 2>/dev/null)

if [ -z "$WHOOP_QUEUE_URL" ]; then
    echo "⚠️  Warning: WHOOP queue '$WHOOP_QUEUE_NAME' not found."
    WHOOP_QUEUE_URL=""
else
    echo "✅ Found WHOOP queue URL: $WHOOP_QUEUE_URL"
fi

# Get Garmin queue URL
GARMIN_QUEUE_NAME="cloud-connector-events-garmin-${STAGE}"
echo "📬 Resolving Garmin SQS queue URL: $GARMIN_QUEUE_NAME"

GARMIN_QUEUE_URL=$(aws sqs get-queue-url \
    --queue-name "$GARMIN_QUEUE_NAME" \
    --region "$REGION" \
    --query 'QueueUrl' \
    --output text 2>/dev/null)

if [ -z "$GARMIN_QUEUE_URL" ]; then
    echo "⚠️  Warning: Garmin queue '$GARMIN_QUEUE_NAME' not found."
    GARMIN_QUEUE_URL=""
else
    echo "✅ Found Garmin queue URL: $GARMIN_QUEUE_URL"
fi

# Get KMS key ID from alias
KMS_ALIAS="alias/synheart-tokens-key-${STAGE}"
echo "🔑 Resolving KMS key ID for alias: $KMS_ALIAS"

KMS_KEY_ID=$(aws kms describe-key \
    --key-id "$KMS_ALIAS" \
    --region "$REGION" \
    --query 'KeyMetadata.KeyId' \
    --output text 2>/dev/null)

if [ -z "$KMS_KEY_ID" ]; then
    echo "⚠️  Warning: KMS alias '$KMS_ALIAS' not found."
    KMS_KEY_ID=""
else
    echo "✅ Found KMS key ID: $KMS_KEY_ID"
fi

# Create or update env file
ENV_FILE="env/${STAGE}.env"

if [ ! -f "$ENV_FILE" ]; then
    mkdir -p env
    touch "$ENV_FILE"
    echo "📝 Created $ENV_FILE"
fi

# Update or add variables
if [ -n "$WHOOP_QUEUE_URL" ]; then
    if grep -q "^WHOOP_SQS_QUEUE_URL=" "$ENV_FILE"; then
        sed -i.bak "s|^WHOOP_SQS_QUEUE_URL=.*|WHOOP_SQS_QUEUE_URL=$WHOOP_QUEUE_URL|" "$ENV_FILE"
    else
        echo "WHOOP_SQS_QUEUE_URL=$WHOOP_QUEUE_URL" >> "$ENV_FILE"
    fi
    echo "✅ Updated WHOOP_SQS_QUEUE_URL"
fi

if [ -n "$GARMIN_QUEUE_URL" ]; then
    if grep -q "^GARMIN_SQS_QUEUE_URL=" "$ENV_FILE"; then
        sed -i.bak "s|^GARMIN_SQS_QUEUE_URL=.*|GARMIN_SQS_QUEUE_URL=$GARMIN_QUEUE_URL|" "$ENV_FILE"
    else
        echo "GARMIN_SQS_QUEUE_URL=$GARMIN_QUEUE_URL" >> "$ENV_FILE"
    fi
    echo "✅ Updated GARMIN_SQS_QUEUE_URL"
fi

if [ -n "$KMS_KEY_ID" ]; then
    if grep -q "^KMS_KEY_ID=" "$ENV_FILE"; then
        sed -i.bak "s|^KMS_KEY_ID=.*|KMS_KEY_ID=$KMS_KEY_ID|" "$ENV_FILE"
    else
        echo "KMS_KEY_ID=$KMS_KEY_ID" >> "$ENV_FILE"
    fi
    echo "✅ Updated KMS_KEY_ID"
fi

# Clean up backup file
[ -f "${ENV_FILE}.bak" ] && rm "${ENV_FILE}.bak"

echo ""
echo "🎉 Environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add vendor secrets to $ENV_FILE:"
echo "     WHOOP_CLIENT_ID=..."
echo "     WHOOP_CLIENT_SECRET=..."
echo "     WHOOP_WEBHOOK_SECRET=..."
echo "     WHOOP_REDIRECT_URI=https://api.wear.synheart.io/v1/whoop-cloud/oauth/callback"
echo ""
echo "     GARMIN_CLIENT_ID=..."
echo "     GARMIN_CLIENT_SECRET=..."
echo "     GARMIN_WEBHOOK_SECRET=..."
echo "     GARMIN_REDIRECT_URI=https://api.wear.synheart.io/v1/garmin-cloud/oauth/callback"
echo ""
echo "  2. Push environment variables to Lambda:"
echo "     laminar env-push $STAGE"

