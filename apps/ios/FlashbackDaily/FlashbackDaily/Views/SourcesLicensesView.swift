import SwiftUI

struct SourcesLicensesView: View {
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            List {
                Section {
                    Text("Flashback Daily generates AI recreations of historical events. All images are labeled as AI-generated and should not be considered photographs.")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                }

                Section("Data Sources") {
                    SourceRow(
                        title: "Wikipedia",
                        description: "Event information via On This Day API",
                        url: "https://www.wikipedia.org"
                    )

                    SourceRow(
                        title: "Wikidata",
                        description: "Structured data (CC0)",
                        url: "https://www.wikidata.org"
                    )

                    SourceRow(
                        title: "Wikimedia Pageviews",
                        description: "Event ranking signals",
                        url: "https://pageviews.wmcloud.org"
                    )
                }

                Section("Image Generation") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("AI Recreation")
                            .font(.system(size: 16, weight: .semibold))

                        Text("All images are generated using AI and are editorial illustrations, not photographs. They are created for educational and entertainment purposes.")
                            .font(.system(size: 14))
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)
                }

                Section("Content Guidelines") {
                    BulletPoint("Images avoid identifiable faces")
                    BulletPoint("No graphic violence or gore")
                    BulletPoint("Period-accurate representations")
                    BulletPoint("Sources always visible")
                }

                Section("Wikimedia Reuse") {
                    Link(destination: URL(string: "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use")!) {
                        HStack {
                            Text("Wikimedia Terms of Use")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                        }
                    }

                    Link(destination: URL(string: "https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia")!) {
                        HStack {
                            Text("Content Reuse Guidelines")
                            Spacer()
                            Image(systemName: "arrow.up.right")
                        }
                    }
                }

                Section {
                    Text("Flashback Daily is not affiliated with or endorsed by the Wikimedia Foundation.")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Sources & Licenses")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

struct SourceRow: View {
    let title: String
    let description: String
    let url: String

    var body: some View {
        Link(destination: URL(string: url)!) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(.primary)

                    Text(description)
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()

                Image(systemName: "arrow.up.right")
                    .font(.system(size: 12))
                    .foregroundColor(.blue)
            }
        }
    }
}

struct BulletPoint: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text("•")
                .foregroundColor(.secondary)
            Text(text)
                .font(.system(size: 14))
        }
    }
}

#Preview {
    SourcesLicensesView()
}
