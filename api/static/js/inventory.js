let collectionCardId = null;
let collectionCardName = null;
let collectionItemId = null;
let collectionItems = [];

const today = () => new Date().toISOString().slice(0, 10);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"})[char]);

async function updateCollection(cardId, action) {
    const response = await fetch(`/inventory/${action}/${cardId}`, { method: "POST" });
    const data = await response.json();
    if (response.ok && data.success) window.location.reload();
}

function toggleOtherFields() {
    for (const field of ["variant", "language"]) {
        const select = document.querySelector(`[name="${field}"]`);
        const other = document.querySelector(`[name="${field}_other"]`);
        const active = select.value === "Other";
        document.getElementById(`collection-${field}-other-wrap`).classList.toggle("d-none", !active);
        other.required = active;
    }
}

function setSelectValue(field, value, fallback) {
    const select = document.querySelector(`[name="${field}"]`);
    const other = document.querySelector(`[name="${field}_other"]`);
    if ((value || "").startsWith("Other: ")) { select.value = "Other"; other.value = value.slice(7); }
    else { select.value = value || fallback; other.value = ""; }
    toggleOtherFields();
}

async function openCollectionForm(cardId, cardName) {
    collectionCardId = cardId;
    collectionCardName = cardName;
    document.getElementById("collection-card-name").innerText = cardName;
    document.getElementById("collection-modal").style.display = "block";
    await showCollectionItems();
}

async function showCollectionItems() {
    const response = await fetch(`/collection/items/card/${collectionCardId}`);
    const payload = await response.json();
    collectionItems = payload.items || [];
    collectionItemId = null;
    document.getElementById("collection-modal-title").innerText = "Manage Collection Copies";
    document.getElementById("collection-fields").classList.add("d-none");
    document.getElementById("collection-management").classList.remove("d-none");
    document.getElementById("collection-submit").classList.add("d-none");
    document.getElementById("collection-back").classList.add("d-none");
    const rows = collectionItems.map((item) => `<div class="border rounded p-2 mb-2"><strong>${escapeHtml(item.quantity)} × ${escapeHtml(item.condition)}</strong><br><small>${escapeHtml(item.variant)} · ${escapeHtml(item.language)} · ${escapeHtml(item.storage_location)}${item.acquisition_date ? ` · ${escapeHtml(item.acquisition_date)}` : ""}</small><div class="mt-2"><button class="btn btn-sm btn-outline-primary me-1" onclick="editCollectionItem(${item.id})">Edit</button><button class="btn btn-sm btn-outline-secondary me-1" onclick="duplicateCollectionItem(${item.id})">Duplicate</button><button class="btn btn-sm btn-outline-danger" onclick="deleteCollectionItem(${item.id})">Delete</button></div></div>`).join("");
    document.getElementById("collection-management").innerHTML = `${rows || '<p class="text-muted">No copies recorded yet.</p>'}<button class="btn btn-success w-100 mt-2" onclick="newCollectionItem()">Add another copy</button>`;
}

function showCollectionEditor(item = null) {
    const form = document.getElementById("collection-form");
    form.reset();
    collectionItemId = item ? item.id : null;
    document.getElementById("collection-modal-title").innerText = item ? "Edit Collection Copy" : "Add to Collection";
    document.getElementById("collection-management").classList.add("d-none");
    document.getElementById("collection-fields").classList.remove("d-none");
    document.getElementById("collection-submit").classList.remove("d-none");
    document.getElementById("collection-back").classList.remove("d-none");
    document.getElementById("collection-form-error").innerText = "";
    form.quantity.value = item?.quantity || 1;
    form.condition.value = item?.condition || "Near Mint";
    setSelectValue("variant", item?.variant, "Normal");
    setSelectValue("language", item?.language, "English");
    form.storage_location.value = item?.storage_location || "Unassigned";
    form.acquisition_date.value = item?.acquisition_date || today();
    form.purchase_price.value = item?.purchase_price ?? "";
    form.notes.value = item?.notes || "";
}

function newCollectionItem() { showCollectionEditor(); }
function editCollectionItem(itemId) { showCollectionEditor(collectionItems.find((item) => item.id === itemId)); }

async function duplicateCollectionItem(itemId) {
    const response = await fetch(`/collection/items/${itemId}/duplicate`, { method: "POST" });
    const payload = await response.json();
    if (!response.ok || !payload.success) { document.getElementById("collection-form-error").innerText = payload.error || "Unable to duplicate this copy."; return; }
    window.location.reload();
}

async function deleteCollectionItem(itemId) {
    if (!window.confirm("Delete this owned copy? This cannot be undone.")) return;
    const response = await fetch(`/collection/items/${itemId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok || !payload.success) { document.getElementById("collection-form-error").innerText = payload.error || "Unable to delete this copy."; return; }
    window.location.reload();
}

function closeCollectionForm() { document.getElementById("collection-modal").style.display = "none"; collectionCardId = null; collectionItemId = null; }

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("collection-form");
    if (!form) return;
    document.querySelector('[name="variant"]').addEventListener("change", toggleOtherFields);
    document.querySelector('[name="language"]').addEventListener("change", toggleOtherFields);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && document.getElementById("collection-modal").style.display === "block") closeCollectionForm(); });
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        toggleOtherFields();
        if (!form.reportValidity()) return;
        const response = await fetch(collectionItemId ? `/collection/items/${collectionItemId}` : `/collection/items/${collectionCardId}`, { method: collectionItemId ? "PATCH" : "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(Object.fromEntries(new FormData(form).entries())) });
        const payload = await response.json();
        if (!response.ok || !payload.success) { document.getElementById("collection-form-error").innerText = payload.error || "Unable to save this collection item."; return; }
        window.location.reload();
    });
});
