let wishlistCardId = null;

function closeWishlist() { document.getElementById("wishlist-modal").style.display = "none"; }

async function openWishlist(button) {
    wishlistCardId = button.dataset.cardId;
    const variantId = button.dataset.variantId || "";
    const form = document.getElementById("wishlist-form");
    form.reset();
    document.getElementById("wishlist-card-name").textContent = button.dataset.cardName;
    document.getElementById("wishlist-variant-id").value = variantId;
    document.getElementById("wishlist-variant-name").textContent = button.dataset.variantName ? `Variant: ${button.dataset.variantName}` : "Card wishlist item";
    document.getElementById("wishlist-error").textContent = "";
    const items = (await (await fetch(`/wishlist/items/card/${wishlistCardId}`)).json()).items || [];
    const existing = items.find(item => (item.source_variant_id || "") === variantId);
    if (existing) {
        form.priority.value = existing.priority;
        form.desired_condition.value = existing.desired_condition || "";
        form.target_price.value = existing.target_price ?? "";
        form.notes.value = existing.notes || "";
    }
    document.getElementById("wishlist-modal").style.display = "block";
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("wishlist-form");
    if (!form) return;
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-wishlist-action]");
        if (!button) return;
        const action = button.dataset.wishlistAction;
        if (action === "open") await openWishlist(button);
        if (action === "close") closeWishlist();
        if (action === "delete" && confirm("Remove this wishlist item?")) {
            await fetch(`/wishlist/items/${button.dataset.wishlistId}`, {method: "DELETE"});
            location.reload();
        }
    });
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeWishlist(); });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        data.source_variant_id = document.getElementById("wishlist-variant-id").value;
        const response = await fetch(`/wishlist/items/${wishlistCardId}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
        if (response.ok) location.reload();
        else document.getElementById("wishlist-error").textContent = (await response.json()).error;
    });
});
