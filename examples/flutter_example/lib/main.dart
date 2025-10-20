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
  final _sdk = SynheartWear(
    config: const SynheartWearConfig(
      enableLocalCaching: true,
      streamInterval: Duration(seconds: 3),
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
    } catch (e) {
      setState(() {
        _status = 'Initialization failed: $e';
      });
    }
  }

  Future<void> _read() async {
    try {
      final m = await _sdk.readMetrics();
      setState(() {
        _last = m.toJson().toString();
      });
    } catch (e) {
      setState(() {
        _last = 'Error: $e';
      });
    }
  }

  Future<void> _requestPermissions() async {
    try {
      final permissions = await _sdk.requestPermissions(
        reason: 'This app needs access to your health data to provide insights.',
      );
      
      setState(() {
        _status = 'Permissions: ${permissions.toString()}';
      });
    } catch (e) {
      setState(() {
        _status = 'Permission error: $e';
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
        appBar: AppBar(title: const Text('synheart_wear example')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Status: $_status'),
              const SizedBox(height: 16),
              Text('Last snapshot:'),
              const SizedBox(height: 8),
              Expanded(
                child: SingleChildScrollView(
                  child: Text(
                    _last,
                    style: const TextStyle(fontFamily: 'monospace'),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ElevatedButton(
                    onPressed: _read,
                    child: const Text('Read Metrics'),
                  ),
                  ElevatedButton(
                    onPressed: _requestPermissions,
                    child: const Text('Request Permissions'),
                  ),
                  ElevatedButton(
                    onPressed: _getCacheStats,
                    child: const Text('Cache Stats'),
                  ),
                  ElevatedButton(
                    onPressed: _clearOldCache,
                    child: const Text('Clear Old Cache'),
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
