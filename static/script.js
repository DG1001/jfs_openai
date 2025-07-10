// Service Worker Registration
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(console.error);
}

// Feedback message
function showMessage(msg, isError) {
  const el = document.getElementById('message');
  el.textContent = msg;
  el.style.color = isError ? 'red' : 'green';
  setTimeout(() => { el.textContent = ''; }, 3000);
}

// Upload page logic
if (document.getElementById('uploadForm')) {
  const form = document.getElementById('uploadForm');
  const fileInput = document.getElementById('image');
  const commentInput = document.getElementById('comment');
  const button = form.querySelector('button[type="submit"]');
  const loading = document.getElementById('loading');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    button.disabled = true;
    loading.hidden = false;
    const formData = new FormData();
    formData.append('image', fileInput.files[0]);
    formData.append('comment', commentInput.value);
    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.success) {
        showMessage('Upload erfolgreich', false);
        form.reset();
      } else {
        showMessage(data.error || 'Fehler', true);
      }
    } catch (err) {
      showMessage('Netzwerkfehler', true);
    } finally {
      button.disabled = false;
      loading.hidden = true;
    }
  });

// Gallery page logic
} else if (document.getElementById('gallery')) {
  const gallery = document.getElementById('gallery');
  async function loadImages() {
    try {
      const res = await fetch('/api/images');
      const data = await res.json();
      gallery.innerHTML = '';
      const now = Date.now();
      data.forEach(item => {
        const ts = new Date(item.timestamp).getTime();
        const age = (now - ts) / 1000;
        const div = document.createElement('div');
        div.className = 'photo';
        if (age >= 5) div.classList.add('fade');
        const img = document.createElement('img');
        img.src = '/uploads/' + item.filename;
        const p = document.createElement('p');
        p.textContent = item.comment || '';
        div.appendChild(img);
        div.appendChild(p);
        gallery.appendChild(div);
      });
    } catch (err) {
      console.error(err);
    }
  }
  loadImages();
  setInterval(loadImages, 2000);
}
