import Foundation

// Mirrors services/api/app/games/schemas.py exactly.
// All types rely on the APIClient's convertFromSnakeCase / convertToSnakeCase strategies
// rather than explicit CodingKeys, so the JSON keys and Swift property names stay in sync
// automatically without dual maintenance.

public struct LastMove: Codable, Sendable, Equatable {
    public let uci: String
    public let san: String
}

public struct GameState: Codable, Sendable, Equatable, Identifiable {
    public var id: String { gameId }
    public let gameId: String
    public let sequence: Int
    public let fen: String
    public let turn: String          // "white" | "black"
    public let status: String        // "active" | "finished"
    public let result: String?       // "1-0" | "0-1" | "1/2-1/2"
    public let lastMove: LastMove?
    public let whiteUserId: String
    public let blackUserId: String?
    public let mode: String          // "local" | "ai"
}

public struct MoveRecord: Codable, Sendable, Equatable {
    public let ply: Int
    public let color: String
    public let uci: String
    public let san: String
    public let fenAfter: String
    public let engine: String?
    public let thinkMs: Int?
}

public struct CreateGameRequest: Codable, Sendable {
    public let mode: String
    public let timeControl: String?
    public let difficulty: String
    public let level: Int?
    public let color: String

    public init(
        mode: String = "local",
        timeControl: String? = nil,
        difficulty: String = "heuristic",
        level: Int? = nil,
        color: String = "white"
    ) {
        self.mode = mode
        self.timeControl = timeControl
        self.difficulty = difficulty
        self.level = level
        self.color = color
    }
}

public struct SubmitMoveRequest: Codable, Sendable {
    public let commandId: String
    public let expectedSequence: Int
    public let move: String

    public init(commandId: String, expectedSequence: Int, move: String) {
        self.commandId = commandId
        self.expectedSequence = expectedSequence
        self.move = move
    }
}

public struct ResignRequest: Codable, Sendable {
    public let commandId: String
    public let expectedSequence: Int

    public init(commandId: String, expectedSequence: Int) {
        self.commandId = commandId
        self.expectedSequence = expectedSequence
    }
}
