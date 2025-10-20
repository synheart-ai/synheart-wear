import 'dart:async';
import 'models.dart';
import '../normalization/normalizer.dart';
import '../adapters/apple_healthkit.dart';
import '../adapters/fitbit.dart';
import 'config.dart';
import 'consent_manager.dart';
import 'local_cache.dart';

/// Main SynheartWear SDK class implementing RFC specifications
class SynheartWear {
  bool _initialized = false;
  final SynheartWearConfig config;
  final Normalizer _normalizer;
  StreamController<WearMetrics>? _hrStreamController;
  StreamController<WearMetrics>? _hrvStreamController;
  Timer? _streamTimer;

  SynheartWear({SynheartWearConfig? config})
      : config = config ?? const SynheartWearConfig(),
        _normalizer = Normalizer();

  /// Initialize the SDK with permissions and setup
  Future<void> initialize() async {
    if (_initialized) return;

    try {
      // Request necessary permissions
      await _requestPermissions();
      
      // Initialize adapters
      await _initializeAdapters();
      
      _initialized = true;
    } catch (e) {
      throw SynheartWearError('Failed to initialize SynheartWear: $e');
    }
  }

  /// Read current metrics from all enabled adapters
  Future<WearMetrics> readMetrics() async {
    if (!_initialized) {
      await initialize();
    }

    try {
      // Validate consents
      ConsentManager.validateConsents(_getRequiredPermissions());

      // Gather data from enabled adapters
      final adapterData = <WearMetrics?>[];
      
      if (config.isAdapterEnabled(DeviceAdapter.appleHealthKit)) {
        try {
          final appleData = await AppleHealthKitAdapter.readSnapshot();
          adapterData.add(appleData);
        } catch (e) {
          // Log error but continue with other adapters
          print('Apple HealthKit error: $e');
        }
      }

      if (config.isAdapterEnabled(DeviceAdapter.fitbit)) {
        try {
          final fitbitData = await FitbitAdapter.readSnapshot();
          adapterData.add(fitbitData);
        } catch (e) {
          print('Fitbit error: $e');
        }
      }

      // Normalize and merge data
      final mergedData = _normalizer.mergeSnapshots(adapterData);
      
      // Validate data quality
      if (!_normalizer.validateMetrics(mergedData)) {
        throw SynheartWearError('Invalid metrics data received');
      }

      // Cache data if enabled
      if (config.enableLocalCaching) {
        await LocalCache.storeSession(mergedData);
      }

      return mergedData;
    } catch (e) {
      if (e is SynheartWearError) rethrow;
      throw SynheartWearError('Failed to read metrics: $e');
    }
  }

  /// Stream real-time heart rate data
  Stream<WearMetrics> streamHR({Duration? interval}) {
    final actualInterval = interval ?? config.streamInterval;
    
    _hrStreamController ??= StreamController<WearMetrics>.broadcast();
    
    // Start streaming if not already active
    if (_streamTimer == null || !_streamTimer!.isActive) {
      _startStreaming(actualInterval);
    }
    
    return _hrStreamController!.stream;
  }

  /// Stream HRV data in configurable windows (RFC specification)
  Stream<WearMetrics> streamHRV({Duration? windowSize}) {
    final actualWindowSize = windowSize ?? config.hrvWindowSize;
    
    _hrvStreamController ??= StreamController<WearMetrics>.broadcast();
    
    // Start HRV streaming
    Timer.periodic(actualWindowSize, (timer) async {
      try {
        final metrics = await readMetrics();
        final hrvData = metrics.getMetric(MetricType.hrvRmssd);
        
        if (hrvData != null) {
          _hrvStreamController!.add(metrics);
        }
      } catch (e) {
        _hrvStreamController!.addError(e);
      }
    });
    
    return _hrvStreamController!.stream;
  }

