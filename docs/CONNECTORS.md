# 🌐 Synheart Connectors Program

> _An open initiative to build the world's most transparent and inclusive wellness data ecosystem._

---

## 🧠 Overview

The **Synheart Connectors Program** invites developers, researchers, and creators to extend the **Synheart Wear SDK** by integrating new **wearables**, **biosignal sensors**, or **behavioral data sources**.

Our mission is to make wellness and affective-computing data open, auditable, and accessible — empowering innovation while preserving trust and privacy.

---

## 💡 Why Join

- 🧩 **Contribute** to cutting-edge emotion-AI and wellness research
- 💚 **Earn rewards** and public recognition for verified integrations
- 🌍 **Expand access** by helping Synheart support more devices
- 🔓 **Keep data open** and verifiable across ecosystems

---

## ⚙️ How It Works

### 1. Fork the Repository

Fork the [synheart-wear repository](https://github.com/synheart-ai/synheart-wear) on GitHub.

### 2. Create Your Adapter Class

Create a new file in `packages/synheart_wear/lib/src/adapters/` named `<device_name>_adapter.dart`:

```dart
import '../core/consent_manager.dart';
import '../core/models.dart';
import 'wear_adapter.dart';

class YourDeviceAdapter implements WearAdapter {
  @override
  String get id => 'your_device';

  @override
  Set<PermissionType> get supportedPermissions => const {
    PermissionType.heartRate,
    PermissionType.steps,
  };

  @override
  Future<void> ensurePermissions() async {
    // Implement device authentication and permission handling
  }

  @override
  Future<WearMetrics?> readSnapshot({bool isRealTime = true}) async {
    // Read and normalize data from your device
  }
}
```

### 3. Implement Required Methods

Your adapter must implement the `WearAdapter` interface with:
- **id**: Unique device identifier
- **supportedPermissions**: Set of biometric data types supported
- **ensurePermissions()**: Handle device authentication
- **readSnapshot()**: Read and normalize device data

### 4. Add Tests

Create a test file `packages/synheart_wear/test/adapters/<device_name>_adapter_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:synheart_wear/src/adapters/your_device_adapter.dart';

void main() {
  group('YourDeviceAdapter', () {
    late YourDeviceAdapter adapter;

    setUp(() {
      adapter = YourDeviceAdapter();
    });

    test('id returns correct identifier', () {
      expect(adapter.id, equals('your_device'));
    });

    test('readSnapshot returns WearMetrics', () async {
      final metrics = await adapter.readSnapshot();
      expect(metrics, isA<WearMetrics>());
    });
  });
}
```

### 5. Submit a Pull Request

- Push your changes to your fork
- Open a pull request with a clear description
- Automated checks will validate your implementation
- Community reviewers will test and approve verified connectors

### 6. Celebrate! 🎉

Once merged, your connector appears in the supported devices list and earns community recognition.

---

## 🪙 Incentives

| Contribution Type | Example | Reward |
|-------------------|---------|--------|
| New Connector | Garmin, Polar, Muse S, etc. | $100 Cash reward + Public credit |
| Data Validation | Signal-quality benchmarking | Access to internal datasets |
| Maintenance | Bug fixes, upgrades | Badge + Leaderboard points |
| Open Dataset | Anonymized HR/HRV data upload | Contributor recognition |

Learn more about submission workflow and eligibility in our [Contributing Guidelines](../CONTRIBUTING.md).

---

## 🩺 Supported Devices

### Tier 1 — Core Supported Devices 

Best data quality and reliable APIs. Ideal for focus, HRV, and emotion inference.

| Device | OS | SDK / API | Signals | Status |
|--------|-----------|--------------------------|----------------------------|-----------------|
| Apple Watch | iOS | Apple HealthKit / WatchKit | HR, HRV (SDNN), Motion, SpO₂ | ✅ Native integration |
| Garmin Watches | iOS / Android | Garmin Health SDK | HR, HRV, Stress, Respiration | 🧩 In progress |
| Polar H10 / Ignite / Unite | iOS / Android | Polar SDK | RR intervals, HR, HRV, Motion | ✅ Preferred research-grade HRV |
| Fitbit Sense / Versa / Charge | iOS / Android | Fitbit Web API | HR, HRV (proxy), Sleep | 🧩 Planned |
| WHOOP Strap 4.0 | iOS / Android | WHOOP Developer API | HRV, Recovery, Sleep | 🧩 Planned |

---

### Tier 2 — Research & Extended Devices

Used in labs, affective computing, or advanced research setups.

| Device | OS | SDK | Signals | Notes |
|--------|-----------|-------------------|-------------------|-----------------------------------|
| Empatica E4 / E5 | iOS / Android | Empatica Research SDK | HRV, EDA, Temp, Motion | High-fidelity biosignals |
| Muse S (EEG) | iOS / Android | Muse SDK | EEG, Attention, Meditation | For focus & cognitive experiments |
| OpenBCI Cyton / Galea | Cross-platform | OpenBCI API | EEG, EMG, HRV, EDA | Open-source neural signals |
| Biostrap EVO | iOS / Android | Biostrap Labs API | HRV, Sleep, Respiration | Premium recovery data |
| Oura Ring Gen 3 | iOS / Android | Oura Cloud API | HRV, Temp, Sleep | Great for passive daily signals |

---

### Tier 3 — Community & Affordable Devices

Accessible devices for large-scale or regional deployments (e.g., Africa).

| Device | OS | Access | Signals | Notes |
|--------|-----------|----------------------------|-------------------------|-----------------------------------|
| Huawei Band / Watch Fit | Android / iOS | Google Fit / Huawei Health Bridge | HR, HRV (limited) | Affordable & common |
| Xiaomi Mi Band / Redmi Band | Android / iOS | Google Fit Bridge / BLE | HR, Steps, Sleep | Popular low-cost wearables |
| Infinix / Tecno Watch Series | Android | Health Connect API | HR, Steps, Motion | Accessible in emerging markets |
| Realme / Oppo Bands | Android | Health Connect API | HR, Sleep | Expanding Android base |
| Amazfit / Zepp OS | Android / iOS | Zepp OS API | HR, HRV, SpO₂ | Good HR accuracy; open SDK |

---

### Tier 4 — Experimental / DIY Devices

For the community or research prototypes.

| Device | Type | SDK / Access | Notes |
|--------|-------------|--------------|--------------------------------------|
| Shimmer3 / Bitalino | Research kits | BLE + Open SDK | Academic-grade HR/EDA data |
| OpenHR / Arduino-based Sensors | DIY | BLE | For education, prototyping, open wellness experiments |
| Raspberry Pi + HR sensor module | DIY | Python SDK | For on-device inference demos |
| Custom Synheart Wear Node | Native | Internal | Potential future open hardware project |

---



---


## 🧾 Verification & Trust

To maintain data integrity, all connectors must satisfy the **Synheart Signal Integrity Standard (SIS)**:

- ✅ Include attestation or provenance metadata (e.g., Apple Health, Garmin Auth)
- ✅ Pass automated validation for timestamp continuity and HRV stability
- ✅ Publish clear documentation on sampling frequency, resolution, and known limits
- 🏅 **Verified connectors earn the "Trusted by Synheart" badge**

---

## 🪴 Community Governance

- Managed transparently via GitHub Discussions
- Monthly "Connector Round" to showcase top contributors
- Contributors may be invited to join the Synheart Research Collective

---

## 💬 Join Us

If you believe wellness tech should be open, ethical, and human-centered, you belong here.

🌱 **Become a Synheart Connector today.**

- [Join on GitHub](https://github.com/synheart-ai/synheart-wear)
- [Read Contributing Guidelines](../CONTRIBUTING.md)
- [Visit synheart.ai/connectors](https://synheart.ai/connectors)

---

## 📚 Resources

- **Contributing Guide**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **API Documentation**: [README.md](../README.md)
- **Data Schema**: [schema/metrics.schema.json](../schema/metrics.schema.json)
- **RFC**: [docs/RFC.md](RFC.md)

---

## 📄 License

By contributing to Synheart Connectors, you agree that your contributions will be licensed under the MIT License.

---

© 2025 Synheart AI. Built with ❤️ science, and community. 

*Technology with a heartbeat.*



