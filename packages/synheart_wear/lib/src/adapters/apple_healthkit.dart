import '../../synheart_wear.dart';
import 'healthkit_platform.dart';
import 'wear_adapter.dart';

class AppleHealthKitAdapter implements WearAdapter {

  @override
  String get id => 'apple_healthkit';

  @override
  Set<PermissionType> get supportedPermissions => const {
    PermissionType.heartRate,
    PermissionType.heartRateVariability,
  };

  @override
  Future<void> ensurePermissions() async {
    // Check if HealthKit is available
    final isAvailable = await HealthKitPlatform.isAvailable();
    if (!isAvailable) {
      throw DeviceUnavailableError('HealthKit is not available on this device');
    }
    
    // Request permissions
    final granted = await HealthKitPlatform.requestPermissions();
    if (!granted) {
      throw PermissionDeniedError('HealthKit permissions were denied');
    }
  }

  @override
  Future<WearMetrics?> readSnapshot() async {
    try {
      // Read real data from HealthKit
      final hr = await HealthKitPlatform.getCurrentHeartRate();
      final hrv = await HealthKitPlatform.getCurrentHRV();
      
      // Return null if no data available
      if (hr == null && hrv == null) {
        return null;
      }
      
      return WearMetrics(
        timestamp: DateTime.now().toUtc(),
        deviceId: 'applewatch_${DateTime.now().millisecondsSinceEpoch}',
        source: id,
        metrics: {
          if (hr != null) 'hr': hr,
          if (hrv != null) 'hrv_rmssd': hrv,
        },
        meta: {
          'battery': 0.8, // TODO: Get real battery level
          'synced': true,
        },
      );
    } catch (e) {
      print('HealthKit read error: $e');
      return null;
    }
  }
}
