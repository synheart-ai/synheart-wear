import Flutter
import UIKit
import HealthKit
import os.log
import WatchConnectivity

/// SynheartWear Flutter Plugin for iOS HealthKit integration
/// Provides real-time and historical health data access with proper error handling and logging
public class SynheartWearPlugin: NSObject, FlutterPlugin {
    
    // MARK: - Constants
    
    /// Configuration constants for the plugin
    private struct Config {
        static let heartRateStreamLookbackMinutes: TimeInterval = 5 * 60 // 5 minutes
        static let hrvStreamLookbackMinutes: TimeInterval = 10 * 60 // 10 minutes
        static let defaultBatteryLevel: Double = 0.85
        static let defaultFirmwareVersion = "10.1"
        static let deviceIdPrefix = "applewatch"
    }
    
    /// Logging subsystem for the plugin
    static let logger = OSLog(subsystem: "com.synheart.wear", category: "SynheartWearPlugin")
    
    /// Shared plugin instance to ensure stream handlers remain active
    private static var sharedInstance: SynheartWearPlugin?
    
    // MARK: - Properties
    
    private var healthStore = HKHealthStore()
    private var heartRateStreamHandler: SynheartWearStreamHandler?
    private var hrvStreamHandler: SynheartWearStreamHandler?

    var heartRateEventSink: FlutterEventSink?
    var hrvEventSink: FlutterEventSink?
    
    /// Active queries for cleanup
    private var heartRateQuery: HKAnchoredObjectQuery?
    private var hrvQuery: HKAnchoredObjectQuery?
    
    /// Streaming timers for polling-based streaming
    private var heartRateTimer: Timer?
    private var hrvTimer: Timer?
    
    /// Real-time workout session properties (iOS 10.0+)
    @available(iOS 10.0, *)
    private var workoutSession: HKWorkoutSession?
    
    @available(iOS 10.0, *)
    private var workoutBuilder: HKLiveWorkoutBuilder?
    
    private var isWorkoutActive = false
    
    /// Streaming configuration
    private let streamingInterval: TimeInterval = 2.0 // Poll every 2 seconds
    private let useRealTimeWorkout = true // Enable real-time workout data
    
    /// Supported HealthKit data types
    private let supportedTypes: Set<HKObjectType> = [
        HKObjectType.quantityType(forIdentifier: .heartRate)!,
        HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
        HKObjectType.quantityType(forIdentifier: .stepCount)!,
        HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!,
        HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!
    ]
    
    /// Data collection state for real-time metrics
    private var lastHeartRate: Double?
    private var lastHRVSDNN: Double?
    private var lastHRVRMSSD: Double?
    private var lastSteps: Double?
    private var lastCalories: Double?
    private var lastStress: Double?

    /// Registers the plugin with Flutter
    /// - Parameter registrar: Flutter plugin registrar
    public static func register(with registrar: FlutterPluginRegistrar) {
        os_log("Registering SynheartWearPlugin", log: logger, type: .info)
        
        // Create and store the shared instance
        let instance = SynheartWearPlugin()
        sharedInstance = instance
        
        let channel = FlutterMethodChannel(name: "synheart_wear", binaryMessenger: registrar.messenger())
        registrar.addMethodCallDelegate(instance, channel: channel)
        
        // Event channels for streaming
        let heartRateEventChannel = FlutterEventChannel(name: "synheart_wear/heart_rate", binaryMessenger: registrar.messenger())
        let hrvEventChannel = FlutterEventChannel(name: "synheart_wear/hrv", binaryMessenger: registrar.messenger())
        
        // Create stream handlers and store references
        instance.heartRateStreamHandler = SynheartWearStreamHandler(plugin: instance, streamType: .heartRate)
        instance.hrvStreamHandler = SynheartWearStreamHandler(plugin: instance, streamType: .hrv)
        
        heartRateEventChannel.setStreamHandler(instance.heartRateStreamHandler)
        hrvEventChannel.setStreamHandler(instance.hrvStreamHandler)
        
        os_log("SynheartWearPlugin registered successfully", log: logger, type: .info)
    }

    /// Handles method calls from Flutter
    /// - Parameters:
    ///   - call: The method call from Flutter
    ///   - result: The result callback
    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        os_log("Handling method call: %{public}@", log: Self.logger, type: .debug, call.method)
        
