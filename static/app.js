/**
 * Pholio — app.js
 * Main UI logic: album selection, config, canvas rendering, interactions.
 * Interact.js is vendored locally in static/interact.min.js.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  album: null,         // album name
  photos: [],          // [{id, w_px, h_px, aspect, exif_date, thumb_url}]
  deleted_photos: [],  // photos removed from layout (restorable)
  placements: [],      // [{photo_id, page, x_mm, y_mm, w_mm, h_mm, locked}]
  page_count: 0,
  config: {
    page_format: 'a4-landscape',
    layout_type: 'mosaic',
    sort_order: 'filename',
    columns: 3,
    margin_top_mm: 10,
    margin_right_mm: 10,
    margin_bottom_mm: 10,
    margin_left_mm: 10,
    spacing_mm: 5,
    target_row_height_mm: 60,
    relock_behaviour: 'keep',
    watermark_text: '',
    target_dpi: 300,
    page_bg_color: '#ffffff',
    cover_bg_color: '#ffffff',
  },
  // Map photo_id -> override {page, x_mm, y_mm, w_mm, h_mm}
  locked_overrides: {},
  // Map photo_id -> size override {w_mm, h_mm} (no position lock)
  size_overrides: {},
  // Map photo_id -> caption text string
  captions: {},
  // Free text blocks [{id, page, x_mm, y_mm, w_mm, h_mm, text, font_size, font_color, align, bold, italic}]
  text_blocks: [],
  // Currently selected photo IDs (for batch operations)
  selected_photos: [],
  // Cover page config
  cover: { photo_id: null, title: '' },
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
const columnsSel       = document.getElementById('columns');
const marginTopInput   = document.getElementById('margin-top');
const marginRightInput = document.getElementById('margin-right');
const marginBottomInput= document.getElementById('margin-bottom');
const marginLeftInput  = document.getElementById('margin-left');
const targetRowHeightInput = document.getElementById('target-row-height');
const targetRowHeightVal   = document.getElementById('target-row-height-val');
const customFormatDiv= document.getElementById('custom-format');
const customWInput   = document.getElementById('custom-w');
const customHInput   = document.getElementById('custom-h');
const pagesContainer    = document.getElementById('pages-container');
const btnSave           = document.getElementById('btn-save');
const btnExport         = document.getElementById('btn-export');
const relockModal       = document.getElementById('relock-modal');
const sizeDialog        = document.getElementById('size-dialog');
const sizeWInput        = document.getElementById('size-w');
const sizeHInput        = document.getElementById('size-h');
const spinnerEl         = document.getElementById('spinner');
const spinnerLabelEl    = document.getElementById('spinner-label');
const placeholderEl     = document.getElementById('canvas-placeholder');
const trashPanel        = document.getElementById('trash-panel');
const trashGrid         = document.getElementById('trash-grid');
const coverSection      = document.getElementById('cover-section');
const coverPhotoName    = document.getElementById('cover-photo-name');
const coverRemoveBtn    = document.getElementById('cover-remove-btn');
const coverTitleInput   = document.getElementById('cover-title-input');
const selectionToolbar    = document.getElementById('selection-toolbar');
const selectionCountEl    = document.getElementById('selection-count');
const selectionSizeSlider = document.getElementById('selection-size-slider');
const selectionSizeVal    = document.getElementById('selection-size-val');
const btnClearSelection   = document.getElementById('btn-clear-selection');
const zoomSlider        = document.getElementById('zoom-slider');
const zoomLabel         = document.getElementById('zoom-label');
const btnZoomIn         = document.getElementById('zoom-in');
const btnZoomOut        = document.getElementById('zoom-out');
const btnZoomReset      = document.getElementById('zoom-reset');
const watermarkInput    = document.getElementById('watermark-text');
const targetDpiSel      = document.getElementById('target-dpi');
const pageBgColorInput  = document.getElementById('page-bg-color');
const coverBgColorInput = document.getElementById('cover-bg-color');
const coverBgLabel      = document.getElementById('cover-bg-label');
const filmstripEl       = document.getElementById('filmstrip');
const filmstripDivider  = document.getElementById('filmstrip-divider');
const captionModal      = document.getElementById('caption-modal');
const exportCoverJpgCheck = document.getElementById('export-cover-jpg');
const captionTextInput  = document.getElementById('caption-text-input');

// Height (mm) reserved at the top of the cover page for the album title
// Must match COVER_TITLE_H_MM in layout.py
const COVER_TITLE_H_MM = 20.0;

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function init() {
  api('/api/version').then(data => {
    const el = document.getElementById('app-version');
    if (el && data.version) el.textContent = 'v' + data.version;
  }).catch(() => {});

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
  state.deleted_photos = [];
  state.locked_overrides = {};
  state.size_overrides = {};
  state.captions = {};
  state.selected_photos = [];
  state.cover = { photo_id: null, title: name };
  updateSelectionToolbar();
  updateCoverUI();
  renderTrash();
  configPanel.style.display = '';
  showSpinner();

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
  if (session.size_overrides) {
    state.size_overrides = { ...session.size_overrides };
  }
  if (session.captions) {
    state.captions = { ...session.captions };
  }
  if (Array.isArray(session.text_blocks)) {
    state.text_blocks = session.text_blocks.map(b => ({ ...b }));
  }
  if (session.cover && session.cover.photo_id) {
    state.cover = { ...session.cover };
    if (coverTitleInput) coverTitleInput.value = state.cover.title || '';
    updateCoverUI();
  }

  await computeLayout();
});

[pageFormatSel, layoutTypeSel, sortOrderSel, columnsSel,
 marginTopInput, marginRightInput, marginBottomInput, marginLeftInput].forEach(el => {
  el.addEventListener('change', async () => {
    state.config.page_format      = pageFormatSel.value;
    state.config.layout_type      = layoutTypeSel.value;
    state.config.sort_order       = sortOrderSel.value;
    state.config.columns          = parseInt(columnsSel.value, 10);
    state.config.margin_top_mm    = parseFloat(marginTopInput.value)    || 0;
    state.config.margin_right_mm  = parseFloat(marginRightInput.value)  || 0;
    state.config.margin_bottom_mm = parseFloat(marginBottomInput.value) || 0;
    state.config.margin_left_mm   = parseFloat(marginLeftInput.value)   || 0;

    if (Object.keys(state.locked_overrides).length > 0) {
      showRelockModal();
    } else {
      await computeLayout();
    }
  });
});

targetRowHeightInput.addEventListener('input', () => {
  const val = parseInt(targetRowHeightInput.value, 10);
  state.config.target_row_height_mm = val;
  targetRowHeightVal.textContent = `${val} mm`;
});
targetRowHeightInput.addEventListener('change', async () => {
  await computeLayout();
});

pageFormatSel.addEventListener('change', () => {
  customFormatDiv.style.display = pageFormatSel.value === 'custom' ? '' : 'none';
});

[customWInput, customHInput].forEach(el => {
  el.addEventListener('change', async () => {
    if (state.config.page_format === 'custom') {
      await computeLayout();
    }
  });
});

btnSave.addEventListener('click', saveSession);
btnExport.addEventListener('click', exportPdf);

if (watermarkInput) {
  watermarkInput.addEventListener('input', () => {
    state.config.watermark_text = watermarkInput.value;
    updateWatermarkOverlays();
  });
}

if (targetDpiSel) {
  targetDpiSel.addEventListener('change', () => {
    state.config.target_dpi = parseInt(targetDpiSel.value, 10);
  });
}

if (pageBgColorInput) {
  pageBgColorInput.addEventListener('input', () => {
    state.config.page_bg_color = pageBgColorInput.value;
    renderCanvas();
  });
}

if (coverBgColorInput) {
  coverBgColorInput.addEventListener('input', () => {
    state.config.cover_bg_color = coverBgColorInput.value;
    renderCanvas();
  });
}

// ---------------------------------------------------------------------------
// Zoom controls
// ---------------------------------------------------------------------------

function updateZoomUI() {
  const pct = Math.round(state.scale / 2.5 * 100);
  zoomLabel.textContent = `${pct}\u00a0%`;
  zoomSlider.value = state.scale;
}

zoomSlider.addEventListener('input', () => {
  state.scale = parseFloat(zoomSlider.value);
  updateZoomUI();
  renderCanvas();
});

btnZoomIn.addEventListener('click', () => {
  state.scale = Math.min(5.0, parseFloat((state.scale + 0.25).toFixed(2)));
  updateZoomUI();
  renderCanvas();
});

btnZoomOut.addEventListener('click', () => {
  state.scale = Math.max(1.0, parseFloat((state.scale - 0.25).toFixed(2)));
  updateZoomUI();
  renderCanvas();
});

btnZoomReset.addEventListener('click', () => {
  state.scale = 2.5;
  updateZoomUI();
  renderCanvas();
});

// Ctrl+Wheel zoom (on the whole document)
document.addEventListener('wheel', (e) => {
  if (!e.ctrlKey) return;
  e.preventDefault();
  const delta = e.deltaY < 0 ? 0.25 : -0.25;
  state.scale = Math.min(5.0, Math.max(1.0, parseFloat((state.scale + delta).toFixed(2))));
  updateZoomUI();
  renderCanvas();
}, { passive: false });

document.querySelectorAll('.modal-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const { behaviour } = btn.dataset;
    if (behaviour === 'unlock') {
      state.locked_overrides = {};
    }
    relockModal.style.display = 'none';
    state.config.relock_behaviour = behaviour;
    await computeLayout();
    state.config.relock_behaviour = 'keep';
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
  marginTopInput.value    = state.config.margin_top_mm    ?? 10;
  marginRightInput.value  = state.config.margin_right_mm  ?? 10;
  marginBottomInput.value = state.config.margin_bottom_mm ?? 10;
  marginLeftInput.value   = state.config.margin_left_mm   ?? 10;
  const trh = state.config.target_row_height_mm ?? 60;
  targetRowHeightInput.value = trh;
  targetRowHeightVal.textContent = `${trh} mm`;
  if (watermarkInput) watermarkInput.value = state.config.watermark_text || '';
  if (targetDpiSel) targetDpiSel.value = String(state.config.target_dpi ?? 300);
  if (pageBgColorInput) pageBgColorInput.value = state.config.page_bg_color || '#ffffff';
  if (coverBgColorInput) coverBgColorInput.value = state.config.cover_bg_color || '#ffffff';
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
// Spinner helpers
// ---------------------------------------------------------------------------

function showSpinner(label = 'Calcul de la mise en page…') {
  if (spinnerLabelEl) spinnerLabelEl.textContent = label;
  placeholderEl.style.display = 'none';
  spinnerEl.style.display     = 'flex';
}

function hideSpinner() {
  spinnerEl.style.display = 'none';
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
  if (!state.album) return;
  const activePhotos = state.photos.filter(p => !state.deleted_photos.find(d => d.id === p.id));
  if (activePhotos.length === 0) {
    state.placements = [];
    state.page_count = 0;
    renderCanvas();
    return;
  }
  updatePageDimensions();
  showSpinner();

  const sortedPhotos = sortPhotos(activePhotos, state.config.sort_order);

  const body = {
    page_w_mm: state.page_w_mm,
    page_h_mm: state.page_h_mm,
    margin_top_mm:    state.config.margin_top_mm,
    margin_right_mm:  state.config.margin_right_mm,
    margin_bottom_mm: state.config.margin_bottom_mm,
    margin_left_mm:   state.config.margin_left_mm,
    spacing_mm: state.config.spacing_mm,
    columns: state.config.columns,
    target_row_height_mm: state.config.target_row_height_mm,
    layout_type: state.config.layout_type,
    relock_behaviour: state.config.relock_behaviour,
    photos: sortedPhotos.map(p => ({ id: p.id, w_px: p.w_px, h_px: p.h_px })),
    locked_overrides: state.locked_overrides,
    size_overrides: state.size_overrides,
    cover_photo_id: state.cover.photo_id,
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
  } finally {
    hideSpinner();
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
  placeholderEl.style.display = 'none';
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

    const isCoverPage = (i === 0 && state.cover.photo_id != null);
    if (isCoverPage) pageEl.classList.add('cover-page');
    pageEl.style.backgroundColor = (isCoverPage ? state.config.cover_bg_color : state.config.page_bg_color) || '#ffffff';

    const pagePlacements = state.placements.filter(p => p.page === i);
    pagePlacements.forEach(pl => {
      const slot = createPhotoSlot(pl, thumbMap[pl.photo_id] || '', sc);
      if (state.size_overrides[pl.photo_id] && !pl.locked) {
        slot.classList.add('size-locked');
      }
      if (state.selected_photos.includes(pl.photo_id)) {
        slot.classList.add('selected');
      }
      if (pl.photo_id === state.cover.photo_id) {
        slot.classList.add('cover');
      }
      pageEl.appendChild(slot);
    });

    if (isCoverPage) {
      const titleEl = document.createElement('div');
      titleEl.className = 'cover-title-overlay';
      titleEl.textContent = state.cover.title || state.album || '';
      titleEl.style.height = `${COVER_TITLE_H_MM * sc}px`;
      pageEl.appendChild(titleEl);
    }

    pagesContainer.appendChild(pageEl);
  }

  // Render text blocks
  const pages = pagesContainer.querySelectorAll('.page');
  state.text_blocks.forEach(block => {
    const pageEl = pages[block.page];
    if (!pageEl) return;
    pageEl.appendChild(createTextBlockEl(block, sc));
  });

  updateWatermarkOverlays();
  renderFilmstrip();
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

  // Size button — opens dialog when free, removes override when size-locked
  const isSizeLocked = !!state.size_overrides[placement.photo_id];
  const sizeBtn = document.createElement('button');
  sizeBtn.className = 'size-btn';
  if (isSizeLocked) {
    sizeBtn.title = 'Libérer la taille forcée';
    sizeBtn.textContent = '🔒';
    sizeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      resetSizeOverride(placement.photo_id);
    });
  } else {
    sizeBtn.title = 'Forcer la taille';
    sizeBtn.textContent = '⇔';
    sizeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openSizeDialog(placement.photo_id);
    });
  }
  slot.appendChild(sizeBtn);

  // Cover button
  const coverBtn = document.createElement('button');
  coverBtn.className = 'cover-btn';
  const isCover = placement.photo_id === state.cover.photo_id;
  coverBtn.title = isCover ? 'Retirer la page de garde' : 'D\u00e9finir comme page de garde';
  coverBtn.textContent = '⭐';
  coverBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleCover(placement.photo_id);
  });
  slot.appendChild(coverBtn);

  // Select button
  const selectBtn = document.createElement('button');
  selectBtn.className = 'select-btn';
  const isSelected = state.selected_photos.includes(placement.photo_id);
  selectBtn.title = isSelected ? 'D\u00e9s\u00e9lectionner' : 'S\u00e9lectionner';
  selectBtn.textContent = isSelected ? '\u2611' : '\u2610';
  selectBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleSelect(placement.photo_id);
  });
  slot.appendChild(selectBtn);

  // Delete button
  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-btn';
  deleteBtn.title = 'Supprimer de l\'album';
  deleteBtn.textContent = '✕';
  deleteBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    deletePhoto(placement.photo_id);
  });
  slot.appendChild(deleteBtn);

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

  // Caption button — opens modal to edit caption
  const captionBtn = document.createElement('button');
  captionBtn.className = 'caption-btn';
  captionBtn.title = 'Légende';
  captionBtn.textContent = '✏️';
  captionBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openCaptionModal(placement.photo_id);
  });
  slot.appendChild(captionBtn);

  // Caption overlay (shown when a caption is set)
  if (state.captions[placement.photo_id]) {
    slot.classList.add('has-caption');
    const capOverlay = document.createElement('div');
    capOverlay.className = 'caption-overlay';
    capOverlay.textContent = state.captions[placement.photo_id];
    slot.appendChild(capOverlay);
  }

  return slot;
}

// ---------------------------------------------------------------------------
// Interactions (Interact.js)
// ---------------------------------------------------------------------------

function attachInteractions() {
  // Unset previous interact configuration to avoid stacking listeners on re-render
  interact('.photo-slot').unset();

  // Drag to move (cross-page capable)
  interact('.photo-slot').draggable({
    listeners: {
      start(event) {
        event.target.style.zIndex = '100';
      },
      end(event) {
        const slot = event.target;
        slot.style.zIndex = '';
        const slotRect = slot.getBoundingClientRect();
        const sc = state.scale;

        // Detect target page from slot center position
        const centerX = slotRect.left + slotRect.width  / 2;
        const centerY = slotRect.top  + slotRect.height / 2;
        const pages = document.querySelectorAll('.page');
        let targetPageEl = slot.closest('.page');
        for (const pageEl of pages) {
          const pr = pageEl.getBoundingClientRect();
          if (centerX >= pr.left && centerX <= pr.right &&
              centerY >= pr.top  && centerY <= pr.bottom) {
            targetPageEl = pageEl;
            break;
          }
        }
        const targetPage = parseInt(targetPageEl.dataset.page, 10);
        const pr = targetPageEl.getBoundingClientRect();
        const x_mm = (slotRect.left - pr.left) / sc;
        const y_mm = (slotRect.top  - pr.top)  / sc;
        lockAndMove(slot.dataset.photoId, targetPage, x_mm, y_mm);
      },
    },
  }).on('dragmove', (event) => {
    const { target } = event;
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
        setSizeOnly(slot.dataset.photoId, w_mm, h_mm);
      },
    },
  }).on('resizemove', (event) => {
    const { target } = event;
    target.style.width  = `${event.rect.width}px`;
    target.style.height = `${event.rect.height}px`;
  });

  // Text blocks: drag and resize
  interact('.text-block').unset();
  interact('.text-block').draggable({
    listeners: {
      move(event) {
        const { blockId } = event.target.dataset;
        const block = state.text_blocks.find(b => b.id === blockId);
        if (!block) return;
        block.x_mm += event.dx / state.scale;
        block.y_mm += event.dy / state.scale;
        event.target.style.left = `${block.x_mm * state.scale}px`;
        event.target.style.top  = `${block.y_mm * state.scale}px`;
      },
    },
  }).resizable({
    edges: { right: true, bottom: true, bottomRight: '.tb-resize-handle' },
    listeners: {
      move(event) {
        const { blockId } = event.target.dataset;
        const block = state.text_blocks.find(b => b.id === blockId);
        if (!block) return;
        block.w_mm = event.rect.width  / state.scale;
        block.h_mm = event.rect.height / state.scale;
        event.target.style.width  = `${event.rect.width}px`;
        event.target.style.height = `${event.rect.height}px`;
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Delete / restore actions
// ---------------------------------------------------------------------------

async function deletePhoto(photoId) {
  const photo = state.photos.find(p => p.id === photoId);
  if (!photo) return;
  state.deleted_photos.push(photo);
  delete state.locked_overrides[photoId];
  delete state.size_overrides[photoId];
  state.selected_photos = state.selected_photos.filter(id => id !== photoId);
  if (state.cover.photo_id === photoId) {
    state.cover.photo_id = null;
    updateCoverUI();
  }
  renderTrash();
  updateSelectionToolbar();
  await computeLayout();
}

async function restorePhoto(photoId) {
  state.deleted_photos = state.deleted_photos.filter(p => p.id !== photoId);
  renderTrash();
  await computeLayout();
}

function renderTrash() {
  trashGrid.innerHTML = '';
  if (state.deleted_photos.length === 0) {
    trashPanel.style.display = 'none';
    return;
  }
  trashPanel.style.display = '';
  state.deleted_photos.forEach(photo => {
    const cell = document.createElement('div');
    cell.className = 'trash-thumb';
    const img = document.createElement('img');
    img.src = photo.thumb_url;
    img.alt = photo.id;
    const btn = document.createElement('button');
    btn.className = 'restore-btn';
    btn.title = 'Restaurer';
    btn.textContent = '↩';
    btn.addEventListener('click', () => restorePhoto(photo.id));
    cell.appendChild(img);
    cell.appendChild(btn);
    trashGrid.appendChild(cell);
  });
}

// ---------------------------------------------------------------------------
// Lock / unlock actions
// ---------------------------------------------------------------------------

async function lockAndMove(photoId, page, x_mm, y_mm) {
  const placement = state.placements.find(p => p.photo_id === photoId);
  if (!placement) return;
  const el = document.querySelector(`[data-photo-id="${CSS.escape(photoId)}"]`);
  if (el) { el.style.transform = ''; el.removeAttribute('data-x'); el.removeAttribute('data-y'); }
  // Merge any existing size override into the position lock
  const sizeOv = state.size_overrides[photoId];
  state.locked_overrides[photoId] = {
    page, x_mm, y_mm,
    w_mm: sizeOv?.w_mm ?? placement.w_mm,
    h_mm: sizeOv?.h_mm ?? placement.h_mm,
  };
  delete state.size_overrides[photoId];
  await computeLayout();
}

async function setSizeOnly(photoId, w_mm, h_mm) {
  if (state.locked_overrides[photoId]) {
    // Photo is position-locked: update size inside the position lock
    state.locked_overrides[photoId].w_mm = w_mm;
    state.locked_overrides[photoId].h_mm = h_mm;
  } else {
    // Size-only lock: position remains computed by layout
    state.size_overrides[photoId] = { w_mm, h_mm };
  }
  await computeLayout();
}

async function toggleLock(photoId, lock) {
  if (lock) {
    const placement = state.placements.find(p => p.photo_id === photoId);
    if (placement) {
      const sizeOv = state.size_overrides[photoId];
      state.locked_overrides[photoId] = {
        page: placement.page,
        x_mm: placement.x_mm,
        y_mm: placement.y_mm,
        w_mm: sizeOv?.w_mm ?? placement.w_mm,
        h_mm: sizeOv?.h_mm ?? placement.h_mm,
      };
      delete state.size_overrides[photoId];
    }
  } else {
    const ov = state.locked_overrides[photoId];
    if (ov) {
      // Preserve the custom size when unlocking position
      state.size_overrides[photoId] = { w_mm: ov.w_mm, h_mm: ov.h_mm };
    }
    delete state.locked_overrides[photoId];
  }
  await computeLayout();
}

// ---------------------------------------------------------------------------
// Force size dialog (single photo only)
// ---------------------------------------------------------------------------

async function resetSizeOverride(photoId) {
  delete state.size_overrides[photoId];
  await computeLayout();
}

function openSizeDialog(photoId) {
  const placement = state.placements.find(p => p.photo_id === photoId);
  if (!placement) return;
  sizeWInput.value = Math.round(placement.w_mm);
  sizeHInput.value = Math.round(placement.h_mm);
  sizeDialog.dataset.photoId = photoId;
  sizeDialog.style.display = 'flex';
}

document.getElementById('size-dialog-ok').addEventListener('click', async () => {
  const w = parseFloat(sizeWInput.value);
  const h = parseFloat(sizeHInput.value);
  sizeDialog.style.display = 'none';
  if (!(w > 0 && h > 0)) return;
  const { photoId } = sizeDialog.dataset;
  if (photoId) await setSizeOnly(photoId, w, h);
});

document.getElementById('size-dialog-cancel').addEventListener('click', () => {
  sizeDialog.style.display = 'none';
});

// ---------------------------------------------------------------------------
// Cover page actions
// ---------------------------------------------------------------------------

function toggleCover(photoId) {
  if (state.cover.photo_id === photoId) {
    state.cover.photo_id = null;
  } else {
    state.cover.photo_id = photoId;
    if (!state.cover.title && state.album) {
      state.cover.title = state.album;
      if (coverTitleInput) coverTitleInput.value = state.cover.title;
    }
  }
  updateCoverUI();
  computeLayout();
}

function updateCoverUI() {
  if (!coverSection) return;
  if (state.cover.photo_id) {
    coverSection.style.display = '';
    if (coverPhotoName) coverPhotoName.textContent = state.cover.photo_id;
    if (coverRemoveBtn) coverRemoveBtn.style.display = '';
    if (coverBgLabel) coverBgLabel.style.display = '';
  } else {
    coverSection.style.display = 'none';
    if (coverRemoveBtn) coverRemoveBtn.style.display = 'none';
    if (coverBgLabel) coverBgLabel.style.display = 'none';
  }
}

if (coverTitleInput) {
  coverTitleInput.addEventListener('input', () => {
    state.cover.title = coverTitleInput.value;
    renderCanvas();
  });
}

if (coverRemoveBtn) {
  coverRemoveBtn.addEventListener('click', () => {
    state.cover.photo_id = null;
    updateCoverUI();
    computeLayout();
  });
}

// ---------------------------------------------------------------------------
// Selection actions
// ---------------------------------------------------------------------------

function toggleSelect(photoId) {
  const idx = state.selected_photos.indexOf(photoId);
  if (idx >= 0) {
    state.selected_photos.splice(idx, 1);
  } else {
    state.selected_photos.push(photoId);
  }
  updateSelectionToolbar();
  renderCanvas();
}

function updateSelectionToolbar() {
  if (!selectionToolbar) return;
  if (state.selected_photos.length > 0) {
    selectionToolbar.style.display = 'flex';
    if (selectionCountEl) {
      selectionCountEl.textContent = `${state.selected_photos.length} s\u00e9lectionn\u00e9e(s)`;
    }
    // Sync the size slider to the first selected photo's current height
    if (selectionSizeSlider) {
      const firstId = state.selected_photos[0];
      const ov = state.size_overrides[firstId] || state.locked_overrides[firstId];
      const pl = state.placements.find(p => p.photo_id === firstId);
      const h = ov ? ov.h_mm : (pl ? pl.h_mm : 60);
      selectionSizeSlider.value = Math.round(h / 5) * 5;
      if (selectionSizeVal) selectionSizeVal.textContent = `${selectionSizeSlider.value}\u00a0mm`;
    }
  } else {
    selectionToolbar.style.display = 'none';
  }
}

if (selectionSizeSlider) {
  selectionSizeSlider.addEventListener('input', () => {
    if (selectionSizeVal) selectionSizeVal.textContent = `${selectionSizeSlider.value}\u00a0mm`;
  });
  selectionSizeSlider.addEventListener('change', async () => {
    const newH = parseFloat(selectionSizeSlider.value);
    for (const photoId of state.selected_photos) {
      const pl = state.placements.find(p => p.photo_id === photoId);
      const aspect = pl ? pl.w_mm / pl.h_mm : 1.0;
      const newW = newH * aspect;
      if (state.locked_overrides[photoId]) {
        state.locked_overrides[photoId].h_mm = newH;
        state.locked_overrides[photoId].w_mm = newW;
      } else {
        state.size_overrides[photoId] = { w_mm: newW, h_mm: newH };
      }
    }
    await computeLayout();
  });
}

if (btnClearSelection) {
  btnClearSelection.addEventListener('click', () => {
    state.selected_photos = [];
    updateSelectionToolbar();
    renderCanvas();
  });
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
    cover: { ...state.cover },
    size_overrides: { ...state.size_overrides },
    captions: { ...state.captions },
    text_blocks: state.text_blocks.map(b => ({ ...b })),
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
  showSpinner('Génération du PDF…');
  try {
    const body = {
      album_name: state.album,
      page_w_mm: state.page_w_mm,
      page_h_mm: state.page_h_mm,
      layout_result: {
        placements: state.placements,
        page_count: state.page_count,
      },
      jpeg_quality: 85,
      target_dpi: state.config.target_dpi ?? 300,
      cover_title: state.cover.photo_id
        ? (state.cover.title || state.album || '')
        : null,
      watermark_text: state.config.watermark_text || null,
      page_bg_color: state.config.page_bg_color || '#ffffff',
      cover_bg_color: state.cover.photo_id ? (state.config.cover_bg_color || '#ffffff') : null,
      cover_photo_id: state.cover.photo_id || null,
      text_blocks: state.text_blocks || [],
      captions: { ...state.captions },
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

    // Optional: cover photo as JPG
    if (exportCoverJpgCheck?.checked && state.cover.photo_id) {
      const params = new URLSearchParams({
        album_name: state.album,
        photo_id: state.cover.photo_id,
      });
      const jpgRes = await fetch(`/api/export/cover-jpg?${params}`);
      if (jpgRes.ok) {
        const jpgBlob = await jpgRes.blob();
        const jpgUrl  = URL.createObjectURL(jpgBlob);
        const jpgA    = document.createElement('a');
        jpgA.href     = jpgUrl;
        jpgA.download = `${state.album}.jpg`;
        jpgA.click();
        URL.revokeObjectURL(jpgUrl);
      }
    }
  } finally {
    hideSpinner();
  }
}

// ---------------------------------------------------------------------------
// Caption modal
// ---------------------------------------------------------------------------

function openCaptionModal(photoId) {
  if (!captionModal || !captionTextInput) return;
  captionTextInput.value = state.captions[photoId] || '';
  captionModal.dataset.photoId = photoId;
  captionModal.style.display = 'flex';
  captionTextInput.focus();
  captionTextInput.select();
}

if (captionModal) {
  captionTextInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('caption-modal-ok').click();
    if (e.key === 'Escape') document.getElementById('caption-modal-cancel').click();
  });

  document.getElementById('caption-modal-ok').addEventListener('click', () => {
    const { photoId } = captionModal.dataset;
    const text = captionTextInput.value.trim();
    if (text) {
      state.captions[photoId] = text;
    } else {
      delete state.captions[photoId];
    }
    captionModal.style.display = 'none';
    renderCanvas();
  });

  document.getElementById('caption-modal-cancel').addEventListener('click', () => {
    captionModal.style.display = 'none';
  });
}

// ---------------------------------------------------------------------------
// Text blocks (PHO-086)
// ---------------------------------------------------------------------------

function createTextBlockEl(block, sc) {
  const el = document.createElement('div');
  el.className = 'text-block';
  el.dataset.blockId = block.id;
  el.style.left   = `${block.x_mm * sc}px`;
  el.style.top    = `${block.y_mm * sc}px`;
  el.style.width  = `${block.w_mm * sc}px`;
  el.style.height = `${block.h_mm * sc}px`;

  const content = document.createElement('div');
  content.className = 'text-block-content';
  content.textContent = block.text || '';
  content.style.fontSize  = `${(block.font_size || 24) * sc * 0.352778}px`;
  content.style.color     = block.font_color || '#000000';
  content.style.fontWeight = block.bold   ? 'bold'   : 'normal';
  content.style.fontStyle  = block.italic ? 'italic' : 'normal';
  content.style.textAlign  = ({ L: 'left', C: 'center', R: 'right' })[block.align] || 'center';
  el.appendChild(content);

  const handle = document.createElement('div');
  handle.className = 'tb-resize-handle';
  el.appendChild(handle);

  el.addEventListener('dblclick', (e) => {
    e.stopPropagation();
    openTextBlockModal(block.id);
  });

  return el;
}

const textBlockModal   = document.getElementById('text-block-modal');
const tbTextArea       = document.getElementById('tb-text');
const tbFontSize       = document.getElementById('tb-font-size');
const tbFontColor      = document.getElementById('tb-font-color');
const tbAlign          = document.getElementById('tb-align');
const tbBold           = document.getElementById('tb-bold');
const tbItalic         = document.getElementById('tb-italic');
const tbModalOk        = document.getElementById('tb-modal-ok');
const tbModalDelete    = document.getElementById('tb-modal-delete');
const tbModalCancel    = document.getElementById('tb-modal-cancel');
const btnAddText       = document.getElementById('btn-add-text');

function openTextBlockModal(blockId) {
  const block = state.text_blocks.find(b => b.id === blockId);
  if (!block || !textBlockModal) return;
  textBlockModal.dataset.blockId = blockId;
  tbTextArea.value   = block.text || '';
  tbFontSize.value   = block.font_size || 24;
  tbFontColor.value  = block.font_color || '#000000';
  tbAlign.value      = block.align || 'C';
  tbBold.checked     = !!block.bold;
  tbItalic.checked   = !!block.italic;
  textBlockModal.style.display = 'flex';
  tbTextArea.focus();
}

if (tbModalOk) {
  tbModalOk.addEventListener('click', () => {
    const { blockId } = textBlockModal.dataset;
    const block = state.text_blocks.find(b => b.id === blockId);
    if (block) {
      block.text       = tbTextArea.value;
      block.font_size  = parseFloat(tbFontSize.value) || 24;
      block.font_color = tbFontColor.value;
      block.align      = tbAlign.value;
      block.bold       = tbBold.checked;
      block.italic     = tbItalic.checked;
    }
    textBlockModal.style.display = 'none';
    renderCanvas();
  });
}

if (tbModalDelete) {
  tbModalDelete.addEventListener('click', () => {
    const { blockId } = textBlockModal.dataset;
    state.text_blocks = state.text_blocks.filter(b => b.id !== blockId);
    textBlockModal.style.display = 'none';
    renderCanvas();
  });
}

if (tbModalCancel) {
  tbModalCancel.addEventListener('click', () => {
    textBlockModal.style.display = 'none';
  });
}

if (btnAddText) {
  btnAddText.addEventListener('click', () => {
    if (!state.album) return;
    // Find the first page visible in the viewport
    let targetPage = 0;
    const mainArea = document.getElementById('main-area');
    const pages = pagesContainer.querySelectorAll('.page');
    if (mainArea && pages.length > 0) {
      const containerRect = mainArea.getBoundingClientRect();
      for (let i = 0; i < pages.length; i++) {
        const r = pages[i].getBoundingClientRect();
        if (r.bottom > containerRect.top + 60) { targetPage = i; break; }
      }
    }
    const block = {
      id: `tb_${Date.now()}`,
      page: targetPage,
      x_mm: 20, y_mm: 20, w_mm: 120, h_mm: 30,
      text: 'Titre', font_size: 24, font_color: '#000000',
      align: 'C', bold: false, italic: false,
    };
    state.text_blocks.push(block);
    renderCanvas();
    openTextBlockModal(block.id);
  });
}

// ---------------------------------------------------------------------------
// Watermark overlay (preview)
// ---------------------------------------------------------------------------

function updateWatermarkOverlays() {
  const text = state.config.watermark_text;
  document.querySelectorAll('.page').forEach(pageEl => {
    let el = pageEl.querySelector('.watermark-overlay');
    if (!text) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement('div');
      el.className = 'watermark-overlay';
      pageEl.appendChild(el);
    }
    el.textContent = text;
  });
}

// ---------------------------------------------------------------------------
// Filmstrip (PHO-072)
// ---------------------------------------------------------------------------

function renderFilmstrip() {
  if (!filmstripEl) return;
  if (!state.album) {
    filmstripEl.style.display = 'none';
    if (filmstripDivider) filmstripDivider.style.display = 'none';
    return;
  }

  const activePhotos = state.photos.filter(
    p => !state.deleted_photos.find(d => d.id === p.id)
  );
  if (activePhotos.length === 0) {
    filmstripEl.style.display = 'none';
    if (filmstripDivider) filmstripDivider.style.display = 'none';
    return;
  }

  const displayOrder = sortPhotos(activePhotos, state.config.sort_order);
  filmstripEl.style.display = 'flex';
  if (filmstripDivider) filmstripDivider.style.display = '';
  filmstripEl.innerHTML = '';

  displayOrder.forEach((photo, idx) => {
    const item = document.createElement('div');
    item.className = 'filmstrip-item';
    item.draggable = true;
    item.dataset.photoId = photo.id;
    item.dataset.index = idx;
    item.title = photo.id;

    const img = document.createElement('img');
    img.src = photo.thumb_url;
    img.alt = photo.id;
    item.appendChild(img);

    // Delete button
    const delBtn = document.createElement('button');
    delBtn.className = 'filmstrip-delete-btn';
    delBtn.textContent = '✕';
    delBtn.title = 'Supprimer de la mise en page';
    delBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      e.preventDefault();
      await deletePhoto(photo.id);
    });
    item.appendChild(delBtn);

    if (state.captions[photo.id]) {
      const dot = document.createElement('div');
      dot.className = 'filmstrip-caption-dot';
      item.appendChild(dot);
    }

    // PHO-083: always-visible action bar
    const actions = document.createElement('div');
    actions.className = 'filmstrip-actions';

    // Lock position button
    const lockBtn = document.createElement('button');
    lockBtn.className = 'filmstrip-action-btn' + (state.locked_overrides[photo.id] ? ' active' : '');
    lockBtn.title = 'Verrouiller la position';
    lockBtn.setAttribute('aria-label', 'Verrouiller la position');
    lockBtn.textContent = '🔒';
    lockBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const pl = state.placements.find(p => p.photo_id === photo.id);
      if (state.locked_overrides[photo.id]) {
        delete state.locked_overrides[photo.id];
        if (pl) pl.locked = false;
        await computeLayout();
      } else if (pl) {
        await lockAndMove(photo.id, pl.page, pl.x_mm, pl.y_mm);
      }
    });
    actions.appendChild(lockBtn);

    // Lock size button
    const sizeBtn = document.createElement('button');
    sizeBtn.className = 'filmstrip-action-btn' + (state.size_overrides[photo.id] ? ' active' : '');
    sizeBtn.title = 'Verrouiller la taille';
    sizeBtn.setAttribute('aria-label', 'Verrouiller la taille');
    sizeBtn.textContent = '⇔';
    sizeBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (state.size_overrides[photo.id]) {
        await resetSizeOverride(photo.id);
      } else {
        const pl = state.placements.find(p => p.photo_id === photo.id);
        if (pl) await setSizeOnly(photo.id, pl.w_mm, pl.h_mm);
      }
    });
    actions.appendChild(sizeBtn);

    // Set as cover button
    const coverBtn = document.createElement('button');
    const isCover = state.cover.photo_id === photo.id;
    coverBtn.className = 'filmstrip-action-btn' + (isCover ? ' is-cover' : '');
    coverBtn.title = isCover ? 'Retirer de la couverture' : 'Définir comme couverture';
    coverBtn.setAttribute('aria-label', isCover ? 'Retirer de la couverture' : 'Définir comme couverture');
    coverBtn.textContent = '⭐';
    coverBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (state.cover.photo_id === photo.id) {
        state.cover.photo_id = null;
        state.cover.title = '';
        if (coverTitleInput) coverTitleInput.value = '';
      } else {
        state.cover.photo_id = photo.id;
      }
      updateCoverUI();
      await computeLayout();
    });
    actions.appendChild(coverBtn);

    item.appendChild(actions);

    // PHO-084: page badge
    const placement = state.placements.find(p => p.photo_id === photo.id);
    if (placement !== undefined) {
      const badge = document.createElement('div');
      badge.className = 'filmstrip-page-badge';
      badge.textContent = `P${placement.page + 1}`;
      item.appendChild(badge);
    }

    item.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', String(idx));
      item.classList.add('dragging');
    });

    // PHO-085: click filmstrip item → scroll canvas to photo
    item.addEventListener('click', () => {
      const pl = state.placements.find(p => p.photo_id === photo.id);
      if (pl == null) return;
      const pages = pagesContainer.querySelectorAll('.page');
      const pageEl = pages[pl.page];
      if (pageEl) pageEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });

    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      filmstripEl.querySelectorAll('.filmstrip-item').forEach(i => i.classList.remove('drag-over'));
    });

    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      item.classList.add('drag-over');
    });

    item.addEventListener('dragleave', () => {
      item.classList.remove('drag-over');
    });

    item.addEventListener('drop', async (e) => {
      e.preventDefault();
      item.classList.remove('drag-over');
      const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
      const toIdx = parseInt(item.dataset.index, 10);
      if (fromIdx === toIdx || isNaN(fromIdx) || isNaN(toIdx)) return;

      // Reorder active photos and rebuild state.photos
      const reordered = sortPhotos(
        state.photos.filter(p => !state.deleted_photos.find(d => d.id === p.id)),
        state.config.sort_order
      );
      const [moved] = reordered.splice(fromIdx, 1);
      reordered.splice(toIdx, 0, moved);

      const deletedIds = new Set(state.deleted_photos.map(p => p.id));
      state.photos = [...reordered, ...state.photos.filter(p => deletedIds.has(p.id))];

      state.config.sort_order = 'manual';
      if (sortOrderSel) sortOrderSel.value = 'manual';

      await computeLayout();
    });

    filmstripEl.appendChild(item);
  });
}

// ---------------------------------------------------------------------------
// Filmstrip divider resize
// ---------------------------------------------------------------------------

(function initDividerResize() {
  if (!filmstripDivider || !filmstripEl) return;
  let startX, startW;
  filmstripDivider.addEventListener('mousedown', (e) => {
    startX = e.clientX;
    startW = filmstripEl.offsetWidth;
    filmstripDivider.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (startX === undefined) return;
    const delta = startX - e.clientX;
    const newW = Math.max(60, Math.min(400, startW + delta));
    filmstripEl.style.width = `${newW}px`;
  });
  document.addEventListener('mouseup', () => {
    if (startX === undefined) return;
    startX = undefined;
    filmstripDivider.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}());

// PHO-085: scroll canvas → highlight filmstrip items
(function initScrollSync() {
  const mainArea = document.getElementById('main-area');
  if (!mainArea) return;
  let scrollRafPending = false;
  mainArea.addEventListener('scroll', () => {
    if (scrollRafPending) return;
    scrollRafPending = true;
    requestAnimationFrame(() => {
      scrollRafPending = false;
      if (!filmstripEl) return;
      const rect = mainArea.getBoundingClientRect();
      const centerY = rect.top + rect.height / 2;
      let closestPage = 0;
      let closestDist = Infinity;
      pagesContainer.querySelectorAll('.page').forEach((pageEl, idx) => {
        const pr = pageEl.getBoundingClientRect();
        const dist = Math.abs(pr.top + pr.height / 2 - centerY);
        if (dist < closestDist) { closestDist = dist; closestPage = idx; }
      });
      const photosOnPage = new Set(
        state.placements.filter(p => p.page === closestPage).map(p => p.photo_id)
      );
      filmstripEl.querySelectorAll('.filmstrip-item').forEach(item => {
        if (photosOnPage.has(item.dataset.photoId)) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    });
  }, { passive: true });
}());

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

init();
