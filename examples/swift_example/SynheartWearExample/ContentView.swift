import SwiftUI

struct ContentView: View {
    @EnvironmentObject var viewModel: HealthViewModel

    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "square.grid.2x2")
                }

            HealthDataView()
                .tabItem {
                    Label("Health Data", systemImage: "heart.text.square")
                }

            StreamingView()
                .tabItem {
                    Label("Streaming", systemImage: "waveform.path.ecg")
                }
        }
        .accentColor(Color(red: 0.898, green: 0.224, blue: 0.208))
    }
}
