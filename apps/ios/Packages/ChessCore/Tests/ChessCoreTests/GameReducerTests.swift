import Testing
@testable import ChessCore

private let startingFEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

private func makeState() -> GameScreenState {
    GameScreenState(server: GameState(
        gameId: "test-game",
        sequence: 0,
        fen: startingFEN,
        turn: "white",
        status: "active",
        result: nil,
        lastMove: nil,
        whiteUserId: "user-1",
        blackUserId: "user-2",
        mode: "local"
    ))
}

private func legalMovesFromStart() -> [Square: [Square]] {
    MoveGenerator(fen: startingFEN)?.legalMoves() ?? [:]
}

@Suite("GameReducer")
struct GameReducerTests {

    @Test("Tapping a piece with legal moves selects it")
    func tapToSelect() {
        var state = makeState()
        let e2 = Square(file: 4, rank: 1)
        reduce(&state, action: .tapSquare(e2), legalMoves: legalMovesFromStart())
        if case .selected(let sq, let targets) = state.local.stage {
            #expect(sq == e2)
            #expect(!targets.isEmpty)
        } else {
            Issue.record("Expected .selected stage")
        }
    }

    @Test("Tapping selected square deselects it")
    func tapSameSquareDeselects() {
        var state = makeState()
        let e2 = Square(file: 4, rank: 1)
        let lm = legalMovesFromStart()
        reduce(&state, action: .tapSquare(e2), legalMoves: lm)
        reduce(&state, action: .tapSquare(e2), legalMoves: lm)
        #expect(state.local.stage == .idle)
    }

    @Test("Tapping empty square from idle stays idle")
    func tapEmptyIdle() {
        var state = makeState()
        let e4 = Square(file: 4, rank: 3)
        reduce(&state, action: .tapSquare(e4), legalMoves: legalMovesFromStart())
        #expect(state.local.stage == .idle)
    }

    @Test("Server state never regresses on older sequence")
    func noSequenceRegression() {
        var state = makeState()
        let newer = GameState(
            gameId: "test-game", sequence: 5, fen: startingFEN,
            turn: "white", status: "active", result: nil, lastMove: nil,
            whiteUserId: "user-1", blackUserId: "user-2", mode: "local"
        )
        let older = GameState(
            gameId: "test-game", sequence: 2, fen: startingFEN,
            turn: "white", status: "active", result: nil, lastMove: nil,
            whiteUserId: "user-1", blackUserId: "user-2", mode: "local"
        )
        reduce(&state, action: .moveSubmitted(newer), legalMoves: [:])
        reduce(&state, action: .stateRefreshed(older), legalMoves: [:])
        #expect(state.server.sequence == 5)
    }

    @Test("Stale 409 reconciles to recovery snapshot")
    func staleReconciles() {
        var state = makeState()
        let recovery = GameState(
            gameId: "test-game", sequence: 3, fen: startingFEN,
            turn: "black", status: "active", result: nil, lastMove: nil,
            whiteUserId: "user-1", blackUserId: "user-2", mode: "local"
        )
        reduce(&state, action: .stateRefreshed(recovery), legalMoves: [:])
        #expect(state.server.sequence == 3)
        #expect(state.server.turn == "black")
        #expect(state.local.stage == .idle)
    }
}
