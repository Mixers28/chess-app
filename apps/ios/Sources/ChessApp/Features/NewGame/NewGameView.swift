import SwiftUI
import ChessCore

private struct Difficulty: Identifiable {
    let id: String
    let label: String
    let description: String
    let requiresEngine: Bool
}

private let difficulties: [Difficulty] = [
    Difficulty(id: "random",    label: "Random",    description: "Plays any legal move at random.",              requiresEngine: false),
    Difficulty(id: "heuristic", label: "Heuristic", description: "Prefers captures and checks. Decent warm-up.", requiresEngine: false),
    Difficulty(id: "search",    label: "Search",    description: "Shallow alpha-beta search. Actually thinks.",  requiresEngine: false),
    Difficulty(id: "stockfish", label: "Stockfish", description: "Full engine — requires server support.",       requiresEngine: true),
]

struct NewGameView: View {
    let onCreate: (CreateGameRequest) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var mode = "local"
    @State private var selectedDifficulty = difficulties[1]   // heuristic default
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
                        if selectedDifficulty.requiresEngine {
                            Label("Stockfish must be installed on the server.", systemImage: "exclamationmark.triangle")
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
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
                                difficulty: selectedDifficulty.id,
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
                        if difficulty.requiresEngine {
                            Image(systemName: "cpu")
                                .font(.caption)
                                .foregroundStyle(.orange)
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
