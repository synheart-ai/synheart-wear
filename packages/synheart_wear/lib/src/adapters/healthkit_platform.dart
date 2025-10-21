import 'dart:io';
import 'package:flutter/services.dart';

class HealthKitPlatform {
  static const MethodChannel _channel =
      MethodChannel('synheart_wear/healthkit');

  /// Request HealthKit permissions for heart rate and HRV
  static Future<bool> requestPermissions() async {
    if (!Platform.isIOS) {
      return false; // HealthKit only available on iOS
    }

    try {
      final result = await _channel.invokeMethod('requestPermissions');
      return result as bool;
    } on PlatformException catch (e) {
      print('HealthKit permission error: ${e.message}');
      return false;
    }
  }

  /// Check if HealthKit is available on this device
  static Future<bool> isAvailable() async {
    if (!Platform.isIOS) return false;

    try {
      final result = await _channel.invokeMethod('isAvailable');
      return result as bool;
    } on PlatformException {
      return false;
    }
  }

  /// Read current heart rate from HealthKit
  static Future<double?> getCurrentHeartRate() async {
    if (!Platform.isIOS) return null;

    try {
      final result = await _channel.invokeMethod('getCurrentHeartRate');
      return result as double?;
    } on PlatformException catch (e) {
      print('HealthKit HR error: ${e.message}');
      return null;
    }
  }

  /// Read HRV data from HealthKit
  static Future<double?> getCurrentHRV() async {
    if (!Platform.isIOS) return null;

    try {
      final result = await _channel.invokeMethod('getCurrentHRV');
      return result as double?;
    } on PlatformException catch (e) {
      print('HealthKit HRV error: ${e.message}');
      return null;
    }
  }
}
