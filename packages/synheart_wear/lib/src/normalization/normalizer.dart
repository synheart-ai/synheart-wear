import '../core/models.dart';

/// Configuration for the normalization engine
class NormalizerConfig {
  final bool preferLatestData;
  final bool mergeMetricsFromMultipleSources;
  final Duration maxDataAge;

  const NormalizerConfig({
    this.preferLatestData = true,
    this.mergeMetricsFromMultipleSources = true,
    this.maxDataAge = const Duration(hours: 12),
  });
}

/// Normalization engine that merges data from multiple wearable sources
class Normalizer {
  final NormalizerConfig config;

  Normalizer({this.config = const NormalizerConfig()});

  /// Merge multiple wearable snapshots into a single normalized output
  WearMetrics mergeSnapshots(List<WearMetrics?> snaps) {
    // Filter out null values and validate data age
    final validSnaps = snaps
        .where((e) => e != null)
        .where((e) => _isDataFresh(e!))
        .cast<WearMetrics>()
        .toList();

    if (validSnaps.isEmpty) {
      return WearMetrics(
        timestamp: DateTime.now(),
        deviceId: 'unknown',
        source: 'none',
        metrics: {},
        meta: {'error': 'no_valid_data'},
      );
    }

    if (config.preferLatestData) {
      // Sort by timestamp (newest first)
      validSnaps.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      final latest = validSnaps.first;

      if (!config.mergeMetricsFromMultipleSources) {
        return latest;
      }

      // Merge metrics from all sources, preferring latest values
      final mergedMetrics = <String, num?>{};
      for (final snap in validSnaps) {
        for (final entry in snap.metrics.entries) {
          // Only add if not already present (latest takes precedence)
          mergedMetrics.putIfAbsent(entry.key, () => entry.value);
        }
      }

      return WearMetrics(
        timestamp: latest.timestamp,
        deviceId: latest.deviceId,
        source: latest.source,
        metrics: mergedMetrics,
        meta: {
          ...latest.meta,
          'merged_sources': validSnaps.length,
          'normalized': true,
        },
      );
    } else {
      // Use first available snapshot
      return validSnaps.first;
    }
  }

  /// Check if data is within acceptable age limit
  bool _isDataFresh(WearMetrics data) {
    final age = DateTime.now().difference(data.timestamp);
    return age <= config.maxDataAge;
  }

  /// Validate metrics data quality
  bool validateMetrics(WearMetrics data) {
    if (!data.hasValidData) return false;

    // Check for reasonable ranges
    final hr = data.getMetric(MetricType.hr);
    if (hr != null && (hr < 30 || hr > 220)) return false;

    final steps = data.getMetric(MetricType.steps);
    if (steps != null && steps < 0) return false;

    return true;
  }
}
