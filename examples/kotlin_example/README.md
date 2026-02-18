# Synheart Wear — Kotlin Example (Jetpack Compose)

A three-tab Android app demonstrating the Synheart Wear SDK with Jetpack Compose and Material 3.

## Tabs

| Tab | Description |
|-----|-------------|
| **Dashboard** | SDK status cards + quick-action buttons (init, permissions, read, encryption, cache) |
| **Health Data** | Raw JSON viewer showing the latest `WearMetrics` snapshot |
| **Streaming** | Start/stop HR and HRV streams with a live metric-card grid |

## Prerequisites

- Android Studio Hedgehog (2023.1) or later
- JDK 17+
- Android SDK 34 (compile) / 26 (min)
- The **synheart-wear-kotlin** SDK repo cloned as a sibling:
  ```
  parent/
  ├── synheart-wear/          ← this repo
  │   └── examples/kotlin_example/
  └── synheart-wear-kotlin/   ← SDK source
  ```

## Setup

```bash
# Clone both repos side-by-side
git clone <synheart-wear-repo>
git clone <synheart-wear-kotlin-repo>

# Generate the Gradle wrapper (if not already present)
cd synheart-wear/examples/kotlin_example
gradle wrapper --gradle-version 8.6

# Build
./gradlew :app:assembleDebug
```

The `settings.gradle.kts` uses a **composite build** (`includeBuild`) so that `ai.synheart:synheart-wear:0.3.0` resolves to the local SDK project automatically — no manual publishing needed.

## Architecture

- **Single Activity** — `MainActivity` hosts a Compose `Scaffold` + `TabRow`
- **ViewModel** — `MainViewModel` (AndroidViewModel) holds a `StateFlow<UiState>` and manages all SDK calls
- **Streaming** — `Flow.collect` inside `viewModelScope.launch`, with `Job` references for cancellation
- **Theme** — Material 3 with dynamic color support (Android 12+)

## Health Connect

The app declares Health Connect read permissions in `AndroidManifest.xml` and includes a `ViewPermissionUsageActivity` alias for the permission rationale screen.
