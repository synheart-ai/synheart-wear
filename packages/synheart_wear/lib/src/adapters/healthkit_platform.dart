import 'dart:io';
import 'package:synheart_wear/synheart_wear.dart';
import 'platform_adapter.dart';

class HealthKitPlatform {
  /// Request permissions using platform interface
  static Future<bool> requestPermissions() async {
    if (!Platform.isIOS) return false;
    
    final isAvailable = await PlatformAdapter.isAvailable();
    if (!isAvailable) return false;
    
    // Request basic permissions for heart rate and HRV
    return await PlatformAdapter.requestPermissions({
      PermissionType.heartRate,
      PermissionType.heartRateVariability,
    });
  }

  /// Check if HealthKit is available
  static Future<bool> isAvailable() async {
    if (!Platform.isIOS) return false;
    return await PlatformAdapter.isAvailable();
  }

  /// Get current heart rate using platform interface
  static Future<double?> getCurrentHeartRate() async {
    if (!Platform.isIOS) return null;
    
    final metrics = await PlatformAdapter.readHealthData({
      PermissionType.heartRate,
    });
    
    return metrics?.getMetric(MetricType.hr)?.toDouble();
  }

  /// Get current HRV using platform interface
  static Future<double?> getCurrentHRV() async {
    if (!Platform.isIOS) return null;
    
    final metrics = await PlatformAdapter.readHealthData({
      PermissionType.heartRateVariability,
    });
    
    return metrics?.getMetric(MetricType.hrvSdnn)?.toDouble();
  }
  
  /// Get permission status using platform interface
  static Future<Map<PermissionType, bool>> getPermissionStatus(
    Set<PermissionType> permissions,
  ) async {
    if (!Platform.isIOS) return {};
    return await PlatformAdapter.getPermissionStatus(permissions);
  }
}