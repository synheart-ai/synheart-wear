# synheart_wear

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/synheart-ai/synheart_wear)
[![Flutter](https://img.shields.io/badge/flutter-%3E%3D3.22.0-blue.svg)](https://flutter.dev)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Unified wearable SDK for Synheart** — Cross-device, cross-platform biometric data ingestion with a single normalized output format. Stream HR, HRV, steps, calories, and stress signals from Apple Watch, Fitbit, Garmin, Whoop, and Samsung devices into your Flutter applications.

## 🚀 Features

- **📱 Cross-Platform**: Works on iOS and Android
- **⌚ Multi-Device Support**: Apple Watch, Fitbit, Garmin, Whoop, Samsung Watch
- **🔄 Real-Time Streaming**: Live HR and HRV data streams
- **📊 Unified Schema**: Consistent data format across all devices
- **🔒 Privacy-First**: Consent-based data access with encryption
- **💾 Local Caching**: Offline data storage with sync capabilities
- **🧠 Syni Integration**: Direct sync to Synheart's AI backend

## 📦 Installation

Add `synheart_wear` to your `pubspec.yaml`:

```yaml
dependencies:
  synheart_wear: ^0.1.0
```

Then run:

```bash
flutter pub get
```

## 🎯 Quick Start

### Basic Usage

```dart
import 'package:synheart_wear/synheart_wear.dart';

void main() async {
  // Initialize the SDK
  final synheart = SynheartWear();
  await synheart.initialize();

  // Read current metrics
  final metrics = await synheart.readMetrics();
  print('Heart Rate: ${metrics.getMetric(MetricType.hr)}');
  print('Steps: ${metrics.getMetric(MetricType.steps)}');
}
```

### Real-Time Streaming

```dart
// Stream heart rate data every 5 seconds
synheart.streamHR(interval: Duration(seconds: 5))
  .listen((metrics) {
    print('Current HR: ${metrics.getMetric(MetricType.hr)}');
  });

// Stream HRV data in 5-second windows
synheart.streamHRV(windowSize: Duration(seconds: 5))
  .listen((metrics) {
    print('HRV RMSSD: ${metrics.getMetric(MetricType.hrvRmssd)}');
  });
```

### Configuration

```dart
final synheart = SynheartWear(
  config: SynheartWearConfig(
    enabledAdapters: {
      DeviceAdapter.appleHealthKit,
      DeviceAdapter.fitbit,
    },
    enableLocalCaching: true,
    enableEncryption: true,
    streamInterval: Duration(seconds: 3),
    syniEndpoint: 'https://api.synheart.ai/sync',
  ),
);
```

## 📊 Data Schema

All wearable data follows the **Synheart Data Schema v1.0**:

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
    "stress": 0.3
  },
  "meta": {
    "battery": 0.82,
    "firmware_version": "10.1",
    "synced": true
  }
}
```

## 🔧 API Reference

### Core Methods

| Method | Description |
|--------|-------------|
| `initialize()` | Request permissions & setup adapters |
| `readMetrics()` | Get current biometric snapshot |
| `streamHR()` | Stream real-time heart rate |
| `streamHRV()` | Stream HRV in configurable windows |
| `syncToSyni()` | Upload data to Synheart backend |

### Permission Management

```dart
// Request specific permissions
final permissions = await synheart.requestPermissions(
  permissions: {PermissionType.heartRate, PermissionType.steps},
  reason: 'This app needs access to your health data for insights.',
);

// Check permission status
final status = synheart.getPermissionStatus();
print('HR permission: ${status[PermissionType.heartRate]}');
```

### Local Caching

```dart
// Get cached sessions
final sessions = await synheart.getCachedSessions(
  startDate: DateTime.now().subtract(Duration(days: 7)),
  limit: 100,
);

// Get cache statistics
final stats = await synheart.getCacheStats();
print('Total sessions: ${stats['total_sessions']}');

// Clear old data
await synheart.clearOldCache(maxAge: Duration(days: 30));
```

## ⌚ Supported Devices

| Device | Platform | Integration | Status |
|--------|----------|-------------|--------|
| Apple Watch | iOS | HealthKit | ✅ Ready |
| Fitbit | iOS/Android | REST API | 🔄 In Development |
| Garmin | iOS/Android | Connect API | 📋 Planned |
| Whoop | iOS/Android | REST API | 📋 Planned |
| Samsung Watch | Android | Samsung Health | 📋 Planned |

## 🔒 Privacy & Security

- **Consent-First Design**: Users must explicitly approve data access
- **Data Encryption**: AES-256 encryption for local storage
- **No Persistent IDs**: Anonymized UUIDs for experiments
- **Compliant**: Follows Synheart Data Governance Policy
- **Right to Forget**: Users can revoke permissions anytime

## 🏗️ Architecture

```
┌─────────────────────────┐
│   synheart_wear SDK     │
├───────────┬─────────────┤
│           │             │
│           ▼             │
├───────────┬─────────────┤
│ Device Adapters Layer   │
│ (Apple, Fitbit, etc.)   │
├───────────┬─────────────┤
│           │             │
│           ▼             │
├───────────┬─────────────┤
│ Normalization Engine    │
│ (standard output schema)│
├───────────┬─────────────┤
│           │             │
│           ▼             │
├───────────┬─────────────┤
│   Syni Core Bridge      │
│   (via API / Socket)    │
└─────────────────────────┘
```

## 📱 Example App

Check out the complete example in `examples/flutter_example/`:

```bash
cd examples/flutter_example
flutter run
```

The example demonstrates:
- SDK initialization
- Permission requests
- Real-time data streaming
- Cache management
- Syni backend sync

## 🧪 Testing

Run the test suite:

```bash
flutter test
```

Tests cover:
- Core SDK functionality
- Data model serialization
- Error handling scenarios
- Permission management
- Configuration system

## 📋 Roadmap

| Version | Goal | Description |
|---------|------|-------------|
| v0.1 | Core SDK | ✅ Apple Watch + Fitbit integration |
| v0.2 | Real-time streaming | 🔄 HRV, HR over BLE |
| v0.3 | Syni Core integration | 📋 Unified upload to backend |
| v0.4 | SWIP integration | 📋 Add impact measurement hooks |
| v1.0 | Public Release | 📋 Open standard SDK and docs |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [docs/RFC.md](docs/RFC.md)
- **Data Schema**: [schema/metrics.schema.json](schema/metrics.schema.json)
- **Synheart AI**: [synheart.ai](https://synheart.ai)
- **Issues**: [GitHub Issues](https://github.com/synheart-ai/synheart_wear/issues)

## 👥 Authors

- **Israel Goytom** - *Initial work* - [@isrugeek](https://github.com/isrugeek)
- **Synheart AI Team** - *RFC Design & Architecture*

---

**Made with ❤️ by the Synheart AI Team**

*Technology with a heartbeat.*
