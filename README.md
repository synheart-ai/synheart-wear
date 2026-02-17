# Synheart Wear

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Unified wearable SDK** — Cross-device, cross-platform biometric data normalization with a single standardized output format. Stream HR, HRV, steps, calories, and stress signals from Apple Watch, Fitbit, Garmin, Whoop, and Samsung devices across Flutter, Android, and iOS applications.

> **📦 SDK Implementations**: This repository contains documentation, specifications, and examples. For platform-specific implementations, see the SDKs below.

## 🚀 Features

- **📱 Cross-Platform**: Works on iOS, Android, and Flutter
- **⌚ Multi-Device Support**: Apple Watch, Fitbit, Garmin, Whoop, Samsung Watch, BLE Heart Rate Monitors
- **🔄 Real-Time Streaming**: Live HR and HRV data streams
- **📡 BLE HRM**: Direct Bluetooth LE heart rate monitor support (WHOOP Broadcast, Polar, Wahoo, any standard HR strap)
- **📊 Unified Schema**: Consistent data format across all devices
- **🔒 Privacy-First**: Consent-based data access with encryption
- **💾 Local Storage**: Encrypted offline data persistence
- **☁️ Cloud Integration**: OAuth support for WHOOP, Garmin, Fitbit

## 📦 Platform SDKs

Choose the SDK for your platform:

