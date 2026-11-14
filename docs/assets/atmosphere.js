(() => {
  'use strict';
  const root = document.documentElement;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const desktop = window.matchMedia('(min-width: 801px) and (pointer: fine)');
  const toggles = Array.from(document.querySelectorAll('[data-motion-toggle]'));
  const stage = document.querySelector('[data-scenic-stage]');
  const frames = stage ? Array.from(stage.querySelectorAll('[data-scene]')) : [];
  const sceneButtons = stage ? Array.from(stage.querySelectorAll('[data-scene-select]')) : [];
  let paused = false;
  try { paused = localStorage.getItem('gavin-motion-paused') === 'true'; } catch {}
  let motion = false, stageVisible = false, current = 0, sequence = 0, timer = null, scrollFrame = null;
  const stopTimer = () => { clearTimeout(timer); timer = null; };
  const canPlay = () => motion && stageVisible && !document.hidden;
  const updateStageState = () => {
    if (stage) stage.dataset.sceneVisible = String(stageVisible && !document.hidden);
  };
  const schedule = () => {
    stopTimer();
    if (stage && canPlay()) timer = setTimeout(async () => {
      if (canPlay()) await selectScene((current + 1) % frames.length, false);
      schedule();
    }, 12000);
  };
  async function selectScene(index, manual = true) {
    const request = ++sequence;
    const frame = frames[index];
    if (!frame) return;
    const image = frame.querySelector('img');
    if (manual) stopTimer();
    try {
      if (image.dataset.src) {
        image.src = image.dataset.src;
        image.loading = 'eager';
        delete image.dataset.src;
      }
      await image.decode();
      if (request !== sequence || (!manual && !canPlay())) return;
      frames.forEach((item,i) => item.classList.toggle('is-active',i === index));
      sceneButtons.forEach((button,i) => button.setAttribute('aria-pressed',String(i === index)));
      current = index;
      stage.querySelector('.scene-status').textContent = '';
    } catch {
      if (manual && request === sequence) stage.querySelector('.scene-status').textContent = '图片未加载，请再试一次。';
    } finally {
      if (manual) schedule();
    }
  }
  const syncMotion = () => {
    motion = !paused && !reduce.matches;
    root.dataset.motion = motion ? 'on' : 'off';
    toggles.forEach(button => {
      button.hidden = false;
      button.disabled = reduce.matches;
      button.setAttribute('aria-pressed',String(motion));
      button.setAttribute('aria-label',reduce.matches ? '遵循系统设置，已减少动态效果' : motion ? '暂停页面动画' : '开启页面动画');
      button.querySelector('[data-motion-label]').textContent = reduce.matches ? '静态模式' : motion ? '暂停动效' : '开启动效';
      button.querySelector('.motion-icon').textContent = motion ? 'Ⅱ' : '▷';
    });
    if (!motion) {
      if (stage) stage.style.setProperty('--scene-shift','0px');
      document.querySelectorAll('.reveal-ready').forEach(item => item.classList.add('is-revealed'));
    }
    updateStageState(); schedule();
  };
  toggles.forEach(button => button.addEventListener('click',() => {
    paused = !paused;
    try { localStorage.setItem('gavin-motion-paused',String(paused)); } catch {}
    syncMotion();
  }));
  reduce.addEventListener('change',syncMotion);
  if (stage) {
    stage.querySelector('.scene-controls').hidden = false;
    sceneButtons.forEach((button,index) => button.addEventListener('click',() => selectScene(index)));
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(entries => {
        stageVisible = entries[0].isIntersecting;
        updateStageState(); schedule();
      },{threshold:0.05}).observe(stage);
    } else { stageVisible = true; }
    const parallax = () => {
      scrollFrame = null;
      if (!canPlay() || !desktop.matches) return;
      const shift = Math.max(0,Math.min(36,-stage.getBoundingClientRect().top * 0.055));
      stage.style.setProperty('--scene-shift',`${shift.toFixed(1)}px`);
    };
    addEventListener('scroll',() => {
      if (canPlay() && desktop.matches && scrollFrame === null) scrollFrame = requestAnimationFrame(parallax);
    },{passive:true});
    desktop.addEventListener('change',() => { stage.style.setProperty('--scene-shift','0px'); });
  }
  document.addEventListener('visibilitychange',() => { updateStageState(); schedule(); });
  syncMotion();
  if (motion && 'IntersectionObserver' in window) {
    const candidates = document.querySelectorAll('.section-heading,.portal,.record,.gallery-item,.timeline article,.experience-bottom>div,.research-project,.me-intro,.pet-intro,.next-pages,.follow-grid');
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-revealed'); observer.unobserve(entry.target);
      }
    }),{threshold:0.03,rootMargin:'0px 0px -20px 0px'});
    candidates.forEach((item,index) => {
      if (item.getBoundingClientRect().top < innerHeight && item.offsetHeight) return;
      item.classList.add('reveal-ready');
      item.style.setProperty('--reveal-delay',`${Math.min(index % 3,2) * 55}ms`);
      observer.observe(item);
    });
  }
})();
