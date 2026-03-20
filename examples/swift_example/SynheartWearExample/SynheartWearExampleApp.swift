import SwiftUI

@main
struct SynheartWearExampleApp: App {
    @StateObject private var viewModel = HealthViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
