import SwiftUI

@main
struct FlashbackDailyApp: App {
    @StateObject private var flashbackStore = FlashbackStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(flashbackStore)
        }
    }
}
