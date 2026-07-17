let collectionCardId = null, collectionItemId = null, collectionItems = [];

const today = () => new Date().toISOString().slice(0, 10);
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"})[char]);

function toggleOtherFields() {
    ["variant", "language"].forEach(field => {
        const enabled = document.querySelector(`[name="${field}"]`).value === "Other";
        document.getElementById(`collection-${field}-other-wrap`).classList.toggle("d-none", !enabled);
        document.querySelector(`[name="${field}_other"]`).required = enabled;
    });
}

function ownershipFields() {
    const graded = document.querySelector('[name="ownership_type"]').value === "Graded";
    document.getElementById("collection-condition").closest(".col-md-3").classList.toggle("d-none", graded);
    document.getElementById("collection-grading-wrap").classList.toggle("d-none", !graded);
    document.querySelector('[name="grade"]').required = graded;
}

async function loadVariants() {
    const select = document.querySelector('[name="variant"]');
    const response = await fetch(`/collection/variants/${collectionCardId}`);
    const imported = (await response.json()).variants || [];
    const options = imported.length
        ? imported.map(variant => `<option value="${escapeHtml(variant.name)}" data-source-variant-id="${escapeHtml(variant.id)}">${escapeHtml(variant.name)}</option>`)
        : ["Normal", "Holo", "Reverse Holo", "1st Edition", "Shadowless", "Promo"].map(name => `<option>${name}</option>`);
    select.innerHTML = options.join("") + "<option>Other</option>";
}

async function loadCollectionItems(cardId, cardName) {
    collectionCardId = cardId;
    document.getElementById("collection-card-name").textContent = cardName;
    document.getElementById("collection-modal").style.display = "block";
    const response = await fetch(`/collection/items/card/${cardId}`);
    collectionItems = (await response.json()).items || [];
}

async function openCollectionForm(cardId, cardName) {
    await loadCollectionItems(cardId, cardName);
    if (collectionItems.length) showCollectionItems();
    else {
        await loadVariants();
        showEditor();
    }
}

function showCollectionItems() {
    collectionItemId = null;
    document.getElementById("collection-fields").classList.add("d-none");
    document.getElementById("collection-management").classList.remove("d-none");
    document.getElementById("collection-submit").classList.add("d-none");
    document.getElementById("collection-back").classList.add("d-none");
    document.getElementById("collection-management").innerHTML = collectionItems.map(item => `
        <div class="border rounded p-2 mb-2"><strong>${item.quantity} × ${escapeHtml(item.ownership_type || "Raw")} ${escapeHtml(item.variant)}</strong>
        <div><button data-collection-action="edit" data-item-id="${item.id}">Edit</button><button data-collection-action="duplicate" data-item-id="${item.id}">Duplicate</button><button data-collection-action="delete" data-item-id="${item.id}">Delete</button></div></div>`).join("") + "<button data-collection-action=\"new\">Add Another Copy</button>";
}

function showEditor(item = null, focusLocation = false) {
    const form = document.getElementById("collection-form");
    form.reset();
    collectionItemId = item?.id || null;
    document.getElementById("collection-management").classList.add("d-none");
    document.getElementById("collection-fields").classList.remove("d-none");
    document.getElementById("collection-submit").classList.remove("d-none");
    document.getElementById("collection-back").classList.toggle("d-none", !collectionItems.length);
    form.quantity.value = item?.quantity || 1;
    form.acquisition_date.value = item?.acquisition_date || today();
    form.ownership_type.value = item?.ownership_type || "Raw";
    form.condition.value = item?.condition || "Near Mint";
    const variantOption = [...form.variant.options].find(option => option.dataset.sourceVariantId === item?.source_variant_id || option.value === item?.variant);
    form.variant.value = variantOption ? variantOption.value : "Other";
    if (!variantOption && item?.variant) form.variant_other.value = item.variant.replace(/^Other:\s*/, "");
    form.language.value = item?.language || "English";
    form.storage_location.value = item?.storage_location || "Unassigned";
    form.grade.value = item?.grade ?? "";
    form.grading_company.value = item?.grading_company || "PSA";
    form.certification_number.value = item?.certification_number || "";
    form.notes.value = item?.notes || "";
    ownershipFields();
    toggleOtherFields();
    if (focusLocation) document.getElementById("collection-location").focus();
}

async function editCollectionItem(cardId, cardName, itemId, focusLocation = false) {
    await loadCollectionItems(cardId, cardName);
    await loadVariants();
    showEditor(collectionItems.find(item => item.id === itemId), focusLocation);
}

function closeCollectionForm() { document.getElementById("collection-modal").style.display = "none"; }

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("collection-form");
    if (!form) return;
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-collection-action]");
        if (!button) return;
        const action = button.dataset.collectionAction;
        const itemId = Number(button.dataset.itemId);
        if (action === "open") await openCollectionForm(button.dataset.cardId, button.dataset.cardName);
        if (action === "close") closeCollectionForm();
        if (action === "back") showCollectionItems();
        if (action === "new") { await loadVariants(); showEditor(); }
        if (action === "edit") { await loadVariants(); showEditor(collectionItems.find(item => item.id === itemId)); }
        if (action === "edit-item") await editCollectionItem(button.dataset.cardId, button.dataset.cardName, itemId);
        if (action === "move-item") await editCollectionItem(button.dataset.cardId, button.dataset.cardName, itemId, true);
        if (action === "trade-item") {
            await fetch(`/collection/items/${itemId}/trade`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({is_trade: button.dataset.isTrade === "1"})});
            location.reload();
        }
        if ((action === "delete" || action === "delete-item") && confirm("Delete this owned copy?")) {
            await fetch(`/collection/items/${itemId}`, {method: "DELETE"});
            location.reload();
        }
        if (action === "duplicate") { await fetch(`/collection/items/${itemId}/duplicate`, {method: "POST"}); location.reload(); }
        if (action === "remove") { await fetch(`/inventory/remove/${button.dataset.cardId}`, {method: "POST"}); location.reload(); }
    });
    document.querySelector('[name="ownership_type"]').addEventListener("change", ownershipFields);
    document.querySelector('[name="variant"]').addEventListener("change", toggleOtherFields);
    document.querySelector('[name="language"]').addEventListener("change", toggleOtherFields);
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeCollectionForm(); });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const data = Object.fromEntries(new FormData(form).entries());
        const option = form.variant.selectedOptions[0];
        data.source_variant_id = option?.dataset.sourceVariantId || "";
        data.variant_name = option?.textContent || data.variant;
        const response = await fetch(collectionItemId ? `/collection/items/${collectionItemId}` : `/collection/items/${collectionCardId}`, {
            method: collectionItemId ? "PATCH" : "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data),
        });
        if (response.ok) location.reload();
        else document.getElementById("collection-form-error").textContent = (await response.json()).error;
    });
});
