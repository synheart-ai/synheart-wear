import 'package:flutter/material.dart';
import 'package:synheart_wear/synheart_wear.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  String _last = '—';
  String _status = 'Not initialized';
  String _permissionStatus = 'Unknown';
  final _sdk = SynheartWear(
    config: const SynheartWearConfig(
      enableLocalCaching: true,
      streamInterval: Duration(seconds: 3),
      enabledAdapters: {DeviceAdapter.appleHealthKit},
    ),
  );

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _sdk.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      setState(() {
        _status = 'Initializing...';
      });

      await _sdk.initialize();

      setState(() {
        _status = 'Initialized successfully';
      });

      // Check permission status after initialization
      await _checkPermissionStatus();
    } catch (e) {
      setState(() {
        _status = 'Initialization failed: $e';
      });
    }
  }

  Future<void> _checkPermissionStatus() async {
    try {
      final status = _sdk.getPermissionStatus();
      setState(() {
        _permissionStatus = status.toString();
      });
    } catch (e) {
      setState(() {
        _permissionStatus = 'Error checking permissions: $e';
      });
    }
  }

  Future<void> _read() async {
    try {
      setState(() {
        _status = 'Reading metrics...';
      });

      final m = await _sdk.readMetrics();
      setState(() {
        _last = m.toJson().toString();
        _status = 'Metrics read successfully';
      });
    } catch (e) {
      setState(() {
        _last = 'Error: $e';
        _status = 'Failed to read metrics';
      });
    }
  }

  Future<void> _requestPermissions() async {
    try {
      setState(() {
        _status = 'Requesting permissions...';
      });

      final permissions = await _sdk.requestPermissions(
        reason:
            'This app needs access to your health data to provide insights.',
      );

      setState(() {
        _status = 'Permissions requested';
        _permissionStatus = permissions.toString();
      });
    } catch (e) {
      setState(() {
        _status = 'Permission error: $e';
      });
    }
  }

  Future<void> _testHealthKit() async {
    try {
      setState(() {
        _status = 'Testing HealthKit integration...';
      });

      // Test if HealthKit is available
      final isAvailable = _sdk.getPermissionStatus();
      setState(() {
        _status = 'HealthKit available: ${isAvailable.isNotEmpty}';
        _last = 'HealthKit Status: $isAvailable';
      });
    } catch (e) {
      setState(() {
        _status = 'HealthKit test failed: $e';
      });
    }
  }

  Future<void> _getCacheStats() async {
    try {
      final stats = await _sdk.getCacheStats();
      setState(() {
        _status = 'Cache stats: ${stats.toString()}';
      });
    } catch (e) {
      setState(() {
        _status = 'Cache error: $e';
      });
    }
  }

  Future<void> _clearOldCache() async {
    try {
      setState(() {
        _status = 'Clearing old cache...';
      });

      await _sdk.clearOldCache(maxAge: const Duration(days: 7));

      setState(() {
        _status = 'Cache cleared successfully';
      });
    } catch (e) {
      setState(() {
        _status = 'Cache clear failed: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(
          title: const Text('Synheart Wear Example'),
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Status Section
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Status: $_status',
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Text('Permissions: $_permissionStatus'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Data Section
              const Text('Last Health Data:',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: SingleChildScrollView(
                      child: Text(
                        _last,
                        style: const TextStyle(
                            fontFamily: 'monospace', fontSize: 12),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Action Buttons
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ElevatedButton.icon(
                    onPressed: _read,
                    icon: const Icon(Icons.favorite),
                    label: const Text('Read Health Data'),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  ),
                  ElevatedButton.icon(
                    onPressed: _requestPermissions,
                    icon: const Icon(Icons.security),
                    label: const Text('Request Permissions'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange),
                  ),
                  ElevatedButton.icon(
                    onPressed: _testHealthKit,
                    icon: const Icon(Icons.health_and_safety),
                    label: const Text('Test HealthKit'),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  ),
                  ElevatedButton.icon(
                    onPressed: _getCacheStats,
                    icon: const Icon(Icons.storage),
                    label: const Text('Cache Stats'),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.blue),
                  ),
                  ElevatedButton.icon(
                    onPressed: _clearOldCache,
                    icon: const Icon(Icons.clear),
                    label: const Text('Clear Cache'),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.grey),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
