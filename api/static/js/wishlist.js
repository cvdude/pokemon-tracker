let wishlistCardId = null;

async function wishlistRequest(url, options = {}) {
    const response = await fetch(url, options);
    let payload; try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) throw new Error(payload.error || "The request could not be completed. Please try again.");
    return payload;
}

function closeWishlist() { document.getElementById("wishlist-modal").style.display = "none"; }
function wishlistError(message = "") { document.getElementById("wishlist-error").textContent = message; }

async function openWishlist(button) {
    wishlistCardId = button.dataset.cardId;
    const variantId = button.dataset.variantId || "", form = document.getElementById("wishlist-form");
    form.reset(); wishlistError(); document.getElementById("wishlist-card-name").textContent = button.dataset.cardName;
    document.getElementById("wishlist-variant-id").value = variantId;
    document.getElementById("wishlist-variant-name").textContent = button.dataset.variantName ? `Variant: ${button.dataset.variantName}` : "Card wishlist item";
    document.getElementById("wishlist-modal").style.display = "block";
    const items = (await wishlistRequest(`/wishlist/items/card/${wishlistCardId}`)).items || [];
    const existing = items.find(item => (item.source_variant_id || "") === variantId);
    if (existing) { form.priority.value = existing.priority; form.desired_condition.value = existing.desired_condition || ""; form.target_price.value = existing.target_price ?? ""; form.notes.value = existing.notes || ""; }
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("wishlist-form");
    if (!form) return;
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-wishlist-action]"); if (!button) return;
        try {
            if (button.dataset.wishlistAction === "open") await openWishlist(button);
            if (button.dataset.wishlistAction === "close") closeWishlist();
            if (button.dataset.wishlistAction === "delete" && confirm("Remove this wishlist item?")) { await wishlistRequest(`/wishlist/items/${button.dataset.wishlistId}`, {method: "DELETE"}); location.reload(); }
        } catch (error) { wishlistError(error.message); }
    });
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeWishlist(); });
    form.addEventListener("submit", async event => {
        event.preventDefault(); if (!form.reportValidity()) return;
        const submit = form.querySelector('[type="submit"]'); submit.disabled = true; wishlistError();
        try {
            const data = Object.fromEntries(new FormData(form).entries()); data.source_variant_id = document.getElementById("wishlist-variant-id").value;
            await wishlistRequest(`/wishlist/items/${wishlistCardId}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
            location.reload();
        } catch (error) { wishlistError(error.message); submit.disabled = false; }
    });
});
