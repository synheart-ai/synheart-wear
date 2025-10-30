# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-12-20
## [0.1.2] - 2025-12-21

### Added
- Optional RR intervals output (`rr_ms`) added to `WearMetrics` (top-level field)
- iOS HealthKit heartbeat series (RR) integration via lightweight plugin
- Example app now displays RR intervals (first few values) in Live Data

### Changed
- Apple adapter attempts heartbeat-series fetch with extended 30-minute window
- iOS deployment target for plugin set to 13.0 to support heartbeat series

### Notes
- RR availability depends on Health permissions and recent Apple Watch heartbeat series samples
- Falls back gracefully when RR is not available


### Fixed
- Fixed data freshness validation in `Normalizer` class
- Added `_isDataFresh()` method to filter out stale data based on `maxDataAge` configuration
- Data older than the configured `maxDataAge` (default 12 hours) is now properly excluded from normalization

## [0.1.0] - 2025-10-27

### Added
- Initial release of synheart_wear package
- Apple HealthKit integration for iOS
- Support for multiple health metrics: heart rate (HR), heart rate variability (HRV), steps, calories
- Real-time data streaming capabilities
- Local encrypted caching for offline data persistence
- Unified data schema following the Synheart RFC specification
- Permission management system
- Data normalization engine for multi-device support
- Example Flutter app demonstrating SDK usage

### Features
- Cross-platform support (iOS and Android)
- Real-time HR and HRV streaming
- Consent-based data access
- AES-256-CBC encryption for local storage
- Automatic data quality validation
- Support for both RMSSD and SDNN HRV metrics

### Platform Support
- iOS: Full support via HealthKit integration
- Android: Under development

[0.1.0]: https://github.com/synheart-ai/synheart_wear/releases/tag/v0.1.0

