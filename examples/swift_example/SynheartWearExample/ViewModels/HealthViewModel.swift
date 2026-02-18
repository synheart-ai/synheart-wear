import Foundation
import Combine
import SynheartWear

@MainActor
class HealthViewModel: ObservableObject {

    // MARK: - Published State

    @Published var sdkInitialized = false
    @Published var permissionsGranted = false
    @Published var encryptionEnabled = false
    @Published var isStreamingHR = false
    @Published var isStreamingHRV = false

    @Published var heartRate: Double?
    @Published var hrv: Double?
    @Published var steps: Double?
    @Published var calories: Double?
    @Published var rrIntervals: [Double]?

    @Published var metricsJson = ""
    @Published var lastUpdate = ""
    @Published var statusMessage = ""
    @Published var cacheStats = ""

    // BLE HRM state
    @Published var isScanning = false
    @Published var bleConnected = false
    @Published var bleDevices: [(id: String, name: String)] = []
    @Published var bleHeartRate: Int?
    @Published var bleDeviceName: String?
    @Published var isStreamingBleHR = false

    // Wearable provider state
    @Published var providerStatuses: [String: Bool] = [:]

    // MARK: - Private

    private let sdk: SynheartWear
    private var hrCancellable: AnyCancellable?
    private var hrvCancellable: AnyCancellable?
    private var bleStreamTask: Task<Void, Never>?

    private let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()

    // MARK: - Init

    init() {
        let config = SynheartWearConfig(
            enabledAdapters: [.appleHealthKit, .bleHrm],
            enableLocalCaching: true,
            enableEncryption: true,
            streamInterval: 3.0
        )
        self.sdk = SynheartWear(config: config)

        // Auto-init on launch (matches Flutter behavior)
        initializeSdk()
    }

    deinit {
        hrCancellable?.cancel()
        hrvCancellable?.cancel()
        bleStreamTask?.cancel()
        sdk.bleHrm?.dispose()
    }

    // MARK: - SDK Actions

    func initializeSdk() {
        Task {
            do {
                statusMessage = "Initializing..."
                try await sdk.initialize()
                sdkInitialized = true
                statusMessage = "SDK initialized"
                // Auto-check permissions and encryption after init
                checkPermissionStatus()
                await checkEncryptionFromCache()
            } catch {
                statusMessage = "Init failed: \(error.localizedDescription)"
            }
        }
    }

    private func checkPermissionStatus() {
        let status = sdk.getPermissionStatus()
        let allGranted = status.values.allSatisfy { $0 }
        permissionsGranted = allGranted
    }

    private func checkEncryptionFromCache() async {
        do {
            let stats = try await sdk.getCacheStats()
            encryptionEnabled = stats["encryption_enabled"] as? Bool ?? false
        } catch { }
    }

    func requestPermissions() {
        Task {
            do {
                let result = try await sdk.requestPermissions([
                    .heartRate, .hrv, .steps, .calories,
                ])
                let allGranted = result.values.allSatisfy { $0 }
                permissionsGranted = allGranted
                statusMessage = allGranted ? "Permissions granted" : "Some permissions denied"
            } catch {
                statusMessage = "Permission error: \(error.localizedDescription)"
            }
        }
    }

    func readHealthData() {
        Task {
            do {
                let metrics = try await sdk.readMetrics(isRealTime: false)
                heartRate = metrics.getMetric(.hr)
                // Try SDNN first, fallback to RMSSD (matches Flutter behavior)
                hrv = metrics.getMetric(.hrvSdnn) ?? metrics.getMetric(.hrvRmssd)
                steps = metrics.getMetric(.steps)
                calories = metrics.getMetric(.calories)
                rrIntervals = metrics.rrIntervals
                metricsJson = formatMetricsJson(metrics.toDict())
                lastUpdate = timeFormatter.string(from: Date())
                statusMessage = "Health data read"
            } catch {
                statusMessage = "Read error: \(error.localizedDescription)"
            }
        }
    }

