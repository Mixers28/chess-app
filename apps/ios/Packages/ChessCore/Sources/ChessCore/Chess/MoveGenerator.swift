import Foundation

/// Client-side legal-move generation from a FEN string.
/// Used only for UI affordance (highlighting legal targets when a piece is selected).
/// The server (python-chess) remains the sole authority for legality and outcomes.
public struct MoveGenerator: Sendable {

    private let board: [Piece?]   // 64 squares, rank-major
    private let sideToMove: PieceColor
    private let castlingRights: String
    private let enPassantSquare: Square?

    public init?(fen: String) {
        let parts = fen.split(separator: " ", omittingEmptySubsequences: false)
        guard parts.count >= 2 else { return nil }
        guard let b = Self.parseBoard(String(parts[0])) else { return nil }
        board = b
        sideToMove = parts[1] == "w" ? .white : .black
        castlingRights = parts.count > 2 ? String(parts[2]) : "-"
        enPassantSquare = parts.count > 3 ? Self.parseEP(String(parts[3])) : nil
    }

    /// Returns a map of from-square → [legal target squares] for the side to move.
    public func legalMoves() -> [Square: [Square]] {
        var result: [Square: [Square]] = [:]
        for idx in 0..<64 {
            let sq = Square(idx)
            guard let piece = board[idx], piece.color == sideToMove else { continue }
            let targets = pseudoLegal(from: sq, piece: piece)
                .filter { !leavesKingInCheck(from: sq, to: $0) }
            if !targets.isEmpty { result[sq] = targets }
        }
        return result
    }

    // MARK: - Pseudo-legal generation

    private func pseudoLegal(from sq: Square, piece: Piece) -> [Square] {
        switch piece.type {
        case .pawn:   return pawnMoves(from: sq, color: piece.color)
        case .knight: return knightMoves(from: sq, color: piece.color)
        case .bishop: return slidingMoves(from: sq, color: piece.color, deltas: bishopDeltas)
        case .rook:   return slidingMoves(from: sq, color: piece.color, deltas: rookDeltas)
        case .queen:  return slidingMoves(from: sq, color: piece.color, deltas: queenDeltas)
        case .king:   return kingMoves(from: sq, color: piece.color)
        }
    }

    private func pawnMoves(from sq: Square, color: PieceColor) -> [Square] {
        var moves: [Square] = []
        let dir = color == .white ? 1 : -1
        let startRank = color == .white ? 1 : 6

        let fwd = Square(file: sq.file, rank: sq.rank + dir)
        if inBounds(fwd) && board[fwd.index] == nil {
            moves.append(fwd)
            if sq.rank == startRank {
                let dbl = Square(file: sq.file, rank: sq.rank + 2 * dir)
                if board[dbl.index] == nil { moves.append(dbl) }
            }
        }
        for df in [-1, 1] {
            let target = Square(file: sq.file + df, rank: sq.rank + dir)
            guard inBounds(target) else { continue }
            if let p = board[target.index], p.color != color { moves.append(target) }
            if let ep = enPassantSquare, target == ep { moves.append(target) }
        }
        return moves
    }

    private let knightDeltas = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
    private func knightMoves(from sq: Square, color: PieceColor) -> [Square] {
        knightDeltas.compactMap { (df, dr) in
            let f = sq.file + df, r = sq.rank + dr
            guard f >= 0 && f < 8 && r >= 0 && r < 8 else { return nil }
            let t = Square(file: f, rank: r)
            if let p = board[t.index], p.color == color { return nil }
            return t
        }
    }

