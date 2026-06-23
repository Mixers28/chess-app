import ChessCore

/// Converts any thrown error into a short human-readable string for alert display.
/// Prefers APIError's own LocalizedError description; falls back to the system description.
func friendlyMessage(_ error: Error) -> String {
    if let api = error as? APIError, let desc = api.errorDescription {
        return desc
    }
    return error.localizedDescription
}