        // Use the shared instance for method calls
        guard let instance = Self.sharedInstance else {
            os_log("No shared instance available", log: Self.logger, type: .error)
            result(FlutterError(code: "NO_INSTANCE", message: "Plugin instance not available", details: nil))
            return
        }
        
        switch call.method {
        case "initialize":
            instance.initialize(result: result)
        case "requestPermissions":
            instance.requestPermissions(call: call, result: result)
        case "readMetrics":
            instance.readMetrics(result: result)
        case "dispose":
            instance.dispose(result: result)
        default:
            os_log("Unknown method called: %{public}@", log: Self.logger, type: .error, call.method)
            result(FlutterMethodNotImplemented)
        }
    }
    
    // MARK: - Core Methods
    
    /// Initializes the HealthKit integration
    /// - Parameter result: Flutter result callback
    private func initialize(result: @escaping FlutterResult) {
        os_log("Initializing HealthKit integration", log: Self.logger, type: .info)
        
        guard HKHealthStore.isHealthDataAvailable() else {
            os_log("Health data is not available on this device", log: Self.logger, type: .error)
            result(FlutterError(
                code: "HEALTH_DATA_UNAVAILABLE",
                message: "Health data is not available on this device",
                details: nil
            ))
            return
        }
        
        // Initialize data collection state
        initializeDataState()
        
        os_log("HealthKit initialization successful", log: Self.logger, type: .info)
        result(true)
    }
    
    /// Initializes the data collection state with current values
    private func initializeDataState() {
        os_log("Initializing data collection state", log: Self.logger, type: .debug)
        
        // Initialize stress with a random value (placeholder)
        lastStress = Double.random(in: 0.1...0.9)
        
        // Load current values for steps and calories
        readDailyStatistics(for: .stepCount, unit: HKUnit.count(), key: "steps") { [weak self] value in
            self?.lastSteps = value
        }
        
        readDailyStatistics(for: .activeEnergyBurned, unit: HKUnit.kilocalorie(), key: "calories") { [weak self] value in
            self?.lastCalories = value
        }
    }
    
    /// Requests HealthKit permissions for specified data types
    /// - Parameters:
    ///   - call: Flutter method call containing permissions array
    ///   - result: Flutter result callback
    private func requestPermissions(call: FlutterMethodCall, result: @escaping FlutterResult) {
        os_log("Requesting HealthKit permissions", log: Self.logger, type: .info)
        
        guard let args = call.arguments as? [String: Any],
              let permissions = args["permissions"] as? [String] else {
            os_log("Invalid arguments for requestPermissions", log: Self.logger, type: .error)
            result(FlutterError(
                code: "INVALID_ARGUMENTS",
                message: "Invalid arguments for requestPermissions",
                details: nil
            ))
            return
        }
        
        let typesToRead = getHealthKitTypes(from: permissions)
        os_log("Requesting permissions for %d data types", log: Self.logger, type: .debug, typesToRead.count)
        
        healthStore.requestAuthorization(toShare: nil, read: typesToRead) { [weak self] success, error in
            DispatchQueue.main.async {
                if let error = error {
                    os_log("Permission request failed: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
                    result(FlutterError(
                        code: "AUTHORIZATION_ERROR",
                        message: error.localizedDescription,
                        details: nil
                    ))
                } else {
                    os_log("Permission request completed with success: %{public}@", log: Self.logger, type: .info, String(success))
                    result([
                        "success": success,
                        "permissions": self?.getPermissionStatus(for: permissions) ?? [:]
                    ])
                }
            }
        }
    }
    
    /// Reads all available health metrics according to the data schema
    /// - Parameter result: Flutter result callback
    private func readMetrics(result: @escaping FlutterResult) {
        os_log("Reading health metrics", log: Self.logger, type: .info)
        
        let group = DispatchGroup()
        var metrics: [String: Any] = [:]
        
        // Read heart rate
        group.enter()
        readLatestSample(for: .heartRate, unit: HKUnit(from: "count/min"), key: "hr") { value in
            if let value = value {
                metrics["hr"] = Int(value) // Convert to integer as per schema
                self.lastHeartRate = value
            }
            group.leave()
        }
        
        // Read HRV SDNN
        group.enter()
        readLatestSample(for: .heartRateVariabilitySDNN, unit: HKUnit.secondUnit(with: .milli), key: "hrv_sdnn") { value in
            if let value = value {
                metrics["hrv_sdnn"] = Int(value) // Convert to integer as per schema
                self.lastHRVSDNN = value
            }
            group.leave()
        }
        
        // Read HRV RMSSD (calculate from SDNN if available)
        group.enter()
        readLatestSample(for: .heartRateVariabilitySDNN, unit: HKUnit.secondUnit(with: .milli), key: "hrv_rmssd") { value in
            if let value = value {
                // RMSSD is typically 0.8-1.2 times SDNN, using 1.0 as approximation
                let rmssd = Int(value * 1.0)
                metrics["hrv_rmssd"] = rmssd
                self.lastHRVRMSSD = value
            }
            group.leave()
        }
        
        // Read steps (daily total)
        group.enter()
        readDailyStatistics(for: .stepCount, unit: HKUnit.count(), key: "steps") { value in
            if let value = value {
                metrics["steps"] = Int(value) // Convert to integer as per schema
                self.lastSteps = value
            }
            group.leave()
        }
        
        // Read calories (daily total)
        group.enter()
        readDailyStatistics(for: .activeEnergyBurned, unit: HKUnit.kilocalorie(), key: "calories") { value in
            if let value = value {
                metrics["calories"] = Double(round(value * 10) / 10) // Round to 1 decimal place
                self.lastCalories = value
            }
            group.leave()
        }
        
        // Read stress (placeholder - not directly available in HealthKit)
        group.enter()
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.1) {
            // Stress is not directly available in HealthKit, using placeholder
            let stress = Double.random(in: 0.1...0.9) // Placeholder stress value
            metrics["stress"] = Double(round(stress * 10) / 10) // Round to 1 decimal place
            self.lastStress = stress
            group.leave()
        }
        
        group.notify(queue: .main) { [weak self] in
            let response: [String: Any] = [
                "timestamp": ISO8601DateFormatter().string(from: Date()),
                "device_id": "\(Config.deviceIdPrefix)_\(Int(Date().timeIntervalSince1970))",
                "source": "apple_healthkit",
                "metrics": metrics,
                "meta": [
                    "battery": Config.defaultBatteryLevel,
                    "firmware_version": Config.defaultFirmwareVersion,
                    "synced": true
                ]
            ]
            
            os_log("Successfully read %d metrics", log: Self.logger, type: .info, metrics.count)
            result(response)
        }
    }
    
    /// Disposes of resources and stops active queries
    /// - Parameter result: Flutter result callback
    private func dispose(result: @escaping FlutterResult) {
        os_log("Disposing plugin resources", log: Self.logger, type: .info)
        
        // Stop real-time workout session
        if isWorkoutActive {
            if #available(iOS 10.0, *) {
                stopRealTimeWorkout()
            }
        }
        
        // Stop all active timers
        heartRateTimer?.invalidate()
        heartRateTimer = nil
        os_log("Stopped heart rate timer", log: Self.logger, type: .debug)
        
        hrvTimer?.invalidate()
        hrvTimer = nil
        os_log("Stopped HRV timer", log: Self.logger, type: .debug)
        
        // Stop all active queries (legacy support)
        if let hrQuery = heartRateQuery {
            healthStore.stop(hrQuery)
            self.heartRateQuery = nil
            os_log("Stopped heart rate query", log: Self.logger, type: .debug)
        }
        
        if let hrvQuery = hrvQuery {
            healthStore.stop(hrvQuery)
            self.hrvQuery = nil
            os_log("Stopped HRV query", log: Self.logger, type: .debug)
        }
        
        // Clear event sinks
        heartRateEventSink = nil
        hrvEventSink = nil
        
        // Clear shared instance if this is the current instance
        if Self.sharedInstance === self {
            Self.sharedInstance = nil
            os_log("Cleared shared instance", log: Self.logger, type: .debug)
        }
        
        os_log("Plugin disposal completed", log: Self.logger, type: .info)
        result(nil)
    }
    
    // MARK: - Generic Data Reading Methods
    
    /// Reads the latest sample for a specific HealthKit quantity type
    /// - Parameters:
    ///   - identifier: HealthKit quantity type identifier
    ///   - unit: Unit for the quantity
    ///   - key: Key for logging purposes
    ///   - completion: Completion handler with the value
    private func readLatestSample(for identifier: HKQuantityTypeIdentifier, unit: HKUnit, key: String, completion: @escaping (Double?) -> Void) {
        guard let quantityType = HKObjectType.quantityType(forIdentifier: identifier) else {
            os_log("Failed to get quantity type for %{public}@", log: Self.logger, type: .error, key)
            completion(nil)
            return
        }
        
        let sortDescriptor = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
        let query = HKSampleQuery(
            sampleType: quantityType,
            predicate: nil,
            limit: 1,
            sortDescriptors: [sortDescriptor]
        ) { _, samples, error in
            if let error = error {
                os_log("Error reading %{public}@: %{public}@", log: Self.logger, type: .error, key, error.localizedDescription)
                completion(nil)
                return
            }
            
            guard let samples = samples as? [HKQuantitySample],
                  let sample = samples.first else {
                os_log("No samples found for %{public}@", log: Self.logger, type: .debug, key)
                completion(nil)
                return
            }
            
            let value = sample.quantity.doubleValue(for: unit)
            os_log("Read %{public}@: %f", log: Self.logger, type: .debug, key, value)
            completion(value)
        }
        
        healthStore.execute(query)
    }
    
    /// Reads daily statistics for a specific HealthKit quantity type
    /// - Parameters:
    ///   - identifier: HealthKit quantity type identifier
    ///   - unit: Unit for the quantity
    ///   - key: Key for logging purposes
    ///   - completion: Completion handler with the value
    private func readDailyStatistics(for identifier: HKQuantityTypeIdentifier, unit: HKUnit, key: String, completion: @escaping (Double?) -> Void) {
        guard let quantityType = HKObjectType.quantityType(forIdentifier: identifier) else {
            os_log("Failed to get quantity type for %{public}@", log: Self.logger, type: .error, key)
            completion(nil)
            return
        }
        
        let calendar = Calendar.current
        let now = Date()
        let startOfDay = calendar.startOfDay(for: now)
        
        let predicate = HKQuery.predicateForSamples(
            withStart: startOfDay,
            end: now,
            options: .strictStartDate
        )
        
        let query = HKStatisticsQuery(
            quantityType: quantityType,
            quantitySamplePredicate: predicate,
            options: .cumulativeSum
        ) { _, statistics, error in
            if let error = error {
                os_log("Error reading daily %{public}@: %{public}@", log: Self.logger, type: .error, key, error.localizedDescription)
                completion(nil)
                return
            }
            
            guard let statistics = statistics,
                  let sum = statistics.sumQuantity() else {
                os_log("No daily statistics found for %{public}@", log: Self.logger, type: .debug, key)
                completion(nil)
                return
            }
            
            let value = sum.doubleValue(for: unit)
            os_log("Read daily %{public}@: %f", log: Self.logger, type: .debug, key, value)
            completion(value)
        }
        
        healthStore.execute(query)
    }
    
    
    // MARK: - Streaming Methods
    
    /// Starts streaming heart rate data from HealthKit
    func startHeartRateStream() {
        guard HKObjectType.quantityType(forIdentifier: .heartRate) != nil else {
            os_log("Heart rate type not available", log: Self.logger, type: .error)
            return
        }
        
        // Stop existing timer
        heartRateTimer?.invalidate()
        heartRateTimer = nil
        
        if useRealTimeWorkout && !isWorkoutActive {
            if #available(iOS 10.0, *) {
                os_log("Starting real-time workout session for heart rate streaming", log: Self.logger, type: .info)
                startRealTimeWorkout()
            } else {
                os_log("Real-time workout not available on this iOS version, using polling", log: Self.logger, type: .info)
                startPollingFallback()
            }
        } else {
            os_log("Starting heart rate stream with polling every %.1f seconds", log: Self.logger, type: .info, streamingInterval)
            startPollingFallback()
        }
        
        os_log("Heart rate stream started successfully", log: Self.logger, type: .info)
    }
    
    /// Polls for the latest heart rate data
    private func pollHeartRateData() {
        readLatestSample(for: .heartRate, unit: HKUnit(from: "count/min"), key: "hr") { [weak self] value in
            guard let self = self, let heartRate = value else {
                return
            }
            
            self.lastHeartRate = heartRate
            
            // Create streaming data format according to schema
            let timestamp = ISO8601DateFormatter().string(from: Date())
            let data: [String: Any] = [
                "timestamp": timestamp,
                "device_id": "\(Config.deviceIdPrefix)_\(Int(Date().timeIntervalSince1970))",
                "source": "apple_healthkit",
                "metrics": [
                    "hr": Int(heartRate),
                    "hrv_rmssd": self.lastHRVRMSSD.map { Int($0) },
                    "hrv_sdnn": self.lastHRVSDNN.map { Int($0) },
                    "steps": self.lastSteps.map { Int($0) },
                    "calories": self.lastCalories.map { Double(round($0 * 10) / 10) },
                    "stress": self.lastStress.map { Double(round($0 * 10) / 10) }
                ].compactMapValues { $0 },
                "meta": [
                    "battery": Config.defaultBatteryLevel,
                    "firmware_version": Config.defaultFirmwareVersion,
                    "synced": true
                ]
            ]
            
            os_log("Streaming HR data: %d BPM", log: Self.logger, type: .debug, Int(heartRate))
            
            // Send to Flutter
            DispatchQueue.main.async {
                self.heartRateEventSink?(data)
            }
        }
    }

    /// Starts streaming HRV data from HealthKit using polling
    func startHRVStream() {
        guard HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) != nil else {
            os_log("HRV type not available", log: Self.logger, type: .error)
            return
        }
        
        // Stop existing timer
        hrvTimer?.invalidate()
        hrvTimer = nil
        
        os_log("Starting HRV stream with polling every %.1f seconds", log: Self.logger, type: .info, streamingInterval)
        
        // Start polling for HRV data
        hrvTimer = Timer.scheduledTimer(withTimeInterval: streamingInterval, repeats: true) { [weak self] _ in
            self?.pollHRVData()
        }
        
        // Poll immediately for initial data
        pollHRVData()
        
        os_log("HRV stream started successfully", log: Self.logger, type: .info)
    }
    
    /// Polls for the latest HRV data
    private func pollHRVData() {
        readLatestSample(for: .heartRateVariabilitySDNN, unit: HKUnit.secondUnit(with: .milli), key: "hrv_sdnn") { [weak self] value in
            guard let self = self, let hrvValue = value else {
                return
            }
            
            self.lastHRVSDNN = hrvValue
            self.lastHRVRMSSD = hrvValue * 1.0 // Approximate RMSSD from SDNN
            
            // Create streaming data format according to schema
            let timestamp = ISO8601DateFormatter().string(from: Date())
            let data: [String: Any] = [
                "timestamp": timestamp,
                "device_id": "\(Config.deviceIdPrefix)_\(Int(Date().timeIntervalSince1970))",
                "source": "apple_healthkit",
                "metrics": [
                    "hr": self.lastHeartRate.map { Int($0) },
                    "hrv_rmssd": Int(self.lastHRVRMSSD ?? 0),
                    "hrv_sdnn": Int(hrvValue),
                    "steps": self.lastSteps.map { Int($0) },
                    "calories": self.lastCalories.map { Double(round($0 * 10) / 10) },
                    "stress": self.lastStress.map { Double(round($0 * 10) / 10) }
                ].compactMapValues { $0 },
                "meta": [
                    "battery": Config.defaultBatteryLevel,
                    "firmware_version": Config.defaultFirmwareVersion,
                    "synced": true
                ]
            ]
            
            os_log("Streaming HRV data: %d ms", log: Self.logger, type: .debug, Int(hrvValue))
            
            // Send to Flutter
            DispatchQueue.main.async {
                self.hrvEventSink?(data)
            }
        }
    }
    
    // MARK: - Real-Time Workout Methods
    
    /// Fallback to polling when workout session is not available or fails
    private func startPollingFallback() {
        os_log("Starting polling fallback for heart rate streaming", log: Self.logger, type: .info)
        
        heartRateTimer = Timer.scheduledTimer(withTimeInterval: streamingInterval, repeats: true) { [weak self] _ in
            self?.pollHeartRateData()
        }
        pollHeartRateData()
    }
    
    /// Starts a real-time workout session for live data streaming (iOS 10.0+)
    @available(iOS 10.0, *)
    private func startRealTimeWorkout() {
        guard HKHealthStore.isHealthDataAvailable() else {
            os_log("Health data not available for workout session", log: Self.logger, type: .error)
            return
        }
        
        // Create workout configuration
        let configuration = HKWorkoutConfiguration()
        configuration.activityType = .other
        configuration.locationType = .unknown
        
        do {
            // Create workout session
            workoutSession = try HKWorkoutSession(healthStore: healthStore, configuration: configuration)
            workoutBuilder = workoutSession?.associatedWorkoutBuilder()
            
            // Set delegates
            workoutSession?.delegate = self
            workoutBuilder?.delegate = self
            
            // Configure data source
            workoutBuilder?.dataSource = HKLiveWorkoutDataSource(healthStore: healthStore, workoutConfiguration: configuration)
            
            // Start the workout session
            let startDate = Date()
            try workoutSession?.startActivity(with: startDate)
            try workoutBuilder?.beginCollection(at: startDate) { [weak self] success, error in
                if let error = error {
                    os_log("Failed to begin workout collection: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
                } else if success {
                    os_log("Workout collection started successfully", log: Self.logger, type: .info)
                    self?.isWorkoutActive = true
                }
            }
            
            os_log("Real-time workout session started", log: Self.logger, type: .info)
            
        } catch {
            os_log("Failed to start workout session: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
            // Fallback to polling
            startPollingFallback()
        }
    }
    
    /// Stops the real-time workout session (iOS 10.0+)
    @available(iOS 10.0, *)
    private func stopRealTimeWorkout() {
        guard let session = workoutSession, isWorkoutActive else {
            return
        }
        
        os_log("Stopping real-time workout session", log: Self.logger, type: .info)
        
        let endDate = Date()
        session.end()
        workoutBuilder?.endCollection(at: endDate) { [weak self] success, error in
            if let error = error {
                os_log("Error ending workout collection: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
            } else {
                os_log("Workout collection ended successfully", log: Self.logger, type: .info)
            }
        }
        
        workoutBuilder?.finishWorkout { [weak self] workout, error in
            if let error = error {
                os_log("Error finishing workout: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
            } else {
                os_log("Workout finished successfully", log: Self.logger, type: .info)
            }
        }
        
        isWorkoutActive = false
        workoutSession = nil
        workoutBuilder = nil
    }
    
    // MARK: - HKWorkoutSessionDelegate (iOS 10.0+)
    
    @available(iOS 10.0, *)
    public func workoutSession(_ workoutSession: HKWorkoutSession, didChangeTo toState: HKWorkoutSessionState, from fromState: HKWorkoutSessionState, date: Date) {
        os_log("Workout session state changed from %{public}@ to %{public}@", log: Self.logger, type: .info, 
               String(describing: fromState), String(describing: toState))
        
        switch toState {
        case .running:
            os_log("Workout session is now running", log: Self.logger, type: .info)
        case .ended:
            os_log("Workout session ended", log: Self.logger, type: .info)
            isWorkoutActive = false
        case .paused:
            os_log("Workout session paused", log: Self.logger, type: .info)
        case .prepared:
            os_log("Workout session prepared", log: Self.logger, type: .info)
        case .stopped:
            os_log("Workout session stopped", log: Self.logger, type: .info)
            isWorkoutActive = false
        @unknown default:
            os_log("Unknown workout session state", log: Self.logger, type: .debug)
        }
    }
    
    @available(iOS 10.0, *)
    public func workoutSession(_ workoutSession: HKWorkoutSession, didFailWithError error: Error) {
        os_log("Workout session failed: %{public}@", log: Self.logger, type: .error, error.localizedDescription)
        isWorkoutActive = false
        startPollingFallback()
    }
    
    // MARK: - HKLiveWorkoutBuilderDelegate (iOS 10.0+)
    
    @available(iOS 10.0, *)
    public func workoutBuilder(_ workoutBuilder: HKLiveWorkoutBuilder, didCollectDataOf collectedTypes: Set<HKSampleType>) {
        // Process collected data in real-time
        for type in collectedTypes {
            if type == HKObjectType.quantityType(forIdentifier: .heartRate) {
                processRealTimeHeartRateData(from: workoutBuilder)
            } else if type == HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) {
                processRealTimeHRVData(from: workoutBuilder)
            }
        }
    }
    
    @available(iOS 10.0, *)
    public func workoutBuilderDidCollectEvent(_ workoutBuilder: HKLiveWorkoutBuilder) {
        // Handle workout events if needed
        os_log("Workout event collected", log: Self.logger, type: .debug)
    }
    
    /// Processes real-time heart rate data from workout builder (iOS 10.0+)
    @available(iOS 10.0, *)
    private func processRealTimeHeartRateData(from workoutBuilder: HKLiveWorkoutBuilder) {
        guard let heartRateType = HKObjectType.quantityType(forIdentifier: .heartRate),
              let statistics = workoutBuilder.statistics(for: heartRateType),
              let mostRecentSample = statistics.mostRecentQuantity() else {
            return
        }
        
        let heartRate = mostRecentSample.doubleValue(for: HKUnit(from: "count/min"))
        self.lastHeartRate = heartRate
        
        let timestamp = ISO8601DateFormatter().string(from: Date())
        
        let data: [String: Any] = [
            "timestamp": timestamp,
            "device_id": "\(Config.deviceIdPrefix)_\(Int(Date().timeIntervalSince1970))",
            "source": "apple_healthkit",
            "metrics": [
                "hr": Int(heartRate),
                "hrv_rmssd": self.lastHRVRMSSD.map { Int($0) },
                "hrv_sdnn": self.lastHRVSDNN.map { Int($0) },
                "steps": self.lastSteps.map { Int($0) },
                "calories": self.lastCalories.map { Double(round($0 * 10) / 10) },
                "stress": self.lastStress.map { Double(round($0 * 10) / 10) }
            ].compactMapValues { $0 },
            "meta": [
                "battery": Config.defaultBatteryLevel,
                "firmware_version": Config.defaultFirmwareVersion,
                "synced": true
            ]
        ]
        
        os_log("Real-time HR data: %d BPM", log: Self.logger, type: .debug, Int(heartRate))
        
        DispatchQueue.main.async {
            self.heartRateEventSink?(data)
        }
    }
    
    /// Processes real-time HRV data from workout builder (iOS 10.0+)
    @available(iOS 10.0, *)
    private func processRealTimeHRVData(from workoutBuilder: HKLiveWorkoutBuilder) {
        guard let hrvType = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN),
              let statistics = workoutBuilder.statistics(for: hrvType),
              let mostRecentSample = statistics.mostRecentQuantity() else {
            return
        }
        
        let hrvValue = mostRecentSample.doubleValue(for: HKUnit.secondUnit(with: .milli))
        self.lastHRVSDNN = hrvValue
        self.lastHRVRMSSD = hrvValue * 1.0 // Approximate RMSSD from SDNN
        
        let timestamp = ISO8601DateFormatter().string(from: Date())
        
        let data: [String: Any] = [
            "timestamp": timestamp,
            "device_id": "\(Config.deviceIdPrefix)_\(Int(Date().timeIntervalSince1970))",
            "source": "apple_healthkit",
            "metrics": [
                "hr": self.lastHeartRate.map { Int($0) },
                "hrv_rmssd": Int(self.lastHRVRMSSD ?? 0),
                "hrv_sdnn": Int(hrvValue),
                "steps": self.lastSteps.map { Int($0) },
                "calories": self.lastCalories.map { Double(round($0 * 10) / 10) },
                "stress": self.lastStress.map { Double(round($0 * 10) / 10) }
            ].compactMapValues { $0 },
            "meta": [
                "battery": Config.defaultBatteryLevel,
                "firmware_version": Config.defaultFirmwareVersion,
                "synced": true
            ]
        ]
        
        os_log("Real-time HRV data: %d ms", log: Self.logger, type: .debug, Int(hrvValue))
        
        DispatchQueue.main.async {
            self.hrvEventSink?(data)
        }
    }
    
    // MARK: - Helper Methods
    
    /// Converts permission strings to HealthKit object types
    /// - Parameter permissions: Array of permission strings
    /// - Returns: Set of HealthKit object types
    private func getHealthKitTypes(from permissions: [String]) -> Set<HKObjectType> {
        var types: Set<HKObjectType> = []
        
        os_log("Converting %d permissions to HealthKit types", log: Self.logger, type: .debug, permissions.count)
        
        for permission in permissions {
            switch permission {
            case "heart_rate":
                if let type = HKObjectType.quantityType(forIdentifier: .heartRate) {
                    types.insert(type)
                    os_log("Added heart rate type", log: Self.logger, type: .debug)
                }
            case "heart_rate_variability":
                if let type = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) {
                    types.insert(type)
                    os_log("Added HRV type", log: Self.logger, type: .debug)
                }
            case "steps":
                if let type = HKObjectType.quantityType(forIdentifier: .stepCount) {
                    types.insert(type)
                    os_log("Added steps type", log: Self.logger, type: .debug)
                }
            case "calories":
                if let type = HKObjectType.quantityType(forIdentifier: .activeEnergyBurned) {
                    types.insert(type)
                    os_log("Added calories type", log: Self.logger, type: .debug)
                }
            case "sleep":
                if let type = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
                    types.insert(type)
                    os_log("Added sleep type", log: Self.logger, type: .debug)
                }
            case "stress":
                // Stress is not directly available in HealthKit
                os_log("Stress permission not supported in HealthKit", log: Self.logger, type: .debug)
                break
            default:
                os_log("Unknown permission: %{public}@", log: Self.logger, type: .debug, permission)
                break
            }
        }
        
        os_log("Converted to %d HealthKit types", log: Self.logger, type: .debug, types.count)
        return types
    }
    
    /// Gets the current authorization status for specified permissions
    /// - Parameter permissions: Array of permission strings
    /// - Returns: Dictionary mapping permission names to authorization status
    private func getPermissionStatus(for permissions: [String]) -> [String: Bool] {
        var status: [String: Bool] = [:]
        
        os_log("Checking permission status for %d permissions", log: Self.logger, type: .debug, permissions.count)
        
        for permission in permissions {
            let isAuthorized: Bool
            
            switch permission {
            case "heart_rate":
                isAuthorized = healthStore.authorizationStatus(for: HKObjectType.quantityType(forIdentifier: .heartRate)!) == .sharingAuthorized
            case "heart_rate_variability":
                isAuthorized = healthStore.authorizationStatus(for: HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!) == .sharingAuthorized
            case "steps":
                isAuthorized = healthStore.authorizationStatus(for: HKObjectType.quantityType(forIdentifier: .stepCount)!) == .sharingAuthorized
            case "calories":
                isAuthorized = healthStore.authorizationStatus(for: HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!) == .sharingAuthorized
            case "sleep":
                isAuthorized = healthStore.authorizationStatus(for: HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!) == .sharingAuthorized
            default:
                isAuthorized = false
            }
            
            status[permission] = isAuthorized
            os_log("Permission %{public}@: %{public}@", log: Self.logger, type: .debug, permission, isAuthorized ? "authorized" : "not authorized")
        }
        
        return status
    }
}

