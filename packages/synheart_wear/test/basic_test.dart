import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/synheart_wear.dart';

void main() {
  group('SynheartWear SDK Tests', () {
    test('WearMetrics model functionality', () {
      final metrics = WearMetrics(
        timestamp: DateTime.now(),
        deviceId: 'test_device',
        source: 'test_source',
        metrics: {'hr': 72, 'steps': 1000},
        meta: {'battery': 0.8},
      );

      expect(metrics.getMetric(MetricType.hr), equals(72));
      expect(metrics.getMetric(MetricType.steps), equals(1000));
      expect(metrics.hasValidData, isTrue);
      expect(metrics.batteryLevel, equals(0.8));
      expect(metrics.isSynced, isFalse);
    });

    test('WearMetrics JSON serialization', () {
      final metrics = WearMetrics(
        timestamp: DateTime.parse('2025-10-20T18:30:00Z'),
        deviceId: 'test_device',
        source: 'test_source',
        metrics: {'hr': 72},
        meta: {'battery': 0.8},
      );

      final json = metrics.toJson();
      expect(json['device_id'], equals('test_device'));
      expect(json['source'], equals('test_source'));
      expect((json['metrics'] as Map<String, dynamic>)['hr'], equals(72));

      final restored = WearMetrics.fromJson(json);
      expect(restored.deviceId, equals(metrics.deviceId));
      expect(restored.getMetric(MetricType.hr), equals(72));
    });

    test('error types work correctly', () {
      final permissionError = PermissionDeniedError('Test permission denied');
      expect(permissionError.code, equals('PERMISSION_DENIED'));

      final deviceError = DeviceUnavailableError('Test device unavailable');
      expect(deviceError.code, equals('DEVICE_UNAVAILABLE'));

      final networkError = NetworkError('Test network error');
      expect(networkError.code, equals('NETWORK_ERROR'));
    });

    test('configuration works correctly', () {
      final config =
          SynheartWearConfig.withAdapters({DeviceAdapter.appleHealthKit});
      expect(config.isAdapterEnabled(DeviceAdapter.appleHealthKit), isTrue);
      expect(config.isAdapterEnabled(DeviceAdapter.fitbit), isFalse);
    });
  });

  // Note: Integration tests that require HealthKit or file system access
  // are disabled for CI compatibility. These should be run on actual devices.
}
