import Foundation
import ChessCore

/// Dependency container. Injected via SwiftUI Environment.
/// Override APIClient's baseURL via the CHESS_API_URL env var for local development.
@Observable
final class AppEnvironment {
    let apiClient: APIClient

    init() {
        let rawURL = ProcessInfo.processInfo.environment["CHESS_API_URL"]
            ?? "https://chess-api.chaosisaladder.co.uk"
        let baseURL = URL(string: rawURL)!
        let userId = ProcessInfo.processInfo.environment["CHESS_DEV_USER_ID"]
            ?? "dev-user-ios"
        apiClient = APIClient(baseURL: baseURL, userId: userId)
    }
}
