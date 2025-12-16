import Foundation

enum APIError: Error, LocalizedError {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .serverError(let message):
            return message
        }
    }
}

class APIService {
    private let baseURL: String
    private let session: URLSession

    init(baseURL: String = "http://localhost:8000") {
        self.baseURL = baseURL

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 60
        config.timeoutIntervalForResource = 120
        self.session = URLSession(configuration: config)
    }

    func getFlashback(date: String, lang: String = "en") async throws -> FlashbackResponse {
        guard let url = URL(string: "\(baseURL)/v1/flashback?date=\(date)&lang=\(lang)") else {
            throw APIError.invalidURL
        }

        return try await fetch(url)
    }

    func getTodayFlashback(lang: String = "en") async throws -> FlashbackResponse {
        guard let url = URL(string: "\(baseURL)/v1/flashback/today?lang=\(lang)") else {
            throw APIError.invalidURL
        }

        return try await fetch(url)
    }

    func getRandomFlashback(lang: String = "en") async throws -> FlashbackResponse {
        guard let url = URL(string: "\(baseURL)/v1/flashback/random?lang=\(lang)") else {
            throw APIError.invalidURL
        }

        return try await fetch(url)
    }

    private func fetch<T: Decodable>(_ url: URL) async throws -> T {
        do {
            let (data, response) = try await session.data(from: url)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.serverError("Invalid response")
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                throw APIError.serverError("Server returned \(httpResponse.statusCode)")
            }

            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch let error as APIError {
            throw error
        } catch let error as DecodingError {
            throw APIError.decodingError(error)
        } catch {
            throw APIError.networkError(error)
        }
    }
}
