# Multi-stage Dockerfile for WHOOP Cloud Connector
# Optimized for AWS Lambda deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --target /build/packages -r requirements.txt

# Stage 2: Runtime
FROM public.ecr.aws/lambda/python:3.11

# Copy installed packages from builder
COPY --from=builder /build/packages ${LAMBDA_TASK_ROOT}

# Copy application code
COPY connector.py ${LAMBDA_TASK_ROOT}/
COPY api.py ${LAMBDA_TASK_ROOT}/

# Copy shared libraries (cloud connector base)
COPY ../../libs/py-cloud-connector/synheart_cloud_connector ${LAMBDA_TASK_ROOT}/synheart_cloud_connector/
COPY ../../libs/py-normalize/synheart_normalize ${LAMBDA_TASK_ROOT}/synheart_normalize/

# Set the Lambda handler
# For FastAPI/Mangum integration:
CMD ["api.handler"]

# Health check (for local testing)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Labels
LABEL maintainer="Synheart <opensource@synheart.ai>"
LABEL description="WHOOP Cloud Connector for Synheart Platform"
LABEL version="0.1.0"