    func checkEncryption() {
        Task {
            do {
                let stats = try await sdk.getCacheStats()
                let enabled = stats["encryption_enabled"] as? Bool ?? false
                encryptionEnabled = enabled
                statusMessage = "Encryption: \(enabled ? "Enabled" : "Disabled")"
            } catch {
                statusMessage = "Encryption check error: \(error.localizedDescription)"
            }
        }
    }

    func testHealthKit() {
        let status = sdk.getPermissionStatus()
        statusMessage = "HealthKit: \(status.count) permission types checked"
    }

    func loadCacheStats() {
        Task {
            do {
                let stats = try await sdk.getCacheStats()
                cacheStats = "\(stats)"
                statusMessage = "Cache stats loaded"
            } catch {
                statusMessage = "Cache error: \(error.localizedDescription)"
            }
        }
    }

    func clearCache() {
        Task {
            do {
                try await sdk.clearOldCache(maxAge: 7 * 24 * 60 * 60)
                statusMessage = "Cache cleared"
            } catch {
                statusMessage = "Clear cache error: \(error.localizedDescription)"
            }
        }
    }

    func loadCachedSessions() {
        Task {
            do {
                let thirtyDaysAgo = Date().addingTimeInterval(-30 * 24 * 60 * 60)
                let sessions = try await sdk.getCachedSessions(startDate: thirtyDaysAgo)
                statusMessage = "Cached sessions: \(sessions.count) found"
            } catch {
                statusMessage = "Cached sessions error: \(error.localizedDescription)"
            }
        }
    }

