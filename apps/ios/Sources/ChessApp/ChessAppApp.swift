import SwiftUI
import ChessCore

@main
struct ChessAppApp: App {
    @State private var env = AppEnvironment()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(env)
        }
    }
}
