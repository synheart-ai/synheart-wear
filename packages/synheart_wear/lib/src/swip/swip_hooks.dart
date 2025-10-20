import '../core/models.dart';

typedef ImpactScore = double;

abstract class SwipHooks {
  /// Called when a partner app experiences a measurable session.
  Future<ImpactScore> onSessionSummary({
    required WearMetrics before,
    required WearMetrics during,
    required WearMetrics after,
    Map<String, Object?> context = const {},
  });
}
