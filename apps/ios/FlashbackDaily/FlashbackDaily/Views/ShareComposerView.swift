import SwiftUI

enum ShareFormat: String, CaseIterable {
    case story = "Story"
    case square = "Square"
    case fivePanel = "5-Panel Strip"

    var size: CGSize {
        switch self {
        case .story: return CGSize(width: 1080, height: 1920)
        case .square: return CGSize(width: 1080, height: 1080)
        case .fivePanel: return CGSize(width: 1080, height: 1920)
        }
    }
}

struct ShareComposerView: View {
    let flashback: FlashbackScene
    let selectedLensIndex: Int

    @State private var shareFormat: ShareFormat = .story
    @State private var showActivitySheet = false
    @State private var shareImage: UIImage?
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()

                VStack(spacing: 24) {
                    // Format selector
                    Picker("Format", selection: $shareFormat) {
                        ForEach(ShareFormat.allCases, id: \.self) { format in
                            Text(format.rawValue).tag(format)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    // Preview
                    ScrollView {
                        Group {
                            switch shareFormat {
                            case .story:
                                StoryShareCard(
                                    flashback: flashback,
                                    lens: flashback.lenses[selectedLensIndex]
                                )
                                .frame(width: 270, height: 480)
                            case .square:
                                SquareShareCard(
                                    flashback: flashback,
                                    lens: flashback.lenses[selectedLensIndex]
                                )
                                .frame(width: 300, height: 300)
                            case .fivePanel:
                                FivePanelShareCard(flashback: flashback)
                                    .frame(width: 270, height: 480)
                            }
                        }
                        .cornerRadius(12)
                        .shadow(radius: 10)
                    }

                    // Share button
                    Button(action: generateAndShare) {
                        HStack {
                            Image(systemName: "square.and.arrow.up")
                            Text("Share")
                        }
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.white)
                        .cornerRadius(12)
                    }
                    .padding(.horizontal)
                    .padding(.bottom)
                }
            }
            .navigationTitle("Share")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { dismiss() }
                        .foregroundColor(.white)
                }
            }
        }
        .sheet(isPresented: $showActivitySheet) {
            if let image = shareImage {
                ActivityView(activityItems: [image])
            }
        }
    }

    @MainActor
    private func generateAndShare() {
        let renderer: UIGraphicsImageRenderer

        switch shareFormat {
        case .story:
            renderer = UIGraphicsImageRenderer(size: CGSize(width: 1080, height: 1920))
            let view = StoryShareCard(flashback: flashback, lens: flashback.lenses[selectedLensIndex])
                .frame(width: 1080, height: 1920)
            shareImage = renderer.image { _ in
                let controller = UIHostingController(rootView: view)
                controller.view.bounds = CGRect(origin: .zero, size: CGSize(width: 1080, height: 1920))
                controller.view.drawHierarchy(in: controller.view.bounds, afterScreenUpdates: true)
            }
        case .square:
            renderer = UIGraphicsImageRenderer(size: CGSize(width: 1080, height: 1080))
            let view = SquareShareCard(flashback: flashback, lens: flashback.lenses[selectedLensIndex])
                .frame(width: 1080, height: 1080)
            shareImage = renderer.image { _ in
                let controller = UIHostingController(rootView: view)
                controller.view.bounds = CGRect(origin: .zero, size: CGSize(width: 1080, height: 1080))
                controller.view.drawHierarchy(in: controller.view.bounds, afterScreenUpdates: true)
            }
        case .fivePanel:
            renderer = UIGraphicsImageRenderer(size: CGSize(width: 1080, height: 1920))
            let view = FivePanelShareCard(flashback: flashback)
                .frame(width: 1080, height: 1920)
            shareImage = renderer.image { _ in
                let controller = UIHostingController(rootView: view)
                controller.view.bounds = CGRect(origin: .zero, size: CGSize(width: 1080, height: 1920))
                controller.view.drawHierarchy(in: controller.view.bounds, afterScreenUpdates: true)
            }
        }

        showActivitySheet = true
    }
}

struct StoryShareCard: View {
    let flashback: FlashbackScene
    let lens: Lens

    var body: some View {
        GeometryReader { geo in
            ZStack {
                Color.black

                VStack(spacing: 0) {
                    // Image area (60% of height)
                    ZStack {
                        if let urlString = lens.imageUrl, let url = URL(string: urlString) {
                            AsyncImage(url: url) { image in
                                image
                                    .resizable()
                                    .aspectRatio(contentMode: .fill)
                            } placeholder: {
                                Color.gray.opacity(0.3)
                            }
                        } else {
                            Color.gray.opacity(0.3)
                        }
                    }
                    .frame(height: geo.size.height * 0.6)
                    .clipped()

                    // Content area
                    VStack(spacing: 12) {
                        Spacer()

                        // Date
                        Text(formatDate(flashback.date))
                            .font(.system(size: geo.size.width * 0.03, weight: .medium, design: .monospaced))
                            .foregroundColor(.gray)

                        // Title
                        Text(flashback.title)
                            .font(.system(size: geo.size.width * 0.06, weight: .bold, design: .serif))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)
                            .lineLimit(3)
                            .padding(.horizontal)

                        // Year
                        if let year = flashback.year {
                            Text(String(year))
                                .font(.system(size: geo.size.width * 0.04, weight: .semibold))
                                .foregroundColor(.white)
                        }

                        Spacer()

                        // Footer
                        HStack {
                            Text(flashback.disclosure)
                                .font(.system(size: geo.size.width * 0.025))
                                .foregroundColor(.gray)

                            Spacer()

                            Text("FLASHBACK DAILY")
                                .font(.system(size: geo.size.width * 0.025, weight: .bold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal)
                        .padding(.bottom, geo.size.height * 0.02)
                    }
                    .frame(height: geo.size.height * 0.4)
                }
            }
        }
    }

    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: dateString) else { return dateString }
        formatter.dateFormat = "MMMM d"
        return formatter.string(from: date).uppercased()
    }
}

