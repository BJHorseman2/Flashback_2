import SwiftUI

struct FlashbackView: View {
    @EnvironmentObject var store: FlashbackStore
    let flashback: FlashbackScene

    @State private var selectedLensIndex = 0
    @State private var showSources = false
    @State private var showShareSheet = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 0) {
                // Header with back button
                HStack {
                    Button(action: { store.clearCurrent() }) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(.white)
                    }

                    Spacer()

                    Button(action: { store.saveCurrentFlashback() }) {
                        Image(systemName: "bookmark")
                            .font(.system(size: 20))
                            .foregroundColor(.white)
                    }
                }
                .padding()

                ScrollView {
                    VStack(spacing: 24) {
                        // Date display
                        Text(formatDateDisplay(flashback.date))
                            .font(.system(size: 14, weight: .medium, design: .monospaced))
                            .foregroundColor(.gray)
                            .tracking(2)

                        // Hero image with lens swiper
                        TabView(selection: $selectedLensIndex) {
                            ForEach(Array(flashback.lenses.enumerated()), id: \.element.id) { index, lens in
                                LensImageView(lens: lens)
                                    .tag(index)
                            }
                        }
                        .tabViewStyle(.page(indexDisplayMode: .never))
                        .frame(height: 300)
                        .cornerRadius(16)

                        // Lens indicator pills
                        LensIndicator(
                            lenses: flashback.lenses,
                            selectedIndex: $selectedLensIndex
                        )

                        // Title
                        Text(flashback.title)
                            .font(.system(size: 28, weight: .bold, design: .serif))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal)

                        // Year badge
                        if let year = flashback.year {
                            Text(String(year))
                                .font(.system(size: 16, weight: .semibold, design: .monospaced))
                                .foregroundColor(.black)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 6)
                                .background(Color.white)
                                .cornerRadius(20)
                        }

                        // Summary
                        Text(flashback.summary)
                            .font(.system(size: 16, weight: .regular))
                            .foregroundColor(.white.opacity(0.9))
                            .lineSpacing(6)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 24)

                        // AI Recreation disclosure
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 12))
                            Text(flashback.disclosure)
                                .font(.system(size: 12, weight: .medium))
                        }
                        .foregroundColor(.gray)
                        .padding(.top, 8)

                        // Action buttons
                        HStack(spacing: 16) {
                            Button(action: { showSources = true }) {
                                HStack {
                                    Image(systemName: "link")
                                    Text("Sources")
                                }
                                .foregroundColor(.white)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 12)
                                .background(Color.white.opacity(0.15))
                                .cornerRadius(25)
                            }

                            Button(action: { showShareSheet = true }) {
                                HStack {
                                    Image(systemName: "square.and.arrow.up")
                                    Text("Share")
                                }
                                .foregroundColor(.black)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 12)
                                .background(Color.white)
                                .cornerRadius(25)
                            }
                        }
                        .padding(.top, 16)

                        Spacer(minLength: 40)
                    }
                }
            }
        }
        .sheet(isPresented: $showSources) {
            SourcesSheet(sources: flashback.sources)
        }
        .sheet(isPresented: $showShareSheet) {
            ShareComposerView(flashback: flashback, selectedLensIndex: selectedLensIndex)
        }
    }

    private func formatDateDisplay(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: dateString) else { return dateString }

        formatter.dateFormat = "MMMM d"
        return formatter.string(from: date).uppercased()
    }
}

struct LensImageView: View {
    let lens: Lens

    var body: some View {
        ZStack {
            if let urlString = lens.imageUrl, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    case .failure:
                        PlaceholderImage(lensName: lens.displayName)
                    @unknown default:
                        PlaceholderImage(lensName: lens.displayName)
                    }
                }
            } else {
                PlaceholderImage(lensName: lens.displayName)
            }
        }
        .clipped()
    }
}

struct PlaceholderImage: View {
    let lensName: String

    var body: some View {
        ZStack {
            Color.gray.opacity(0.3)
            VStack {
                Image(systemName: "photo")
                    .font(.system(size: 40))
                    .foregroundColor(.gray)
                Text(lensName)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
        }
    }
}

struct LensIndicator: View {
    let lenses: [Lens]
    @Binding var selectedIndex: Int

    var body: some View {
        HStack(spacing: 8) {
            ForEach(Array(lenses.enumerated()), id: \.element.id) { index, lens in
                Button(action: {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        selectedIndex = index
                    }
                }) {
                    Text(lens.displayName)
                        .font(.system(size: 12, weight: index == selectedIndex ? .bold : .regular))
                        .foregroundColor(index == selectedIndex ? .black : .white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(index == selectedIndex ? Color.white : Color.white.opacity(0.2))
                        .cornerRadius(16)
                }
            }
        }
    }
}

struct SourcesSheet: View {
    let sources: [Source]
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            List(sources) { source in
                Link(destination: URL(string: source.url)!) {
                    HStack {
                        Text(source.label)
                            .foregroundColor(.primary)
                        Spacer()
                        Image(systemName: "arrow.up.right")
                            .foregroundColor(.blue)
                    }
                }
            }
            .navigationTitle("Sources")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    FlashbackView(flashback: FlashbackScene(
        sceneId: "test",
        date: "2024-07-20",
        title: "Apollo 11 Moon Landing",
        year: 1969,
        summary: "NASA's Apollo 11 mission successfully landed the first humans on the Moon. Astronauts Neil Armstrong and Buzz Aldrin walked on the lunar surface while Michael Collins orbited above.",
        sources: [
            Source(label: "Wikipedia", url: "https://en.wikipedia.org/wiki/Apollo_11")
        ],
        lenses: [
            Lens(lensId: 1, name: "Wide", imageUrl: nil),
            Lens(lensId: 2, name: "POV", imageUrl: nil),
            Lens(lensId: 3, name: "Detail", imageUrl: nil),
            Lens(lensId: 4, name: "Behind", imageUrl: nil),
            Lens(lensId: 5, name: "After", imageUrl: nil)
        ],
        disclosure: "AI Recreation"
    ))
    .environmentObject(FlashbackStore())
}
