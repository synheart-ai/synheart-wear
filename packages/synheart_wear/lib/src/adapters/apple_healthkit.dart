import '../../synheart_wear.dart';
import '../core/models.dart';
import 'wear_adapter.dart';

class AppleHealthKitAdapter implements WearAdapter {

  @override
  String get id => 'apple_healthkit';

  @override
  Set<PermissionType> get supportedPermissions => const {
    PermissionType.heartRate,
    PermissionType.heartRateVariability,
  };

  Future<void> ensurePermissions() async {
    // TODO: Implement HealthKit permission requests via platform channel.
  }

  Future<WearMetrics?> readSnapshot() async {
    // TODO: Read HR, HRV, steps via HealthKit bridge.
    return WearMetrics(
      timestamp: DateTime.now().toUtc(),
      deviceId: 'applewatch_demo',
      source: 'apple_healthkit',
      metrics: {
        'hr': 72,
        'hrv_rmssd': 45,
        'steps': 1000,
      },
      meta: {'battery': 0.8},
    );
  }
}
