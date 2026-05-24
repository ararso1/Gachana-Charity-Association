/**
 * Portal mobile navigation — slide-in sidebar from the left.
 */
(function () {
  const sidebar = document.getElementById('portal-sidebar');
  const overlay = document.getElementById('portal-sidebar-overlay');
  const toggle = document.getElementById('portal-menu-toggle');
  const closeBtn = document.getElementById('portal-sidebar-close');

  if (!sidebar || !overlay || !toggle) {
    return;
  }

  const MQ = window.matchMedia('(max-width: 991.98px)');

  function isMobile() {
    return MQ.matches;
  }

  function setOpen(open) {
    sidebar.classList.toggle('is-open', open);
    overlay.classList.toggle('is-visible', open);
    overlay.setAttribute('aria-hidden', open ? 'false' : 'true');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.body.classList.toggle('portal-nav-open', open);
  }

  function openNav() {
    if (!isMobile()) return;
    setOpen(true);
  }

  function closeNav() {
    setOpen(false);
  }

  function toggleNav() {
    if (!isMobile()) return;
    setOpen(!sidebar.classList.contains('is-open'));
  }

  toggle.addEventListener('click', toggleNav);
  overlay.addEventListener('click', closeNav);

  if (closeBtn) {
    closeBtn.addEventListener('click', closeNav);
  }

  sidebar.querySelectorAll('.portal-sidebar__nav a, .portal-sidebar__footer a').forEach((link) => {
    link.addEventListener('click', () => {
      if (isMobile()) closeNav();
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
      closeNav();
    }
  });

  MQ.addEventListener('change', (e) => {
    if (!e.matches) closeNav();
  });

  window.addEventListener('resize', () => {
    if (!isMobile()) closeNav();
  });
})();
