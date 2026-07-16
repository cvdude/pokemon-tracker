async function updateCollection(cardId, action) {

    try {

        const response = await fetch(`/inventory/${action}/${cardId}`, {
            method: "POST"
        });

        const data = await response.json();

        if (!data.success) {
            return;
        }

        const countElement = document.getElementById(`count-${cardId}`);

        if (countElement) {
            countElement.innerText = data.count;
        }

    } catch (err) {

        console.error("Inventory update failed:", err);

    }

}