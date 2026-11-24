/* VelaOra shared behaviour: header, menu, lead forms, one gentle popup. */
(function () {
  var FORMSPREE = 'https://formspree.io/f/mrevbyoa';
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function track(name, params) { if (typeof gtag === 'function') gtag('event', name, params || {}); }

  /* Header shadow */
  var header = document.getElementById('vo-header');
  if (header) window.addEventListener('scroll', function () { header.classList.toggle('is-scrolled', window.scrollY > 10); }, { passive: true });

  /* Topics dropdown */
  document.querySelectorAll('.vo-dd').forEach(function (dd) {
    var btn = dd.querySelector('.vo-dd-btn');
    function set(open) { dd.classList.toggle('open', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    btn.addEventListener('click', function (e) { e.stopPropagation(); set(!dd.classList.contains('open')); });
    dd.addEventListener('mouseenter', function () { if (window.matchMedia('(hover:hover)').matches) set(true); });
    dd.addEventListener('mouseleave', function () { if (window.matchMedia('(hover:hover)').matches) set(false); });
    document.addEventListener('click', function (e) { if (!dd.contains(e.target)) set(false); });
  });

  /* Mobile drawer */
  var burger = document.querySelector('.vo-burger'), drawer = document.getElementById('vo-drawer');
  if (burger && drawer) burger.addEventListener('click', function () {
    var open = !drawer.classList.contains('open');
    drawer.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.body.style.overflow = open ? 'hidden' : '';
  });

  /* Mark current page in nav */
  var here = location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/';
  document.querySelectorAll('.vo-nav > a, .vo-dd-menu a').forEach(function (a) {
    if (a.getAttribute('href') === here) a.setAttribute('aria-current', 'page');
  });

  /* Old one-page anchors (e.g. velaora.co.nz/#wellness-club in old posts) now go to the new pages */
  if (here === '/' && location.hash) {
    var map = { '#perimenopause': '/perimenopause', '#menopause': '/menopause', '#fertility': '/fertility', '#anxiety': '/anxiety',
      '#separation': '/separation', '#articles': '/articles', '#wellness-club': '/wellness-club', '#wellness': '/wellness-club',
      '#about': '/about', '#contact': '/about#contact', '#news': '/resources', '#resources': '/resources' };
    if (map[location.hash]) location.replace(map[location.hash]);
    else if (location.hash === '#subscribe') setTimeout(function () { var f = document.querySelector('.vo-footer-band'); if (f) f.scrollIntoView(); }, 50);
  }

  /* Lead forms (GP guide, quiz): send to Formspree, then unlock the guide */
  document.querySelectorAll('form[data-vo-lead]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type=submit]'), msg = form.parentNode.querySelector('.vo-msg');
      var label = btn.textContent; btn.disabled = true; btn.textContent = 'Sending…';
      var data = new FormData(form);
      data.append('source', form.getAttribute('data-vo-lead'));
      data.append('page', location.pathname);
      if (!data.get('_subject')) data.append('_subject', 'New VelaOra signup: ' + form.getAttribute('data-vo-lead'));
      fetch(FORMSPREE, { method: 'POST', body: data, headers: { Accept: 'application/json' } }).then(function (r) {
        if (!r.ok) throw new Error('bad');
        store('velaora_gp_unlocked', '1'); store('vo_subscribed', '1');
        track('generate_lead', { source: form.getAttribute('data-vo-lead') });
        var after = form.getAttribute('data-vo-after');
        if (after === 'stay') {
          var ok = form.getAttribute('data-vo-ok');
          if (ok && msg) { msg.className = 'vo-msg ok'; msg.textContent = ok; form.style.display = 'none'; }
          form.dispatchEvent(new CustomEvent('vo:done')); return;
        }
        location.href = '/gp-guide#guide';
      }).catch(function () {
        btn.disabled = false; btn.textContent = label;
        if (msg) { msg.className = 'vo-msg err'; msg.textContent = 'Sorry, that didn\'t send. Please try again.'; }
      });
    });
  });

  /* Newsletter + other forms: analytics only */
  document.querySelectorAll('form[data-vo-track]').forEach(function (f) {
    f.addEventListener('submit', function () { store('vo_subscribed', '1'); track('newsletter_signup', { location: f.getAttribute('data-vo-track') }); });
  });
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href*="iherb.com"], a[href*="rcode="]');
    if (a) track('affiliate_click', { link_url: a.href });
  });

  /* One gentle popup: never mid-read. Shows on exit intent (desktop) or when you reach the end of a page (mobile).
     Not on quiz, guide or separation pages. At most once every 14 days, never after signing up. */
  var pop = document.getElementById('vo-pop');
  var skip = /^\/(quiz|gp-guide|separation|privacy|terms|restora)/.test(here);
  var last = parseInt(store('vo_pop_seen') || '0', 10);
  var recently = Date.now() - last < 14 * 864e5;
  if (pop && !skip && !recently && !store('vo_subscribed') && !store('velaora_gp_unlocked')) {
    var shown = false, armed = false;
    setTimeout(function () { armed = true; }, 12000);
    function show(why) {
      if (shown || !armed) return; shown = true;
      pop.classList.add('open'); store('vo_pop_seen', String(Date.now())); track('popup_shown', { trigger: why });
    }
    document.addEventListener('mouseout', function (e) { if (!e.relatedTarget && e.clientY < 8) show('exit'); });
    window.addEventListener('scroll', function () {
      var h = document.documentElement;
      if ((h.scrollTop + window.innerHeight) / h.scrollHeight > 0.9) show('end_of_page');
    }, { passive: true });
  }
  function closePop() { if (pop) pop.classList.remove('open'); }
  if (pop) {
    pop.addEventListener('click', function (e) { if (e.target === pop) closePop(); });
    pop.querySelector('.vo-pop-x').addEventListener('click', closePop);
    pop.querySelector('.vo-pop-no').addEventListener('click', closePop);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePop(); });
  }
})();
