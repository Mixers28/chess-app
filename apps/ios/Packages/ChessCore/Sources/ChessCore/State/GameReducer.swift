import Foundation

// Authoritative state comes from the server, keyed by sequence number.
// Local state is ephemeral UI: selected square, in-flight move, pending promotion.

public struct LocalInteraction: Sendable, Equatable {
    public enum Stage: Sendable, Equatable {
        case idle
        case selected(square: Square, legalTargets: [Square])
        case pendingPromotion(from: Square, to: Square)
        case submitting
    }
    public var stage: Stage = .idle
    public var error: String? = nil

    public init() {}
}

public struct GameScreenState: Sendable, Equatable {
    public var server: GameState          // last committed snapshot from the server
    public var local: LocalInteraction
    public var moves: [MoveRecord]
    public var isLoading: Bool

    public init(server: GameState) {
        self.server = server
        self.local = LocalInteraction()
        self.moves = []
        self.isLoading = false
    }
}

public enum GameAction: Sendable {
    case tapSquare(Square)
    case selectPromotion(piece: String)   // "q" | "r" | "b" | "n"
    case cancelPromotion
    case moveSubmitted(GameState)         // server returned new canonical state
    case moveRejected(String)            // illegal / other server error
    case stateRefreshed(GameState)       // GET /games/{id} result
    case movesLoaded([MoveRecord])
    case aiMoveApplied(GameState)
    case clearError
    case resignConfirmed(GameState)
    case setLoading(Bool)
}

public func reduce(_ state: inout GameScreenState, action: GameAction, legalMoves: [Square: [Square]]) {
    switch action {

    case .tapSquare(let sq):
        guard !state.isLoading else { return }
        switch state.local.stage {
        case .idle:
            if let targets = legalMoves[sq], !targets.isEmpty {
                state.local.stage = .selected(square: sq, legalTargets: targets)
                state.local.error = nil
            }

        case .selected(let from, let targets):
            if sq == from {
                state.local.stage = .idle
                return
            }
            guard targets.contains(sq) else {
                // Tapped a different own piece → re-select.
                if let newTargets = legalMoves[sq], !newTargets.isEmpty {
                    state.local.stage = .selected(square: sq, legalTargets: newTargets)
                } else {
                    state.local.stage = .idle
                }
                return
            }
            // Check if this move needs a promotion choice.
            if needsPromotion(from: from, to: sq, fen: state.server.fen) {
                state.local.stage = .pendingPromotion(from: from, to: sq)
            } else {
                state.local.stage = .submitting
            }

        case .pendingPromotion, .submitting:
            break
        }

    case .selectPromotion:
        guard case .pendingPromotion = state.local.stage else { return }
        state.local.stage = .submitting

    case .cancelPromotion:
        state.local.stage = .idle

    case .moveSubmitted(let newState), .aiMoveApplied(let newState):
        if newState.sequence >= state.server.sequence {
            state.server = newState
        }
        state.local.stage = .idle
        state.local.error = nil
        state.isLoading = false

    case .moveRejected(let message):
        state.local.stage = .idle
        state.local.error = message
        state.isLoading = false

    case .stateRefreshed(let newState):
        if newState.sequence >= state.server.sequence {
            state.server = newState
        }
        state.local.stage = .idle
        state.isLoading = false

    case .movesLoaded(let records):
        state.moves = records

    case .clearError:
        state.local.error = nil

    case .resignConfirmed(let newState):
        state.server = newState
        state.local = LocalInteraction()
        state.isLoading = false

    case .setLoading(let loading):
        state.isLoading = loading
    }
}

// Returns true when a pawn is moving to the back rank.
private func needsPromotion(from: Square, to: Square, fen: String) -> Bool {
    // Side to move is encoded in FEN part 2.
    let parts = fen.split(separator: " ")
    guard parts.count >= 2 else { return false }
    let side = parts[1]
    let toRank = to.rank
    let fromRank = from.rank
    if side == "w" && fromRank == 6 && toRank == 7 { return true }
    if side == "b" && fromRank == 1 && toRank == 0 { return true }
    return false
}
