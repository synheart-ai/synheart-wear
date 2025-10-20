import '../core/models.dart';

class AppleHealthKitAdapter {
  static Future<void> ensurePermissions() async {
    // TODO: Implement HealthKit permission requests via platform channel.
  }

  static Future<WearMetrics?> readSnapshot() async {
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