| Platform | Repository | Version | Installation |
|----------|-----------|---------|--------------|
| **Flutter/Dart** | [synheart-wear-dart](https://github.com/synheart-ai/synheart-wear-dart) | ![pub.dev](https://img.shields.io/badge/pub-0.2.1-blue) | `flutter pub add synheart_wear` |
| **Android (Kotlin)** | [synheart-wear-kotlin](https://github.com/synheart-ai/synheart-wear-kotlin) | ![JitPack](https://img.shields.io/badge/jitpack-0.1.0-blue) | Via JitPack |
| **iOS (Swift)** | [synheart-wear-swift](https://github.com/synheart-ai/synheart-wear-swift) | ![SPM](https://img.shields.io/badge/spm-0.1.0-blue) | Swift Package Manager |

### Additional Tools

| Tool | Repository | Purpose |
|------|-----------|---------|
| **CLI & Local Dev Server** | [synheart-wear-cli](https://github.com/synheart-ai/synheart-wear-cli) | Local development tool with OAuth, webhooks, and ngrok integration for cloud wearables |

## 🎯 Quick Start

### Flutter/Dart

```dart
import 'package:synheart_wear/synheart_wear.dart';

void main() async {
  final synheart = SynheartWear(
    config: SynheartWearConfig.withAdapters({
      DeviceAdapter.appleHealthKit,
    }),
  );

  await synheart.initialize();
  final metrics = await synheart.readMetrics();
  print('Heart Rate: ${metrics.getMetric(MetricType.hr)} bpm');
}
```

See [synheart-wear-dart](https://github.com/synheart-ai/synheart-wear-dart) for full documentation.

### Android (Kotlin)

```kotlin
import ai.synheart.wear.SynheartWear
import ai.synheart.wear.config.SynheartWearConfig

val synheartWear = SynheartWear(
    context = this,
    config = SynheartWearConfig(
        enabledAdapters = setOf(DeviceAdapter.HEALTH_CONNECT)
    )
)

lifecycleScope.launch {
    synheartWear.initialize()
    val metrics = synheartWear.readMetrics()
    Log.d(TAG, "Heart Rate: ${metrics.getMetric(MetricType.HR)} bpm")
}
```

See [synheart-wear-kotlin](https://github.com/synheart-ai/synheart-wear-kotlin) for full documentation.

### iOS (Swift)

```swift
import SynheartWear

let config = SynheartWearConfig(
    enabledAdapters: [.appleHealthKit],
    enableLocalCaching: true,
    enableEncryption: true
)

let synheartWear = SynheartWear(config: config)

Task {
    try await synheartWear.initialize()
    let metrics = try await synheartWear.readMetrics()
    print("Heart Rate: \(metrics.getMetric(.hr) ?? 0) bpm")
}
```

See [synheart-wear-swift](https://github.com/synheart-ai/synheart-wear-swift) for full documentation.

## 📊 Unified Data Schema

All platform SDKs output the same **Synheart Data Schema v1.0**:

```json
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
    "distance": 2.5
  },
  "meta": {
    "battery": 0.82,
    "firmware_version": "10.1",
    "synced": true
  },
  "rr_ms": [800, 850, 820]
}
```

📚 **[Full Schema Documentation](schema/metrics.schema.json)**

## ⌚ Supported Devices

| Device | Flutter | Android | iOS | Status |
|--------|---------|---------|-----|--------|
| **Apple Watch** | ✅ | ✅ (via Health Connect) | ✅ (via HealthKit) | Ready |
| **Health Connect** | ✅ | ✅ (Native) | ❌ | Ready |
| **WHOOP** | 🔄 | ✅ | ✅ | Mixed |
| **BLE Heart Rate Monitors** | ✅ | ✅ | ✅ | Ready |
| **Fitbit** | 📋 | 📋 | 📋 | Planned |
| **Garmin (Cloud)** | ✅ | ✅ | ✅ | Ready |
| **Garmin (Native RTS)** | ✅ | ✅ | ✅ | On demand (licensed) |
| **Samsung Watch** | 📋 | 📋 | ❌ | Planned |
| **Oura Ring** | ✅ | ✅ | ✅ | Via HealthKit/Connect |

> **Note:** 🔄 for WHOOP on Flutter indicates Flux data processing support only (JSON transformation), not a live device adapter.

> **Garmin Native RTS:** The Garmin Health SDK Real-Time Streaming (RTS) capability requires a separate license from Garmin. The `GarminHealth` facade is available on demand for licensed integrations. The underlying Garmin Health SDK code is proprietary to Garmin and is not distributed as open source. For cloud-based Garmin data (OAuth + webhooks), use `GarminProvider`.

**Legend:** ✅ Ready | 🔄 In Development | 📋 Planned

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│              Synheart Wear Ecosystem                 │
│         (Documentation & Specifications)             │
└──────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌─────▼─────┐ ┌───────▼────────┐
│ synheart-wear- │ │synheart-  │ │ synheart-wear- │
│     dart       │ │wear-kotlin│ │     swift      │
│  (Flutter)     │ │ (Android) │ │     (iOS)      │
└────────────────┘ └───────────┘ └────────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         │
                ┌────────▼─────────┐
                │ synheart-wear-cli │
                │   (Python CLI)    │
                │  + Local Server   │
                │  + ngrok Tunnel   │
                └───────────────────┘
```

### Repository Structure

- **synheart-wear** (this repo): Documentation hub, RFC, schemas, examples
- **synheart-wear-dart**: Flutter plugin for iOS & Android
- **synheart-wear-kotlin**: Native Android SDK with Health Connect
- **synheart-wear-swift**: Native iOS SDK with HealthKit
- **synheart-wear-cli**: Local development server with OAuth, webhooks, and ngrok for cloud wearables (WHOOP, Garmin, Fitbit)

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[RFC](docs/RFC.md)** | Design specifications and architecture |
| **[BLE HRM RFC](docs/RFC-BLE-HRM.md)** | BLE Heart Rate Monitor provider specification |
| **[Data Schema](schema/metrics.schema.json)** | JSON schema for metrics format |
| **[Connector Interface](docs/CONNECTOR_INTERFACE.md)** | Guide for implementing cloud connectors |
| **[Data Flow](docs/DATA_FLOW.md)** | Architecture diagrams and flow |
| **[Connectors Program](docs/CONNECTORS.md)** | Community program for device support |

## 📱 Example Application

This repository includes a Flutter example application:

```bash
cd examples/flutter_example
flutter pub get
flutter run
```

**Example demonstrates:**
- SDK initialization
- Permission requests
- Real-time HR/HRV streaming
- Local cache management
- Multi-source data integration

## 🤝 Contributing

We welcome contributions! The easiest way to contribute is by:

1. **Adding device support** - Implement adapters in the language-specific repos
2. **Improving documentation** - Update guides, add examples, fix typos
3. **Reporting issues** - Found a bug? Report it in the respective repo

### Adding Device Support

Choose the platform and follow the contributing guide:

- **Flutter/Dart**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-dart/blob/main/CONTRIBUTING.md)
- **Android/Kotlin**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-kotlin/blob/main/CONTRIBUTING.md)
- **iOS/Swift**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-swift/blob/main/CONTRIBUTING.md)

See our **[Connectors Program](docs/CONNECTORS.md)** for incentives and supported devices.

### Improving Documentation

Documentation improvements are welcome in this repository:

1. Fork this repository
2. Make your changes to docs or README files
3. Submit a pull request

## 🔒 Privacy & Security

- **Consent-First Design**: Users must explicitly approve data access
- **Data Encryption**: AES-256 encryption for local storage
- **Key Management**: Automatic key generation and secure storage
- **No Persistent IDs**: Anonymized UUIDs for experiments
- **Compliant**: Follows Synheart Data Governance Policy
- **Right to Forget**: Users can revoke permissions and delete data

## 📋 Roadmap

| Version | Goal | Status |
|---------|------|--------|
| v0.1 | Core SDK (HealthKit + Fitbit) | ✅ Complete |
| v0.2 | Extended device support (WHOOP) & Real-time streaming (HR/HRV) | ✅ Complete |
| v0.3 | BLE Heart Rate Monitor support & Extended device support (Garmin) | 🔄 In Progress |
| v1.0 | Public Release | 📋 Planned |

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

### Platform SDKs
- **Flutter/Dart**: [synheart-wear-dart](https://github.com/synheart-ai/synheart-wear-dart)
- **Android/Kotlin**: [synheart-wear-kotlin](https://github.com/synheart-ai/synheart-wear-kotlin)
- **iOS/Swift**: [synheart-wear-swift](https://github.com/synheart-ai/synheart-wear-swift)

### Tools & Services
- **CLI & Local Dev Server**: [synheart-wear-cli](https://github.com/synheart-ai/synheart-wear-cli)
- **Local API Docs**: http://localhost:8000/docs (when running `wear start dev`)

### Resources
- **Synheart AI**: [synheart.ai](https://synheart.ai)
- **Issues**: [GitHub Issues](https://github.com/synheart-ai/synheart-wear/issues)
- **Discussions**: [GitHub Discussions](https://github.com/synheart-ai/synheart-wear/discussions)

## 👥 Authors

- **Israel Goytom** - *Initial work* 
- **Synheart AI Team** - *RFC Design & Architecture*
- **Synheart Engineering Team** - *Maintenance and support*


---

**Made with 💜 by the Synheart AI Team**

*Technology with a heartbeat.*
