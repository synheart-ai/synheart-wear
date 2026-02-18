import 'dart:async';
import 'dart:developer';
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
  String _encryptionStatus = 'Unknown';
  bool _isHrStreaming = false;
  bool _isHrvStreaming = false;
  StreamSubscription<WearMetrics>? _hrSubscription;
  StreamSubscription<WearMetrics>? _hrvSubscription;

  // Live metrics data
  num? _currentHr;
  num? _currentHrv;
  num? _currentSteps;
  num? _currentCalories;
  List<double>? _currentRrMs;
  String _lastUpdateTime = 'No data';

  // BLE HRM state
  final _bleHrm = BleHrmProvider();
  bool _isBleScan = false;
  bool _bleConnected = false;
  bool _isBleStreaming = false;
  List<BleHrmDevice> _bleDevices = [];
  int? _bleHeartRate;
  String? _bleDeviceName;
  StreamSubscription<HeartRateSample>? _bleSubscription;

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
    _bleSubscription?.cancel();
    _bleHrm.dispose();
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
      log('$e');
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

  Future<void> _checkEncryptionStatus() async {
    try {
      final stats = await _sdk.getCacheStats();
      setState(() {
        _encryptionStatus =
            stats['encryption_enabled'] == true ? 'Enabled' : 'Disabled';
      });
    } catch (e) {
      setState(() {
        _encryptionStatus = 'Error: $e';
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
    } catch (e, s) {
      setState(() {
        _last = 'Error: $e, $s';
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

  Future<void> _getCachedSessions() async {
    try {
      final sessions = await _sdk.getCachedSessions(
        startDate: DateTime.now().subtract(const Duration(days: 30)),
      );

      setState(() {
        _status = 'Cached sessions: ${sessions.length} found';
      });
    } catch (e) {
      setState(() {
        _status = 'Cached sessions error: $e';
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
            _updateMetrics(metrics);
            _currentRrMs = metrics.rrMs;
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
            _updateMetrics(metrics);
            _currentRrMs = metrics.rrMs;
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

  // ── BLE HRM ──────────────────────────────────────────────

  Future<void> _scanBle() async {
    try {
      setState(() {
        _isBleScan = true;
        _status = 'Scanning for BLE HR monitors...';
      });
      final devices = await _bleHrm.scan(timeoutMs: 10000);
      setState(() {
        _isBleScan = false;
        _bleDevices = devices;
        _status = '${devices.length} BLE device(s) found';
      });
    } catch (e) {
      setState(() {
        _isBleScan = false;
        _status = 'BLE scan error: $e';
      });
    }
  }

  Future<void> _connectBle(String deviceId) async {
    try {
      setState(() {
        _status = 'Connecting to BLE device...';
      });
      await _bleHrm.connect(deviceId: deviceId);
      final connected = await _bleHrm.isConnected();
      setState(() {
        _bleConnected = connected;
        _bleDeviceName =
            _bleDevices.firstWhere((d) => d.deviceId == deviceId).name;
        _status = connected ? 'BLE device connected' : 'BLE connection failed';
      });
    } catch (e) {
      setState(() {
        _status = 'BLE connect error: $e';
      });
    }
  }

  Future<void> _disconnectBle() async {
    try {
      await _bleSubscription?.cancel();
      _bleSubscription = null;
      await _bleHrm.disconnect();
      setState(() {
        _bleConnected = false;
        _bleDeviceName = null;
        _bleHeartRate = null;
        _isBleStreaming = false;
        _status = 'BLE device disconnected';
      });
    } catch (e) {
      setState(() {
        _status = 'BLE disconnect error: $e';
      });
    }
  }

  void _toggleBleStream() {
    if (_isBleStreaming) {
      _bleSubscription?.cancel();
      _bleSubscription = null;
      setState(() {
        _isBleStreaming = false;
        _status = 'BLE HR stream stopped';
      });
    } else {
      _bleSubscription = _bleHrm.onHeartRate.listen(
        (sample) {
          setState(() {
            _bleHeartRate = sample.bpm.toInt();
            _lastUpdateTime =
                DateTime.now().toLocal().toString().substring(11, 19);
          });
        },
        onError: (error) {
          setState(() {
            _isBleStreaming = false;
            _status = 'BLE HR stream error: $error';
          });
        },
      );
      setState(() {
        _isBleStreaming = true;
        _status = 'BLE HR stream started';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: DefaultTabController(
        length: 3,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Synheart Wear Example'),
            backgroundColor: Colors.blue,
            foregroundColor: Colors.white,
            bottom: const TabBar(
              indicatorColor: Colors.white,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white70,
              tabs: [
                Tab(icon: Icon(Icons.dashboard), text: 'Dashboard'),
                Tab(icon: Icon(Icons.favorite), text: 'Health Data'),
                Tab(icon: Icon(Icons.stream), text: 'Streaming'),
              ],
            ),
          ),
          body: TabBarView(
            children: [
              _buildDashboardTab(),
              _buildHealthDataTab(),
              _buildStreamingTab(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDashboardTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Status Cards
          Row(
            children: [
              Expanded(
                child: _buildStatusCard(
                  'SDK Status',
                  _status,
                  _status.contains('successfully')
                      ? Colors.green
                      : Colors.orange,
                  Icons.check_circle,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatusCard(
                  'Permissions',
                  _permissionStatus,
                  _permissionStatus.contains('granted')
                      ? Colors.green
                      : Colors.red,
                  Icons.security,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildStatusCard(
                  'Encryption',
                  _encryptionStatus,
                  _encryptionStatus == 'Enabled' ? Colors.green : Colors.grey,
                  Icons.lock,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatusCard(
                  'Streaming',
                  _streamingStatus,
                  _isHrStreaming || _isHrvStreaming
                      ? Colors.green
                      : Colors.grey,
                  Icons.stream,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Quick Actions
          const Text(
            'Quick Actions',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildActionButton(
                'Read Health Data',
                Icons.favorite,
                Colors.red,
                _read,
              ),
              _buildActionButton(
                'Request Permissions',
                Icons.security,
                Colors.orange,
                _requestPermissions,
              ),
              _buildActionButton(
                'Check Encryption',
                Icons.lock,
                Colors.indigo,
                _checkEncryptionStatus,
              ),
              _buildActionButton(
                'Test HealthKit',
                Icons.health_and_safety,
                Colors.green,
                _testHealthKit,
              ),
              _buildActionButton(
                'Cache Stats',
                Icons.storage,
                Colors.blue,
                _getCacheStats,
              ),
              _buildActionButton(
                'Clear Cache',
                Icons.clear,
                Colors.grey,
                _clearOldCache,
              ),
              _buildActionButton(
                'Cached Sessions',
                Icons.history,
                Colors.teal,
                _getCachedSessions,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHealthDataTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Health Data',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: Card(
              elevation: 4,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Latest Metrics',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        IconButton(
                          onPressed: _read,
                          icon: const Icon(Icons.refresh),
                          tooltip: 'Refresh Data',
                        ),
                      ],
                    ),
                    const Divider(),
                    Expanded(
                      child: SingleChildScrollView(
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.grey[100],
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.grey[300]!),
                          ),
                          child: Text(
                            _last,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStreamingTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Real-Time Streaming',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          // Streaming Status
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    _isHrStreaming || _isHrvStreaming
                        ? Icons.play_circle
                        : Icons.pause_circle,
                    color: _isHrStreaming || _isHrvStreaming
                        ? Colors.green
                        : Colors.grey,
                    size: 24,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _streamingStatus,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: _isHrStreaming || _isHrvStreaming
                            ? Colors.green
                            : Colors.grey,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Streaming Controls
          const Text(
            'Stream Controls',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          Row(
            children: [
              Expanded(
                child: _buildStreamButton(
                  'Heart Rate',
                  _isHrStreaming ? 'Stop HR' : 'Start HR',
                  _isHrStreaming ? Icons.stop : Icons.play_arrow,
                  _isHrStreaming ? Colors.red : Colors.pink,
                  _startHrStreaming,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStreamButton(
                  'Heart Rate Variability',
                  _isHrvStreaming ? 'Stop HRV' : 'Start HRV',
                  _isHrvStreaming ? Icons.stop : Icons.play_arrow,
                  _isHrvStreaming ? Colors.red : Colors.purple,
                  _startHrvStreaming,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _stopAllStreaming,
              icon: const Icon(Icons.stop_circle, color: Colors.white),
              label: const Text(
                'Stop All Streams',
                style: TextStyle(color: Colors.white),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red[800],
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Live Data Display
          const Text(
            'Live Data',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _buildMetricsDisplay(),
          ),

          // ── BLE Heart Rate Monitor ─────────────────────
          const SizedBox(height: 20),
          const Text(
            'BLE Heart Rate Monitor',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          // BLE status card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    _bleConnected ? Icons.bluetooth_connected : Icons.bluetooth,
                    color: _bleConnected ? Colors.blue : Colors.grey,
                    size: 24,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _bleConnected
                              ? 'Connected: ${_bleDeviceName ?? "BLE Device"}'
                              : 'No BLE Device Connected',
                          style: TextStyle(
                            fontWeight: FontWeight.w500,
                            color: _bleConnected ? Colors.blue : Colors.grey,
                          ),
                        ),
                        if (_bleHeartRate != null)
                          Text(
                            'BLE HR: $_bleHeartRate BPM',
                            style: const TextStyle(
                                color: Colors.red, fontSize: 12),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          if (!_bleConnected) ...[
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isBleScan ? null : _scanBle,
                icon: _isBleScan
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.bluetooth_searching, color: Colors.white),
                label: Text(
                  _isBleScan ? 'Scanning...' : 'Scan for BLE HR Monitors',
                  style: const TextStyle(color: Colors.white),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            if (_bleDevices.isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'Discovered Devices',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 4),
              ..._bleDevices.map(
                (device) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: OutlinedButton(
                    onPressed: () => _connectBle(device.deviceId),
                    child: Row(
                      children: [
                        const Icon(Icons.bluetooth, color: Colors.blue),
                        const SizedBox(width: 8),
                        Expanded(child: Text(device.name)),
                        const Text('Connect',
                            style: TextStyle(color: Colors.blue)),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ] else ...[
            Row(
              children: [
                Expanded(
                  child: _buildStreamButton(
                    'BLE HR',
                    _isBleStreaming ? 'Stop' : 'Start',
                    _isBleStreaming ? Icons.stop : Icons.play_arrow,
                    _isBleStreaming ? Colors.red : Colors.blue,
                    _toggleBleStream,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _disconnectBle,
                    icon: const Icon(Icons.link_off, color: Colors.white),
                    label: const Text('Disconnect',
                        style: TextStyle(color: Colors.white)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
            if (_bleHeartRate != null) ...[
              const SizedBox(height: 12),
              _buildMetricCard(
                'BLE Heart Rate',
                '$_bleHeartRate',
                'BPM',
                Colors.blue,
                Icons.bluetooth,
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildStatusCard(
      String title, String status, Color color, IconData icon) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Text(
              status,
              style: TextStyle(color: color, fontSize: 11),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(
      String label, IconData icon, Color color, VoidCallback onPressed) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, color: Colors.white, size: 16),
      label: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
    );
  }

  Widget _buildStreamButton(String title, String action, IconData icon,
      Color color, VoidCallback onPressed) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Icon(icon, color: color, size: 32),
              const SizedBox(height: 8),
              Text(
                title,
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                action,
                style: TextStyle(color: color, fontSize: 10),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Update live metrics data from stream
  void _updateMetrics(WearMetrics metrics) {
    _currentHr = metrics.getMetric(MetricType.hr);
    // Try hrvSdnn first, fallback to hrvRmssd if not available
    _currentHrv = metrics.getMetric(MetricType.hrvSdnn) ??
        metrics.getMetric(MetricType.hrvRmssd);
    _currentSteps = metrics.getMetric(MetricType.steps);
    _currentCalories = metrics.getMetric(MetricType.calories);
    _lastUpdateTime = DateTime.now().toLocal().toString().substring(11, 19);
  }

  /// Build metrics display with cards
  Widget _buildMetricsDisplay() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Last update time
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue[200]!),
              ),
              child: Text(
                'Last Update: $_lastUpdateTime',
                style: TextStyle(
                  color: Colors.blue[700],
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 16),

            // Metrics grid
            Expanded(
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.2,
                children: [
                  _buildMetricCard(
                    'Heart Rate',
                    _currentHr?.toStringAsFixed(0) ?? '—',
                    'BPM',
                    Colors.red,
                    Icons.favorite,
                  ),
                  _buildMetricCard(
                    'HRV',
                    _currentHrv?.toStringAsFixed(1) ?? '—',
                    'ms',
                    Colors.purple,
                    Icons.analytics,
                  ),
                  _buildMetricCard(
                    'Steps',
                    _currentSteps?.toStringAsFixed(0) ?? '—',
                    'steps',
                    Colors.green,
                    Icons.directions_walk,
                  ),
                  _buildMetricCard(
                    'Calories',
                    _currentCalories?.toStringAsFixed(0) ?? '—',
                    'kcal',
                    Colors.orange,
                    Icons.local_fire_department,
                  ),
                  _buildMetricCard(
                    'RR intervals',
                    _currentRrMs == null
                        ? '—'
                        : (_currentRrMs!.isEmpty
                            ? '0'
                            : (_currentRrMs!
                                    .take(3)
                                    .map((e) => e.toStringAsFixed(0))
                                    .join(', ') +
                                (_currentRrMs!.length > 3 ? ' …' : ''))),
                    _currentRrMs == null ? '' : 'ms',
                    Colors.teal,
                    Icons.timeline,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build individual metric card
  Widget _buildMetricCard(
      String title, String value, String unit, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            title,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          Text(
            unit,
            style: TextStyle(
              color: color.withValues(alpha: 0.7),
              fontSize: 10,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
