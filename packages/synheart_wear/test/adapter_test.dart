import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/src/adapters/apple_healthkit.dart';
import 'package:synheart_wear/src/adapters/fitbit.dart';
import 'package:synheart_wear/src/adapters/wear_adapter.dart';
import 'package:synheart_wear/synheart_wear.dart';

void main() {
  group('WearAdapter Interface Tests', () {
    test('AppleHealthKitAdapter implements WearAdapter correctly', () {
      final adapter = AppleHealthKitAdapter();

      expect(adapter.id, equals('apple_healthkit'));
      expect(adapter.supportedPermissions, contains(PermissionType.heartRate));
      expect(adapter.supportedPermissions,
          contains(PermissionType.heartRateVariability));
      expect(adapter.supportedPermissions, contains(PermissionType.steps));
      expect(adapter.supportedPermissions, contains(PermissionType.calories));
    });

    test('FitbitAdapter implements WearAdapter correctly', () {
      final adapter = FitbitAdapter();

      expect(adapter.id, equals('fitbit'));
      expect(adapter.supportedPermissions, contains(PermissionType.heartRate));
      expect(adapter.supportedPermissions, contains(PermissionType.steps));
      expect(adapter.supportedPermissions, contains(PermissionType.calories));
      expect(adapter.supportedPermissions,
          isNot(contains(PermissionType.heartRateVariability)));
    });
  });

  group('Mock Adapter Tests', () {
    test('MockWearAdapter works correctly', () async {
      final mockAdapter = MockWearAdapter();

      expect(mockAdapter.id, equals('mock_adapter'));
      expect(
          mockAdapter.supportedPermissions, contains(PermissionType.heartRate));

      final metrics = await mockAdapter.readSnapshot();
      expect(metrics, isNotNull);
      expect(metrics!.source, equals('mock_adapter'));
      expect(metrics.getMetric(MetricType.hr), equals(75));
      expect(mockAdapter.readSnapshotCalled, isTrue);
    });

    test('FailingWearAdapter throws correctly', () async {
      final failingAdapter = FailingWearAdapter();

      expect(failingAdapter.id, equals('failing_adapter'));
      expect(failingAdapter.supportedPermissions,
          contains(PermissionType.heartRate));

      expect(
        () async => await failingAdapter.readSnapshot(),
        throwsA(isA<UnimplementedError>()),
      );
    });
  });

  // Note: Integration tests that require HealthKit or actual device access
  // are disabled for CI compatibility. These should be run on actual devices.
}

// Mock adapter for testing
class MockWearAdapter implements WearAdapter {
  bool readSnapshotCalled = false;

  @override
  String get id => 'mock_adapter';

  @override
  Set<PermissionType> get supportedPermissions => {PermissionType.heartRate};

  @override
  Future<void> ensurePermissions() async {}

  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = false}) async {
    readSnapshotCalled = true;
    return WearMetrics(
      timestamp: DateTime.now(),
      deviceId: 'mock_device',
      source: id,
      metrics: {'hr': 75},
    );
  }
}

// Failing adapter for error testing
class FailingWearAdapter implements WearAdapter {
  @override
  String get id => 'failing_adapter';

  @override
  Set<PermissionType> get supportedPermissions => {PermissionType.heartRate};

  @override
  Future<void> ensurePermissions() async {}

  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = false}) {
    throw UnimplementedError();
  }
}
