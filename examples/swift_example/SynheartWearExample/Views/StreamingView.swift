import SwiftUI

struct StreamingView: View {
    @EnvironmentObject var viewModel: HealthViewModel

    private let synheartRed = Color(red: 0.898, green: 0.224, blue: 0.208)
    private let synheartRedDark = Color(red: 0.776, green: 0.157, blue: 0.157)
    private let synheartPurple = Color(red: 0.482, green: 0.122, blue: 0.635)
    private let synheartGreen = Color(red: 0.263, green: 0.627, blue: 0.278)
    private let synheartOrange = Color(red: 0.984, green: 0.549, blue: 0.0)
    private let synheartBlue = Color(red: 0.118, green: 0.533, blue: 0.898)
    private let synheartTeal = Color(red: 0.0, green: 0.537, blue: 0.482)
    private let synheartGrey = Color(red: 0.459, green: 0.459, blue: 0.459)

    private var isAnyStreaming: Bool {
        viewModel.isStreamingHR || viewModel.isStreamingHRV
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Streaming status card
                    HStack(spacing: 12) {
                        Image(systemName: isAnyStreaming ? "play.fill" : "stop.fill")
                            .font(.title2)
                            .foregroundColor(isAnyStreaming ? synheartGreen : synheartGrey)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(isAnyStreaming ? "Streaming Active" : "All Streams Stopped")
                                .font(.headline)
                                .foregroundColor(isAnyStreaming ? synheartGreen : synheartGrey)
                            if !viewModel.lastUpdate.isEmpty {
                                Text("Last update: \(viewModel.lastUpdate)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                        Spacer()
                    }
                    .padding(16)
                    .background(
                        (isAnyStreaming ? synheartGreen : synheartGrey).opacity(0.1)
                    )
                    .cornerRadius(12)

                    // Stream controls
                    Text("Stream Controls")
                        .font(.title2)
                        .fontWeight(.semibold)

                    HStack(spacing: 12) {
                        Button(action: { viewModel.toggleHRStream() }) {
                            HStack {
                                Image(systemName: "heart.fill")
                                Text(viewModel.isStreamingHR ? "Stop" : "Heart Rate")
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .foregroundColor(.white)
                            .background(viewModel.isStreamingHR ? synheartRedDark : synheartRed)
                            .cornerRadius(10)
                        }

                        Button(action: { viewModel.toggleHRVStream() }) {
                            HStack {
                                Image(systemName: "waveform.path.ecg")
                                Text(viewModel.isStreamingHRV ? "Stop" : "HRV")
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .foregroundColor(.white)
                            .background(viewModel.isStreamingHRV ? synheartRedDark : synheartPurple)
                            .cornerRadius(10)
                        }
                    }

                    Button(action: { viewModel.stopAllStreams() }) {
                        HStack {
                            Image(systemName: "stop.fill")
                            Text("Stop All Streams")
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .foregroundColor(.white)
                        .background(isAnyStreaming ? synheartRedDark : synheartGrey)
                        .cornerRadius(10)
                    }
                    .disabled(!isAnyStreaming)

                    // Live data
                    Text("Live Data")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .padding(.top, 8)

                    if !viewModel.lastUpdate.isEmpty {
                        Text("Updated at \(viewModel.lastUpdate)")
                            .font(.caption)
                            .foregroundColor(synheartBlue)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(synheartBlue.opacity(0.08))
                            .cornerRadius(4)
                    }

                    // Metrics grid
                    LazyVGrid(columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12),
                    ], spacing: 12) {
                        MetricCardView(
                            title: "Heart Rate",
                            value: viewModel.heartRate.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "BPM",
                            icon: "heart.fill",
                            color: synheartRed
                        )
                        MetricCardView(
                            title: "HRV",
                            value: viewModel.hrv.map { String(format: "%.1f", $0) } ?? "--",
                            unit: "ms",
                            icon: "waveform.path.ecg",
                            color: synheartPurple
                        )
                        MetricCardView(
                            title: "Steps",
                            value: viewModel.steps.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "steps",
                            icon: "figure.walk",
                            color: synheartGreen
                        )
                        MetricCardView(
                            title: "Calories",
                            value: viewModel.calories.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "kcal",
                            icon: "flame.fill",
                            color: synheartOrange
                        )
                    }

                    // RR Intervals (full width)
                    let rrText: String = {
                        guard let intervals = viewModel.rrIntervals, !intervals.isEmpty else {
                            return "--"
                        }
                        if intervals.count > 3 {
                            return intervals.prefix(3).map { String(format: "%.1f", $0) }.joined(separator: ", ") + "…"
                        }
                        return intervals.map { String(format: "%.1f", $0) }.joined(separator: ", ")
                    }()

                    MetricCardView(
                        title: "RR Intervals",
                        value: rrText,
                        unit: "ms",
                        icon: "chart.line.uptrend.xyaxis",
                        color: synheartTeal
                    )

                    // ── BLE Heart Rate Monitor ─────────────────────
                    Text("BLE Heart Rate Monitor")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .padding(.top, 8)

                    // BLE status card
                    HStack(spacing: 12) {
                        Image(systemName: viewModel.bleConnected ? "antenna.radiowaves.left.and.right" : "antenna.radiowaves.left.and.right.slash")
                            .font(.title2)
                            .foregroundColor(viewModel.bleConnected ? synheartBlue : synheartGrey)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(viewModel.bleConnected ? "Connected: \(viewModel.bleDeviceName ?? "BLE Device")" : "No BLE Device Connected")
                                .font(.headline)
                                .foregroundColor(viewModel.bleConnected ? synheartBlue : synheartGrey)
                            if let hr = viewModel.bleHeartRate {
                                Text("BLE HR: \(hr) BPM")
                                    .font(.caption)
                                    .foregroundColor(synheartRed)
                            }
                        }
                        Spacer()
                    }
                    .padding(16)
                    .background(
                        (viewModel.bleConnected ? synheartBlue : synheartGrey).opacity(0.1)
                    )
                    .cornerRadius(12)

                    if !viewModel.bleConnected {
                        // Scan button
                        Button(action: { viewModel.scanBleDevices() }) {
                            HStack {
                                if viewModel.isScanning {
                                    ProgressView()
                                        .tint(.white)
                                    Text("Scanning...")
                                } else {
                                    Image(systemName: "antenna.radiowaves.left.and.right")
                                    Text("Scan for BLE HR Monitors")
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .foregroundColor(.white)
                            .background(viewModel.isScanning ? synheartGrey : synheartBlue)
                            .cornerRadius(10)
                        }
                        .disabled(viewModel.isScanning)

                        // Discovered devices
                        if !viewModel.bleDevices.isEmpty {
                            Text("Discovered Devices")
                                .font(.subheadline)
                                .fontWeight(.semibold)

                            ForEach(viewModel.bleDevices, id: \.id) { device in
                                Button(action: { viewModel.connectBleDevice(deviceId: device.id) }) {
                                    HStack {
                                        Image(systemName: "antenna.radiowaves.left.and.right")
                                            .foregroundColor(synheartBlue)
                                        Text(device.name)
                                            .foregroundColor(.primary)
                                        Spacer()
                                        Text("Connect")
                                            .foregroundColor(synheartBlue)
                                    }
                                    .padding(12)
                                    .background(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(synheartBlue.opacity(0.3))
                                    )
                                }
                            }
                        }
                    } else {
                        // Connected: stream toggle + disconnect
                        HStack(spacing: 12) {
                            Button(action: { viewModel.toggleBleHRStream() }) {
                                HStack {
                                    Image(systemName: "antenna.radiowaves.left.and.right")
                                    Text(viewModel.isStreamingBleHR ? "Stop" : "BLE HR")
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .foregroundColor(.white)
                                .background(viewModel.isStreamingBleHR ? synheartRedDark : synheartBlue)
                                .cornerRadius(10)
                            }

                            Button(action: { viewModel.disconnectBleDevice() }) {
                                HStack {
                                    Image(systemName: "xmark.circle")
                                    Text("Disconnect")
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .foregroundColor(.white)
                                .background(synheartGrey)
                                .cornerRadius(10)
                            }
                        }

                        if let hr = viewModel.bleHeartRate {
                            MetricCardView(
                                title: "BLE Heart Rate",
                                value: "\(hr)",
                                unit: "BPM",
                                icon: "antenna.radiowaves.left.and.right",
                                color: synheartBlue
                            )
                        }
                    }
                }
                .padding(16)
            }
            .navigationTitle("Streaming")
        }
    }
}
