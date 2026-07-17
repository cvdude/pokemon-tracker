(() => {
  const list = document.getElementById('widget-settings');
  if (!list) return;
  let dragging;
  list.querySelectorAll('[draggable="true"]').forEach((item) => {
    item.addEventListener('dragstart', () => { dragging = item; });
    item.addEventListener('dragover', (event) => event.preventDefault());
    item.addEventListener('drop', (event) => {
      event.preventDefault();
      if (dragging && dragging !== item) list.insertBefore(dragging, item);
    });
  });
  document.getElementById('settings-form').addEventListener('submit', () => {
    const checked = [...list.querySelectorAll('input:checked')].map((input) => input.value);
    const order = [...list.children].map((item) => item.dataset.widget);
    const hidden = order.filter((id) => !checked.includes(id));
    const hiddenInput = document.querySelector('input[name="hidden_dashboard_widgets"]');
    hiddenInput.remove();
    list.querySelectorAll('input[type="checkbox"]').forEach((input) => { input.disabled = true; });
    order.filter((id) => checked.includes(id)).forEach((id) => {
      const input = document.createElement('input'); input.type = 'hidden'; input.name = 'dashboard_widgets'; input.value = id; list.parentElement.appendChild(input);
    });
    hidden.forEach((id) => { const input = document.createElement('input'); input.type = 'hidden'; input.name = 'hidden_dashboard_widgets'; input.value = id; list.parentElement.appendChild(input); });
  });
})();
