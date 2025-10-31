import '../../synheart_wear.dart';
import 'health_adapter.dart';
import 'wear_adapter.dart';
import 'healthkit_rr_channel.dart';

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
    // Check if HealthKit is available
    final isAvailable = await HealthAdapter.isAvailable();
    if (!isAvailable) {
      throw DeviceUnavailableError('HealthKit is not available on this device');
    }

    // Request permissions using health package
    final granted =
        await HealthAdapter.requestPermissions(supportedPermissions);
    if (!granted) {
      throw PermissionDeniedError('HealthKit permissions were denied');
    }
  }

  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    try {
      // Use shorter time range for real-time focus exercises, longer for general health
      final timeRange = const Duration(hours: 24);

      // Read data using health package
      final dataPoints = await HealthAdapter.readHealthData(
        supportedPermissions,
        startTime: DateTime.now().subtract(timeRange),
        endTime: DateTime.now(),
      );

      // Convert to WearMetrics
      final metrics = HealthAdapter.convertToWearMetrics(
        dataPoints,
        deviceId: 'applewatch_${DateTime.now().millisecondsSinceEpoch}',
        source: id,
      );

      if (metrics != null) {
        // Attempt to enrich with RR intervals via HealthKit heartbeat series
        final rr = await HealthKitRRChannel.fetchHeartbeatSeries(
          start: DateTime.now().subtract(const Duration(minutes: 30)),
          end: DateTime.now(),
        );
        if (rr.isNotEmpty) {
          return WearMetrics(
            timestamp: metrics.timestamp,
            deviceId: metrics.deviceId,
            source: metrics.source,
            metrics: metrics.metrics,
            meta: metrics.meta,
            rrIntervalsMs: rr,
          );
        }
      }

      return metrics;
    } catch (e) {
      print('HealthKit read error: $e');
      return null;
    }
  }
}