    func purgeAllData() {
        Task {
            do {
                try await sdk.purgeAllData()
                statusMessage = "All data purged (GDPR)"
            } catch {
                statusMessage = "Purge error: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Streaming

    func toggleHRStream() {
        if isStreamingHR {
            hrCancellable?.cancel()
            hrCancellable = nil
            isStreamingHR = false
            statusMessage = "HR stream stopped"
        } else {
            isStreamingHR = true
            statusMessage = "HR stream started"
            hrCancellable = sdk.streamHR(interval: 2.0)
                .receive(on: DispatchQueue.main)
                .sink(
                    receiveCompletion: { [weak self] completion in
                        if case .failure(let error) = completion {
                            self?.statusMessage = "HR stream error: \(error.localizedDescription)"
                        }
                        self?.isStreamingHR = false
                    },
                    receiveValue: { [weak self] metrics in
                        guard let self else { return }
                        if let hr = metrics.getMetric(.hr) { self.heartRate = hr }
                        if let s = metrics.getMetric(.steps) { self.steps = s }
                        if let c = metrics.getMetric(.calories) { self.calories = c }
                        if let rr = metrics.rrIntervals { self.rrIntervals = rr }
                        self.lastUpdate = self.timeFormatter.string(from: Date())
                    }
                )
        }
    }

    func toggleHRVStream() {
        if isStreamingHRV {
            hrvCancellable?.cancel()
            hrvCancellable = nil
            isStreamingHRV = false
            statusMessage = "HRV stream stopped"
        } else {
            isStreamingHRV = true
            statusMessage = "HRV stream started"
            hrvCancellable = sdk.streamHRV(window: 5.0)
                .receive(on: DispatchQueue.main)
                .sink(
                    receiveCompletion: { [weak self] completion in
                        if case .failure(let error) = completion {
                            self?.statusMessage = "HRV stream error: \(error.localizedDescription)"
                        }
                        self?.isStreamingHRV = false
                    },
                    receiveValue: { [weak self] metrics in
                        guard let self else { return }
                        if let h = metrics.getMetric(.hrvSdnn) ?? metrics.getMetric(.hrvRmssd) {
                            self.hrv = h
                        }
                        if let rr = metrics.rrIntervals { self.rrIntervals = rr }
                        self.lastUpdate = self.timeFormatter.string(from: Date())
                    }
                )
        }
    }

    func stopAllStreams() {
        hrCancellable?.cancel()
        hrCancellable = nil
        hrvCancellable?.cancel()
        hrvCancellable = nil
        isStreamingHR = false
        isStreamingHRV = false
        statusMessage = "All streams stopped"
    }

    // MARK: - BLE HRM

    func scanBleDevices() {
        Task {
            do {
                isScanning = true
                statusMessage = "Scanning for BLE HR monitors..."
                let devices = try await sdk.bleHrm?.scan(timeoutMs: 10000) ?? []
                bleDevices = devices.map { (id: $0.deviceId, name: $0.name ?? "Unknown") }
                isScanning = false
                statusMessage = "\(devices.count) BLE device(s) found"
            } catch {
                isScanning = false
                statusMessage = "BLE scan error: \(error.localizedDescription)"
            }
        }
    }

    func connectBleDevice(deviceId: String) {
        Task {
            do {
                statusMessage = "Connecting to BLE device..."
                try await sdk.bleHrm?.connect(deviceId: deviceId)
                let connected = sdk.bleHrm?.isConnected() ?? false
                bleConnected = connected
                bleDeviceName = bleDevices.first(where: { $0.id == deviceId })?.name
                statusMessage = connected ? "BLE device connected" : "BLE connection failed"
            } catch {
                statusMessage = "BLE connect error: \(error.localizedDescription)"
            }
        }
    }

    func disconnectBleDevice() {
        Task {
            do {
                bleStreamTask?.cancel()
                bleStreamTask = nil
                try await sdk.bleHrm?.disconnect()
                bleConnected = false
                bleDeviceName = nil
                bleHeartRate = nil
                isStreamingBleHR = false
                statusMessage = "BLE device disconnected"
            } catch {
                statusMessage = "BLE disconnect error: \(error.localizedDescription)"
            }
        }
    }

    func toggleBleHRStream() {
        if isStreamingBleHR {
            bleStreamTask?.cancel()
            bleStreamTask = nil
            isStreamingBleHR = false
            statusMessage = "BLE HR stream stopped"
        } else {
            isStreamingBleHR = true
            statusMessage = "BLE HR stream started"
            bleStreamTask = Task {
                guard let stream = sdk.bleHrm?.onHeartRate else { return }
                for await sample in stream {
                    if Task.isCancelled { break }
                    bleHeartRate = sample.bpm
                    lastUpdate = timeFormatter.string(from: Date())
                }
                isStreamingBleHR = false
            }
        }
    }

    // MARK: - Wearable Providers

    func connectProvider(_ adapter: DeviceAdapter) {
        Task {
            do {
                statusMessage = "Connecting \(adapter)..."
                let provider = try sdk.getProvider(adapter)
                try await provider.connect()
                statusMessage = "\(adapter): OAuth URL received — open in browser to authorize."
            } catch {
                statusMessage = "\(adapter) connect error: \(error.localizedDescription)"
            }
        }
    }

    func disconnectProvider(_ adapter: DeviceAdapter) {
        Task {
            do {
                let provider = try sdk.getProvider(adapter)
                try await provider.disconnect()
                providerStatuses.removeValue(forKey: "\(adapter)")
                statusMessage = "\(adapter) disconnected"
            } catch {
                statusMessage = "\(adapter) disconnect error: \(error.localizedDescription)"
            }
        }
    }

    func checkProviderStatus(_ adapter: DeviceAdapter) {
        Task {
            do {
                let provider = try sdk.getProvider(adapter)
                let connected = provider.isConnected()
                providerStatuses["\(adapter)"] = connected
                statusMessage = "\(adapter): \(connected ? "Connected" : "Not connected")"
            } catch {
                statusMessage = "\(adapter) status error: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Helpers

    private func formatMetricsJson(_ dict: [String: Any]) -> String {
        guard let data = try? JSONSerialization.data(
            withJSONObject: dict,
            options: [.prettyPrinted, .sortedKeys]
        ) else { return "{}" }
        return String(data: data, encoding: .utf8) ?? "{}"
    }
}
