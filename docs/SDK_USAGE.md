# Flutter SDK Usage Guide

## Getting Data from WHOOP Cloud

After pulling data using the CLI (`wear pull once --vendor whoop --since 7d`), you can fetch it from your Flutter app using the SDK.

## Setup

### 1. Configure the SDK with ngrok URL

When running `wear start dev`, the CLI shows an ngrok URL. Use this as the `baseUrl`:

```dart
import 'package:synheart_wear/synheart_wear.dart';

// Use the ngrok URL from CLI output
final whoopProvider = WhoopProvider(
  baseUrl: 'https://abc123.ngrok-free.app',  // From CLI output
  redirectUri: 'synheart://oauth/callback',
);
```

### 2. Connect (OAuth)

```dart
// Launch OAuth flow
await whoopProvider.connect(context);

// Or if you have the authorization code from deep link:
await whoopProvider.connectWithCode(code, state, redirectUri);
```

### 3. Fetch Data

After connecting and pulling data, fetch it from the backend:

```dart
// Fetch recovery data
final recoveryData = await whoopProvider.fetchRecovery(
  start: DateTime.now().subtract(Duration(days: 7)),
  end: DateTime.now(),
  limit: 25,
);

// Access the records
final records = recoveryData['records'] as List;
print('Found ${records.length} recovery records');

// Fetch sleep data
final sleepData = await whoopProvider.fetchSleep(
  start: DateTime.now().subtract(Duration(days: 7)),
  limit: 25,
);

// Fetch workouts
final workoutData = await whoopProvider.fetchWorkouts(
  start: DateTime.now().subtract(Duration(days: 7)),
  limit: 25,
);

// Fetch cycles
final cycleData = await whoopProvider.fetchCycles(
  start: DateTime.now().subtract(Duration(days: 7)),
  limit: 25,
);
```

## Complete Example

```dart
import 'package:flutter/material.dart';
import 'package:synheart_wear/synheart_wear.dart';

class WhoopDataScreen extends StatefulWidget {
  @override
  _WhoopDataScreenState createState() => _WhoopDataScreenState();
}

class _WhoopDataScreenState extends State<WhoopDataScreen> {
  late WhoopProvider whoopProvider;
  Map<String, dynamic>? recoveryData;
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    // Use ngrok URL from CLI output
    whoopProvider = WhoopProvider(
      baseUrl: 'https://abc123.ngrok-free.app',
      redirectUri: 'synheart://oauth/callback',
    );
    
    // Restore previous connection
    whoopProvider.restoreConnection();
  }

  Future<void> connectWhoop() async {
    try {
      await whoopProvider.connect(context);
      setState(() {
        // User is now connected
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connection failed: $e')),
      );
    }
  }

  Future<void> fetchRecoveryData() async {
    if (!whoopProvider.isConnected) {
      await connectWhoop();
      return;
    }

    setState(() => isLoading = true);
    try {
      final data = await whoopProvider.fetchRecovery(
        start: DateTime.now().subtract(Duration(days: 7)),
        limit: 25,
      );
      
      setState(() {
        recoveryData = data;
        isLoading = false;
      });
    } catch (e) {
      setState(() => isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to fetch data: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('WHOOP Data')),
      body: Column(
        children: [
          ElevatedButton(
            onPressed: fetchRecoveryData,
            child: Text('Fetch Recovery Data'),
          ),
          if (isLoading)
            CircularProgressIndicator()
          else if (recoveryData != null)
            Expanded(
              child: ListView.builder(
                itemCount: (recoveryData!['records'] as List).length,
                itemBuilder: (context, index) {
                  final record = (recoveryData!['records'] as List)[index];
                  return ListTile(
                    title: Text('Recovery Score: ${record['recovery_score'] ?? 'N/A'}'),
                    subtitle: Text('Date: ${record['created_at'] ?? 'N/A'}'),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
```

## API Endpoints

The SDK uses these backend endpoints:

- `GET /v1/data/{user_id}/recovery` - Recovery records
- `GET /v1/data/{user_id}/sleep` - Sleep records  
- `GET /v1/data/{user_id}/workouts` - Workout records
- `GET /v1/data/{user_id}/cycles` - Cycle records
- `GET /v1/data/{user_id}/profile` - User profile

## Data Format

Each endpoint returns WHOOP's raw data format:

```json
{
  "records": [
    {
      "id": "...",
      "recovery_score": 85,
      "hrv_rmssd_milli": 45.2,
      "resting_heart_rate": 50,
      "created_at": "2025-10-29T00:00:00Z",
      ...
    }
  ],
  "total": 7,
  "limit": 25
}
```

---

## BLE Heart Rate Monitor

The SDK supports direct BLE heart rate monitor connections for real-time HR streaming. This works with any standard Bluetooth LE heart rate device including WHOOP (Broadcast HR), Polar chest straps, Wahoo, and Garmin HRM sensors.

### Setup

No cloud backend is needed. BLE HRM connects directly to the device over Bluetooth.

#### Platform Permissions

**Android** — Add to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

**iOS** — Add to `Info.plist`:
```xml
<key>NSBluetoothAlwaysUsageDescription</key>
<string>This app uses Bluetooth to connect to heart rate monitors.</string>
```

### Flutter/Dart Usage

