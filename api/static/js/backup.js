(() => {
  const form = document.getElementById('backup-import-form');
  if (!form) return;
  const previewBox = document.getElementById('import-preview');
  const applyButton = document.getElementById('apply-import');
  const previewButton = document.getElementById('preview-import');

  const show = (message, level = 'secondary') => {
    previewBox.className = `alert alert-${level} mt-3`;
    previewBox.textContent = message;
  };
  const body = () => new FormData(form);

  previewButton.addEventListener('click', async () => {
    if (!form.file.files.length) return show('Choose an export file first.', 'warning');
    previewButton.disabled = true;
    try {
      const response = await fetch('/backup/import/preview', { method: 'POST', body: body() });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Preview failed.');
      const collection = result.preview.collection_items;
      const wishlist = result.preview.wishlist_items;
      show(`Preview: ${collection.rows} inventory row(s) (${collection.duplicates} duplicate, ${collection.new_rows} new) and ${wishlist.rows} wishlist row(s) (${wishlist.duplicates} duplicate, ${wishlist.new_rows} new).`);
      applyButton.classList.remove('d-none');
    } catch (error) {
      applyButton.classList.add('d-none');
      show(error.message, 'danger');
    } finally { previewButton.disabled = false; }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mode = form.mode.value;
    if (mode === 'replace' && !window.confirm('Replace your current collection and wishlist? A backup will be made first.')) return;
    applyButton.disabled = true;
    try {
      const response = await fetch('/backup/import', { method: 'POST', body: body() });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Import failed.');
      show(`Import complete: ${result.inserted} row(s) added and ${result.merged} row(s) merged. Backup: ${result.backup.filename}. Reloading…`, 'success');
      window.setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      show(error.message, 'danger');
      applyButton.disabled = false;
    }
  });

  document.querySelectorAll('.restore-backup').forEach((button) => {
    button.addEventListener('click', async () => {
      if (!window.confirm(`Restore ${button.dataset.backupName}? A snapshot of the current database will be created first.`)) return;
      button.disabled = true;
      try {
        const response = await fetch(`/backup/restore/${button.dataset.backupId}`, { method: 'POST' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Restore failed.');
        window.location.reload();
      } catch (error) { window.alert(error.message); button.disabled = false; }
    });
  });
})();
