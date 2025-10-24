import '../core/models.dart';
import '../core/consent_manager.dart';

abstract class WearAdapter {
  String get id;
  Set<PermissionType> get supportedPermissions;

  Future<void> ensurePermissions();
  Future<WearMetrics?> readSnapshot({bool isRealTime = true});
}
