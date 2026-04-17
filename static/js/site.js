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
});
