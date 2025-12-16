import Foundation

struct FlashbackResponse: Codable {
    let status: String
    let scene: FlashbackScene?
    let message: String?
    let retryAfter: Int?

    enum CodingKeys: String, CodingKey {
        case status, scene, message
        case retryAfter = "retry_after"
    }
}

struct FlashbackScene: Codable, Identifiable {
    let sceneId: String
    let date: String
    let title: String
    let year: Int?
    let summary: String
    let sources: [Source]
    let lenses: [Lens]
    let disclosure: String

    var id: String { sceneId }

    enum CodingKeys: String, CodingKey {
        case sceneId = "scene_id"
        case date, title, year, summary, sources, lenses, disclosure
    }
}

struct Source: Codable, Identifiable {
    let label: String
    let url: String

    var id: String { label }
}

struct Lens: Codable, Identifiable {
    let lensId: Int
    let name: String
    let imageUrl: String?

    var id: Int { lensId }

    enum CodingKeys: String, CodingKey {
        case lensId = "lens_id"
        case name
        case imageUrl = "image_url"
    }
}

extension Lens {
    static let lensNames = ["Wide", "POV", "Detail", "Behind", "After"]

    var displayName: String {
        switch lensId {
        case 1: return "Wide"
        case 2: return "POV"
        case 3: return "Detail"
        case 4: return "Behind"
        case 5: return "After"
        default: return name
        }
    }

    var description: String {
        switch lensId {
        case 1: return "Establishing Shot"
        case 2: return "Witness Perspective"
        case 3: return "Key Detail"
        case 4: return "Behind the Scenes"
        case 5: return "Aftermath"
        default: return ""
        }
    }
}
