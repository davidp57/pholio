/**
 * Pholio — app.js
 * Main UI logic: album selection, config, canvas rendering, interactions.
 * Interact.js is loaded via CDN in index.html.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  album: null,         // album name
  photos: [],          // [{id, w_px, h_px, aspect, exif_date, thumb_url}]
  placements: [],      // [{photo_id, page, x_mm, y_mm, w_mm, h_mm, locked}]
  page_count: 0,
  config: {
    page_format: 'a4-landscape',
    layout_type: 'mosaic',
    sort_order: 'filename',
    columns: 3,
    margin_mm: 10,
    spacing_mm: 5,
    target_row_height_mm: 60,
    relock_behaviour: 'keep',
  },
  // Map photo_id -> override {page, x_mm, y_mm, w_mm, h_mm}
  locked_overrides: {},
  // Page dimensions in mm (set from page_format)
  page_w_mm: 297,
  page_h_mm: 210,
  // Render scale: px per mm
  scale: 2.5,
};

// ---------------------------------------------------------------------------
// Page format registry
// ---------------------------------------------------------------------------

const PAGE_FORMATS = {
  'a4-landscape':     [297, 210],
  'a4-portrait':      [210, 297],
  'a3-landscape':     [420, 297],
  'a3-portrait':      [297, 420],
  'square-30':        [300, 300],
  'square-20':        [200, 200],
  'letter-landscape': [279.4, 215.9],
  'letter-portrait':  [215.9, 279.4],
};

// ---------------------------------------------------------------------------
// DOM references
// ---------------------------------------------------------------------------

const albumSelect    = document.getElementById('album-select');
const configPanel    = document.getElementById('config-panel');
const pageFormatSel  = document.getElementById('page-format');
const layoutTypeSel  = document.getElementById('layout-type');
const sortOrderSel   = document.getElementById('sort-order');
const columnsSel     = document.getElementById('columns');
const customFormatDiv= document.getElementById('custom-format');
const customWInput   = document.getElementById('custom-w');
const customHInput   = document.getElementById('custom-h');
const pagesContainer = document.getElementById('pages-container');
const btnSave        = document.getElementById('btn-save');
const btnExport      = document.getElementById('btn-export');
const relockModal    = document.getElementById('relock-modal');

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function init() {
  const albums = await api('/api/albums');
  albums.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.name;
    opt.textContent = a.name;
    albumSelect.appendChild(opt);
  });
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

albumSelect.addEventListener('change', async () => {
  const name = albumSelect.value;
  if (!name) return;
  state.album = name;
  configPanel.style.display = '';

  // Load saved session
  const session = await api(`/api/session/${encodeURIComponent(name)}`);
  if (session.config) Object.assign(state.config, session.config);
  syncConfigUI();

  // Load photos
  state.photos = await api(`/api/albums/${encodeURIComponent(name)}/photos`);
  if (session.photos && session.photos.length > 0) {
    // Restore locked overrides
    session.photos.forEach(p => {
      if (p.locked && p.override) {
        state.locked_overrides[p.id] = p.override;
      }
    });
    // Restore manual order if applicable
    if (state.config.sort_order === 'manual') {
      const orderMap = {};
      session.photos.forEach(p => { orderMap[p.id] = p.manual_order; });
      state.photos.sort((a, b) => (orderMap[a.id] ?? 999) - (orderMap[b.id] ?? 999));
    }
  }

  await computeLayout();
});

[pageFormatSel, layoutTypeSel, sortOrderSel, columnsSel].forEach(el => {
  el.addEventListener('change', async () => {
    state.config.page_format  = pageFormatSel.value;
    state.config.layout_type  = layoutTypeSel.value;
    state.config.sort_order   = sortOrderSel.value;
    state.config.columns      = parseInt(columnsSel.value, 10);

    if (Object.keys(state.locked_overrides).length > 0) {
      showRelockModal();
    } else {
      await computeLayout();
    }
  });
});

pageFormatSel.addEventListener('change', () => {
  customFormatDiv.style.display = pageFormatSel.value === 'custom' ? '' : 'none';
});

btnSave.addEventListener('click', saveSession);
btnExport.addEventListener('click', exportPdf);

document.querySelectorAll('.modal-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    state.config.relock_behaviour = btn.dataset.behaviour;
    if (btn.dataset.behaviour === 'unlock') {
      state.locked_overrides = {};
    }
    relockModal.style.display = 'none';
    await computeLayout();
  });
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function syncConfigUI() {
  pageFormatSel.value = state.config.page_format || 'a4-landscape';
  layoutTypeSel.value = state.config.layout_type || 'mosaic';
  sortOrderSel.value  = state.config.sort_order  || 'filename';
  columnsSel.value    = state.config.columns      || 3;
}

function updatePageDimensions() {
  if (state.config.page_format === 'custom') {
    state.page_w_mm = parseFloat(customWInput.value) || 200;
    state.page_h_mm = parseFloat(customHInput.value) || 200;
  } else {
    const dims = PAGE_FORMATS[state.config.page_format] || [297, 210];
    [state.page_w_mm, state.page_h_mm] = dims;
  }
}

function showRelockModal() {
  relockModal.style.display = 'flex';
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Layout computation
// ---------------------------------------------------------------------------

async function computeLayout() {
  if (!state.album || state.photos.length === 0) return;
  updatePageDimensions();

  const sortedPhotos = sortPhotos(state.photos, state.config.sort_order);

  const body = {
    page_w_mm: state.page_w_mm,
    page_h_mm: state.page_h_mm,
    margin_mm: state.config.margin_mm,
    spacing_mm: state.config.spacing_mm,
    columns: state.config.columns,
    target_row_height_mm: state.config.target_row_height_mm,
    layout_type: state.config.layout_type,
    relock_behaviour: state.config.relock_behaviour,
    photos: sortedPhotos.map(p => ({ id: p.id, w_px: p.w_px, h_px: p.h_px })),
    locked_overrides: state.locked_overrides,
  };

  try {
    const result = await api('/api/layout/compute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    state.placements = result.placements;
    state.page_count = result.page_count;
    renderCanvas();
  } catch (err) {
    console.error('Layout error:', err);
    pagesContainer.innerHTML = `<p style="color:red;padding:16px">Erreur de mise en page : ${err.message}</p>`;
  }
}

function sortPhotos(photos, order) {
  const sorted = [...photos];
  if (order === 'filename') {
    sorted.sort((a, b) => a.id.localeCompare(b.id));
  } else if (order === 'exif_date') {
    sorted.sort((a, b) => (a.exif_date || '').localeCompare(b.exif_date || ''));
  }
  // 'manual' order is preserved as-is
  return sorted;
}

// ---------------------------------------------------------------------------
// Canvas rendering
// ---------------------------------------------------------------------------

function renderCanvas() {
  pagesContainer.innerHTML = '';
  const sc = state.scale;
  const pw = state.page_w_mm * sc;
  const ph = state.page_h_mm * sc;

  // Build a map: photo_id -> thumb_url
  const thumbMap = {};
  state.photos.forEach(p => { thumbMap[p.id] = p.thumb_url; });

  for (let i = 0; i < state.page_count; i++) {
    const pageEl = document.createElement('div');
    pageEl.className = 'page';
    pageEl.style.width  = `${pw}px`;
    pageEl.style.height = `${ph}px`;
    pageEl.dataset.page = i;

    const pagePlacements = state.placements.filter(p => p.page === i);
    pagePlacements.forEach(pl => {
      const slot = createPhotoSlot(pl, thumbMap[pl.photo_id] || '', sc);
      pageEl.appendChild(slot);
    });

    pagesContainer.appendChild(pageEl);
  }

  attachInteractions();
}

function createPhotoSlot(placement, thumbUrl, sc) {
  const slot = document.createElement('div');
  slot.className = 'photo-slot' + (placement.locked ? ' locked' : '');
  slot.dataset.photoId = placement.photo_id;
  slot.dataset.page    = placement.page;
  slot.style.left   = `${placement.x_mm * sc}px`;
  slot.style.top    = `${placement.y_mm * sc}px`;
  slot.style.width  = `${placement.w_mm * sc}px`;
  slot.style.height = `${placement.h_mm * sc}px`;

  const img = document.createElement('img');
  img.src = thumbUrl;
  img.alt = placement.photo_id;
  img.draggable = false;
  slot.appendChild(img);

  // Lock button
  const lockBtn = document.createElement('button');
  lockBtn.className = 'lock-btn';
  lockBtn.title = placement.locked ? 'Déverrouiller' : 'Verrouiller';
  lockBtn.textContent = placement.locked ? '🔒' : '🔓';
  lockBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleLock(placement.photo_id, !placement.locked);
  });
  slot.appendChild(lockBtn);

  // Resize handle
  const handle = document.createElement('div');
  handle.className = 'resize-handle se';
  slot.appendChild(handle);

  return slot;
}

// ---------------------------------------------------------------------------
// Interactions (Interact.js)
// ---------------------------------------------------------------------------

function attachInteractions() {
  // Unset previous interact configuration to avoid stacking listeners on re-render
  interact('.photo-slot').unset();

  // Drag to move
  interact('.photo-slot').draggable({
    listeners: {
      end(event) {
        const slot = event.target;
        const page = parseInt(slot.closest('.page').dataset.page, 10);
        const pageEl = slot.closest('.page');
        const rect = pageEl.getBoundingClientRect();
        const slotRect = slot.getBoundingClientRect();
        const sc = state.scale;
        const x_mm = (slotRect.left - rect.left) / sc;
        const y_mm = (slotRect.top  - rect.top)  / sc;
        lockAndMove(slot.dataset.photoId, page, x_mm, y_mm);
      },
    },
    modifiers: [
      interact.modifiers.restrictToParent({ elementRect: { top: 0, left: 0, bottom: 1, right: 1 } }),
    ],
  }).on('dragmove', (event) => {
    const target = event.target;
    const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
    const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
    target.style.transform = `translate(${x}px, ${y}px)`;
    target.setAttribute('data-x', x);
    target.setAttribute('data-y', y);
  });

  // Resize handle
  interact('.photo-slot').resizable({
    edges: { right: true, bottom: true, bottomRight: '.resize-handle.se' },
    listeners: {
      end(event) {
        const slot = event.target;
        const sc = state.scale;
        const w_mm = event.rect.width  / sc;
        const h_mm = event.rect.height / sc;
        lockAndResize(slot.dataset.photoId, w_mm, h_mm);
      },
    },
  }).on('resizemove', (event) => {
    const target = event.target;
    target.style.width  = `${event.rect.width}px`;
    target.style.height = `${event.rect.height}px`;
  });
}

// ---------------------------------------------------------------------------
// Lock / unlock actions
// ---------------------------------------------------------------------------

async function lockAndMove(photoId, page, x_mm, y_mm) {
  const placement = state.placements.find(p => p.photo_id === photoId);
  if (!placement) return;
  // Reset any residual drag transform on the element before re-render
  const el = document.querySelector(`[data-photo-id="${CSS.escape(photoId)}"]`);
  if (el) { el.style.transform = ''; el.removeAttribute('data-x'); el.removeAttribute('data-y'); }
  state.locked_overrides[photoId] = {
    page, x_mm, y_mm,
    w_mm: placement.w_mm,
    h_mm: placement.h_mm,
  };
  await computeLayout();
}

async function lockAndResize(photoId, w_mm, h_mm) {
  const placement = state.placements.find(p => p.photo_id === photoId);
  if (!placement) return;
  state.locked_overrides[photoId] = {
    page: placement.page,
    x_mm: placement.x_mm,
    y_mm: placement.y_mm,
    w_mm, h_mm,
  };
  await computeLayout();
}

async function toggleLock(photoId, lock) {
  if (lock) {
    const placement = state.placements.find(p => p.photo_id === photoId);
    if (placement) {
      state.locked_overrides[photoId] = {
        page: placement.page,
        x_mm: placement.x_mm,
        y_mm: placement.y_mm,
        w_mm: placement.w_mm,
        h_mm: placement.h_mm,
      };
    }
  } else {
    delete state.locked_overrides[photoId];
  }
  await computeLayout();
}

// ---------------------------------------------------------------------------
// Save session
// ---------------------------------------------------------------------------

async function saveSession() {
  if (!state.album) return;
  const sessionData = {
    version: 1,
    album_path: `images/${state.album}`,
    config: { ...state.config },
    photos: state.photos.map((p, i) => ({
      id: p.id,
      manual_order: i,
      locked: !!state.locked_overrides[p.id],
      override: state.locked_overrides[p.id] || null,
    })),
  };
  await fetch(`/api/session/${encodeURIComponent(state.album)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sessionData),
  });
  alert('Session sauvegardée !');
}

// ---------------------------------------------------------------------------
// Export PDF
// ---------------------------------------------------------------------------

async function exportPdf() {
  if (!state.album || state.placements.length === 0) return;
  const body = {
    album_path: `images/${state.album}`,
    page_w_mm: state.page_w_mm,
    page_h_mm: state.page_h_mm,
    layout_result: {
      placements: state.placements,
      page_count: state.page_count,
    },
    jpeg_quality: 90,
  };
  const res = await fetch('/api/export/pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) { alert('Erreur lors de l\'export PDF.'); return; }
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `${state.album}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

init();
