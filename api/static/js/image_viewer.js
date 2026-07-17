(() => {
  const viewer = document.getElementById('image-viewer');
  if (!viewer) return;
  const scans = JSON.parse(viewer.dataset.scans || '[]');
  const variants = JSON.parse(viewer.dataset.variants || '[]');
  const image = viewer.querySelector('[data-viewer-image]');
  const stage = viewer.querySelector('[data-viewer-stage]');
  const scanList = viewer.querySelector('[data-viewer-scans]');
  const compare = viewer.querySelector('[data-variant-comparison]');
  const controls = viewer.querySelector('[data-viewer-controls]');
  const label = document.getElementById('viewer-scan-label');
  let scanIndex = 0, scale = 1, x = 0, y = 0, dragging = false, startX, startY;

  const transform = () => { image.style.transform = `translate(${x}px, ${y}px) scale(${scale})`; };
  const reset = () => { scale = 1; x = 0; y = 0; transform(); };
  const loadScan = (index) => {
    scanIndex = index; reset(); image.removeAttribute('src'); image.dataset.src = scans[index].url;
    image.src = image.dataset.src; image.loading = 'eager'; label.textContent = `· ${scans[index].label}`;
    scanList.querySelectorAll('button').forEach((button, i) => button.classList.toggle('active', i === index));
  };
  scans.forEach((scan, index) => { const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-sm btn-outline-light'; button.textContent = scan.label; button.addEventListener('click', () => loadScan(index)); scanList.appendChild(button); });
  const setMode = (mode) => {
    const comparison = mode === 'compare'; stage.hidden = comparison; controls.hidden = comparison; scanList.hidden = comparison; compare.hidden = !comparison;
    if (comparison && !compare.childElementCount) variants.forEach((variant) => {
      const card = document.createElement('article'); card.className = `variant-comparison-card ${variant.owned ? 'owned' : 'missing'}`;
      const variantImage = document.createElement('img'); variantImage.loading = 'lazy'; variantImage.src = scans[0].url; variantImage.alt = `${variant.name} card scan`;
      const name = document.createElement('strong'); name.textContent = variant.name;
      const status = document.createElement('span'); status.textContent = variant.owned ? '✓ Owned' : '○ Missing';
      card.append(variantImage, name, status);
      compare.appendChild(card);
    });
  };
  const open = (mode = 'image') => { viewer.hidden = false; document.body.classList.add('viewer-open'); setMode(mode); loadScan(scanIndex); viewer.querySelector('[data-image-viewer-close]').focus(); };
  const close = () => { viewer.hidden = true; document.body.classList.remove('viewer-open'); history.replaceState(null, '', location.pathname); };
  document.querySelectorAll('[data-image-viewer-open]').forEach((button) => button.addEventListener('click', () => open(button.dataset.viewerMode || 'image')));
  viewer.querySelector('[data-image-viewer-close]').addEventListener('click', close);
  viewer.querySelectorAll('[data-viewer-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.viewerMode)));
  viewer.querySelectorAll('[data-viewer-zoom]').forEach((button) => button.addEventListener('click', () => { const action = button.dataset.viewerZoom; if (action === 'reset') reset(); else { scale = Math.min(4, Math.max(1, scale + (action === 'in' ? .25 : -.25))); transform(); } }));
  stage.addEventListener('wheel', (event) => { event.preventDefault(); scale = Math.min(4, Math.max(1, scale + (event.deltaY < 0 ? .15 : -.15))); transform(); }, { passive: false });
  stage.addEventListener('pointerdown', (event) => { if (scale === 1) return; dragging = true; startX = event.clientX - x; startY = event.clientY - y; stage.setPointerCapture(event.pointerId); });
  stage.addEventListener('pointermove', (event) => { if (!dragging) return; x = event.clientX - startX; y = event.clientY - startY; transform(); });
  stage.addEventListener('pointerup', () => { dragging = false; });
  document.addEventListener('keydown', (event) => { if (!viewer.hidden && event.key === 'Escape') close(); });
  if (new URLSearchParams(location.search).get('viewer') === '1') open();
})();
