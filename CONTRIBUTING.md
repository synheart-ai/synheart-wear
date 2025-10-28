# Contributing to synheart_wear

Thank you for your interest in contributing to synheart_wear! This document provides guidelines for implementing new wearable device adapters.

## Table of Contents

- [Getting Started](#getting-started)
- [Implementing a WearAdapter](#implementing-a-wearadapter)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Submission Process](#submission-process)

## Getting Started

### Prerequisites

- Flutter SDK (>=3.22.0)
- Dart SDK
- Git
- A wearable device or access to its API/SDK

### Setting Up the Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/synheart_wear.git
   cd synheart_wear
   ```
3. Install dependencies:
   ```bash
   cd packages/synheart_wear
   flutter pub get
   ```

## Implementing a WearAdapter

### Overview

The `WearAdapter` abstract class is the core interface for integrating wearable devices. Each device (Apple Watch, Fitbit, Garmin, etc.) requires its own adapter implementation.

### Required Interface

```dart
abstract class WearAdapter {
  String get id;  // Unique identifier for the adapter
  Set<PermissionType> get supportedPermissions;  // Permissions this adapter supports

  Future<void> ensurePermissions();  // Request and verify permissions
  Future<WearMetrics?> readSnapshot({bool isRealTime = true});  // Read current metrics
}
```

### Step-by-Step Implementation Guide

#### 1. Create Your Adapter Class

Create a new file in `packages/synheart_wear/lib/src/adapters/` named `your_device_adapter.dart`:

```dart
import '../core/consent_manager.dart';
import '../core/models.dart';
import 'wear_adapter.dart';

class YourDeviceAdapter implements WearAdapter {
  // Implementation details below
}
```

#### 2. Implement the `id` Getter

Return a unique, lowercase identifier for your adapter:

```dart
@override
String get id => 'your_device';  // e.g., 'garmin', 'whoop', 'samsung'
```

**Guidelines:**
- Use lowercase letters and underscores only
- Keep it short and descriptive
- Check existing adapters to avoid conflicts

#### 3. Define Supported Permissions

Specify which biometric data your device can provide:

```dart
@override
Set<PermissionType> get supportedPermissions => const {
  PermissionType.heartRate,
  PermissionType.steps,
  PermissionType.calories,
  // Add only permissions that your device actually supports
};
```

**Available Permission Types:**
- `PermissionType.heartRate`
- `PermissionType.heartRateVariability`
- `PermissionType.steps`
- `PermissionType.calories`
- `PermissionType.sleep`
- `PermissionType.stress`
- `PermissionType.all`

#### 4. Implement `ensurePermissions()`

This method should:
1. Check device availability
2. Request necessary permissions
3. Handle errors appropriately

```dart
@override
Future<void> ensurePermissions() async {
  // Example implementation:
  
  // 1. Check if device/API is available
  final isAvailable = await YourDeviceAPI.isAvailable();
  if (!isAvailable) {
    throw DeviceUnavailableError('Your Device is not available');
  }

  // 2. Request permissions
  final granted = await YourDeviceAPI.requestPermissions();
  if (!granted) {
    throw PermissionDeniedError('Permissions were denied');
  }
}
```

**Error Handling:**
- Throw `DeviceUnavailableError` if the device is not available
- Throw `PermissionDeniedError` if permissions are denied
- Throw `NetworkError` for network-related issues
- Use the base `SynheartWearError` for other errors

#### 5. Implement `readSnapshot()`

This method should:
1. Read data from your device
2. Normalize it to the `WearMetrics` format
3. Return `null` if data is unavailable

```dart
@override
Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
  try {
    // 1. Read raw data from device
    final rawData = await YourDeviceAPI.readData();
    
    // 2. Check if data exists
    if (rawData == null) return null;

    // 3. Normalize data to WearMetrics format
    final metrics = {
      'hr': rawData.heartRate,
      'steps': rawData.steps,
      'calories': rawData.calories,
    };

    // 4. Create metadata
    final meta = {
      'source': id,
      'device_model': rawData.model,
      'battery': rawData.batteryLevel,
      'synced': true,
    };

    // 5. Create and return WearMetrics
    return WearMetrics(
      timestamp: DateTime.now(),
      deviceId: '${id}_${DateTime.now().millisecondsSinceEpoch}',
      source: id,
      metrics: metrics,
      meta: meta,
    );
  } catch (e) {
    print('YourDevice read error: $e');
    return null;
  }
}
```

**Metric Keys and Format:**
- `hr`: Heart rate in BPM (number)
- `hrv_rmssd`: HRV RMSSD in milliseconds (number)
- `hrv_sdnn`: HRV SDNN in milliseconds (number)
- `steps`: Step count (number)
- `calories`: Calories burned (number)
- `stress`: Stress level 0.0-1.0 (number)

### 6. Device-Specific Considerations

#### For SDK-Based Devices
If your device provides an SDK:
```dart
import 'package:device_sdk/device_sdk.dart';

class DeviceSDKAdapter implements WearAdapter {
  final DeviceSDK _sdk = DeviceSDK();
  
  @override
  Future<void> ensurePermissions() async {
    final granted = await _sdk.requestAuthorization();
    if (!granted) {
      throw PermissionDeniedError('Permissions denied');
    }
  }
  
  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    final data = await _sdk.getLatestMetrics();
    // Convert to WearMetrics...
  }
}
```

#### For API-Based Devices (OAuth/REST)
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class RESTAPIAdapter implements WearAdapter {
  String? _accessToken;
  
  @override
  Future<void> ensurePermissions() async {
    // Implement OAuth flow
    _accessToken = await _authenticate();
    if (_accessToken == null) {
      throw PermissionDeniedError('Authentication failed');
    }
  }
  
  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    if (_accessToken == null) {
      throw PermissionDeniedError('Not authenticated');
    }
    
    final response = await http.get(
      Uri.parse('https://api.device.com/metrics'),
      headers: {'Authorization': 'Bearer $_accessToken'},
    );
    
    if (response.statusCode != 200) {
      throw NetworkError('Failed to fetch data');
    }
    
    final data = jsonDecode(response.body);
    // Convert to WearMetrics...
  }
}
```

