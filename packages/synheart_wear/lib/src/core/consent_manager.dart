import '../core/models.dart';

/// Consent status for data access
enum ConsentStatus {
  notRequested,
  granted,
  denied,
  revoked,
}

/// Permission types for different data access levels
enum PermissionType {
  heartRate,
  heartRateVariability,
  steps,
  calories,
  sleep,
  stress,
  all,
}

/// Consent management for wearable data access
class ConsentManager {
  static final Map<PermissionType, ConsentStatus> _permissions = {};
  static final Map<String, DateTime> _consentTimestamps = {};

  /// Request consent for specific permission types
  static Future<Map<PermissionType, ConsentStatus>> requestConsent(
    Set<PermissionType> permissions, {
    String? reason,
  }) async {
    final results = <PermissionType, ConsentStatus>{};

    for (final permission in permissions) {
      try {
        // TODO: Implement actual permission request UI/platform calls
        // For now, simulate consent request
        final granted = await _simulateConsentRequest(permission, reason);

        _permissions[permission] =
            granted ? ConsentStatus.granted : ConsentStatus.denied;
        _consentTimestamps[permission.name] = DateTime.now();

        results[permission] = _permissions[permission]!;
      } catch (e) {
        _permissions[permission] = ConsentStatus.denied;
        results[permission] = ConsentStatus.denied;
      }
    }

    return results;
  }

  /// Check if consent is granted for specific permission
  static bool hasConsent(PermissionType permission) {
    return _permissions[permission] == ConsentStatus.granted ||
        _permissions[PermissionType.all] == ConsentStatus.granted;
  }

  /// Check if consent is granted for any of the specified permissions
  static bool hasAnyConsent(Set<PermissionType> permissions) {
    return permissions.any((p) => hasConsent(p));
  }

  /// Revoke consent for specific permission
  static Future<void> revokeConsent(PermissionType permission) async {
    _permissions[permission] = ConsentStatus.revoked;
    _consentTimestamps.remove(permission.name);

    // TODO: Notify adapters to stop collecting this data
  }

  /// Revoke all consents
  static Future<void> revokeAllConsents() async {
    for (final permission in _permissions.keys) {
      await revokeConsent(permission);
    }
  }

  /// Get consent status for all permissions
  static Map<PermissionType, ConsentStatus> getAllConsents() {
    return Map.from(_permissions);
  }

  /// Get consent timestamp for a permission
  static DateTime? getConsentTimestamp(PermissionType permission) {
    return _consentTimestamps[permission.name];
  }

  /// Check if consent is still valid (not expired)
  static bool isConsentValid(PermissionType permission) {
    final timestamp = getConsentTimestamp(permission);
    if (timestamp == null) return false;

    // Consent expires after 30 days
    final expiry = timestamp.add(const Duration(days: 30));
    return DateTime.now().isBefore(expiry);
  }

  /// Simulate consent request (placeholder for actual implementation)
  static Future<bool> _simulateConsentRequest(
    PermissionType permission,
    String? reason,
  ) async {
    // TODO: Replace with actual platform-specific permission requests
    // This would typically show a system permission dialog

    // For development, simulate user granting consent
    await Future.delayed(const Duration(milliseconds: 500));
    return true; // Simulate granted consent
  }

  /// Validate that required consents are in place before data collection
  static void validateConsents(Set<PermissionType> requiredPermissions) {
    final missingConsents = <PermissionType>[];

    for (final permission in requiredPermissions) {
      if (!hasConsent(permission) || !isConsentValid(permission)) {
        missingConsents.add(permission);
      }
    }

    if (missingConsents.isNotEmpty) {
      throw PermissionDeniedError(
        'Missing or expired consents for: ${missingConsents.map((p) => p.name).join(', ')}',
      );
    }
  }
}
