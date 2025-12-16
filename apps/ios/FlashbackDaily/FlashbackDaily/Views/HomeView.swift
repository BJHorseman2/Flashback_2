import SwiftUI

struct HomeView: View {
    @EnvironmentObject var store: FlashbackStore
    @State private var selectedDate = Date()
    @State private var showDatePicker = false
    @State private var birthdayDate: Date?

    var body: some View {
        ZStack {
            // Background
            Color.black.ignoresSafeArea()

            VStack(spacing: 40) {
                Spacer()

                // Logo/Title
                VStack(spacing: 8) {
                    Text("FLASHBACK")
                        .font(.system(size: 42, weight: .bold, design: .serif))
                        .foregroundColor(.white)
                        .tracking(4)

                    Text("DAILY")
                        .font(.system(size: 18, weight: .medium, design: .default))
                        .foregroundColor(.gray)
                        .tracking(8)
                }

                // Date display
                if showDatePicker {
                    DatePicker(
                        "Select Date",
                        selection: $selectedDate,
                        in: ...Date(),
                        displayedComponents: .date
                    )
                    .datePickerStyle(.wheel)
                    .labelsHidden()
                    .colorScheme(.dark)
                    .padding()
                    .background(Color.gray.opacity(0.2))
                    .cornerRadius(16)

                    Button("Done") {
                        withAnimation {
                            showDatePicker = false
                        }
                    }
                    .foregroundColor(.white)
                    .padding(.top, 8)
                }

                Spacer()

                // Action buttons
                VStack(spacing: 16) {
                    // Today button
                    ActionButton(
                        title: "Today",
                        subtitle: formattedToday,
                        icon: "calendar"
                    ) {
                        Task {
                            await store.fetchToday()
                        }
                    }

                    // Pick a Date button
                    ActionButton(
                        title: "Pick a Date",
                        subtitle: showDatePicker ? formattedSelectedDate : "Choose any date",
                        icon: "calendar.badge.clock"
                    ) {
                        if showDatePicker {
                            Task {
                                await store.fetchFlashback(for: selectedDate)
                            }
                        } else {
                            withAnimation {
                                showDatePicker = true
                            }
                        }
                    }

                    // Random button
                    ActionButton(
                        title: "Random",
                        subtitle: "Surprise me",
                        icon: "shuffle"
                    ) {
                        Task {
                            await store.fetchRandom()
                        }
                    }

                    // My Birthday button
                    ActionButton(
                        title: "My Birthday",
                        subtitle: birthdayDate.map { formattedDate($0) } ?? "Set your birthday",
                        icon: "gift"
                    ) {
                        if let birthday = birthdayDate {
                            Task {
                                await store.fetchFlashback(for: birthday)
                            }
                        } else {
                            // Show birthday picker
                            showDatePicker = true
                        }
                    }
                }
                .padding(.horizontal, 24)

                Spacer()

                // Loading indicator
                if store.isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                }

                // Error message
                if let error = store.error {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                        .padding()
                }

                Spacer()
            }
        }
        .onAppear {
            store.loadFromDisk()
        }
    }

    private var formattedToday: String {
        formattedDate(Date())
    }

    private var formattedSelectedDate: String {
        formattedDate(selectedDate)
    }

    private func formattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM d"
        return formatter.string(from: date)
    }
}

struct ActionButton: View {
    let title: String
    let subtitle: String
    let icon: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .frame(width: 30)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 18, weight: .semibold))
                    Text(subtitle)
                        .font(.system(size: 12))
                        .foregroundColor(.gray)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14))
                    .foregroundColor(.gray)
            }
            .foregroundColor(.white)
            .padding()
            .background(Color.white.opacity(0.1))
            .cornerRadius(12)
        }
    }
}

#Preview {
    HomeView()
        .environmentObject(FlashbackStore())
}
