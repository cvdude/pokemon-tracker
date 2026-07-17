(() => {
  const body = document.body;
  const theme = body.dataset.theme;
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  body.dataset.resolvedTheme = dark ? 'dark' : 'light';
  const imageSize = { small: ['42px', '59px'], medium: ['50px', '70px'], large: ['90px', '126px'] }[body.dataset.cardImageSize];
  if (imageSize) document.querySelectorAll('[data-card-image]').forEach((image) => { image.style.width = imageSize[0]; image.style.height = imageSize[1]; });
  try {
    const order = JSON.parse(body.dataset.dashboardWidgets || '[]');
    const hidden = new Set(JSON.parse(body.dataset.hiddenDashboardWidgets || '[]'));
    const container = document.querySelector('[data-dashboard-container]');
    if (!container) return;
    const widgets = new Map([...container.querySelectorAll('[data-dashboard-widget]')].map((item) => [item.dataset.dashboardWidget, item]));
    order.forEach((id) => { const widget = widgets.get(id); if (widget) container.appendChild(widget); });
    hidden.forEach((id) => { const widget = widgets.get(id); if (widget) widget.hidden = true; });
  } catch (_) { /* Defaults remain visible if stored JSON is invalid. */ }
})();
