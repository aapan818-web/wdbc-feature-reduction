
(() => {
  'use strict';
  const result = window.PROJECT_RESULTS;
  if (!result || !result.models) return;
  const fmt = (v, n=3) => v == null ? '未定义' : Number(v).toFixed(n);
  const text = (id, value) => { const el = document.getElementById(id); if(el) el.textContent = value; };
  function show(id) {
    const model = result.models[id];
    if(!model || !['LR5','LR10','LR30'].includes(id)) return;
    const t=model.test, c=model.cv;
    document.querySelectorAll('[data-model]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.model === id)));
    document.querySelectorAll('[data-model-row]').forEach(r => r.classList.toggle('model-current',r.dataset.modelRow===id));
    text('model-status',`当前展示 ${id}：${model.k} 个特征。开发集 CV AUC ${fmt(c.mean_auc)} ± ${fmt(c.sd_auc)}。`);
    text('metric-auc',fmt(t.auc));text('metric-auc-ci',`95% CI [${fmt(t.auc_ci_low)}, ${fmt(t.auc_ci_high)}]`);
    text('metric-sensitivity',fmt(t.sensitivity));text('metric-specificity',fmt(t.specificity));text('metric-errors',`${t.fn} / ${t.fp}`);
    for(const cell of ['tn','fp','fn','tp']) text('cm-'+cell,t[cell]);
    const list=document.getElementById('feature-list');list.replaceChildren();
    for(const f of model.features){const item=document.createElement('span');item.className='feature-token';item.textContent=f;list.appendChild(item);}
  }
  document.querySelectorAll('[data-model]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.model)));
  const initial=document.querySelector('[data-model][aria-pressed="true"]');if(initial)show(initial.dataset.model);
})();
