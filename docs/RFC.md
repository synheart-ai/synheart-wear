# RFC: synheart_wear (v0.1)

Status: Draft
Author: Synheart AI
Date: 2025-10-20

## Overview
`synheart_wear` standardizes biometric data ingestion from Apple Watch, Fitbit, Garmin, Samsung, and Whoop into a single schema and streams to Syni Core.

## Goals
- Real-time HR/HRV
- Unified schema + offline cache
- Consent-first, encrypted sync
- SWIP hooks for wellness impact

## Architecture
- Core SDK (permissions, caching, streams)
- Device Adapters (vendor-specific)
- Normalization Engine (schema v1)
- Syni Bridge (HTTP/WebSocket/gRPC)

## Schema (excerpt)
See `schema/metrics.schema.json`.

## Roadmap
v0.1 Core; v0.2 Streaming; v0.3 Syni integration; v0.4 SWIP; v1.0 Public.
