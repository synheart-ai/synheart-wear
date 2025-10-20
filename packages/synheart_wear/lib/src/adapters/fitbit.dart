import '../core/consent_manager.dart';
import '../core/models.dart';
import 'wear_adapter.dart';

class FitbitAdapter implements WearAdapter {

  @override
  String get id => 'fitbit';

  @override
  Set<PermissionType> get supportedPermissions => const {
    PermissionType.heartRate,
    PermissionType.steps,
    PermissionType.calories,
  };

  @override
  Future<void> ensurePermissions() async {
    // TODO: OAuth and scopes.
  }

  @override
  Future<WearMetrics?> readSnapshot() async {
    // TODO: Fitbit Web API call.
    return null; // if unavailable
  }
}
