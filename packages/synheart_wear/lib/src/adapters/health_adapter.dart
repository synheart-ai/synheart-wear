import 'package:health/health.dart';
import '../core/consent_manager.dart';
import '../core/models.dart';

/// Adapter for the health package to handle HealthKit integration
class HealthAdapter {
  static final Health _health = Health();
  static bool _configured = false;

  /// Configure the health package (required before any operations)
  static Future<void> _ensureConfigured() async {
    if (!_configured) {
      await _health.configure();
      _configured = true;
    }
  }

  /// Map Synheart permission types to Health package types
  static List<HealthDataType> mapPermissions(Set<PermissionType> permissions) {
    final healthTypes = <HealthDataType>[];

    for (final permission in permissions) {
      switch (permission) {
        case PermissionType.heartRate:
          healthTypes.add(HealthDataType.HEART_RATE);
          break;
        case PermissionType.heartRateVariability:
          healthTypes.add(HealthDataType.HEART_RATE_VARIABILITY_SDNN);
          break;
        case PermissionType.steps:
          healthTypes.add(HealthDataType.STEPS);
          break;
        case PermissionType.calories:
          healthTypes.add(HealthDataType.ACTIVE_ENERGY_BURNED);
          break;
        case PermissionType.sleep:
          healthTypes.add(HealthDataType.SLEEP_IN_BED);
          break;
        case PermissionType.stress:
          // Note: Stress is not directly available in Health package
          // You might need to calculate from HRV or use other metrics
          break;
        case PermissionType.all:
          // Request all available types
          healthTypes.addAll([
            HealthDataType.HEART_RATE,
            HealthDataType.HEART_RATE_VARIABILITY_SDNN,
            HealthDataType.STEPS,
            HealthDataType.ACTIVE_ENERGY_BURNED,
            HealthDataType.SLEEP_IN_BED,
          ]);
          break;
      }
    }

    return healthTypes;
  }

  /// Request permissions using health package (v13.2.1 API)
  static Future<bool> requestPermissions(
      Set<PermissionType> permissions) async {
    final healthTypes = mapPermissions(permissions);
    if (healthTypes.isEmpty) return false;

    try {
      await _ensureConfigured();
      return await _health.requestAuthorization(healthTypes);
    } catch (e) {
      print('Health permission request error: $e');
      return false;
    }
  }

  /// Check if health data is available
  static Future<bool> isAvailable() async {
    try {
      await _ensureConfigured();
      // For now, assume health data is available if we can configure
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Read health data for specific permissions (v13.2.1 API)
  static Future<List<HealthDataPoint>> readHealthData(
    Set<PermissionType> permissions, {
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    final healthTypes = mapPermissions(permissions);
    if (healthTypes.isEmpty) return [];

    final start =
        startTime ?? DateTime.now().subtract(const Duration(seconds: 2));
    final end = endTime ?? DateTime.now();

    try {
      await _ensureConfigured();
      final data = await _health.getHealthDataFromTypes(
        startTime: start,
        endTime: end,
        types: healthTypes,
      );

      //print("Data: $data");

      return data;
    } catch (e) {
      print('Health data read error: $e');
      return [];
    }
  }

  /// Convert HealthDataPoint to WearMetrics format
  static WearMetrics? convertToWearMetrics(
    List<HealthDataPoint> dataPoints, {
    String? deviceId,
    String? source,
  }) {
    if (dataPoints.isEmpty) return null;

    final metrics = <String, num?>{};
    final meta = <String, Object?>{};
    final metricTimestamps =
        <String, DateTime>{}; // Track individual metric timestamps

    // Find the most recent data point for each metric type
    // This ensures we get the latest available value for each metric
    final Map<HealthDataType, HealthDataPoint> mostRecentByType = {};

    for (final point in dataPoints) {
      if (!mostRecentByType.containsKey(point.type) ||
          point.dateTo.isAfter(mostRecentByType[point.type]!.dateTo)) {
        mostRecentByType[point.type] = point;
      }
    }

    // Get the most recent data point overall for main timestamp
    final latestPoint = mostRecentByType.values.isEmpty
        ? dataPoints.first
        : mostRecentByType.values.reduce(
            (a, b) => a.dateTo.isAfter(b.dateTo) ? a : b,
          );

    // Process the most recent data point for each metric type
    for (final point in mostRecentByType.values) {
      switch (point.type) {
        case HealthDataType.HEART_RATE:
          if (point.value is NumericHealthValue) {
            metrics['hr'] = (point.value as NumericHealthValue).numericValue;
            metricTimestamps['hr'] = point.dateTo;
          }
          break;
        case HealthDataType.HEART_RATE_VARIABILITY_SDNN:
          if (point.value is NumericHealthValue) {
            metrics['hrv_rmssd'] =
                (point.value as NumericHealthValue).numericValue;
            metricTimestamps['hrv_rmssd'] = point.dateTo;
          }
          break;
        case HealthDataType.STEPS:
          if (point.value is NumericHealthValue) {
            metrics['steps'] = (point.value as NumericHealthValue).numericValue;
            metricTimestamps['steps'] = point.dateTo;
          }
          break;
        case HealthDataType.ACTIVE_ENERGY_BURNED:
          if (point.value is NumericHealthValue) {
            metrics['calories'] =
                (point.value as NumericHealthValue).numericValue;
            metricTimestamps['calories'] = point.dateTo;
          }
          break;
        case HealthDataType.SLEEP_IN_BED:
          // Convert sleep duration to hours
          final duration = point.dateTo.difference(point.dateFrom);
          metrics['sleep_hours'] = duration.inMinutes / 60.0;
          metricTimestamps['sleep_hours'] = point.dateTo;
          break;
        default:
          break;
      }
    }

    // Add metadata
    meta['source'] = source ?? 'health_package';
    meta['data_points_count'] = dataPoints.length;
    meta['data_points_filtered'] = mostRecentByType.length;
    meta['synced'] = true;
    // Store individual metric timestamps in metadata
    meta['metric_timestamps'] = metricTimestamps.map(
      (key, value) => MapEntry(key, value.toIso8601String()),
    );

    return WearMetrics(
      timestamp: latestPoint.dateTo,
      deviceId: deviceId ?? 'health_${DateTime.now().millisecondsSinceEpoch}',
      source: source ?? 'health_package',
      metrics: metrics,
      meta: meta,
    );
  }

  /// Get permission status for specific types (v13.2.1 feature)
  static Future<Map<PermissionType, bool>> getPermissionStatus(
    Set<PermissionType> permissions,
  ) async {
    final healthTypes = mapPermissions(permissions);
    final results = <PermissionType, bool>{};

    try {
      await _ensureConfigured();

      for (int i = 0; i < permissions.length; i++) {
        final permission = permissions.elementAt(i);
        final healthType = healthTypes[i];

        // Use hasPermissions method from health package
        final hasPermission = await _health.hasPermissions([healthType]);
        results[permission] = hasPermission ?? false;
      }
    } catch (e) {
      // Mark all as false on error
      for (final permission in permissions) {
        results[permission] = false;
      }
    }

    return results;
  }
}
