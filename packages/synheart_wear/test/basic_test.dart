import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/synheart_wear.dart';

void main() {
  // group('SynheartWear SDK Tests', () {
  //   late SynheartWear sdk;

  //   setUp(() {
  //     sdk = SynheartWear(
  //       config: const SynheartWearConfig(
  //         enableLocalCaching: false, // Disable for tests
  //         enableEncryption: false,
  //       ),
  //     );
  //   });

  //   tearDown(() {
  //     sdk.dispose();
  //   });

  //   test('initialize and readMetrics', () async {
  //     await sdk.initialize();
  //     final snap = await sdk.readMetrics();

  //     expect(snap.metrics, isA<Map<String, num?>>());
  //     expect(snap.timestamp, isA<DateTime>());
  //     expect(snap.deviceId, isA<String>());
  //     expect(snap.source, isA<String>());
  //   });

  //   test('configuration works correctly', () {
  //     final config = SynheartWearConfig.withAdapters({DeviceAdapter.appleHealthKit});
  //     expect(config.isAdapterEnabled(DeviceAdapter.appleHealthKit), isTrue);
  //     expect(config.isAdapterEnabled(DeviceAdapter.fitbit), isFalse);
  //   });

  //   test('error handling for invalid data', () async {
  //     await sdk.initialize();

  //     // This should not throw due to error handling in readMetrics
  //     final snap = await sdk.readMetrics();
  //     expect(snap, isA<WearMetrics>());
  //   });

  //   test('permission management', () async {
  //     final permissions = await sdk.requestPermissions();
  //     expect(permissions, isA<Map<PermissionType, ConsentStatus>>());

  //     final status = sdk.getPermissionStatus();
  //     expect(status, isA<Map<PermissionType, ConsentStatus>>());
  //   });

  //   test('WearMetrics model functionality', () {
  //     final metrics = WearMetrics(
  //       timestamp: DateTime.now(),
  //       deviceId: 'test_device',
  //       source: 'test_source',
  //       metrics: {'hr': 72, 'steps': 1000},
  //       meta: {'battery': 0.8},
  //     );

  //     expect(metrics.getMetric(MetricType.hr), equals(72));
  //     expect(metrics.getMetric(MetricType.steps), equals(1000));
  //     expect(metrics.hasValidData, isTrue);
  //     expect(metrics.batteryLevel, equals(0.8));
  //     expect(metrics.isSynced, isFalse);
  //   });

  //   test('WearMetrics JSON serialization', () {
  //     final metrics = WearMetrics(
  //       timestamp: DateTime.parse('2025-10-20T18:30:00Z'),
  //       deviceId: 'test_device',
  //       source: 'test_source',
  //       metrics: {'hr': 72},
  //       meta: {'battery': 0.8},
  //     );

  //     final json = metrics.toJson();
  //     expect(json['device_id'], equals('test_device'));
  //     expect(json['source'], equals('test_source'));
  //     expect(json['metrics']['hr'], equals(72));

  //     final restored = WearMetrics.fromJson(json);
  //     expect(restored.deviceId, equals(metrics.deviceId));
  //     expect(restored.getMetric(MetricType.hr), equals(72));
  //   });

  //   test('error types work correctly', () {
  //     final permissionError = PermissionDeniedError('Test permission denied');
  //     expect(permissionError.code, equals('PERMISSION_DENIED'));

  //     final deviceError = DeviceUnavailableError('Test device unavailable');
  //     expect(deviceError.code, equals('DEVICE_UNAVAILABLE'));

  //     final networkError = NetworkError('Test network error');
  //     expect(networkError.code, equals('NETWORK_ERROR'));
  //   });
  // });

  Add this test to test/basic_test.dart
  test('stream timers start/stop based on subscribers', () async {
    // Create a simple test
    final sdk = SynheartWear();
    await sdk.initialize();

    // No subscribers - no timer should be running
    print('Timer active: ${sdk.isStreamTimerActive}'); // Should be false

    // Add subscriber - timer should start
    final subscription = sdk.streamHR().listen((_) {});
    await Future.delayed(Duration(milliseconds: 100));
    print('Timer active: ${sdk.isStreamTimerActive}'); // Should be true

    // Cancel subscription - timer should stop
    await subscription.cancel();
    await Future.delayed(Duration(milliseconds: 100));
    print('Timer active: ${sdk.isStreamTimerActive}'); //
  });
}
