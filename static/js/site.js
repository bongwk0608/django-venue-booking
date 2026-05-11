document.addEventListener("DOMContentLoaded", () => {
    const availabilityDateForm = document.querySelector(".availability-date-form");
    if (availabilityDateForm) {
        const availabilityDateInput = availabilityDateForm.querySelector('input[type="date"]');
        if (availabilityDateInput) {
            availabilityDateInput.addEventListener("change", () => {
                availabilityDateForm.submit();
            });
        }
    }

    const bookingForm = document.querySelector(".booking-form");
    if (!bookingForm) {
        return;
    }

    const minDate = bookingForm.dataset.minDate;
    const dateInput = bookingForm.querySelector('input[name="booking_date"]');
    if (dateInput && minDate) {
        dateInput.min = minDate;
    }

    const startInput = bookingForm.querySelector('input[name="start_time"]');
    const endInput = bookingForm.querySelector('input[name="end_time"]');
    const slotButtons = bookingForm.querySelectorAll(".slot-choice:not(:disabled)");
    const selectedSummary = bookingForm.querySelector(".selected-slot-summary");
    let selectedStartIndex = null;
    let selectedEndIndex = null;

    const clearSlotSelection = () => {
        slotButtons.forEach((slotButton) => {
            slotButton.classList.remove("is-selected", "is-in-range");
        });
    };

    const findSlotByIndex = (index) => {
        return Array.from(slotButtons).find((slotButton) => Number(slotButton.dataset.index) === index);
    };

    const hasCompleteAvailableRange = (startIndex, endIndex) => {
        for (let index = startIndex; index <= endIndex; index += 1) {
            if (!findSlotByIndex(index)) {
                return false;
            }
        }
        return true;
    };

    const applySlotSelection = (startIndex, endIndex) => {
        clearSlotSelection();

        const firstSlot = findSlotByIndex(startIndex);
        const lastSlot = findSlotByIndex(endIndex);
        if (!firstSlot || !lastSlot) {
            return;
        }

        slotButtons.forEach((slotButton) => {
            const slotIndex = Number(slotButton.dataset.index);
            if (slotIndex >= startIndex && slotIndex <= endIndex) {
                slotButton.classList.add("is-in-range");
            }
        });
        firstSlot.classList.add("is-selected");
        lastSlot.classList.add("is-selected");

        if (startInput) {
            startInput.value = firstSlot.dataset.start;
        }
        if (endInput) {
            endInput.value = lastSlot.dataset.end;
        }
        if (selectedSummary) {
            selectedSummary.textContent = `Selected: ${firstSlot.dataset.start} - ${lastSlot.dataset.end}`;
            selectedSummary.classList.add("has-selection");
        }
    };

    slotButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const clickedIndex = Number(button.dataset.index);

            if (selectedStartIndex === null || selectedEndIndex !== null) {
                selectedStartIndex = clickedIndex;
                selectedEndIndex = null;
                applySlotSelection(clickedIndex, clickedIndex);
                return;
            }

            const rangeStart = Math.min(selectedStartIndex, clickedIndex);
            const rangeEnd = Math.max(selectedStartIndex, clickedIndex);

            if (!hasCompleteAvailableRange(rangeStart, rangeEnd)) {
                selectedStartIndex = clickedIndex;
                selectedEndIndex = null;
                applySlotSelection(clickedIndex, clickedIndex);
                return;
            }

            selectedStartIndex = rangeStart;
            selectedEndIndex = rangeEnd;
            applySlotSelection(rangeStart, rangeEnd);
        });
    });
});
