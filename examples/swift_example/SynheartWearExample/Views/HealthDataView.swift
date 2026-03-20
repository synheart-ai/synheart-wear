import SwiftUI

struct HealthDataView: View {
    @EnvironmentObject var viewModel: HealthViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Header with refresh
                    HStack {
                        Text("Latest Metrics")
                            .font(.title3)
                            .fontWeight(.semibold)
                        Spacer()
                        Button(action: { viewModel.readHealthData() }) {
                            Image(systemName: "arrow.clockwise")
                                .font(.title3)
                                .foregroundColor(.accentColor)
                        }
                    }

                    Divider()

                    if viewModel.metricsJson.isEmpty {
                        Text("No data yet. Tap refresh or read health data from the Dashboard.")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .padding(.vertical, 20)
                    } else {
                        ScrollView(.horizontal, showsIndicators: true) {
                            Text(viewModel.metricsJson)
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(.primary)
                                .padding(12)
                        }
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color(.systemGray6))
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(Color(.systemGray4), lineWidth: 1)
                        )
                    }
                }
                .padding(16)
            }
            .navigationTitle("Health Data")
        }
    }
}
