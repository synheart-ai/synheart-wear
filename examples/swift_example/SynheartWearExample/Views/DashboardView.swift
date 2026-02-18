import SwiftUI
import SynheartWear

struct DashboardView: View {
    @EnvironmentObject var viewModel: HealthViewModel

    private let synheartRed = Color(red: 0.898, green: 0.224, blue: 0.208)
    private let synheartGreen = Color(red: 0.263, green: 0.627, blue: 0.278)
    private let synheartOrange = Color(red: 0.984, green: 0.549, blue: 0.0)
    private let synheartIndigo = Color(red: 0.224, green: 0.286, blue: 0.671)
    private let synheartBlue = Color(red: 0.118, green: 0.533, blue: 0.898)
    private let synheartGrey = Color(red: 0.459, green: 0.459, blue: 0.459)
    private let synheartTeal = Color(red: 0.0, green: 0.537, blue: 0.482)
    private let synheartRedDark = Color(red: 0.776, green: 0.157, blue: 0.157)

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Status section
                    Text("Status")
                        .font(.title2)
                        .fontWeight(.semibold)

                    LazyVGrid(columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12),
                    ], spacing: 12) {
                        StatusCardView(
                            title: "SDK Status",
                            value: viewModel.sdkInitialized ? "Ready" : "Not Init",
                            icon: "checkmark.circle.fill",
                            color: viewModel.sdkInitialized ? synheartGreen : synheartOrange
                        )
                        StatusCardView(
                            title: "Permissions",
                            value: viewModel.permissionsGranted ? "Granted" : "Pending",
                            icon: "shield.checkered",
                            color: viewModel.permissionsGranted ? synheartGreen : synheartRed
                        )
                        StatusCardView(
                            title: "Encryption",
                            value: viewModel.encryptionEnabled ? "Enabled" : "Disabled",
                            icon: "lock.fill",
                            color: viewModel.encryptionEnabled ? synheartGreen : synheartGrey
                        )
                        StatusCardView(
                            title: "Streaming",
                            value: (viewModel.isStreamingHR || viewModel.isStreamingHRV) ? "Active" : "Idle",
                            icon: "antenna.radiowaves.left.and.right",
                            color: (viewModel.isStreamingHR || viewModel.isStreamingHRV) ? synheartGreen : synheartGrey
                        )
                    }

                    // Quick Actions section
                    Text("Quick Actions")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .padding(.top, 8)

                    FlowLayout(spacing: 8) {
                        actionButton("Initialize SDK", icon: "play.fill", color: synheartGreen) {
                            viewModel.initializeSdk()
                        }
                        actionButton("Read Health Data", icon: "heart.fill", color: synheartRed) {
                            viewModel.readHealthData()
                        }
                        actionButton("Request Permissions", icon: "shield.fill", color: synheartOrange) {
                            viewModel.requestPermissions()
                        }
                        actionButton("Check Encryption", icon: "lock.fill", color: synheartIndigo) {
                            viewModel.checkEncryption()
                        }
                        actionButton("Test HealthKit", icon: "stethoscope", color: synheartGreen) {
                            viewModel.testHealthKit()
                        }
                        actionButton("Cache Stats", icon: "chart.bar.fill", color: synheartBlue) {
                            viewModel.loadCacheStats()
                        }
                        actionButton("Clear Cache", icon: "trash.fill", color: synheartGrey) {
                            viewModel.clearCache()
                        }
                        actionButton("Cached Sessions", icon: "clock.arrow.circlepath", color: synheartTeal) {
                            viewModel.loadCachedSessions()
                        }
                        actionButton("Purge All Data", icon: "exclamationmark.triangle.fill", color: synheartRedDark) {
                            viewModel.purgeAllData()
                        }
                    }

                    // ── Wearable Providers ─────────────────────
                    Text("Wearable Providers")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .padding(.top, 8)

                    let cloudProviders: [(adapter: DeviceAdapter, label: String, color: Color)] = [
                        (.garmin, "Garmin", synheartGreen),
                        (.whoop, "WHOOP", synheartIndigo),
                        (.fitbit, "Fitbit", synheartBlue),
                    ]

                    ForEach(cloudProviders, id: \.label) { provider in
                        let isConnected = viewModel.providerStatuses["\(provider.adapter)"] == true
                        HStack(spacing: 8) {
                            Image(systemName: isConnected ? "cloud.fill" : "cloud")
                                .foregroundColor(isConnected ? provider.color : synheartGrey)
                            Text(provider.label)
                                .fontWeight(.medium)
                            Spacer()
                            Button("Status") {
                                viewModel.checkProviderStatus(provider.adapter)
                            }
                            .font(.caption)
                            .buttonStyle(.bordered)

                            if isConnected {
                                actionButton("Disconnect", icon: "cloud.slash", color: synheartRedDark) {
                                    viewModel.disconnectProvider(provider.adapter)
                                }
                            } else {
                                actionButton("Connect", icon: "cloud.fill", color: provider.color) {
                                    viewModel.connectProvider(provider.adapter)
                                }
                            }
                        }
                    }

                    // BLE status on dashboard
                    HStack {
                        Image(systemName: "antenna.radiowaves.left.and.right")
                            .foregroundColor(viewModel.bleConnected ? synheartBlue : synheartGrey)
                        Text(viewModel.bleConnected ? "BLE HRM: \(viewModel.bleDeviceName ?? "Connected")" : "BLE HRM: Not connected")
                            .font(.subheadline)
                        Spacer()
                        Text(viewModel.bleConnected ? "Active" : "Idle")
                            .font(.caption)
                            .foregroundColor(viewModel.bleConnected ? synheartBlue : synheartGrey)
                    }
                    .padding(.top, 4)

                    if !viewModel.statusMessage.isEmpty {
                        Text(viewModel.statusMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .padding(.top, 4)
                    }
                }
                .padding(16)
            }
            .navigationTitle("Synheart Wear")
        }
    }

    @ViewBuilder
    private func actionButton(_ label: String, icon: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundColor(color)
                Text(label)
                    .font(.subheadline)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(color.opacity(0.12))
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }
}

// Simple flow layout for wrapping buttons
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layout(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layout(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y),
                proposal: .unspecified
            )
        }
    }

    private func layout(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        var maxX: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth, x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            positions.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
            maxX = max(maxX, x)
        }

        return (CGSize(width: maxX, height: y + rowHeight), positions)
    }
}
