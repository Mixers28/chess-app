import Foundation

public actor APIClient {
    private let base: URL
    private let session: URLSession
    private let userId: String
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    public init(baseURL: URL, userId: String, session: URLSession = .shared) {
        self.base = baseURL
        self.userId = userId
        self.session = session
    }

    // MARK: - Games

    public func createGame(_ body: CreateGameRequest) async throws -> GameState {
        try await post("/v1/games", body: body)
    }

    public func getGame(_ gameId: String) async throws -> GameState {
        try await get("/v1/games/\(gameId)")
    }

    public func submitMove(gameId: String, body: SubmitMoveRequest) async throws -> GameState {
        try await post("/v1/games/\(gameId)/moves", body: body)
    }

    public func resign(gameId: String, body: ResignRequest) async throws -> GameState {
        try await post("/v1/games/\(gameId)/resign", body: body)
    }

    public func listMoves(gameId: String) async throws -> [MoveRecord] {
        try await get("/v1/games/\(gameId)/moves")
    }

    public func triggerAIMove(gameId: String) async throws -> GameState {
        try await post("/v1/games/\(gameId)/ai-move", body: EmptyBody())
    }

    // MARK: - Transport

    private func request(method: String, path: String, body: (any Encodable)?) throws -> URLRequest {
        var req = URLRequest(url: base.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(userId, forHTTPHeaderField: "X-Dev-User")
        if let body {
            req.httpBody = try encoder.encode(body)
        }
        return req
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let req = try request(method: "GET", path: path, body: nil as EmptyBody?)
        return try await execute(req)
    }

    private func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        let req = try request(method: "POST", path: path, body: body)
        return try await execute(req)
    }

    private func execute<T: Decodable>(_ req: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: req)
        } catch let e as URLError {
            throw APIError.network(e)
        } catch {
            throw APIError.unknown(error)
        }

        let http = response as! HTTPURLResponse
        switch http.statusCode {
        case 200...299:
            break
        case 404:
            throw APIError.notFound
        case 403:
            throw APIError.unauthorized
        case 503:
            throw APIError.engineUnavailable
        case 409:
            // Body: {"error":"stale_sequence", "state": <GameState>}
            if let wrapper = try? decoder.decode(StaleBody.self, from: data) {
                throw APIError.stale(recovery: wrapper.state)
            }
            throw APIError.http(statusCode: 409, body: String(data: data, encoding: .utf8) ?? "")
        case 422:
            let detail = (try? decoder.decode(ErrorBody.self, from: data))?.detail ?? "Illegal move"
            throw APIError.illegalMove(detail: detail)
        default:
            throw APIError.http(statusCode: http.statusCode,
                                body: String(data: data, encoding: .utf8) ?? "")
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch let e as DecodingError {
            throw APIError.decode(e)
        }
    }
}

private struct EmptyBody: Encodable {}
private struct StaleBody: Decodable { let state: GameState }
