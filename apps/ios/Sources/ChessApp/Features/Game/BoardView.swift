import SwiftUI
import ChessCore

struct BoardView: View {
    let fen: String
    let flipped: Bool                     // true = black's perspective
    let selectedSquare: Square?
    let legalTargets: [Square]
    let lastMoveUCI: String?
    let onSquareTap: (Square) -> Void

    private var board: [Piece?] { parseFEN(fen) }
    private var lastMoveSquares: Set<Square> { lastMoveUCISquares(lastMoveUCI) }

    var body: some View {
        GeometryReader { geo in
            let size = min(geo.size.width, geo.size.height)
            let sq = size / 8
            VStack(spacing: 0) {
                ForEach(ranks, id: \.self) { rank in
                    HStack(spacing: 0) {
                        ForEach(files, id: \.self) { file in
                            let square = Square(file: file, rank: rank)
                            SquareView(
                                square: square,
                                piece: board[square.index],
                                isLight: (file + rank) % 2 == 1,
                                isSelected: selectedSquare == square,
                                isLegalTarget: legalTargets.contains(square),
                                isLastMove: lastMoveSquares.contains(square),
                                onTap: { onSquareTap(square) }
                            )
                            .frame(width: sq, height: sq)
                        }
                    }
                }
            }
            .frame(width: size, height: size)
        }
        .aspectRatio(1, contentMode: .fit)
    }

    private var ranks: [Int] {
        flipped ? Array(0..<8) : Array((0..<8).reversed())
    }
    private var files: [Int] {
        flipped ? Array((0..<8).reversed()) : Array(0..<8)
    }

    private func parseFEN(_ fen: String) -> [Piece?] {
        MoveGenerator(fen: fen).map { _ in
            var board = [Piece?](repeating: nil, count: 64)
            let piecePart = String(fen.split(separator: " ").first ?? "")
            var rank = 7, file = 0
            for ch in piecePart {
                if ch == "/" { rank -= 1; file = 0 }
                else if let skip = ch.wholeNumberValue { file += skip }
                else if let piece = Piece(fenChar: ch) {
                    board[rank * 8 + file] = piece
                    file += 1
                }
            }
            return board
        } ?? [Piece?](repeating: nil, count: 64)
    }

    private func lastMoveUCISquares(_ uci: String?) -> Set<Square> {
        guard let uci, uci.count >= 4 else { return [] }
        let chars = Array(uci)
        let files = "abcdefgh"
        guard
            let f1 = files.firstIndex(of: chars[0]),
            let r1 = Int(String(chars[1])),
            let f2 = files.firstIndex(of: chars[2]),
            let r2 = Int(String(chars[3]))
        else { return [] }
        let fd = (f: files.distance(from: files.startIndex, to: f1), r: r1 - 1)
        let td = (f: files.distance(from: files.startIndex, to: f2), r: r2 - 1)
        return [Square(file: fd.f, rank: fd.r), Square(file: td.f, rank: td.r)]
    }
}
