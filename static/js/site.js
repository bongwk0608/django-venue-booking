document.addEventListener("DOMContentLoaded", () => {
    const bookingForm = document.querySelector(".booking-form");
    if (!bookingForm) {
        return;
    }

    const minDate = bookingForm.dataset.minDate;
    const dateInput = bookingForm.querySelector('input[type="date"]');
    if (dateInput && minDate) {
        dateInput.min = minDate;
    }

    if (dateInput) {
        dateInput.addEventListener("change", () => {
            const nextUrl = new URL(window.location.href);
            nextUrl.searchParams.set("date", dateInput.value);
            window.location.href = nextUrl.toString();
        });
    }

    const startInput = bookingForm.querySelector('input[name="start_time"]');
    const endInput = bookingForm.querySelector('input[name="end_time"]');
    const slotButtons = bookingForm.querySelectorAll(".slot-choice:not(:disabled)");

    slotButtons.forEach((button) => {
        button.addEventListener("click", () => {
            if (startInput) {
                startInput.value = button.dataset.start;
            }
            if (endInput) {
                endInput.value = button.dataset.end;
            }

            slotButtons.forEach((slotButton) => slotButton.classList.remove("is-selected"));
            button.classList.add("is-selected");
        });
    });
});
