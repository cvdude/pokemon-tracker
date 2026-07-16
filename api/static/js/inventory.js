let collectionCardId = null;
let collectionItemId = null;

const today = () => new Date().toISOString().slice(0, 10);

async function updateCollection(cardId, action) {
    try {
        const response = await fetch(`/inventory/${action}/${cardId}`, { method: "POST" });
        const data = await response.json();
        if (!response.ok || !data.success) return;
        window.location.reload();
    } catch (error) {
        console.error("Collection update failed:", error);
    }
}

function setSelectValue(selectName, otherName, value, fallback) {
    const select = document.querySelector(`[name="${selectName}"]`);
    const other = document.querySelector(`[name="${otherName}"]`);
    if (value && value.startsWith("Other: ")) {
        select.value = "Other";
        other.value = value.slice(7);
    } else {
        select.value = value || fallback;
        other.value = "";
    }
    toggleOtherFields();
}

function toggleOtherFields() {
    for (const field of ["variant", "language"]) {
        const select = document.querySelector(`[name="${field}"]`);
        const other = document.querySelector(`[name="${field}_other"]`);
        const wrapper = document.getElementById(`collection-${field}-other-wrap`);
        const required = select.value === "Other";
        wrapper.classList.toggle("d-none", !required);
        other.required = required;
    }
}

async function openCollectionForm(cardId, cardName) {
    const form = document.getElementById("collection-form");
    collectionCardId = cardId;
    collectionItemId = null;
    form.reset();
    document.getElementById("collection-card-name").innerText = cardName;
    document.getElementById("collection-modal-title").innerText = "Add to Collection";
    document.getElementById("collection-submit").innerText = "Save to Collection";
    document.getElementById("collection-form-error").innerText = "";
    form.quantity.value = 1;
    form.acquisition_date.value = today();
    form.storage_location.value = "Unassigned";
    toggleOtherFields();

    try {
        const response = await fetch(`/collection/items/card/${cardId}`);
        const payload = await response.json();
        const item = payload.items && payload.items[0];
        if (item) {
            collectionItemId = item.id;
            document.getElementById("collection-modal-title").innerText = "Edit Collection Item";
            document.getElementById("collection-submit").innerText = "Save Changes";
            form.quantity.value = item.quantity;
            form.condition.value = item.condition;
            setSelectValue("variant", "variant_other", item.variant, "Normal");
            setSelectValue("language", "language_other", item.language, "English");
            form.storage_location.value = item.storage_location;
            form.acquisition_date.value = item.acquisition_date || today();
            form.purchase_price.value = item.purchase_price ?? "";
            form.notes.value = item.notes || "";
        }
    } catch (error) {
        console.error("Collection item lookup failed:", error);
    }
    document.getElementById("collection-modal").style.display = "block";
}

function closeCollectionForm() {
    document.getElementById("collection-modal").style.display = "none";
    collectionCardId = null;
    collectionItemId = null;
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("collection-form");
    if (!form) return;
    document.querySelector('[name="variant"]').addEventListener("change", toggleOtherFields);
    document.querySelector('[name="language"]').addEventListener("change", toggleOtherFields);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        toggleOtherFields();
        if (!form.reportValidity()) return;
        const response = await fetch(
            collectionItemId ? `/collection/items/${collectionItemId}` : `/collection/items/${collectionCardId}`,
            {
                method: collectionItemId ? "PATCH" : "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(Object.fromEntries(new FormData(form).entries())),
            },
        );
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            document.getElementById("collection-form-error").innerText = payload.error || "Unable to save this collection item.";
            return;
        }
        window.location.reload();
    });
});
