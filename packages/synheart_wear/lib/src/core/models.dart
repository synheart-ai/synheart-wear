/// Supported metric types as defined in the RFC schema
enum MetricType {
  hr,
  hrvRmssd,
  hrvSdnn,
  steps,
  calories,
  stress,
}

/// Error types for the SDK
class SynheartWearError implements Exception {
  final String message;
  final String? code;
  final Exception? originalException;

  SynheartWearError(this.message, {this.code, this.originalException});

  @override
  String toString() =>
      'SynheartWearError: $message${code != null ? ' ($code)' : ''}';
}

class PermissionDeniedError extends SynheartWearError {
  PermissionDeniedError(String message)
      : super(message, code: 'PERMISSION_DENIED');
}

class DeviceUnavailableError extends SynheartWearError {
  DeviceUnavailableError(String message)
      : super(message, code: 'DEVICE_UNAVAILABLE');
}

class NetworkError extends SynheartWearError {
  NetworkError(String message, [Exception? originalException])
      : super(message,
            code: 'NETWORK_ERROR', originalException: originalException);
}

/// Unified wearable metrics data model following RFC schema
class WearMetrics {
  final DateTime timestamp;
  final String deviceId;
  final String source;
  final Map<String, num?> metrics;
  final Map<String, Object?> meta;

  WearMetrics({
    required this.timestamp,
    required this.deviceId,
    required this.source,
    required this.metrics,
    this.meta = const {},
  });

  /// Create WearMetrics from JSON
  factory WearMetrics.fromJson(Map<String, Object?> json) {
    return WearMetrics(
      timestamp: DateTime.parse(json['timestamp'] as String),
      deviceId: json['device_id'] as String,
      source: json['source'] as String,
      metrics: Map<String, num?>.from(json['metrics'] as Map),
      meta: Map<String, Object?>.from(json['meta'] as Map? ?? {}),
    );
  }

  /// Convert to JSON following RFC schema
  Map<String, Object?> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'device_id': deviceId,
        'source': source,
        'metrics': metrics,
        'meta': meta,
      };

  /// Get specific metric value with type safety
  num? getMetric(MetricType type) {
    switch (type) {
      case MetricType.hr:
        return metrics['hr'];
      case MetricType.hrvRmssd:
        return metrics['hrv_rmssd'];
      case MetricType.hrvSdnn:
        return metrics['hrv_sdnn'];
      case MetricType.steps:
        return metrics['steps'];
      case MetricType.calories:
        return metrics['calories'];
      case MetricType.stress:
        return metrics['stress'];
    }
  }

  /// Check if metrics contain valid data
  bool get hasValidData => metrics.values.any((value) => value != null);

  /// Get battery level from meta
  double? get batteryLevel => meta['battery'] as double?;

  /// Check if data is synced
  bool get isSynced => meta['synced'] as bool? ?? false;
}
