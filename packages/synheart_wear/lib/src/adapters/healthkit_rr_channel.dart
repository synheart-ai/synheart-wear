import 'dart:io';
import 'package:flutter/services.dart';

class HealthKitRRChannel {
  static const MethodChannel _channel =
      MethodChannel('synheart_wear/healthkit_rr');

  static Future<bool> isHeartbeatSeriesAvailable() async {
    if (!Platform.isIOS) return false;
    try {
      final result = await _channel.invokeMethod<bool>('isAvailable');
      return result ?? false;
    } catch (_) {
      return false;
    }
  }

  static Future<List<double>> fetchHeartbeatSeries({
    required DateTime start,
    required DateTime end,
  }) async {
    if (!Platform.isIOS) return <double>[];
    try {
      final List<dynamic>? rr = await _channel.invokeMethod<List<dynamic>>(
        'fetchRR',
        {
          'start': start.toIso8601String(),
          'end': end.toIso8601String(),
        },
      );
      return rr?.map((e) => (e as num).toDouble()).toList() ?? <double>[];
    } catch (_) {
      return <double>[];
    }
  }
}
