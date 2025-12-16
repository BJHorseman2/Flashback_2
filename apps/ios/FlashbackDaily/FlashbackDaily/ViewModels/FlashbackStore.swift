import Foundation
import Combine

@MainActor
class FlashbackStore: ObservableObject {
    @Published var currentFlashback: FlashbackScene?
    @Published var isLoading = false
    @Published var error: String?
    @Published var savedFlashbacks: [FlashbackScene] = []

    private let apiService = APIService()

    func fetchFlashback(for date: Date) async {
        isLoading = true
        error = nil

        let dateString = formatDate(date)

        do {
            let response = try await apiService.getFlashback(date: dateString)

            switch response.status {
            case "ready":
                if let scene = response.scene {
                    currentFlashback = scene
                }
            case "generating":
                // Poll again after retry interval
                if let retryAfter = response.retryAfter {
                    try await Task.sleep(nanoseconds: UInt64(retryAfter * 1_000_000_000))
                    await fetchFlashback(for: date)
                }
            case "failed":
                error = response.message ?? "Failed to generate flashback"
            default:
                error = "Unknown status: \(response.status)"
            }
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func fetchToday() async {
        await fetchFlashback(for: Date())
    }

    func fetchRandom() async {
        isLoading = true
        error = nil

        do {
            let response = try await apiService.getRandomFlashback()
            if let scene = response.scene {
                currentFlashback = scene
            } else if let message = response.message {
                error = message
            }
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func saveCurrentFlashback() {
        guard let flashback = currentFlashback else { return }
        if !savedFlashbacks.contains(where: { $0.sceneId == flashback.sceneId }) {
            savedFlashbacks.append(flashback)
            saveToDisk()
        }
    }

    func clearCurrent() {
        currentFlashback = nil
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private func saveToDisk() {
        if let encoded = try? JSONEncoder().encode(savedFlashbacks) {
            UserDefaults.standard.set(encoded, forKey: "savedFlashbacks")
        }
    }

    func loadFromDisk() {
        if let data = UserDefaults.standard.data(forKey: "savedFlashbacks"),
           let decoded = try? JSONDecoder().decode([FlashbackScene].self, from: data) {
            savedFlashbacks = decoded
        }
    }
}
