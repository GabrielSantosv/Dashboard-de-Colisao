(() => {
  const styleClearButtons = () => {
    document.querySelectorAll('.dash-dropdown-clear').forEach((el) => {
      el.style.width = '24px';
      el.style.height = '24px';
      el.style.minWidth = '24px';
      el.style.minHeight = '24px';
      el.style.display = 'flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
      el.style.borderRadius = '6px';
      el.style.marginLeft = '4px';
      el.style.cursor = 'pointer';
    });
  };

  const schedule = () => window.requestAnimationFrame(styleClearButtons);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', schedule, { once: true });
  } else {
    schedule();
  }

  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
