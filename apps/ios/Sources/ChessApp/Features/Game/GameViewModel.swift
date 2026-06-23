import Foundation
import ChessCore

@Observable
@MainActor
final class GameViewModel {
    private(set) var screenState: GameScreenState
    private(set) var legalMoves: [Square: [Square]] = [:]
    private(set) var pendingUCI: String? = nil   // built from from+to during promotion

    private let gameId: String
    private let apiClient: APIClient
    private var isSendingMove = false

    init(gameId: String, initialState: GameState, apiClient: APIClient) {
        self.gameId = gameId
        self.apiClient = apiClient
        self.screenState = GameScreenState(server: initialState)
        refreshLegalMoves(fen: initialState.fen)
    }

    // MARK: - User actions

    func tapSquare(_ sq: Square) {
        // Build UCI from selection → destination for promotion path.
        if case .selected(let from, let targets) = screenState.local.stage,
           targets.contains(sq) {
            pendingUCI = "\(from.name)\(sq.name)"
        }

        let moves = legalMoves
        reduce(&screenState, action: .tapSquare(sq), legalMoves: moves)

        if case .submitting = screenState.local.stage, let uci = pendingUCI {
            pendingUCI = nil
            Task { await submitMove(uci: uci) }
        }
    }

    func selectPromotion(_ piece: String) {
        guard let base = pendingUCI else { return }
        reduce(&screenState, action: .selectPromotion(piece: piece), legalMoves: legalMoves)
        pendingUCI = nil
        Task { await submitMove(uci: base + piece) }
    }

    func cancelPromotion() {
        pendingUCI = nil
        reduce(&screenState, action: .cancelPromotion, legalMoves: legalMoves)
    }

    func resign() {
        Task {
            let commandId = UUID().uuidString
            let seq = screenState.server.sequence
            do {
                let state = try await apiClient.resign(
                    gameId: gameId,
                    body: ResignRequest(commandId: commandId, expectedSequence: seq)
                )
                reduce(&screenState, action: .resignConfirmed(state), legalMoves: [:])
                refreshLegalMoves(fen: state.fen)
            } catch {
                reduce(&screenState, action: .moveRejected(friendlyError(error)), legalMoves: legalMoves)
            }
        }
    }

    func refresh() {
        Task {
            reduce(&screenState, action: .setLoading(true), legalMoves: legalMoves)
            do {
                let state = try await apiClient.getGame(gameId)
                reduce(&screenState, action: .stateRefreshed(state), legalMoves: legalMoves)
                refreshLegalMoves(fen: state.fen)
                let moves = try await apiClient.listMoves(gameId: gameId)
                reduce(&screenState, action: .movesLoaded(moves), legalMoves: legalMoves)
            } catch {
                reduce(&screenState, action: .moveRejected(friendlyError(error)), legalMoves: legalMoves)
            }
        }
    }

    func clearError() {
        reduce(&screenState, action: .clearError, legalMoves: legalMoves)
    }

    func retryAIMove() {
        Task {
            do {
                let state = try await apiClient.triggerAIMove(gameId: gameId)
                reduce(&screenState, action: .aiMoveApplied(state), legalMoves: legalMoves)
                refreshLegalMoves(fen: state.fen)
            } catch {
                reduce(&screenState, action: .moveRejected(friendlyError(error)), legalMoves: legalMoves)
            }
        }
    }

    // MARK: - Private

    private func submitMove(uci: String) async {
        guard !isSendingMove else { return }
        isSendingMove = true
        defer { isSendingMove = false }

        let commandId = UUID().uuidString
        let seq = screenState.server.sequence
        do {
            let state = try await apiClient.submitMove(
                gameId: gameId,
                body: SubmitMoveRequest(commandId: commandId, expectedSequence: seq, move: uci)
            )
            reduce(&screenState, action: .moveSubmitted(state), legalMoves: legalMoves)
            refreshLegalMoves(fen: state.fen)
            let moves = try await apiClient.listMoves(gameId: gameId)
            reduce(&screenState, action: .movesLoaded(moves), legalMoves: legalMoves)
        } catch APIError.stale(let recovery) {
            reduce(&screenState, action: .stateRefreshed(recovery), legalMoves: legalMoves)
            refreshLegalMoves(fen: recovery.fen)
        } catch {
            reduce(&screenState, action: .moveRejected(friendlyError(error)), legalMoves: legalMoves)
        }
    }

    private func refreshLegalMoves(fen: String) {
        legalMoves = MoveGenerator(fen: fen)?.legalMoves() ?? [:]
    }

    private func friendlyError(_ error: Error) -> String {
        friendlyMessage(error)
    }
}
