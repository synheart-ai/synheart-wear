# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-12-01

### Added

- Initial specification release for Synheart Wear
- Unified wearable data schema for cross-device HR/HRV collection
- Connector interface specification for pluggable device adapters
- BLE HRM connector specification (RFC-BLE-HRM)
- Supported devices: Apple Watch, Garmin, Polar H10/Verity, generic BLE HRM
- Core metric keys: hr, hrv_rmssd, hrv_sdnn, steps, calories, distance, stress, recovery_score
- Cross-platform SDK specification (Dart, Kotlin, Swift)
- CLI tool specification (synheart-wear-cli)
- Garmin companion app specification
- Documentation: RFC, BLE HRM RFC, Data Flow, Connector Interface, SDK Usage
- Cross-platform examples (Flutter, Kotlin, Swift)
- CONTRIBUTING.md

### Platform Releases

| Platform | Version | Changelog |
|---|---|---|
| Dart | 0.2.1 | [CHANGELOG](https://github.com/synheart-ai/synheart-wear-dart/blob/main/CHANGELOG.md) |
| Kotlin | 0.1.0 | [CHANGELOG](https://github.com/synheart-ai/synheart-wear-kotlin/blob/main/CHANGELOG.md) |
| Swift | 0.1.0 | [CHANGELOG](https://github.com/synheart-ai/synheart-wear-swift/blob/main/CHANGELOG.md) |
