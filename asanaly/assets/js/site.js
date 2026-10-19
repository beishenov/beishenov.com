/* Minimal runtime replacing the Adobe Portfolio bundle:
 *  - responsive (hamburger) navigation
 *  - image lightbox for project modules
 */
(function () {
  'use strict';

  var root = document.documentElement;

  // ---- Responsive nav -----------------------------------------------------
  var openBtn = document.querySelector('.js-hamburger');
  var closeBtn = document.querySelector('.js-close-responsive-nav');

  function openNav() { root.classList.add('show-responsive-nav'); }
  function closeNav() { root.classList.remove('show-responsive-nav'); }

  if (openBtn) openBtn.addEventListener('click', openNav);
  if (closeBtn) closeBtn.addEventListener('click', closeNav);

  // ---- Contact form (Adobe's backend is gone; hand off to the mail client) --
  var form = document.querySelector('form.contact-form');
  if (form) {
    var mailLink = document.querySelector('a[href^="mailto:"]');
    var to = mailLink ? mailLink.getAttribute('href').slice(7) : '';
    var submit = form.querySelector('.js-submit');
    var send = function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      var name = form.querySelector('[name="field1"]').value.trim();
      var email = form.querySelector('[name="email"]').value.trim();
      var msg = form.querySelector('[name="field2"]').value.trim();
      var body = msg + '\n\n— ' + name + ' <' + email + '>';
      window.location.href = 'mailto:' + to +
        '?subject=' + encodeURIComponent('Message from ' + (name || email)) +
        '&body=' + encodeURIComponent(body);
      form.style.display = 'none';
      var sent = form.parentElement.querySelector('.contact-form-sent');
      if (sent) sent.style.display = 'block';
    };
    if (submit) submit.addEventListener('click', send);
    form.addEventListener('submit', send);
  }

  // ---- Photo grids ----------------------------------------------------------
  // Items carry inline width/flex-grow; Adobe's "flexbox-sizer" only toggled these classes.
  Array.prototype.forEach.call(document.querySelectorAll('.grid--main'), function (g) {
    g.classList.add('grid--ready');
  });
  Array.prototype.forEach.call(document.querySelectorAll('.js-grid-spacer'), function (s) {
    s.classList.add('grid__item-spacer');
  });

  // ---- Lightbox -----------------------------------------------------------
  var items = [];
  Array.prototype.forEach.call(document.querySelectorAll('.js-lightbox[data-src]'), function (el) {
    items.push({ el: el, src: el.getAttribute('data-src'), caption: '' });
  });
  Array.prototype.forEach.call(document.querySelectorAll('.grid__item-container'), function (el) {
    var thumb = el.querySelector('img.grid__item-image');
    if (!thumb) return;
    var candidates = (thumb.getAttribute('srcset') || '').split(',');
    var largest = candidates.length ? candidates[candidates.length - 1].trim().split(/\s+/)[0] : '';
    var cap = el.querySelector('.grid__caption-text');
    el.classList.add('hoverable');
    items.push({ el: el, src: largest || thumb.getAttribute('src'), caption: cap ? cap.textContent : '' });
  });
  if (!items.length) return;

  var overlay = document.createElement('div');
  overlay.className = 'site-lightbox';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.innerHTML =
    '<button class="site-lightbox__close" aria-label="Close">&times;</button>' +
    '<button class="site-lightbox__prev" aria-label="Previous">&#8249;</button>' +
    '<button class="site-lightbox__next" aria-label="Next">&#8250;</button>' +
    '<figure class="site-lightbox__figure"><img class="site-lightbox__img" alt="">' +
    '<figcaption class="site-lightbox__caption"></figcaption></figure>';
  document.body.appendChild(overlay);

  var img = overlay.querySelector('.site-lightbox__img');
  var caption = overlay.querySelector('.site-lightbox__caption');
  var current = -1;

  function show(index) {
    current = (index + items.length) % items.length;
    img.src = items[current].src;
    img.alt = items[current].caption;
    caption.textContent = items[current].caption;
    caption.style.display = items[current].caption ? '' : 'none';
    overlay.classList.add('is-open');
    root.classList.add('lightbox-enabled');
  }

  function hide() {
    overlay.classList.remove('is-open');
    root.classList.remove('lightbox-enabled');
    img.removeAttribute('src');
    current = -1;
  }

  items.forEach(function (item, i) {
    item.el.classList.add('lightbox-link');
    item.el.addEventListener('click', function (e) {
      e.preventDefault();
      show(i);
    });
  });

  overlay.querySelector('.site-lightbox__close').addEventListener('click', hide);
  overlay.querySelector('.site-lightbox__prev').addEventListener('click', function (e) {
    e.stopPropagation();
    show(current - 1);
  });
  overlay.querySelector('.site-lightbox__next').addEventListener('click', function (e) {
    e.stopPropagation();
    show(current + 1);
  });
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay || e.target === img || e.target === caption) hide();
  });

  document.addEventListener('keydown', function (e) {
    if (current < 0) return;
    if (e.key === 'Escape') hide();
    else if (e.key === 'ArrowLeft') show(current - 1);
    else if (e.key === 'ArrowRight') show(current + 1);
  });
})();
