/// Supported device adapters
enum DeviceAdapter {
  appleHealthKit,
  fitbit,
  garmin,
  whoop,
  samsungHealth,
}

/// Configuration for the SynheartWear SDK
class SynheartWearConfig {
  final Set<DeviceAdapter> enabledAdapters;
  final Duration streamInterval;
  final Duration hrvWindowSize;
  final bool enableLocalCaching;
  final bool enableEncryption;
  final Map<String, Object?> adapterConfig;

  const SynheartWearConfig({
    this.enabledAdapters = const {
      DeviceAdapter.appleHealthKit,
      DeviceAdapter.fitbit,
    },
    this.streamInterval = const Duration(seconds: 5),
    this.hrvWindowSize = const Duration(seconds: 5),
    this.enableLocalCaching = true,
    this.enableEncryption = true,
    this.adapterConfig = const {},
  });

  /// Create config with only specific adapters enabled
  SynheartWearConfig.withAdapters(Set<DeviceAdapter> adapters) : this(
    enabledAdapters: adapters,
  );

  /// Create config for development/testing
  SynheartWearConfig.development() : this(
    enabledAdapters: const {DeviceAdapter.appleHealthKit},
    enableLocalCaching: false,
    enableEncryption: false,
  );

  /// Create config for production
  SynheartWearConfig.production() : this(
    enabledAdapters: const {
      DeviceAdapter.appleHealthKit,
      DeviceAdapter.fitbit,
      DeviceAdapter.garmin,
      DeviceAdapter.whoop,
      DeviceAdapter.samsungHealth,
    },
    enableLocalCaching: true,
    enableEncryption: true,
  );

  /// Check if a specific adapter is enabled
  bool isAdapterEnabled(DeviceAdapter adapter) {
    return enabledAdapters.contains(adapter);
  }

  /// Get configuration for a specific adapter
  Map<String, Object?> getAdapterConfig(DeviceAdapter adapter) {
    final adapterKey = adapter.name;
    return Map<String, Object?>.from(
      adapterConfig[adapterKey] as Map? ?? {},
    );
  }

  /// Create a copy with modified settings
  SynheartWearConfig copyWith({
    Set<DeviceAdapter>? enabledAdapters,
    Duration? streamInterval,
    Duration? hrvWindowSize,
    bool? enableLocalCaching,
    bool? enableEncryption,
    Map<String, Object?>? adapterConfig,
  }) {
    return SynheartWearConfig(
      enabledAdapters: enabledAdapters ?? this.enabledAdapters,
      streamInterval: streamInterval ?? this.streamInterval,
      hrvWindowSize: hrvWindowSize ?? this.hrvWindowSize,
      enableLocalCaching: enableLocalCaching ?? this.enableLocalCaching,
      enableEncryption: enableEncryption ?? this.enableEncryption,
      adapterConfig: adapterConfig ?? this.adapterConfig,
    );
  }
}
