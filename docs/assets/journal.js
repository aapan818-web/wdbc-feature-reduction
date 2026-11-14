(() => {
  'use strict';
  const dialog = document.querySelector('.lightbox');
  let galleryLinks = [], currentIndex = 0, returnFocus = null;
  const showPhoto = (index) => {
    currentIndex = (index + galleryLinks.length) % galleryLinks.length;
    const link = galleryLinks[currentIndex];
    const photo = dialog.querySelector('[data-lightbox-image]');
    photo.src = link.href;
    photo.alt = link.dataset.caption;
    dialog.querySelector('[data-lightbox-caption]').textContent = link.dataset.caption;
    dialog.querySelector('[data-lightbox-counter]').textContent = `${currentIndex + 1} / ${galleryLinks.length}`;
    dialog.querySelector('[data-lightbox-original]').href = link.href;
  };
  document.querySelectorAll('[data-gallery]').forEach(gallery => {
    const items = Array.from(gallery.querySelectorAll('.gallery-item'));
    const filters = Array.from(gallery.querySelectorAll('[data-filter]'));
    const more = gallery.querySelector('[data-more]');
    const limit = Number(gallery.dataset.limit) || 12;
    let selected = 'all', shown = limit;
    const matching = () => items.filter(item => selected === 'all' || item.dataset.group === selected);
    const render = () => {
      const filtered = matching();
      items.forEach(item => { item.hidden = true; });
      filtered.slice(0, shown).forEach(item => { item.hidden = false; });
      filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === selected)));
      more.hidden = shown >= filtered.length;
      more.textContent = `再看 ${Math.min(limit, Math.max(0, filtered.length - shown))} 张 ↓`;
      gallery.querySelector('[data-gallery-count]').textContent = `${filtered.length} 张照片`;
    };
    gallery.querySelector('[data-filters]').hidden = filters.length <= 2;
    filters.forEach(button => button.addEventListener('click', () => {
      selected = button.dataset.filter; shown = limit; render();
    }));
    more.addEventListener('click', () => {
      const filtered = matching(), next = filtered[shown];
      shown += limit; render();
      if (next) next.querySelector('a').focus({preventScroll:true});
    });
    items.forEach(item => item.querySelector('.photo-link').addEventListener('click', event => {
      if (!dialog || typeof dialog.showModal !== 'function' || event.metaKey || event.ctrlKey || event.shiftKey) return;
      event.preventDefault();
      galleryLinks = matching().map(item => item.querySelector('.photo-link'));
      returnFocus = event.currentTarget;
      showPhoto(galleryLinks.indexOf(returnFocus)); dialog.showModal();
    }));
    render();
  });
  if (dialog) {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.querySelector('[data-prev]').addEventListener('click', () => showPhoto(currentIndex - 1));
    dialog.querySelector('[data-next]').addEventListener('click', () => showPhoto(currentIndex + 1));
    dialog.addEventListener('keydown', event => {
      if (event.key === 'ArrowRight') { event.preventDefault(); showPhoto(currentIndex + 1); }
      if (event.key === 'ArrowLeft') { event.preventDefault(); showPhoto(currentIndex - 1); }
    });
    dialog.addEventListener('close', () => { if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true}); });
    let touchX = null;
    dialog.querySelector('[data-lightbox-image]').addEventListener('touchstart', event => { touchX = event.changedTouches[0].clientX; }, {passive:true});
    dialog.querySelector('[data-lightbox-image]').addEventListener('touchend', event => {
      if (touchX === null) return;
      const delta = event.changedTouches[0].clientX - touchX;
      if (Math.abs(delta) > 60) showPhoto(currentIndex + (delta < 0 ? 1 : -1));
      touchX = null;
    }, {passive:true});
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const status = document.querySelector('[data-copy-status]');
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        status.textContent = '已复制，去抖音粘贴搜索。';
      } catch {
        const input = document.querySelector('#douyin-handle');
        input.focus(); input.select(); input.setSelectionRange(0, input.value.length);
        status.textContent = '号码已选中，可以长按或按快捷键复制。';
      }
    });
  });
  document.querySelectorAll('[data-share]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const status = document.querySelector('.share-status');
      try {
        await navigator.clipboard.writeText(document.querySelector('link[rel=canonical]').href);
        status.textContent = '这一页的链接已复制。';
      } catch {
        status.textContent = '可以从浏览器地址栏复制本页链接。';
      }
    });
  });
  document.querySelectorAll('.mobile-menu a').forEach(link => link.addEventListener('click', () => { link.closest('details').open = false; }));
})();