    private let bishopDeltas = [(-1,-1),(-1,1),(1,-1),(1,1)]
    private let rookDeltas   = [(-1,0),(1,0),(0,-1),(0,1)]
    private let queenDeltas  = [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)]

    private func slidingMoves(from sq: Square, color: PieceColor, deltas: [(Int,Int)]) -> [Square] {
        var moves: [Square] = []
        for (df, dr) in deltas {
            var f = sq.file + df, r = sq.rank + dr
            while f >= 0 && f < 8 && r >= 0 && r < 8 {
                let t = Square(file: f, rank: r)
                if let p = board[t.index] {
                    if p.color != color { moves.append(t) }
                    break
                }
                moves.append(t)
                f += df; r += dr
            }
        }
        return moves
    }

    private func kingMoves(from sq: Square, color: PieceColor) -> [Square] {
        var moves = queenDeltas.compactMap { (df, dr) -> Square? in
            let f = sq.file + df, r = sq.rank + dr
            guard f >= 0 && f < 8 && r >= 0 && r < 8 else { return nil }
            let t = Square(file: f, rank: r)
            if let p = board[t.index], p.color == color { return nil }
            return t
        }
        // Castling (simplified — only adds the squares; check/blocking is filtered by leavesKingInCheck)
        let backRank = color == .white ? 0 : 7
        if sq == Square(file: 4, rank: backRank) {
            let kSide = color == .white ? "K" : "k"
            let qSide = color == .white ? "Q" : "q"
            if castlingRights.contains(kSide) {
                let f = Square(file: 5, rank: backRank)
                let g = Square(file: 6, rank: backRank)
                if board[f.index] == nil && board[g.index] == nil { moves.append(g) }
            }
            if castlingRights.contains(qSide) {
                let b = Square(file: 1, rank: backRank)
                let c = Square(file: 2, rank: backRank)
                let d = Square(file: 3, rank: backRank)
                if board[b.index] == nil && board[c.index] == nil && board[d.index] == nil { moves.append(c) }
            }
        }
        return moves
    }

    // MARK: - Check detection

    private func leavesKingInCheck(from: Square, to: Square) -> Bool {
        var b = board
        b[to.index] = b[from.index]
        b[from.index] = nil
        // En-passant capture removes the pawn on the same rank.
        if let piece = b[to.index], piece.type == .pawn,
           let ep = enPassantSquare, to == ep {
            let dir = piece.color == .white ? -1 : 1
            b[Square(file: to.file, rank: to.rank + dir).index] = nil
        }
        return isInCheck(board: b, color: sideToMove)
    }

    private func isInCheck(board: [Piece?], color: PieceColor) -> Bool {
        guard let kingSq = (0..<64).first(where: {
            board[$0]?.type == .king && board[$0]?.color == color
        }).map(Square.init) else { return false }
        let opp = color == .white ? PieceColor.black : .white
        for idx in 0..<64 {
            guard let p = board[idx], p.color == opp else { continue }
            let from = Square(idx)
            if attacks(from: from, piece: p, to: kingSq, board: board) { return true }
        }
        return false
    }

    private func attacks(from sq: Square, piece: Piece, to target: Square, board: [Piece?]) -> Bool {
        switch piece.type {
        case .pawn:
            let dir = piece.color == .white ? 1 : -1
            return abs(sq.file - target.file) == 1 && target.rank - sq.rank == dir
        case .knight:
            let df = abs(sq.file - target.file), dr = abs(sq.rank - target.rank)
            return (df == 1 && dr == 2) || (df == 2 && dr == 1)
        case .bishop:
            return rayHits(from: sq, to: target, deltas: bishopDeltas, board: board)
        case .rook:
            return rayHits(from: sq, to: target, deltas: rookDeltas, board: board)
        case .queen:
            return rayHits(from: sq, to: target, deltas: queenDeltas, board: board)
        case .king:
            return max(abs(sq.file - target.file), abs(sq.rank - target.rank)) == 1
        }
    }

    private func rayHits(from sq: Square, to target: Square, deltas: [(Int,Int)], board: [Piece?]) -> Bool {
        for (df, dr) in deltas {
            var f = sq.file + df, r = sq.rank + dr
            while f >= 0 && f < 8 && r >= 0 && r < 8 {
                let t = Square(file: f, rank: r)
                if t == target { return true }
                if board[t.index] != nil { break }
                f += df; r += dr
            }
        }
        return false
    }

    // MARK: - FEN parsing

    private static func parseBoard(_ piecePart: String) -> [Piece?]? {
        var board = [Piece?](repeating: nil, count: 64)
        let ranks = piecePart.split(separator: "/")
        guard ranks.count == 8 else { return nil }
        for (rankIdx, rankStr) in ranks.reversed().enumerated() {
            var fileIdx = 0
            for ch in rankStr {
                if let skip = ch.wholeNumberValue {
                    fileIdx += skip
                } else if let piece = Piece(fenChar: ch) {
                    board[rankIdx * 8 + fileIdx] = piece
                    fileIdx += 1
                }
            }
        }
        return board
    }

    private static func parseEP(_ s: String) -> Square? {
        guard s.count == 2 else { return nil }
        let chars = Array(s)
        guard let file = "abcdefgh".firstIndex(of: chars[0]),
              let rank = Int(String(chars[1])) else { return nil }
        let f = "abcdefgh".distance(from: "abcdefgh".startIndex, to: file)
        return Square(file: f, rank: rank - 1)
    }

    private func inBounds(_ sq: Square) -> Bool {
        sq.file >= 0 && sq.file < 8 && sq.rank >= 0 && sq.rank < 8
    }
}

// MARK: - Piece

public enum PieceColor: Sendable, Equatable { case white, black }
public enum PieceType: Sendable, Equatable { case pawn, knight, bishop, rook, queen, king }

public struct Piece: Sendable, Equatable {
    public let color: PieceColor
    public let type: PieceType

    public init(color: PieceColor, type: PieceType) {
        self.color = color
        self.type = type
    }

    public init?(fenChar: Character) {
        let isWhite = fenChar.isUppercase
        color = isWhite ? .white : .black
        switch fenChar.lowercased() {
        case "p": type = .pawn
        case "n": type = .knight
        case "b": type = .bishop
        case "r": type = .rook
        case "q": type = .queen
        case "k": type = .king
        default: return nil
        }
    }

    public var fenChar: Character {
        let c: Character
        switch type {
        case .pawn:   c = "p"
        case .knight: c = "n"
        case .bishop: c = "b"
        case .rook:   c = "r"
        case .queen:  c = "q"
        case .king:   c = "k"
        }
        return color == .white ? Character(c.uppercased()) : c
    }

    public var symbol: String {
        switch type {
        case .king:   return "♚"
        case .queen:  return "♛"
        case .rook:   return "♜"
        case .bishop: return "♝"
        case .knight: return "♞"
        case .pawn:   return "♟"
        }
    }
}