```dart
import 'package:synheart_wear/synheart_wear.dart';

// Create the BLE HRM bridge
final bleHrm = BleHrmBridge();

// Scan for nearby HR monitors
final devices = await bleHrm.scan(timeoutMs: 10000, namePrefix: 'WHOOP');

// Connect to a device
await bleHrm.connect(
  deviceId: devices.first.deviceId,
  sessionId: 'my-session',
);

// Listen to heart rate samples
bleHrm.heartRateStream.listen((sample) {
  print('BPM: ${sample.bpm}');
  if (sample.rrIntervalsMs != null) {
    print('RR: ${sample.rrIntervalsMs}');
  }
});

// Disconnect when done
await bleHrm.disconnect();
```

### Swift Usage

```swift
import SynheartWear

let config = SynheartWearConfig(enabledAdapters: [.bleHrm])
let synheartWear = SynheartWear(config: config)

// Access the BLE HRM provider
guard let bleHrm = synheartWear.bleHrm else { return }

// Scan for devices
let devices = try await bleHrm.scan(timeoutMs: 10000, namePrefix: "WHOOP")

// Connect
try await bleHrm.connect(deviceId: devices.first.deviceId)

// Stream heart rate samples
for await sample in bleHrm.onHeartRate {
    print("BPM: \(sample.bpm)")
}
```

### Kotlin Usage

```kotlin
import ai.synheart.wear.SynheartWear
import ai.synheart.wear.models.DeviceAdapter

val synheartWear = SynheartWear(
    context = this,
    config = SynheartWearConfig(
        enabledAdapters = setOf(DeviceAdapter.BLE_HRM)
    )
)

val bleHrm = synheartWear.bleHrm ?: return

// Scan for devices
val devices = bleHrm.scan(timeoutMs = 10000, namePrefix = "WHOOP")

// Connect
bleHrm.connect(deviceId = devices.first().deviceId)

// Collect heart rate samples
bleHrm.heartRateFlow.collect { sample ->
    Log.d(TAG, "BPM: ${sample.bpm}")
}
```

### HeartRateSample Schema

Each sample contains:

| Field | Type | Description |
|-------|------|-------------|
| `tsMs` | `Int64` | Phone receipt timestamp (ms since epoch) |
| `bpm` | `Int` | Heart rate in beats per minute |
| `source` | `String` | Always `"ble_hrm"` |
| `deviceId` | `String` | BLE device UUID |
| `deviceName` | `String?` | Device advertised name |
| `sessionId` | `String?` | Optional session tag |
| `rrIntervalsMs` | `[Double]?` | RR intervals in milliseconds (if supported by device) |

### Error Codes

| Code | Meaning |
|------|---------|
| `PERMISSION_DENIED` | Bluetooth permission not granted |
| `BLUETOOTH_OFF` | Bluetooth adapter is off |
| `DEVICE_NOT_FOUND` | Device not found or connection failed |
| `SUBSCRIBE_FAILED` | Failed to subscribe to HR notifications |
| `DISCONNECTED` | Device disconnected |

### Notes

- BLE HRM connects directly to the device — no cloud backend needed
- WHOOP devices broadcast HR when the "Broadcast Heart Rate" setting is enabled in the WHOOP app
- RR intervals are available on some devices (Polar chest straps) but not all (WHOOP typically does not include them)
- Reconnection is automatic: 3 retries with exponential backoff (1s, 2s, 4s)
- Only one BLE HRM device can be connected at a time (v1)

---

## Garmin Health SDK (Native Device Integration)

The Synheart Wear SDK supports native Garmin device integration through the `GarminHealth` facade. This provides direct BLE connectivity to Garmin watches for scanning, pairing, real-time streaming, and metric reads.

> **Important:** The Garmin Health SDK Real-Time Streaming (RTS) capability requires a separate license from Garmin. The `GarminHealth` facade is available on demand for licensed integrations. The underlying Garmin Health SDK code is proprietary to Garmin and is not distributed as open source. Contact Synheart for licensed access.

For cloud-based Garmin data (OAuth + webhooks with 12 summary types), use `GarminProvider` instead.

### Flutter/Dart Usage

```dart
import 'package:synheart_wear/synheart_wear.dart';

final garmin = GarminHealth(licenseKey: 'your-garmin-sdk-key');
await garmin.initialize();

// Scan for devices
garmin.scannedDevicesStream.listen((devices) {
  print('Found ${devices.length} devices');
});
await garmin.startScanning();

// Pair and read metrics
final paired = await garmin.pairDevice(scannedDevice);
final metrics = await garmin.readMetrics();
```

### Swift Usage

```swift
import SynheartWear

let garmin = GarminHealth(licenseKey: "your-garmin-sdk-key")
try await garmin.initialize()

// Scan for devices
for await devices in garmin.scannedDevicesStream() {
    print("Found \(devices.count) devices")
}

// Pair and read metrics
let paired = try await garmin.pairDevice(scannedDevice)
let metrics = try await garmin.readMetrics()
```

### Kotlin Usage

```kotlin
import ai.synheart.wear.adapters.GarminHealth

val garmin = GarminHealth(licenseKey = "your-garmin-sdk-key")
garmin.initialize()

// Scan for devices
garmin.scannedDevicesFlow.collect { devices ->
    println("Found ${devices.size} devices")
}

// Pair and read metrics
val paired = garmin.pairDevice(scannedDevice)
val metrics = garmin.readMetrics()
```

---

## Notes

- The data you pull with `wear pull` is stored on the backend
- Fetch it using the SDK methods above
- Use the ngrok URL when running in dev mode
- The SDK handles authentication automatically (tokens stored on backend)

