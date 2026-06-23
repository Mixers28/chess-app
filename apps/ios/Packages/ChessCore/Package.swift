// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ChessCore",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "ChessCore", targets: ["ChessCore"]),
    ],
    targets: [
        .target(
            name: "ChessCore",
            path: "Sources/ChessCore"
        ),
        .testTarget(
            name: "ChessCoreTests",
            dependencies: ["ChessCore"],
            path: "Tests/ChessCoreTests"
        ),
    ]
)
