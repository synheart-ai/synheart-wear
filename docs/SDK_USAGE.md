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

## Notes

- The data you pull with `wear pull` is stored on the backend
- Fetch it using the SDK methods above
- Use the ngrok URL when running in dev mode
- The SDK handles authentication automatically (tokens stored on backend)

