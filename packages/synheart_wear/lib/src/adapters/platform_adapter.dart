import 'package:synheart_wear/synheart_wear_platform_interface.dart';
import '../core/models.dart';
import '../core/consent_manager.dart';

/// Adapter that uses the platform interface for data access
class PlatformAdapter {
  static final SynheartWearPlatform _platform = SynheartWearPlatform.instance;

  /// Map Synheart permission types to platform permission strings
  static List<String> mapPermissions(Set<PermissionType> permissions) {
    final permissionStrings = <String>[];

    for (final permission in permissions) {
      switch (permission) {
        case PermissionType.heartRate:
          permissionStrings.add('heart_rate');
          break;
        case PermissionType.heartRateVariability:
          permissionStrings.add('heart_rate_variability');
          break;
        case PermissionType.steps:
          permissionStrings.add('steps');
          break;
        case PermissionType.calories:
          permissionStrings.add('calories');
          break;
        case PermissionType.sleep:
          permissionStrings.add('sleep');
          break;
        case PermissionType.stress:
          permissionStrings.add('stress');
          break;
        case PermissionType.all:
          permissionStrings.addAll([
            'heart_rate',
            'heart_rate_variability',
            'steps',
            'calories',
            'sleep',
            'stress',
          ]);
          break;
      }
    }

    return permissionStrings;
  }

  /// Request permissions using platform interface
  static Future<bool> requestPermissions(Set<PermissionType> permissions) async {
    try {
      final permissionStrings = mapPermissions(permissions);
      final result = await _platform.requestPermissions(permissionStrings);
      return result['success'] == true;
    } catch (e) {
      print('Platform permission request error: $e');
      return false;
    }
  }

  /// Check if platform is available
  static Future<bool> isAvailable() async {
    try {
      return await _platform.initialize();
    } catch (e) {
      return false;
    }
  }

  /// Read health data using platform interface
  static Future<WearMetrics?> readHealthData(
    Set<PermissionType> permissions, {
    DateTime? startTime,
    DateTime? endTime,
  }) async {
    try {
      final result = await _platform.readMetrics();
      return WearMetrics.fromJson(result);
    } catch (e) {
      print('Platform data read error: $e');
      return null;
    }
  }

  /// Get permission status
  static Future<Map<PermissionType, bool>> getPermissionStatus(
    Set<PermissionType> permissions,
  ) async {
    final results = <PermissionType, bool>{};
    
    try {
      final permissionStrings = mapPermissions(permissions);
      final result = await _platform.requestPermissions(permissionStrings);
      
      for (final permission in permissions) {
        final permissionString = permission.name;
        results[permission] = result[permissionString] == true;
      }
    } catch (e) {
      for (final permission in permissions) {
        results[permission] = false;
      }
    }

    return results;
  }
}