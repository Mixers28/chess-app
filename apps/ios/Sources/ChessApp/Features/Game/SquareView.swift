import SwiftUI
import ChessCore

struct SquareView: View {
    let square: Square
    let piece: Piece?
    let isLight: Bool
    let isSelected: Bool
    let isLegalTarget: Bool
    let isLastMove: Bool
    let onTap: () -> Void

    private var background: Color {
        if isSelected { return .yellow.opacity(0.7) }
        if isLastMove { return .yellow.opacity(0.4) }
        return isLight ? Color(white: 0.93) : Color(hue: 0.1, saturation: 0.4, brightness: 0.55)
    }

    var body: some View {
        ZStack {
            Rectangle()
                .fill(background)
            if let piece {
                Text(piece.symbol)
                    .font(.system(size: 42))
                    .minimumScaleFactor(0.5)
                    .accessibilityLabel(pieceLabel(piece))
            }
            if isLegalTarget {
                Circle()
                    .fill(Color.black.opacity(piece != nil ? 0 : 0.15))
                    .overlay(
                        Circle()
                            .strokeBorder(Color.black.opacity(piece != nil ? 0.4 : 0), lineWidth: 3)
                    )
                    .padding(piece != nil ? 2 : 10)
            }
        }
        .onTapGesture(perform: onTap)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(squareLabel)
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
    }

    private var squareLabel: String {
        var parts = [square.name]
        if let piece { parts.append(pieceLabel(piece)) }
        if isSelected { parts.append("selected") }
        if isLegalTarget { parts.append("legal destination") }
        return parts.joined(separator: ", ")
    }

    private func pieceLabel(_ p: Piece) -> String {
        let color = p.color == .white ? "white" : "black"
        let type: String
        switch p.type {
        case .pawn:   type = "pawn"
        case .knight: type = "knight"
        case .bishop: type = "bishop"
        case .rook:   type = "rook"
        case .queen:  type = "queen"
        case .king:   type = "king"
        }
        return "\(color) \(type)"
    }
}
