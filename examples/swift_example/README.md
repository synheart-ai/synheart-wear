# Synheart Wear — Swift Example (SwiftUI)

A three-tab iOS app demonstrating the Synheart Wear SDK with SwiftUI.

## Tabs

| Tab | Description |
|-----|-------------|
| **Dashboard** | SDK status cards + quick-action buttons (init, permissions, read, encryption, cache) |
| **Health Data** | Raw JSON viewer showing the latest `WearMetrics` snapshot |
| **Streaming** | Start/stop HR and HRV streams with a live metric-card grid |

## Prerequisites

- Xcode 15+
- iOS 16.0+ deployment target
- The **synheart-wear-swift** SDK repo cloned as a sibling:
  ```
  parent/
  ├── synheart-wear/              ← this repo
  │   └── examples/swift_example/
  └── synheart-wear-swift/        ← SDK source
  ```

## Setup

### Option A: XcodeGen (recommended)

```bash
brew install xcodegen   # if not installed

cd synheart-wear/examples/swift_example
xcodegen generate
open SynheartWearExample.xcodeproj
```

`project.yml` references the local SDK package at `../../../synheart-wear-swift` via SPM.

### Option B: Manual Xcode Project

1. Open Xcode and create a new **iOS App** project (SwiftUI, Swift)
2. Add a **local Swift package** dependency pointing at `../../../synheart-wear-swift`
3. Copy the `SynheartWearExample/` source folder into the project
4. Set the HealthKit capability and add the entitlements
5. Build and run

## Architecture

- **App entry** — `@main` struct with `@StateObject` ViewModel
- **ViewModel** — `ObservableObject` shared via `@EnvironmentObject` across all tabs
- **Streaming** — Combine `AnyPublisher.sink()` with `.receive(on: DispatchQueue.main)`, cancellables stored for cleanup
- **One-shot calls** — `async/await` in `Task {}` blocks
- **Layout** — `TabView` with 3 tabs, `NavigationStack` per tab

## HealthKit

The app declares `NSHealthShareUsageDescription` and `NSHealthUpdateUsageDescription` in `Info.plist` and enables the HealthKit entitlement for read access to heart rate, HRV, steps, and calories.