#### For BLE-Based Devices
```dart
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

class BLEAdapter implements WearAdapter {
  BluetoothDevice? _device;
  
  @override
  Future<void> ensurePermissions() async {
    // Check BLE permissions
    if (!await FlutterBluePlus.isSupported) {
      throw DeviceUnavailableError('Bluetooth not supported');
    }
    
    // Scan and connect to device
    _device = await _scanAndConnect();
  }
  
  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    if (_device == null) return null;
    
    final characteristic = await _device!.discoverServices()
        .then((services) => services.firstWhere((s) => s.uuid == heartRateUuid).characteristics.first);
    
    final data = await characteristic.read();
    // Parse and convert to WearMetrics...
  }
}
```

## Code Style and Standards

### Dart Style Guide

Follow the [Effective Dart](https://dart.dev/guides/language/effective-dart) guidelines:

1. **Naming Conventions:**
   - Use `camelCase` for variables and methods
   - Use `PascalCase` for classes
   - Use `lowercase_with_underscores` for adapter IDs
   - Use descriptive names: `readSnapshot` not `read`

2. **Documentation:**
   - Add dartdoc comments for public APIs
   - Document complex logic
   - Include examples in doc comments

   ```dart
   /// Reads the current biometric snapshot from the device.
   /// 
   /// Returns [null] if data is unavailable.
   /// 
   /// Throws [PermissionDeniedError] if permissions haven't been granted.
   @override
   Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
     // Implementation
   }
   ```

3. **Error Handling:**
   - Always handle errors gracefully
   - Use try-catch blocks for async operations
   - Log errors for debugging: `print('Error: $e')`
   - Throw appropriate error types

4. **Null Safety:**
   - Use nullable types when appropriate
   - Return `null` if data is unavailable
   - Use null-aware operators (`?.`, `??`)

### File Organization

```
packages/synheart_wear/lib/src/
├── adapters/
│   ├── wear_adapter.dart          # Abstract base class
│   ├── your_device_adapter.dart    # Your implementation
│   ├── apple_healthkit.dart       # Examples
│   └── fitbit.dart
├── core/
│   ├── models.dart                # Data models
│   └── consent_manager.dart       # Permission types
└── ...
```

## Testing

### Write Unit Tests

Create a test file: `packages/synheart_wear/test/adapters/your_device_adapter_test.dart`

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/src/adapters/your_device_adapter.dart';

void main() {
  group('YourDeviceAdapter', () {
    late YourDeviceAdapter adapter;

    setUp(() {
      adapter = YourDeviceAdapter();
    });

    test('id returns correct identifier', () {
      expect(adapter.id, equals('your_device'));
    });

    test('supportedPermissions returns expected permissions', () {
      expect(adapter.supportedPermissions, contains(PermissionType.heartRate));
      expect(adapter.supportedPermissions, contains(PermissionType.steps));
    });

    test('ensurePermissions throws on unavailable device', () async {
      // Mock device as unavailable
      expect(() => adapter.ensurePermissions(), throwsA(isA<DeviceUnavailableError>()));
    });

    test('readSnapshot returns WearMetrics on success', () async {
      // Mock successful data read
      final metrics = await adapter.readSnapshot();
      expect(metrics, isA<WearMetrics>());
      expect(metrics?.source, equals('your_device'));
    });

    test('readSnapshot returns null on failure', () async {
      // Mock failure scenario
      final metrics = await adapter.readSnapshot();
      expect(metrics, isNull);
    });
  });
}
```

### Running Tests

```bash
cd packages/synheart_wear
flutter test
```

### Integration Testing

Test your adapter with the example app:

```bash
cd examples/flutter_example
flutter run
```

## Submission Process

### Before Submitting

1. **Run Tests:**
   ```bash
   flutter test
   ```

2. **Format Code:**
   ```bash
   flutter format lib/ test/
   ```

3. **Analyze Code:**
   ```bash
   flutter analyze
   ```

4. **Update Documentation:**
   - Add your adapter to the README.md device list
   - Update CHANGELOG.md
   - Add your adapter to the example app

### Creating a Pull Request

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-device-adapter
   ```

2. Commit your changes:
   ```bash
   git add lib/src/adapters/your_device_adapter.dart
   git add test/adapters/your_device_adapter_test.dart
   git commit -m "Add YourDevice adapter"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-device-adapter
   ```

4. Open a Pull Request on GitHub with:
   - Clear description of what was implemented
   - Reference to related issues
   - Test results
   - Screenshots (if applicable)

### Pull Request Template

```markdown
## Description
Brief description of the adapter and device

## Device Information
- **Device Name:** [Device Name]
- **Manufacturer:** [Manufacturer]
- **API/SDK Used:** [API/SDK Name and Version]
- **Platform:** iOS/Android/Both

## Supported Metrics
- [ ] Heart Rate
- [ ] HRV
- [ ] Steps
- [ ] Calories
- [ ] Sleep
- [ ] Stress

## Testing
- [ ] Unit tests added
- [ ] Integration tests passed
- [ ] Tested on physical device

## Documentation
- [ ] Code documented
- [ ] README updated
- [ ] CHANGELOG updated
```

## Examples

### Complete Implementation Example

See `packages/synheart_wear/lib/src/adapters/apple_healthkit.dart` for a complete reference implementation.

### Other Adapters

- **Apple HealthKit:** Native iOS integration via health package
- **Fitbit:** REST API integration (in progress)
- **Garmin:** To be implemented
- **Whoop:** To be implemented
- **Samsung Watch:** To be implemented

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/synheart-ai/synheart_wear/issues)
- **Discussions:** [GitHub Discussions](https://github.com/synheart-ai/synheart_wear/discussions)

## Code of Conduct

Please be respectful and inclusive. Report any issues to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to synheart_wear! 🎉

