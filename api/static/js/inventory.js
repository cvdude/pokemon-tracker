let collectionCardId = null, collectionItemId = null, collectionItems = [];

const today = () => new Date().toISOString().slice(0, 10);
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"})[char]);

async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload;
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) throw new Error(payload.error || "The request could not be completed. Please try again.");
    return payload;
}

function setCollectionError(message = "") {
    document.getElementById("collection-form-error").textContent = message;
}

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
    const imported = (await requestJson(`/collection/variants/${collectionCardId}`)).variants || [];
    const options = imported.length
        ? imported.map(variant => `<option value="${escapeHtml(variant.name)}" data-source-variant-id="${escapeHtml(variant.id)}">${escapeHtml(variant.name)}</option>`)
        : ["Normal", "Holo", "Reverse Holo", "1st Edition", "Shadowless", "Promo"].map(name => `<option>${name}</option>`);
    select.innerHTML = options.join("") + "<option>Other</option>";
}

async function loadCollectionItems(cardId, cardName) {
    collectionCardId = cardId;
    document.getElementById("collection-card-name").textContent = cardName;
    document.getElementById("collection-modal").style.display = "block";
    const management = document.getElementById("collection-management");
    management.classList.remove("d-none");
    management.setAttribute("aria-busy", "true");
    management.textContent = "Loading collection copies…";
    collectionItems = (await requestJson(`/collection/items/card/${cardId}`)).items || [];
    management.removeAttribute("aria-busy");
}

async function openCollectionForm(cardId, cardName) {
    try {
        setCollectionError();
        await loadCollectionItems(cardId, cardName);
        if (collectionItems.length) showCollectionItems();
        else { await loadVariants(); showEditor(); }
    } catch (error) { setCollectionError(error.message); }
}

function showCollectionItems() {
    collectionItemId = null;
    document.getElementById("collection-fields").classList.add("d-none");
    const management = document.getElementById("collection-management");
    management.classList.remove("d-none");
    document.getElementById("collection-submit").classList.add("d-none");
    document.getElementById("collection-back").classList.add("d-none");
    management.innerHTML = collectionItems.map(item => `
        <div class="border rounded p-2 mb-2"><strong>${item.quantity} × ${escapeHtml(item.ownership_type || "Raw")} ${escapeHtml(item.variant)}</strong>
        <div class="mt-2"><button class="btn btn-sm btn-outline-primary" data-collection-action="edit" data-item-id="${item.id}">Edit</button><button class="btn btn-sm btn-outline-secondary" data-collection-action="duplicate" data-item-id="${item.id}">Duplicate</button><button class="btn btn-sm btn-outline-danger" data-collection-action="delete" data-item-id="${item.id}">Delete</button></div></div>`).join("") + "<button class=\"btn btn-success\" data-collection-action=\"new\">Add Another Copy</button>";
}

function showEditor(item = null, focusLocation = false) {
    const form = document.getElementById("collection-form");
    form.reset(); setCollectionError(); collectionItemId = item?.id || null;
    document.getElementById("collection-management").classList.add("d-none");
    document.getElementById("collection-fields").classList.remove("d-none");
    document.getElementById("collection-submit").classList.remove("d-none");
    document.getElementById("collection-back").classList.toggle("d-none", !collectionItems.length);
    form.quantity.value = item?.quantity || 1; form.acquisition_date.value = item?.acquisition_date || today();
    form.ownership_type.value = item?.ownership_type || "Raw"; form.condition.value = item?.condition || "Near Mint";
    const variantOption = [...form.variant.options].find(option => option.dataset.sourceVariantId === item?.source_variant_id || option.value === item?.variant);
    form.variant.value = variantOption ? variantOption.value : "Other";
    if (!variantOption && item?.variant) form.variant_other.value = item.variant.replace(/^Other:\s*/, "");
    form.language.value = item?.language || "English"; form.storage_location.value = item?.storage_location || "Unassigned";
    form.grade.value = item?.grade ?? ""; form.grading_company.value = item?.grading_company || "PSA";
    form.certification_number.value = item?.certification_number || ""; form.notes.value = item?.notes || "";
    form.purchase_price.value = item?.purchase_price ?? ""; form.purchase_date.value = item?.purchase_date || "";
    form.purchase_source.value = item?.purchase_source || ""; form.estimated_value.value = item?.estimated_value ?? "";
    form.last_valuation_date.value = item?.last_valuation_date || ""; form.valuation_source.value = item?.valuation_source || "Manual";
    form.insurance_value.value = item?.insurance_value ?? ""; form.currency.value = item?.currency || "USD";
    ownershipFields(); toggleOtherFields(); if (focusLocation) document.getElementById("collection-location").focus();
}

async function editCollectionItem(cardId, cardName, itemId, focusLocation = false) {
    await loadCollectionItems(cardId, cardName); await loadVariants();
    showEditor(collectionItems.find(item => item.id === itemId), focusLocation);
}

function closeCollectionForm() { document.getElementById("collection-modal").style.display = "none"; }

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("collection-form");
    if (!form) return;
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-collection-action]");
        if (!button) return;
        try {
            const action = button.dataset.collectionAction, itemId = Number(button.dataset.itemId);
            if (action === "open") await openCollectionForm(button.dataset.cardId, button.dataset.cardName);
            else if (action === "close") closeCollectionForm();
            else if (action === "back") showCollectionItems();
            else if (action === "new") { await loadVariants(); showEditor(); }
            else if (action === "edit") { await loadVariants(); showEditor(collectionItems.find(item => item.id === itemId)); }
            else if (action === "edit-item") await editCollectionItem(button.dataset.cardId, button.dataset.cardName, itemId);
            else if (action === "move-item") await editCollectionItem(button.dataset.cardId, button.dataset.cardName, itemId, true);
            else if (action === "trade-item") { await requestJson(`/collection/items/${itemId}/trade`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({is_trade: button.dataset.isTrade === "1"})}); location.reload(); }
            else if ((action === "delete" || action === "delete-item") && confirm("Delete this owned copy?")) { await requestJson(`/collection/items/${itemId}`, {method: "DELETE"}); location.reload(); }
            else if (action === "duplicate") { await requestJson(`/collection/items/${itemId}/duplicate`, {method: "POST"}); location.reload(); }
            else if (action === "remove") { await requestJson(`/inventory/remove/${button.dataset.cardId}`, {method: "POST"}); location.reload(); }
        } catch (error) { setCollectionError(error.message); }
    });
    document.querySelector('[name="ownership_type"]').addEventListener("change", ownershipFields);
    document.querySelector('[name="variant"]').addEventListener("change", toggleOtherFields);
    document.querySelector('[name="language"]').addEventListener("change", toggleOtherFields);
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeCollectionForm(); });
    form.addEventListener("submit", async event => {
        event.preventDefault(); if (!form.reportValidity()) return;
        const submit = document.getElementById("collection-submit"); submit.disabled = true; setCollectionError();
        try {
            const data = Object.fromEntries(new FormData(form).entries()), option = form.variant.selectedOptions[0];
            data.source_variant_id = option?.dataset.sourceVariantId || ""; data.variant_name = option?.textContent || data.variant;
            await requestJson(collectionItemId ? `/collection/items/${collectionItemId}` : `/collection/items/${collectionCardId}`, {method: collectionItemId ? "PATCH" : "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
            location.reload();
        } catch (error) { setCollectionError(error.message); submit.disabled = false; }
    });
});
