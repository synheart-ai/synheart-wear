import Flutter
import UIKit
import HealthKit

public class SynheartWearPlugin: NSObject, FlutterPlugin {
  private let healthStore = HKHealthStore()

  public static func register(with registrar: FlutterPluginRegistrar) {
    let channel = FlutterMethodChannel(name: "synheart_wear/healthkit_rr", binaryMessenger: registrar.messenger())
    let instance = SynheartWearPlugin()
    registrar.addMethodCallDelegate(instance, channel: channel)
  }

  public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "isAvailable":
      if #available(iOS 13.0, *) {
        let available = HKHealthStore.isHealthDataAvailable()
        result(available)
      } else {
        result(false)
      }
    case "fetchRR":
      guard #available(iOS 13.0, *) else {
        result([Double]())
        return
      }
      guard let args = call.arguments as? [String: Any],
            let startStr = args["start"] as? String,
            let endStr = args["end"] as? String,
            let start = ISO8601DateFormatter().date(from: startStr),
            let end = ISO8601DateFormatter().date(from: endStr) else {
        result([Double]())
        return
      }
      requestHeartbeatSeries(start: start, end: end, completion: result)
    default:
      result(FlutterMethodNotImplemented)
    }
  }

  @available(iOS 13.0, *)
  private func requestHeartbeatSeries(start: Date, end: Date, completion: @escaping FlutterResult) {
    // Use string literal (bridged) to avoid enum symbol issues across SDKs
    guard let heartbeatType = HKObjectType.seriesType(forIdentifier: "HKHeartbeatSeriesTypeIdentifier") else {
      completion([Double]())
      return
    }
    let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

    let rrCollector = HeartbeatRRCollector()

    // Request authorization if needed
    healthStore.requestAuthorization(toShare: nil, read: [heartbeatType]) { [weak self] (granted, error) in
      guard let self = self, granted, error == nil else {
        completion([Double]())
        return
      }

      let sort = [NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: true)]
      let sampleQuery = HKSampleQuery(sampleType: heartbeatType, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: sort) { [weak self] (_, samples, err) in
        guard let self = self, err == nil, let hbSamples = samples as? [HKHeartbeatSeriesSample], !hbSamples.isEmpty else {
          completion([Double]())
          return
        }
        let group = DispatchGroup()
        for sample in hbSamples {
          group.enter()
          let seriesQuery = HKHeartbeatSeriesQuery(heartbeatSeries: sample) { (_, timeSinceSeriesStart, _, done, error) in
            if error == nil {
              rrCollector.add(timeSinceSeriesStart: timeSinceSeriesStart, precededByGap: false)
            }
            if done {
              group.leave()
            }
          }
          self.healthStore.execute(seriesQuery)
        }
        group.notify(queue: .main) {
          completion(rrCollector.toRRMs())
        }
      }
      self.healthStore.execute(sampleQuery)
    }
  }
}

// Helper to convert heartbeat times to RR intervals (best-effort)
@available(iOS 13.0, *)
fileprivate class HeartbeatRRCollector {
  private var times: [Double] = [] // seconds since series start
  func add(timeSinceSeriesStart: TimeInterval, precededByGap: Bool) {
    times.append(timeSinceSeriesStart)
  }
  func toRRMs() -> [Double] {
    guard times.count >= 2 else { return [] }
    var rr: [Double] = []
    for i in 1..<times.count {
      let diffSec = times[i] - times[i-1]
      rr.append(diffSec * 1000.0)
    }
    return rr
  }
}


