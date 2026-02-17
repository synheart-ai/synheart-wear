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

**Tier 0 — BLE Heart Rate Monitors (Direct Connection)**

Any standard Bluetooth LE heart rate device. No cloud API needed — connects directly over BLE.

| **Device** | **OS** | **SDK / API** | **Signals** | **Status** |
| --- | --- | --- | --- | --- |
| WHOOP (Broadcast HR) | iOS / Android | CoreBluetooth / Android BLE | HR | ✅ Implemented |
| Polar H10 / OH1 | iOS / Android | CoreBluetooth / Android BLE | HR, RR intervals | ✅ Implemented |
| Wahoo TICKR | iOS / Android | CoreBluetooth / Android BLE | HR, RR intervals | ✅ Implemented |
| Garmin HRM-Pro / Dual | iOS / Android | CoreBluetooth / Android BLE | HR, RR intervals | ✅ Implemented |
| Any BLE HR strap | iOS / Android | Standard BLE HR Profile (0x180D) | HR, RR intervals (if supported) | ✅ Implemented |

See [RFC-BLE-HRM](RFC-BLE-HRM.md) for full specification.

---

**Tier 1 — Core Supported Smart Watches**

Best data quality and reliable APIs. Ideal for focus, HRV, and emotion inference.

| **Device** | **OS** | **SDK / API** | **Signals** | **Status** |
| --- | --- | --- | --- | --- |
| Apple Watch | iOS | Apple HealthKit / WatchKit | HR, HRV, ACC, SpO₂, RR, Temperature | ✅ Native integration |
| Samsung Galaxy Watch | Android | Samsung Health Sensor SDK | HR, ACC, SpO₂, RR, Temperature , EDA, GYRO | 📋 Planned |
| Pixel Watch | Android | Wear OS SDK | HR, HRV, ACC, EDA, GYRO | 🧩 In progress |
| Polar H10 / Ignite / Unite | iOS / Android | Polar SDK | HR, HRV, ACC, SpO₂, Temperature, GYRO | 🧩 In progress |
| Garmin Watches (Cloud) | iOS / Android | Garmin Health API (OAuth) | HR, HRV, Sleep, Stress, SpO₂, Body Composition | ✅ Cloud API |
| Garmin Watches (Native RTS) | iOS / Android | Garmin Health SDK | HR, HRV, ACC, SpO₂, RR, Temperature, GYRO | ✅ On demand (licensed) |
| Fitbit Sense / Versa / Charge | iOS / Android | Fitbit Web API | HR, HRV, ACC, RR, Temperature , GYRO | 🧩 Planned |

> **Garmin Health SDK (RTS):** The Garmin Health SDK Real-Time Streaming (RTS) capability requires a separate license from Garmin. The Synheart Wear SDK supports Garmin RTS through the `GarminHealth` facade, which is available on demand for licensed integrations. The underlying Garmin Health SDK code is proprietary to Garmin and is not distributed as open source. For cloud-based Garmin data (OAuth + webhooks), use the `GarminProvider` which is included in the open-source SDK.

---

**Tier 2 — Extended Health Wearables**

Best data quality and reliable APIs. Ideal for health and fitness biomarkers.

| **Device** | **OS** | **SDK** | **Signals** | **Notes** |
| --- | --- | --- | --- | --- |
| Empatica E4 / E5 | iOS / Android | Empatica Research SDK | HR, HRV, RR, ACC, EDA, Temperature, GYRO | High-fidelity biosignals |
| Biostrap EVO | iOS / Android | Biostrap Labs API | HR, HRV, SpO₂, RR, ACC, Temperature | Premium recovery data |
| Oura Ring Gen 3 | iOS / Android | Oura Cloud API | HR, ACC, SpO₂, EDA, Temperature | Great for passive daily signals |
| WHOOP Strap 4.0 | iOS / Android | WHOOP Developer API | HR, HRV, ACC, Temperature , EDA, GYRO | Provides continuous health and fitness data |

---

**Tier 3 — Community & Affordable Smart Watches / Bands**

Accessible devices for large-scale.

| **Device** | **OS** | **Access** | **Signals** | **Notes** |
| --- | --- | --- | --- | --- |
| Huawei Band / Watch Fit | Android / iOS | Google Fit / Huawei Health Bridge | HR, HRV, ACC, SpO₂, RR, Temperature, GYRO | Affordable & common |
| Withings | Android / iOS | Withings Public API | HR, ACC, Temperature, GYRO | Inclusive product line |
| Amazfit / Zepp OS | Android / iOS | Zepp OS API | HR, HRV, ACC, SpO₂, GYRO | Good HR accuracy; open SDK |
| Oppo Bands | Android | Health Connect API | HR, HRV, SpO₂,, ACC | Expanding Android base |
| Xiaomi Mi / Redmi / Realme Band | Android / iOS | Google Fit Bridge / BLE | HR, ACC | Popular low-cost wearables |
| Infinix / Tecno Watch Series | Android | Health Connect API | - | Accessible in emerging markets |

---

**Tier 4 — Brain-computer interface devices for Research**

Used in labs, affective computing, or advanced research setups.

| **Device** | **OS** | **SDK** | **Signals** | **Notes** |
| --- | --- | --- | --- | --- |
| Muse S (EEG) | iOS / Android | Muse SDK | HR, HRV, ACC, SpO₂ | For focus & cognitive experiments |
| OpenBCI Cyton / Galea | Cross-platform | OpenBCI API | HR, HRV, ACC, EDA GYRO | Open-source neural signals |

---

### Tier 5 — Experimental / DIY Devices

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



