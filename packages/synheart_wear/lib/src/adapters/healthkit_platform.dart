import 'dart:io';
import 'package:synheart_wear/synheart_wear.dart';
import 'health_adapter.dart';

class HealthKitPlatform {
  /// Request permissions using health package (v13.2.1)
  static Future<bool> requestPermissions() async {
    if (!Platform.isIOS) return false;
    
    final isAvailable = await HealthAdapter.isAvailable();
    if (!isAvailable) return false;
    
    // Request basic permissions for heart rate and HRV
    return await HealthAdapter.requestPermissions({
      PermissionType.heartRate,
      PermissionType.heartRateVariability,
    });
  }

  /// Check if HealthKit is available
  static Future<bool> isAvailable() async {
    if (!Platform.isIOS) return false;
    return await HealthAdapter.isAvailable();
  }

  /// Get current heart rate
  static Future<double?> getCurrentHeartRate() async {
    if (!Platform.isIOS) return null;
    
    final dataPoints = await HealthAdapter.readHealthData({
      PermissionType.heartRate,
    });
    
    final metrics = HealthAdapter.convertToWearMetrics(dataPoints);
    return metrics?.getMetric(MetricType.hr)?.toDouble();
  }

  /// Get current HRV
  static Future<double?> getCurrentHRV() async {
    if (!Platform.isIOS) return null;
    
    final dataPoints = await HealthAdapter.readHealthData({
      PermissionType.heartRateVariability,
    });
    
    final metrics = HealthAdapter.convertToWearMetrics(dataPoints);
    return metrics?.getMetric(MetricType.hrvSdnn)?.toDouble();
  }
  
  /// Get permission status for specific types (v13.2.1 feature)
  static Future<Map<PermissionType, bool>> getPermissionStatus(
    Set<PermissionType> permissions,
  ) async {
    if (!Platform.isIOS) return {};
    return await HealthAdapter.getPermissionStatus(permissions);
  }
}