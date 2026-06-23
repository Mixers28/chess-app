import Foundation

/// A chess square (0–63), rank-file indexed. File 0 = a, Rank 0 = rank 1.
public struct Square: Hashable, Sendable, Equatable {
    public let index: Int   // 0 = a1, 7 = h1, 56 = a8, 63 = h8

    public var file: Int { index % 8 }
    public var rank: Int { index / 8 }

    public init(_ index: Int) { self.index = index }
    public init(file: Int, rank: Int) { self.index = rank * 8 + file }

    public var name: String {
        let f = "abcdefgh"
        return "\(f[f.index(f.startIndex, offsetBy: file)])\(rank + 1)"
    }
}
