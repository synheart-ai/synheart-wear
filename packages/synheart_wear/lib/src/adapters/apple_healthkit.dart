import '../../synheart_wear.dart';
import 'platform_adapter.dart';
import 'wear_adapter.dart';

class AppleHealthKitAdapter implements WearAdapter {
  @override
  String get id => 'apple_healthkit';

  @override
  Set<PermissionType> get supportedPermissions => const {
        PermissionType.heartRate,
        PermissionType.heartRateVariability,
        PermissionType.steps,
        PermissionType.calories,
      };

  @override
  Future<void> ensurePermissions() async {
    // Check if platform is available
    final isAvailable = await PlatformAdapter.isAvailable();
    if (!isAvailable) {
      throw DeviceUnavailableError('HealthKit is not available on this device');
    }

    // Request permissions using platform interface
    final granted = await PlatformAdapter.requestPermissions(supportedPermissions);
    if (!granted) {
      throw PermissionDeniedError('HealthKit permissions were denied');
    }
  }

  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    try {
      // Read data using platform interface
      final metrics = await PlatformAdapter.readHealthData(
        supportedPermissions,
        startTime: isRealTime 
            ? DateTime.now().subtract(const Duration(minutes: 2))
            : DateTime.now().subtract(const Duration(hours: 24)),
        endTime: DateTime.now(),
      );

      return metrics;
    } catch (e) {
      print('HealthKit read error: $e');
      return null;
    }
  }
}