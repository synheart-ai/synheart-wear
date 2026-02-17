# RFC: synheart_wear (v0.1)

Status: Draft
Author: Synheart AI
Date: 2025-10-20

Version: 0.1
Repository: [github.com/synheart-ai/synheart_wear](https://github.com/synheart-ai/synheart_wear)

---

## Overview
synheart_wear is the Synheart Wearable SDK — a unified layer that standardizes biometric data ingestion from multiple wearable devices (Apple Watch, Fitbit, Garmin, Whoop, Samsung Watch, etc.) into a single normalized output format. It enables real-time HRV, heart rate, and activity data collection with a consistent schema for all supported devices, powering experiments, analytics, and AI-driven wellness applications under the Synheart ecosystem.

---

## Motivation
Wearable data is fragmented across different vendor SDKs and APIs, each with its own structure, rate, and permission model. Developers need a reliable, cross-platform bridge to aggregate these signals into a unified format.

synheart_wear provides:
- A Flutter SDK for mobile apps (Android + iOS) with wearable support.
- A unified data model for biosignal streaming.
- Offline caching and secure data storage for applications.
- Consistent API across all supported wearable devices.

---

## Goals

### Primary Goals
- Build a cross-device integration layer that standardizes:
  - HR (Heart Rate)
  - HRV (SDNN, RMSSD)
  - Steps
  - Calories
  - Motion & Stress (if available)
- Offer developers a simple SDK interface to:

```dart
final data = await synheart.readMetrics();
final hr = data.getMetric(MetricType.hr);
```

- Provide real-time streaming of normalized biometric data.
- Enable offline caching of wearable data with encryption.

### Secondary Goals
- Provide open-source adapters for major platforms.
- Create Synheart Wellness Impact Protocol (SWIP) hooks to measure app impact.
- Enable data collection consent and encryption by design.

---

## Architecture

```
+--------------------------+
|     synheart_wear SDK    |
+-----------+--------------+
            |
            v
+-----------+--------------+
|   Device Adapters Layer  |
| (Apple, Fitbit, Garmin…) |
+-----------+--------------+
            |
            v
+-----------+--------------+
|   Normalization Engine   |
| (standard output schema) |
+-----------+--------------+
            |
            v
+-----------+--------------+
|   Local Cache & Storage  |
|   (encrypted, offline)   |
+--------------------------+
```

### Modules
1. Core SDK — permissions, caching, streams
2. Device Adapters — vendor-specific bridges (HealthKit, Google Fit, Fitbit, Garmin Connect)
3. Normalization Engine — converts raw signals to standardized JSON
4. Local Storage — encrypted offline caching and data persistence

---

## Unified Data Schema
All wearable outputs conform to the Synheart Data Schema (v1.0):

```
{
  "timestamp": "2025-10-20T18:30:00Z",
  "device_id": "applewatch_1234",
  "source": "apple_healthkit",
  "metrics": {
    "hr": 72,
    "hrv_rmssd": 45,
    "hrv_sdnn": 62,
    "steps": 1045,
    "calories": 120.4,
    "stress": 0.3
  },
  "meta": {
    "battery": 0.82,
    "firmware_version": "10.1",
    "synced": true
  }
}
```

See `schema/metrics.schema.json` for the full specification.

---

## SDK Design (Flutter)

### Installation
```
flutter pub add synheart_wear
```

### Usage Example
```
import 'package:synheart_wear/synheart_wear.dart';

void main() async {
  final synheart = SynheartWear();
  await synheart.initialize();

  final data = await synheart.readMetrics();
  print(data.toJson());
}
```

### Supported Methods

| Method         | Description                          |
| -------------  | ------------------------------------ |
| initialize()   | Requests permissions & sets up adapters|
| readMetrics()  | Returns snapshot of available signals |
| streamHR()     | Streams real-time heart rate          |
| streamHRV()    | Streams HRV in 5-second windows       |
| getCachedSessions() | Retrieves cached wearable data      |
| clearOldCache() | Cleans up old cached data            |

---

## Supported Devices (v0.1)

| Device        | Platform        | Integration Type       |
| ------------- | --------------- | ---------------------- |
| Apple Watch   | iOS             | HealthKit              |
| Fitbit        | Android / iOS   | REST API               |
| Garmin (Cloud)| Android / iOS   | Garmin Health API (OAuth) |
| Garmin (Native RTS) | Android / iOS | Garmin Health SDK (licensed, on demand) |
| Whoop         | iOS / Android   | REST API               |
| Samsung Watch | Android         | Samsung Health SDK     |
| BLE Heart Rate Monitors | iOS / Android | Bluetooth LE (0x180D) |

BLE HRM support enables direct connection to any standard Bluetooth LE heart rate device (WHOOP Broadcast, Polar, Wahoo, Garmin HRM straps, gym equipment). See [RFC-BLE-HRM](RFC-BLE-HRM.md) for the full specification.

---

## Security & Privacy
- Data encryption: AES-256 for local storage, HTTPS for sync.
- Consent-first design: users must approve data access explicitly.
- No persistent identifiers: anonymized UUIDs used for experiments.
- Compliant with Synheart Data Governance Policy.

---

## Example Output (Local Cache)

```
/synheart/cache/wear/
 ├── 2025-10-20/
 │    ├── session_01.json
 │    ├── session_02.json
 │    └── meta.log
```

---

## Roadmap

| Version | Goal                 | Description                         |
|-------- |----------------------|-------------------------------------|
| v0.1    | Core SDK             | Apple Watch + Fitbit integration    |
| v0.2    | Real-time streaming  | HRV, HR over BLE                    |
| v0.2.1  | WHOOP cloud support  | WHOOP API integration                |
| v0.3    | BLE HRM + Extended support | BLE HR monitors, Garmin cloud + native SDK integration |
| v0.4    | SWIP integration     | Add impact measurement hooks        |
| v1.0    | Public Release       | Open standard SDK and docs          |

---

## References
- Synheart Data Governance Policy
- Synheart Wellness Impact Protocol (SWIP) Spec

