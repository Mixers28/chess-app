import Foundation

public enum APIError: Error, Sendable {
    case network(URLError)
    case http(statusCode: Int, body: String)
    case stale(recovery: GameState)      // 409 with canonical snapshot
    case illegalMove(detail: String)     // 422
    case notFound                        // 404
    case unauthorized                    // 403
    case engineUnavailable               // 503 — AI engine not configured on server
    case decode(DecodingError)
    case unknown(Error)
}

extension APIError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .network(let e):
            return "Cannot reach the server. Make sure the backend is running. (\(e.localizedDescription))"
        case .illegalMove(let d):
            return "Illegal move: \(d)"
        case .stale:
            return "Move was out of order — the board has been refreshed."
        case .notFound:
            return "Game not found."
        case .unauthorized:
            return "Not authorised for this action."
        case .engineUnavailable:
            return "Stockfish engine is not available on this server. Choose a different difficulty."
        case .http(let code, _):
            return "Server returned an error (HTTP \(code))."
        case .decode(let e):
            return "Could not read server response: \(e.localizedDescription)"
        case .unknown(let e):
            return e.localizedDescription
        }
    }
}

struct ErrorBody: Codable {
    let detail: String?
}
