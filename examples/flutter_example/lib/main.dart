import 'dart:async';
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
  String _streamingStatus = 'Not streaming';
  bool _isHrStreaming = false;
  bool _isHrvStreaming = false;
  StreamSubscription<WearMetrics>? _hrSubscription;
  StreamSubscription<WearMetrics>? _hrvSubscription;

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
    _hrSubscription?.cancel();
    _hrvSubscription?.cancel();
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

  Future<void> _startHrStreaming() async {
    try {
      if (_isHrStreaming) {
        await _stopHrStreaming();
        return;
      }

      setState(() {
        _streamingStatus = 'Starting HR stream...';
      });

      _hrSubscription =
          _sdk.streamHR(interval: const Duration(seconds: 2)).listen(
        (metrics) {
          setState(() {
            _last = 'HR Stream: ${metrics.toJson()}';
            _streamingStatus =
                'HR streaming (${DateTime.now().toLocal().toString().substring(11, 19)})';
          });
        },
        onError: (error) {
          setState(() {
            _streamingStatus = 'HR stream error: $error';
          });
        },
      );

      setState(() {
        _isHrStreaming = true;
        _streamingStatus = 'HR streaming active';
      });
    } catch (e) {
      setState(() {
        _streamingStatus = 'Failed to start HR stream: $e';
      });
    }
  }

  Future<void> _stopHrStreaming() async {
    await _hrSubscription?.cancel();
    _hrSubscription = null;
    setState(() {
      _isHrStreaming = false;
      _streamingStatus = 'HR stream stopped';
    });
  }

  Future<void> _startHrvStreaming() async {
    try {
      if (_isHrvStreaming) {
        await _stopHrvStreaming();
        return;
      }

      setState(() {
        _streamingStatus = 'Starting HRV stream...';
      });

      _hrvSubscription =
          _sdk.streamHRV(windowSize: const Duration(seconds: 5)).listen(
        (metrics) {
          setState(() {
            _last = 'HRV Stream: ${metrics.toJson()}';
            _streamingStatus =
                'HRV streaming (${DateTime.now().toLocal().toString().substring(11, 19)})';
          });
        },
        onError: (error) {
          setState(() {
            _streamingStatus = 'HRV stream error: $error';
          });
        },
      );

      setState(() {
        _isHrvStreaming = true;
        _streamingStatus = 'HRV streaming active';
      });
    } catch (e) {
      setState(() {
        _streamingStatus = 'Failed to start HRV stream: $e';
      });
    }
  }

  Future<void> _stopHrvStreaming() async {
    await _hrvSubscription?.cancel();
    _hrvSubscription = null;
    setState(() {
      _isHrvStreaming = false;
      _streamingStatus = 'HRV stream stopped';
    });
  }

  Future<void> _stopAllStreaming() async {
    await _stopHrStreaming();
    await _stopHrvStreaming();
    setState(() {
      _streamingStatus = 'All streams stopped';
    });
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
                      const SizedBox(height: 8),
                      Text('Streaming: $_streamingStatus',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: _isHrStreaming || _isHrvStreaming
                                ? Colors.green
                                : Colors.grey,
                          )),
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
                    icon: const Icon(Icons.favorite, color: Colors.white),
                    label: const Text('Read Health Data',
                        style: TextStyle(color: Colors.white)),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  ),
                  ElevatedButton.icon(
                    onPressed: _requestPermissions,
                    icon: const Icon(Icons.security, color: Colors.white),
                    label: const Text('Request Permissions',
                        style: TextStyle(color: Colors.white)),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange),
                  ),
                  ElevatedButton.icon(
                    onPressed: _testHealthKit,
                    icon: const Icon(Icons.health_and_safety,
                        color: Colors.white),
                    label: const Text('Test HealthKit',
                        style: TextStyle(color: Colors.white)),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  ),
                  ElevatedButton.icon(
                    onPressed: _getCacheStats,
                    icon: const Icon(Icons.storage, color: Colors.white),
                    label: const Text('Cache Stats',
                        style: TextStyle(color: Colors.white)),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.blue),
                  ),
                  ElevatedButton.icon(
                    onPressed: _clearOldCache,
                    icon: const Icon(Icons.clear, color: Colors.white),
                    label: const Text('Clear Cache',
                        style: TextStyle(color: Colors.white)),
                    style:
                        ElevatedButton.styleFrom(backgroundColor: Colors.grey),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Streaming Section
              const Text('Real-Time Streaming:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ElevatedButton.icon(
                    onPressed: _startHrStreaming,
                    icon: Icon(_isHrStreaming ? Icons.stop : Icons.play_arrow,
                        color: Colors.white),
                    label: Text(
                        _isHrStreaming ? 'Stop HR Stream' : 'Start HR Stream',
                        style: const TextStyle(color: Colors.white)),
                    style: ElevatedButton.styleFrom(
                        backgroundColor:
                            _isHrStreaming ? Colors.red : Colors.pink),
                  ),
                  ElevatedButton.icon(
                    onPressed: _startHrvStreaming,
                    icon: Icon(_isHrvStreaming ? Icons.stop : Icons.play_arrow,
                        color: Colors.white),
                    label: Text(
                        _isHrvStreaming
                            ? 'Stop HRV Stream'
                            : 'Start HRV Stream',
                        style: const TextStyle(color: Colors.white)),
                    style: ElevatedButton.styleFrom(
                        backgroundColor:
                            _isHrvStreaming ? Colors.red : Colors.purple),
                  ),
                  ElevatedButton.icon(
                    onPressed: _stopAllStreaming,
                    icon: const Icon(Icons.stop_circle, color: Colors.white),
                    label: const Text('Stop All Streams',
                        style: TextStyle(color: Colors.white)),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red[800]),
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
