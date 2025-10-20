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
    expect(adapter.supportedPermissions, contains(PermissionType.heartRateVariability));
    expect(adapter.supportedPermissions, isNot(contains(PermissionType.steps)));
  });

  test('FitbitAdapter implements WearAdapter correctly', () {
    final adapter = FitbitAdapter();
    
    expect(adapter.id, equals('fitbit'));
    expect(adapter.supportedPermissions, contains(PermissionType.heartRate));
    expect(adapter.supportedPermissions, contains(PermissionType.steps));
    expect(adapter.supportedPermissions, contains(PermissionType.calories));
    expect(adapter.supportedPermissions, isNot(contains(PermissionType.heartRateVariability)));
  });
});

group('Adapter Registry Tests', () {
  test('required permissions are union of enabled adapters', () async {
    final sdk = SynheartWear(
      config: const SynheartWearConfig(
        enabledAdapters: {DeviceAdapter.appleHealthKit, DeviceAdapter.fitbit},
        enableLocalCaching: false,
      ),
    );
    
    await sdk.initialize();
    
    // Should include permissions from both adapters
    final permissions = await sdk.requestPermissions();
    expect(permissions.keys, contains(PermissionType.heartRate));
    expect(permissions.keys, contains(PermissionType.heartRateVariability));
    expect(permissions.keys, contains(PermissionType.steps));
    expect(permissions.keys, contains(PermissionType.calories));
  });

  test('custom adapter registry works', () async {
    // Create a mock adapter
    final mockAdapter = MockWearAdapter();
    
    final sdk = SynheartWear(
      config: const SynheartWearConfig(
        enabledAdapters: {DeviceAdapter.appleHealthKit},
        enableLocalCaching: false,
      ),
      adapters: {
        DeviceAdapter.appleHealthKit: mockAdapter,
      },
    );
    
    await sdk.initialize();
    final metrics = await sdk.readMetrics();
    
    expect(metrics.source, equals('mock_adapter'));
    expect(mockAdapter.readSnapshotCalled, isTrue);
  });
});

group('Adapter Error Handling Tests', () {
  test('one adapter failure does not break readMetrics', () async {
    final failingAdapter = FailingWearAdapter();
    
    final sdk = SynheartWear(
      config: const SynheartWearConfig(
        enabledAdapters: {DeviceAdapter.appleHealthKit, DeviceAdapter.fitbit},
        enableLocalCaching: false,
      ),
      adapters: {
        DeviceAdapter.appleHealthKit: AppleHealthKitAdapter(), // This works
        DeviceAdapter.fitbit: failingAdapter, // This fails
      },
    );
    
    await sdk.initialize();
    
    // Should not throw, should return data from working adapter
    final metrics = await sdk.readMetrics();
    expect(metrics, isA<WearMetrics>());
    expect(metrics.source, equals('apple_healthkit'));
  });
});
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
  Future<WearMetrics?> readSnapshot() async {
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
  Future<WearMetrics?> readSnapshot() async {
    throw Exception('Adapter failure');
  }
}
