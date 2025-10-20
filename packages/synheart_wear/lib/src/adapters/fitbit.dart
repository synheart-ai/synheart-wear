import '../core/models.dart';

class FitbitAdapter {
  static Future<void> ensurePermissions() async {
    // TODO: OAuth and scopes.
  }

  static Future<WearMetrics?> readSnapshot() async {
    // TODO: Fitbit Web API call.
    return null; // if unavailable
  }
}
