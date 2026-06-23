import SwiftUI
import ChessCore

struct GameListView: View {
    @Environment(AppEnvironment.self) private var env
    @State private var path = NavigationPath()
    @State private var showNewGame = false
    @State private var error: String? = nil

    var body: some View {
        NavigationStack(path: $path) {
            ContentUnavailableView(
                "No active game",
                systemImage: "checkerboard.rectangle",
                description: Text("Tap + to start a new game.")
            )
            .navigationTitle("Chess")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showNewGame = true } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityLabel("New game")
                }
            }
            .sheet(isPresented: $showNewGame) {
                NewGameView { req in
                    await startGame(req)
                }
            }
            .alert("Error", isPresented: Binding(get: { error != nil }, set: { if !$0 { error = nil } })) {
                Button("OK", role: .cancel) { error = nil }
            } message: {
                Text(error ?? "")
            }
            .navigationDestination(for: String.self) { gameId in
                GameView(gameId: gameId)
            }
        }
    }

    private func startGame(_ req: CreateGameRequest) async {
        do {
            let state = try await env.apiClient.createGame(req)
            path.append(state.gameId)
        } catch {
            self.error = friendlyMessage(error)
        }
    }
}
