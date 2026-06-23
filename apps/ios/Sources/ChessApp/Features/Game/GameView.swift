import SwiftUI
import ChessCore

struct GameView: View {
    @Environment(AppEnvironment.self) private var env
    @State private var vm: GameViewModel?
    @State private var loadError: String?

    let gameId: String

    var body: some View {
        Group {
            if let vm {
                GameScreen(vm: vm)
            } else if let err = loadError {
                ContentUnavailableView("Failed to load", systemImage: "exclamationmark.triangle",
                                       description: Text(err))
            } else {
                ProgressView("Loading…")
            }
        }
        .navigationTitle("Game")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            do {
                let state = try await env.apiClient.getGame(gameId)
                vm = GameViewModel(gameId: gameId, initialState: state, apiClient: env.apiClient)
                vm?.refresh()
            } catch {
                loadError = friendlyMessage(error)
            }
        }
    }
}

private struct GameScreen: View {
    @Bindable var vm: GameViewModel

    private var server: GameState { vm.screenState.server }
    private var local: LocalInteraction { vm.screenState.local }

    private var isAIGame: Bool { server.mode == "ai" }
    private var flipped: Bool { false }   // TODO: flip for black in Phase 4

    private var selectedSquare: Square? {
        if case .selected(let sq, _) = local.stage { return sq }
        return nil
    }
    private var legalTargets: [Square] {
        if case .selected(_, let t) = local.stage { return t }
        return []
    }
    private var showPromotion: Bool {
        if case .pendingPromotion = local.stage { return true }
        return false
    }
    private var promotionColor: PieceColor {
        server.turn == "white" ? .white : .black
    }

    var body: some View {
        VStack(spacing: 0) {
            statusBanner
            boardArea
            controlBar
            if !vm.screenState.moves.isEmpty { moveList }
        }
        .alert("Error", isPresented: Binding(
            get: { local.error != nil },
            set: { if !$0 { vm.clearError() } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(local.error ?? "")
        }
    }

    // MARK: - Subviews

    private var statusBanner: some View {
        HStack {
            Circle()
                .fill(server.turn == "white" ? Color.white : Color.black)
                .overlay(Circle().strokeBorder(.gray, lineWidth: 1))
                .frame(width: 14, height: 14)
            Text(statusText)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
            Spacer()
            if isAIGame && server.status == "active" && server.turn != "white" {
                Button("Retry AI") { vm.retryAIMove() }
                    .font(.caption)
                    .buttonStyle(.bordered)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private var boardArea: some View {
        ZStack(alignment: .center) {
            BoardView(
                fen: server.fen,
                flipped: flipped,
                selectedSquare: selectedSquare,
                legalTargets: legalTargets,
                lastMoveUCI: server.lastMove?.uci,
                onSquareTap: { vm.tapSquare($0) }
            )
            .disabled(server.status != "active" || local.stage == .submitting)

            if showPromotion {
                Color.black.opacity(0.4).ignoresSafeArea()
                PromotionView(
                    color: promotionColor,
                    onSelect: { vm.selectPromotion($0) },
                    onCancel: { vm.cancelPromotion() }
                )
            }

            if local.stage == .submitting {
                ProgressView()
                    .padding()
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private var controlBar: some View {
        HStack {
            Button(role: .destructive) { vm.resign() } label: {
                Label("Resign", systemImage: "flag.fill")
            }
            .disabled(server.status != "active")
            .accessibilityLabel("Resign game")

            Spacer()

            Button { vm.refresh() } label: {
                Label("Refresh", systemImage: "arrow.clockwise")
            }
            .accessibilityLabel("Refresh game state")
        }
        .padding()
        .background(.bar)
    }

    private var moveList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 2) {
                ForEach(Array(vm.screenState.moves.enumerated()), id: \.offset) { _, m in
                    HStack {
                        Text(m.ply % 2 == 1 ? "\((m.ply + 1) / 2)." : "")
                            .frame(width: 36, alignment: .trailing)
                            .foregroundStyle(.secondary)
                            .font(.caption.monospacedDigit())
                        Text(m.san)
                            .font(.callout.monospaced())
                        if let engine = m.engine {
                            Text("(\(engine))")
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }
                        Spacer()
                    }
                    .padding(.horizontal)
                }
            }
        }
        .frame(maxHeight: 160)
    }

    // MARK: - Helpers

    private var statusText: String {
        switch server.status {
        case "finished":
            switch server.result {
            case "1-0":      return "White wins"
            case "0-1":      return "Black wins"
            case "1/2-1/2":  return "Draw"
            default:         return "Game over"
            }
        default:
            return "\(server.turn.capitalized) to move"
        }
    }
}
