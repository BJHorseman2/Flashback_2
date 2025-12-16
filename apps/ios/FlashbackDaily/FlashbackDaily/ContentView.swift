import SwiftUI

struct ContentView: View {
    @EnvironmentObject var store: FlashbackStore

    var body: some View {
        NavigationStack {
            if let flashback = store.currentFlashback {
                FlashbackView(flashback: flashback)
            } else {
                HomeView()
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(FlashbackStore())
}