struct SquareShareCard: View {
    let flashback: FlashbackScene
    let lens: Lens

    var body: some View {
        GeometryReader { geo in
            ZStack {
                // Background image
                if let urlString = lens.imageUrl, let url = URL(string: urlString) {
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Color.gray.opacity(0.3)
                    }
                } else {
                    Color.gray.opacity(0.3)
                }

                // Gradient overlay
                LinearGradient(
                    colors: [.clear, .black.opacity(0.8)],
                    startPoint: .top,
                    endPoint: .bottom
                )

                // Content
                VStack {
                    Spacer()

                    VStack(spacing: 8) {
                        if let year = flashback.year {
                            Text(String(year))
                                .font(.system(size: geo.size.width * 0.05, weight: .bold))
                                .foregroundColor(.white)
                        }

                        Text(flashback.title)
                            .font(.system(size: geo.size.width * 0.06, weight: .bold, design: .serif))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)
                            .lineLimit(2)
                    }
                    .padding()

                    // Footer
                    HStack {
                        Text(flashback.disclosure)
                            .font(.system(size: geo.size.width * 0.03))
                        Spacer()
                        Text("FLASHBACK DAILY")
                            .font(.system(size: geo.size.width * 0.03, weight: .bold))
                    }
                    .foregroundColor(.white.opacity(0.7))
                    .padding(.horizontal)
                    .padding(.bottom)
                }
            }
        }
        .clipped()
    }
}

struct FivePanelShareCard: View {
    let flashback: FlashbackScene

    var body: some View {
        GeometryReader { geo in
            ZStack {
                Color.black

                VStack(spacing: 4) {
                    // Header
                    VStack(spacing: 4) {
                        Text(formatDate(flashback.date))
                            .font(.system(size: geo.size.width * 0.03, weight: .medium, design: .monospaced))
                            .foregroundColor(.gray)

                        Text(flashback.title)
                            .font(.system(size: geo.size.width * 0.045, weight: .bold, design: .serif))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)
                            .lineLimit(2)
                    }
                    .padding(.vertical, 8)

                    // 5 panels in a grid
                    LazyVGrid(columns: [
                        GridItem(.flexible(), spacing: 4),
                        GridItem(.flexible(), spacing: 4)
                    ], spacing: 4) {
                        ForEach(Array(flashback.lenses.prefix(4).enumerated()), id: \.element.id) { index, lens in
                            PanelView(lens: lens, size: geo.size.width * 0.48)
                        }
                    }

                    // Fifth panel (wider)
                    if flashback.lenses.count >= 5 {
                        PanelView(lens: flashback.lenses[4], size: geo.size.width * 0.98)
                            .frame(height: geo.size.height * 0.18)
                    }

                    // Footer
                    HStack {
                        Text(flashback.disclosure)
                            .font(.system(size: geo.size.width * 0.025))
                            .foregroundColor(.gray)

                        Spacer()

                        Text("FLASHBACK DAILY")
                            .font(.system(size: geo.size.width * 0.025, weight: .bold))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 8)
                    .padding(.bottom, 8)
                }
                .padding(4)
            }
        }
    }

    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: dateString) else { return dateString }
        formatter.dateFormat = "MMMM d, yyyy"
        return formatter.string(from: date)
    }
}

struct PanelView: View {
    let lens: Lens
    let size: CGFloat

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            if let urlString = lens.imageUrl, let url = URL(string: urlString) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    Color.gray.opacity(0.3)
                }
            } else {
                Color.gray.opacity(0.3)
            }

            // Lens label
            Text(lens.displayName)
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.black.opacity(0.6))
                .cornerRadius(4)
                .padding(4)
        }
        .frame(width: size, height: size * 0.7)
        .clipped()
        .cornerRadius(4)
    }
}

struct ActivityView: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

#Preview {
    ShareComposerView(
        flashback: FlashbackScene(
            sceneId: "test",
            date: "1969-07-20",
            title: "Apollo 11 Moon Landing",
            year: 1969,
            summary: "NASA's Apollo 11 mission successfully landed the first humans on the Moon.",
            sources: [],
            lenses: [
                Lens(lensId: 1, name: "Wide", imageUrl: nil),
                Lens(lensId: 2, name: "POV", imageUrl: nil),
                Lens(lensId: 3, name: "Detail", imageUrl: nil),
                Lens(lensId: 4, name: "Behind", imageUrl: nil),
                Lens(lensId: 5, name: "After", imageUrl: nil)
            ],
            disclosure: "AI Recreation"
        ),
        selectedLensIndex: 0
    )
}
