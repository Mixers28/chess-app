import SwiftUI
import ChessCore

struct PromotionView: View {
    let color: PieceColor
    let onSelect: (String) -> Void
    let onCancel: () -> Void

    private let choices: [(String, PieceType)] = [
        ("q", .queen), ("r", .rook), ("b", .bishop), ("n", .knight)
    ]

    var body: some View {
        VStack(spacing: 0) {
            Text("Promote to")
                .font(.headline)
                .padding(.bottom, 8)

            HStack(spacing: 16) {
                ForEach(choices, id: \.0) { code, type in
                    let piece = Piece(color: color, type: type)
                    Button {
                        onSelect(code)
                    } label: {
                        Text(piece.symbol)
                            .font(.system(size: 52))
                    }
                    .accessibilityLabel("Promote to \(type)")
                }
            }

            Button("Cancel", role: .cancel, action: onCancel)
                .padding(.top, 12)
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .padding()
    }
}
