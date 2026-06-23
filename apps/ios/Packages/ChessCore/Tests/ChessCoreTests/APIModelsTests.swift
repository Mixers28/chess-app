import Testing
@testable import ChessCore

@Suite("APIModels")
struct APIModelsTests {

    @Test("GameState decodes from server JSON (snake_case → camelCase via convertFromSnakeCase)")
    func decodeGameState() throws {
        // JSON keys are snake_case (as returned by the Python API).
        // The decoder's convertFromSnakeCase strategy maps them to Swift camelCase properties.
        let json = """
        {
          "game_id": "abc123",
          "sequence": 4,
          "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
          "turn": "black",
          "status": "active",
          "result": null,
          "last_move": {"uci": "e2e4", "san": "e4"},
          "white_user_id": "user-1",
          "black_user_id": "user-2",
          "mode": "ai"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let state = try decoder.decode(GameState.self, from: json)

        #expect(state.gameId == "abc123")
        #expect(state.sequence == 4)
        #expect(state.turn == "black")
        #expect(state.mode == "ai")
        #expect(state.whiteUserId == "user-1")
        #expect(state.blackUserId == "user-2")
        #expect(state.lastMove?.uci == "e2e4")
        #expect(state.lastMove?.san == "e4")
    }

    @Test("SubmitMoveRequest encodes to snake_case")
    func encodeSubmitMove() throws {
        let req = SubmitMoveRequest(commandId: "cmd-1", expectedSequence: 3, move: "e2e4")
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(req)
        let raw = try #require(try JSONSerialization.jsonObject(with: data) as? [String: Any])
        #expect(raw["command_id"] as? String == "cmd-1")
        #expect(raw["expected_sequence"] as? Int == 3)
        #expect(raw["move"] as? String == "e2e4")
    }
}