// MARK: - Stream Handler

/// Types of data streams supported by the plugin
enum StreamType {
    case heartRate
    case hrv
}

/// Handles Flutter event streams for health data
class SynheartWearStreamHandler: NSObject, FlutterStreamHandler {
    private weak var plugin: SynheartWearPlugin?
    private let streamType: StreamType
    private var eventSink: FlutterEventSink?
    
    /// Initializes the stream handler
    /// - Parameters:
    ///   - plugin: Reference to the main plugin instance
    ///   - streamType: Type of stream to handle
    init(plugin: SynheartWearPlugin, streamType: StreamType) {
        self.plugin = plugin
        self.streamType = streamType
        super.init()
    }
    
    /// Called when Flutter starts listening to the stream
    /// - Parameters:
    ///   - arguments: Optional arguments from Flutter
    ///   - events: Event sink for sending data to Flutter
    /// - Returns: Flutter error if any occurred
    func onListen(withArguments arguments: Any?, eventSink events: @escaping FlutterEventSink) -> FlutterError? {
        os_log("Starting %{public}@ stream listener", log: SynheartWearPlugin.logger, type: .info, streamTypeDescription)
        
        self.eventSink = events
        
        // Store the event sink in the plugin and start streaming
        switch streamType {
        case .heartRate:
            plugin?.heartRateEventSink = events
            plugin?.startHeartRateStream()
        case .hrv:
            plugin?.hrvEventSink = events
            plugin?.startHRVStream()
        }
        
        return nil
    }
    
    /// Called when Flutter stops listening to the stream
    /// - Parameter arguments: Optional arguments from Flutter
    /// - Returns: Flutter error if any occurred
    func onCancel(withArguments arguments: Any?) -> FlutterError? {
        os_log("Stopping %{public}@ stream listener", log: SynheartWearPlugin.logger, type: .info, streamTypeDescription)
        
        // Clear the event sink from the plugin
        switch streamType {
        case .heartRate:
            plugin?.heartRateEventSink = nil
        case .hrv:
            plugin?.hrvEventSink = nil
        }
        
        eventSink = nil
        return nil
    }
    
    /// Human-readable description of the stream type
    private var streamTypeDescription: String {
        switch streamType {
        case .heartRate:
            return "heart rate"
        case .hrv:
            return "HRV"
        }
    }
}
