const fileInput = document.getElementById('fileInput');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const uploadForm = document.getElementById('uploadForm');
const progress = document.getElementById('progress');

fileInput.addEventListener('change', () => {
  const count = fileInput.files.length;
  fileNameDisplay.textContent = count > 0 ? `${count} files selected` : '';
});

// bu method formu flaska gönderiyor.
uploadForm.addEventListener('submit', (e) => {
  if (fileInput.files.length === 0) {
    e.preventDefault();
    alert("Please select at least one file to upload.");
    return;
  }
  progress.classList.add('is-active');
});

// ---- Yan Panel (Drawer) Optimizasyonu ----
const overlay = document.getElementById('overlay');
const drawer = document.getElementById('drawer');

//aside da çıkacak eleanlar
const els = {
    date: document.getElementById('metaDate'),
    dim: document.getElementById('metaDim'),
    scanDate: document.getElementById('metaScanDate'),
    vendor: document.getElementById('metaVendor'),
    mag: document.getElementById('metaMag'),
    levelCount: document.getElementById('metaLevelCount'),
    mpp: document.getElementById('metaMpp'),
    height: document.getElementById('height'),
    width: document.getElementById('width')
};

// Panel açma/kapama mantığı
const toggleDrawer = (isOpen) => {
    overlay.classList.toggle('is-open', isOpen);
    drawer.classList.toggle('is-open', isOpen);
    drawer.setAttribute('aria-hidden', !isOpen);
};

document.getElementById('drawerClose').addEventListener('click', () => toggleDrawer(false));
overlay.addEventListener('click', () => toggleDrawer(false));
document.addEventListener('keydown', e => e.key === 'Escape' && toggleDrawer(false));

// Dosya tıklama olayları
document.querySelectorAll('.result-row--clickable').forEach(row => {
    row.addEventListener('click', async () => {
        const { name, status, match } = row.dataset;
        const isAdded = status === 'added';
        
        document.getElementById('drawerFilename').textContent = name;
        document.getElementById('drawerStatus').className = `drawer__status drawer__status--${isAdded ? 'added' : 'duplicate'}`;
        document.getElementById('drawerStatus').textContent = isAdded ? 'Added' : 'Duplicate';
        document.getElementById('metaNote').classList.toggle('is-visible', !isAdded);
        if (!isAdded) document.getElementById('metaMatch').textContent = match;

        Object.values(els).forEach(el => el.textContent = "Yükleniyor...");
        toggleDrawer(true);

        try {
            const fetchName = (!isAdded && match !== 'Unknown' && match) ? match : name;
            const res = await fetch(`/slide-details/${encodeURIComponent(fetchName)}`);
            if (!res.ok) throw new Error();
            
            const { date, properties: p = {} } = await res.json();
            
            // JSON Parse ve HTML Güncelleme (Çok daha kısa)
            const w = p['openslide.level[0].width'], h = p['openslide.level[0].height'];
            const mppX = parseFloat(p['openslide.mpp-x']), mppY = parseFloat(p['openslide.mpp-y']);
            const mag = p['openslide.objective-power'] || p['aperio.AppMag'];

            els.date.textContent = date || "Unknown";
            els.dim.textContent = (w && h) ? `${w} × ${h} px` : "Unknown";
            els.width.textContent = p['openslide.level[0].width'] || "Unknown";
            els.height.textContent = p['openslide.level[0].height'] || "Unknown";
            els.scanDate.textContent = p['aperio.Date'] || p['tiff.DateTime'] || "Unknown";
            els.vendor.textContent = p['openslide.vendor'] || "Unknown";
            els.mag.textContent = mag ? `${mag}x` : "Unknown";
            els.levelCount.textContent = p['openslide.level-count'] || "Unknown";

            
            els.mpp.textContent = (mppX && mppY) 
                ? (mppX === mppY ? `${mppX.toFixed(4)} µm/px` : `${mppX.toFixed(4)} x ${mppY.toFixed(4)} µm/px`) 
                : "Unknown";

        } catch {
            Object.values(els).forEach(el => el.textContent = "Not Found");
        }
    });
});
