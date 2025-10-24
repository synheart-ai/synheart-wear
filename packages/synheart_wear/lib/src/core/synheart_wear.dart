import 'dart:async';
import 'package:flutter/foundation.dart';

import '../adapters/wear_adapter.dart';
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

  final Map<DeviceAdapter, WearAdapter> _adapterRegistry;

  Timer? _hrvTimer; // Separate timer for HRV

  SynheartWear(
      {SynheartWearConfig? config, Map<DeviceAdapter, WearAdapter>? adapters})
      : config = config ?? const SynheartWearConfig(),
        _normalizer = Normalizer(),
        _adapterRegistry = adapters ??
            {
              DeviceAdapter.appleHealthKit: AppleHealthKitAdapter(),
              DeviceAdapter.fitbit: FitbitAdapter(),
            };

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
      for (final adapter in _enabledAdapters()) {
        try {
          final data = await adapter.readSnapshot();
          adapterData.add(data);
        } catch (e) {
          // Keep non-fatal, tag by adapter id
          print('${adapter.id} error: $e');
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
        await LocalCache.storeSession(mergedData,
            enableEncryption: config.enableEncryption);
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

    // Start timer when first listener subscribes
    if (!_hrStreamController!.hasListener) {
      _startStreaming(actualInterval);
    }

    return _hrStreamController!.stream;
  }

  /// Stream HRV data in configurable windows (RFC specification)
  Stream<WearMetrics> streamHRV({Duration? windowSize}) {
    final actualWindowSize = windowSize ?? config.hrvWindowSize;

    _hrvStreamController ??= StreamController<WearMetrics>.broadcast();

    // Start timer when first listener subscribes
    if (!_hrvStreamController!.hasListener) {
      _startHrvStreaming(actualWindowSize);
    }

    return _hrvStreamController!.stream;
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
  Future<void> clearOldCache(
      {Duration maxAge = const Duration(days: 30)}) async {
    if (!config.enableLocalCaching) return;

    await LocalCache.clearOldData(maxAge: maxAge);
  }

  /// Request permissions for data access
  Future<Map<PermissionType, ConsentStatus>> requestPermissions({
    Set<PermissionType>? permissions,
    String? reason,
  }) async {
    final requiredPermissions = permissions ?? _getRequiredPermissions();
    return await ConsentManager.requestConsent(requiredPermissions,
        reason: reason);
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
    _hrvTimer?.cancel();
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
    for (final adapter in _enabledAdapters()) {
      permissions.addAll(adapter.supportedPermissions);
    }
    return permissions;
  }

  // Helper to get enabled adapter instances
  List<WearAdapter> _enabledAdapters() {
    return config.enabledAdapters
        .where(_adapterRegistry.containsKey)
        .map((d) => _adapterRegistry[d]!)
        .toList();
  }

  /// Initialize enabled adapters
  Future<void> _initializeAdapters() async {
    for (final adapter in _enabledAdapters()) {
      await adapter.ensurePermissions();
    }
  }

  /// Start the streaming timer
  void _startStreaming(Duration interval) {
    _streamTimer?.cancel();
    _streamTimer = Timer.periodic(interval, (timer) async {
      // Check if we still have subscribers
      if (_hrStreamController?.hasListener != true) {
        _streamTimer?.cancel();
        _streamTimer = null;
        return;
      }

      try {
        final metrics = await readMetrics();
        _hrStreamController?.add(metrics);
      } catch (e) {
        _hrStreamController?.addError(e);
      }
    });
  }

  /// Start HRV streaming timer
  void _startHrvStreaming(Duration windowSize) {
    _hrvTimer?.cancel();
    _hrvTimer = Timer.periodic(windowSize, (timer) async {
      // Check if we still have subscribers
      if (_hrvStreamController?.hasListener != true) {
        _hrvTimer?.cancel();
        _hrvTimer = null;
        return;
      }

      try {
        final metrics = await readMetrics();
        final hrvData = metrics.getMetric(MetricType.hrvRmssd);

        if (hrvData != null) {
          _hrvStreamController?.add(metrics);
        }
      } catch (e) {
        _hrvStreamController?.addError(e);
      }
    });
  }

  /// Getter for testing timer state
  @visibleForTesting
  bool get isStreamTimerActive => _streamTimer?.isActive ?? false;

  @visibleForTesting
  bool get isHrvTimerActive => _hrvTimer?.isActive ?? false;
}
