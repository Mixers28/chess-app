import SwiftUI
import ChessCore

private struct Difficulty: Identifiable {
    let id: Int
    let label: String
    let description: String
}

private let difficulties: [Difficulty] = [
    Difficulty(id: 1, label: "Beginner", description: "Loose, beatable play with simple mistakes."),
    Difficulty(id: 2, label: "Casual", description: "Grabs obvious material and checks."),
    Difficulty(id: 3, label: "Club", description: "Short search with occasional inaccuracies."),
    Difficulty(id: 4, label: "Advanced", description: "Deeper tactics with fewer mistakes."),
    Difficulty(id: 5, label: "Expert", description: "Strong built-in search."),
    Difficulty(id: 6, label: "Engine 1", description: "Entry-level Stockfish when available."),
    Difficulty(id: 7, label: "Engine 2", description: "Faster, sharper engine play."),
    Difficulty(id: 8, label: "Engine 3", description: "Stronger Stockfish settings."),
    Difficulty(id: 9, label: "Engine 4", description: "High-strength engine play."),
    Difficulty(id: 10, label: "Master", description: "The strongest configured engine level."),
]

struct NewGameView: View {
    let onCreate: (CreateGameRequest) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var mode = "local"
    @State private var selectedDifficulty = difficulties[2]   // Club default
    @State private var color = "white"
    @State private var isCreating = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Mode") {
                    Picker("Game mode", selection: $mode) {
                        Text("Local (hotseat)").tag("local")
                        Text("vs AI").tag("ai")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityLabel("Game mode")
                }

                if mode == "ai" {
                    Section {
                        ForEach(difficulties) { diff in
                            DifficultyRow(
                                difficulty: diff,
                                isSelected: selectedDifficulty.id == diff.id,
                                onSelect: { selectedDifficulty = diff }
                            )
                        }
                    } header: {
                        Text("Difficulty")
                    } footer: {
                        Text("Higher engine levels use Stockfish when the server has it, otherwise the strongest built-in search is used.")
                    }

                    Section("Play as") {
                        Picker("Color", selection: $color) {
                            Text("White").tag("white")
                            Text("Black").tag("black")
                        }
                        .pickerStyle(.segmented)
                        .accessibilityLabel("Play as color")
                    }
                }
            }
            .navigationTitle("New Game")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Start") {
                        isCreating = true
                        Task {
                            await onCreate(CreateGameRequest(
                                mode: mode,
                                difficulty: "level",
                                level: selectedDifficulty.id,
                                color: color
                            ))
                            dismiss()
                        }
                    }
                    .disabled(isCreating)
                }
            }
        }
    }
}

private struct DifficultyRow: View {
    let difficulty: Difficulty
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
                    .font(.title3)
                    .padding(.top, 2)

                VStack(alignment: .leading, spacing: 2) {
                    HStack {
                        Text(difficulty.label)
                            .font(.body)
                            .foregroundStyle(.primary)
                        if difficulty.id >= 6 {
                            Image(systemName: "cpu")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Text(difficulty.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(difficulty.label): \(difficulty.description)")
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
    }
}
