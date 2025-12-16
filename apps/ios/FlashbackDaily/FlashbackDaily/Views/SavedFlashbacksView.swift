import SwiftUI

struct SavedFlashbacksView: View {
    @EnvironmentObject var store: FlashbackStore
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()

                if store.savedFlashbacks.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "bookmark")
                            .font(.system(size: 48))
                            .foregroundColor(.gray)

                        Text("No saved flashbacks")
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(.gray)

                        Text("Tap the bookmark icon on any flashback to save it here")
                            .font(.system(size: 14))
                            .foregroundColor(.gray.opacity(0.7))
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 40)
                    }
                } else {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(store.savedFlashbacks) { flashback in
                                SavedFlashbackCard(flashback: flashback)
                                    .onTapGesture {
                                        store.currentFlashback = flashback
                                        dismiss()
                                    }
                            }
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Saved")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(.white)
                }
            }
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }
}

struct SavedFlashbackCard: View {
    let flashback: FlashbackScene

    var body: some View {
        HStack(spacing: 16) {
            // Thumbnail
            ZStack {
                if let lens = flashback.lenses.first,
                   let urlString = lens.imageUrl,
                   let url = URL(string: urlString) {
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Color.gray.opacity(0.3)
                    }
                } else {
                    Color.gray.opacity(0.3)
                    Image(systemName: "photo")
                        .foregroundColor(.gray)
                }
            }
            .frame(width: 80, height: 60)
            .cornerRadius(8)
            .clipped()

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(flashback.title)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)
                    .lineLimit(2)

                HStack {
                    if let year = flashback.year {
                        Text(String(year))
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.gray)
                    }

                    Text(formatDate(flashback.date))
                        .font(.system(size: 12))
                        .foregroundColor(.gray)
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundColor(.gray)
                .font(.system(size: 14))
        }
        .padding()
        .background(Color.white.opacity(0.1))
        .cornerRadius(12)
    }

    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: dateString) else { return dateString }
        formatter.dateFormat = "MMM d"
        return formatter.string(from: date)
    }
}

#Preview {
    SavedFlashbacksView()
        .environmentObject(FlashbackStore())
}
