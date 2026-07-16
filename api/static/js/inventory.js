let collectionCardId = null;

async function updateCollection(cardId, action) {
    try {
        const response = await fetch(`/inventory/${action}/${cardId}`, { method: "POST" });
        const data = await response.json();
        if (!data.success) {
            return;
        }

        const countElement = document.getElementById(`count-${cardId}`);
        if (countElement) {
            countElement.innerText = data.count;
        } else {
            window.location.reload();
        }
    } catch (err) {
        console.error("Collection update failed:", err);
    }
}

function openCollectionForm(cardId, cardName) {
    collectionCardId = cardId;
    document.getElementById("collection-card-name").innerText = cardName;
    document.getElementById("collection-form-error").innerText = "";
    document.getElementById("collection-form").reset();
    document.querySelector('#collection-form [name="quantity"]').value = 1;
    document.getElementById("collection-modal").style.display = "block";
}

function closeCollectionForm() {
    document.getElementById("collection-modal").style.display = "none";
    collectionCardId = null;
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("collection-form");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        const response = await fetch(`/collection/items/${collectionCardId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            document.getElementById("collection-form-error").innerText = payload.error || "Unable to add this card.";
            return;
        }
        closeCollectionForm();
        window.location.reload();
    });
});