  /// Sync data to Syni Core backend (RFC specification)
  Future<void> syncToSyni({Map<String, Object?> context = const {}}) async {
    if (config.syniEndpoint == null) {
      throw SynheartWearError('Syni endpoint not configured');
    }

    try {
      // Get cached sessions that haven't been synced
      final sessions = await LocalCache.getCachedSessions();
      final unsyncedSessions = sessions.where((s) => !s.isSynced).toList();

      if (unsyncedSessions.isEmpty) {
        return; // Nothing to sync
      }

      // TODO: Implement actual HTTP/gRPC sync to Syni Core
      // For now, simulate successful sync
      await _simulateSyniSync(unsyncedSessions, context);
      
      // Mark sessions as synced
      for (final session in unsyncedSessions) {
        final syncedSession = WearMetrics(
          timestamp: session.timestamp,
          deviceId: session.deviceId,
          source: session.source,
          metrics: session.metrics,
          meta: {...session.meta, 'synced': true},
        );
        
        if (config.enableLocalCaching) {
          await LocalCache.storeSession(syncedSession);
        }
      }
    } catch (e) {
      throw NetworkError('Failed to sync to Syni: $e', e is Exception ? e : null);
    }
  }

  /// Get cached sessions for analysis
  Future<List<WearMetrics>> getCachedSessions({
    DateTime? startDate,
    DateTime? endDate,
    int? limit,
  }) async {
    if (!config.enableLocalCaching) {
      throw SynheartWearError('Local caching is disabled');
    }
    
    return await LocalCache.getCachedSessions(
      startDate: startDate,
      endDate: endDate,
      limit: limit,
    );
  }

  /// Get cache statistics
  Future<Map<String, Object?>> getCacheStats() async {
    if (!config.enableLocalCaching) {
      return {'enabled': false};
    }
    
    return await LocalCache.getCacheStats();
  }

  /// Clear old cached data
  Future<void> clearOldCache({Duration maxAge = const Duration(days: 30)}) async {
    if (!config.enableLocalCaching) return;
    
    await LocalCache.clearOldData(maxAge: maxAge);
  }

  /// Request permissions for data access
  Future<Map<PermissionType, ConsentStatus>> requestPermissions({
    Set<PermissionType>? permissions,
    String? reason,
  }) async {
    final requiredPermissions = permissions ?? _getRequiredPermissions();
    return await ConsentManager.requestConsent(requiredPermissions, reason: reason);
  }

  /// Check current permission status
  Map<PermissionType, ConsentStatus> getPermissionStatus() {
    return ConsentManager.getAllConsents();
  }

  /// Revoke all permissions
  Future<void> revokeAllPermissions() async {
    await ConsentManager.revokeAllConsents();
  }

  /// Dispose resources
  void dispose() {
    _streamTimer?.cancel();
    _hrStreamController?.close();
    _hrvStreamController?.close();
    _initialized = false;
  }

  /// Request necessary permissions based on enabled adapters
  Future<void> _requestPermissions() async {
    final requiredPermissions = _getRequiredPermissions();
    await ConsentManager.requestConsent(requiredPermissions);
  }

  /// Get required permissions based on enabled adapters
  Set<PermissionType> _getRequiredPermissions() {
    final permissions = <PermissionType>{};
    
    if (config.isAdapterEnabled(DeviceAdapter.appleHealthKit)) {
      permissions.addAll({PermissionType.heartRate, PermissionType.heartRateVariability});
    }
    
    if (config.isAdapterEnabled(DeviceAdapter.fitbit)) {
      permissions.addAll({PermissionType.heartRate, PermissionType.steps, PermissionType.calories});
    }
    
    return permissions;
  }

  /// Initialize enabled adapters
  Future<void> _initializeAdapters() async {
    if (config.isAdapterEnabled(DeviceAdapter.appleHealthKit)) {
      await AppleHealthKitAdapter.ensurePermissions();
    }
    
    if (config.isAdapterEnabled(DeviceAdapter.fitbit)) {
      await FitbitAdapter.ensurePermissions();
    }
  }

  /// Start the streaming timer
  void _startStreaming(Duration interval) {
    _streamTimer?.cancel();
    _streamTimer = Timer.periodic(interval, (timer) async {
      try {
        final metrics = await readMetrics();
        _hrStreamController?.add(metrics);
      } catch (e) {
        _hrStreamController?.addError(e);
      }
    });
  }

  /// Simulate Syni sync (placeholder implementation)
  Future<void> _simulateSyniSync(List<WearMetrics> sessions, Map<String, Object?> context) async {
    // TODO: Replace with actual HTTP/gRPC call to Syni Core
    await Future.delayed(const Duration(milliseconds: 100));
    print('Simulated sync of ${sessions.length} sessions to Syni Core');
  }
}
