import 'package:flutter/services.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';

abstract class SynheartWearPlatform extends PlatformInterface {
  /// Constructs a SynheartWearPlatform.
  SynheartWearPlatform() : super(token: _token);

  static final Object _token = Object();
  static SynheartWearPlatform _instance = MethodChannelSynheartWear();
  
  /// The default instance of [SynheartWearPlatform] to use.
  static SynheartWearPlatform get instance => _instance;
  
  /// Platform-specific implementations should set this with their own
  /// platform-specific class that extends [SynheartWearPlatform] when
  /// they register themselves.
  static set instance(SynheartWearPlatform instance) {
    PlatformInterface.verifyToken(instance, _token);
    _instance = instance;
  }

  /// Initialize the platform
  Future<bool> initialize();

  /// Request permissions for data access
  Future<Map<String, dynamic>> requestPermissions(List<String> permissions);

  /// Read current metrics snapshot
  Future<Map<String, dynamic>> readMetrics();

  /// Stream real-time heart rate data
  Stream<Map<String, dynamic>> streamHeartRate();

  /// Stream HRV data in configurable windows
  Stream<Map<String, dynamic>> streamHRV();

  /// Dispose resources
  Future<void> dispose();
}

/// The default implementation of [SynheartWearPlatform], using method channels.
class MethodChannelSynheartWear extends SynheartWearPlatform {
  /// The method channel used to interact with the native platform.
  static const MethodChannel _channel = MethodChannel('synheart_wear');

  @override
  Future<bool> initialize() async {
    return await _channel.invokeMethod<bool>('initialize') ?? false;
  }

  @override
  Future<Map<String, dynamic>> requestPermissions(List<String> permissions) async {
    final result = await _channel.invokeMethod<Map<Object?, Object?>>(
      'requestPermissions',
      {'permissions': permissions},
    );
    return Map<String, dynamic>.from(result ?? {});
  }

  @override
  Future<Map<String, dynamic>> readMetrics() async {
    final result = await _channel.invokeMethod<Map<Object?, Object?>>('readMetrics');
    return Map<String, dynamic>.from(result ?? {});
  }

  @override
  Stream<Map<String, dynamic>> streamHeartRate() {
    const eventChannel = EventChannel('synheart_wear/heart_rate');
    return eventChannel.receiveBroadcastStream().map((event) {
      return Map<String, dynamic>.from(event as Map<Object?, Object?>);
    });
  }

  @override
  Stream<Map<String, dynamic>> streamHRV() {
    const eventChannel = EventChannel('synheart_wear/hrv');
    return eventChannel.receiveBroadcastStream().map((event) {
      return Map<String, dynamic>.from(event as Map<Object?, Object?>);
    });
  }

  @override
  Future<void> dispose() async {
    await _channel.invokeMethod('dispose');
  }
}