'use strict';
const copyButton = document.querySelector('[data-copy-handle]');
const copyStatus = document.getElementById('copy-status');
const handle = document.getElementById('douyin-handle');
if (copyButton && copyStatus && handle && navigator.clipboard && window.isSecureContext) {
  copyButton.hidden = false;
  copyButton.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(handle.textContent.trim());
      copyStatus.textContent = '已复制。在抖音搜索，就能按这个账号查找我。';
    } catch {
      copyStatus.textContent = '浏览器未允许复制，请长按或选中上方抖音号复制。';
    }
  });
}
