// hotfix.js: pequeñas correcciones sin tocar app.js

(function () {
  function fixCartImagesDom() {
    try {
      const body = document.getElementById('cart-items');
      if (!body) return;
      const imgs = body.querySelectorAll('.cart-item img');
      if (!imgs || !imgs.length) return;
      // Obtener los items reales para conocer portada_url
      fetch('/api/v1/cart', { credentials: 'same-origin' })
        .then(r => r.json()).then(cart => {
          const items = Object.values(cart || {});
          imgs.forEach((img, idx) => {
            const it = items[idx] || {};
            const src = it.portada_url || it.imagen_url || ('/static/img/productos/' + (it.id || 'item') + '.png');
            if (!img.getAttribute('src')) img.setAttribute('src', src);
            img.onerror = () => { img.onerror = null; img.src = 'https://placehold.co/80x60?text=IMG'; };
          });
        }).catch(() => {});
    } catch {}
  }

  // Evita envíos duplicados del checkout
  function preventDuplicateCheckoutSubmits() {
    try {
      document.addEventListener('submit', function (e) {
        const form = e.target;
        if (form && form.id === 'checkout-form') {
          if (window.__checkout_in_progress) {
            e.preventDefault();
            return;
          }
          window.__checkout_in_progress = true;
          const sb = document.getElementById('checkout-submit');
          if (sb) sb.disabled = true;
        }
      }, true);

      // Cuando se cierra el checkout, limpiar flag
      const exitCleanup = () => { try { window.__checkout_in_progress = false; } catch {} };
      document.addEventListener('click', function (e) {
        const btn = e.target.closest && e.target.closest('#checkout-cancel, #success-close');
        if (btn) exitCleanup();
      }, true);
    } catch {}
  }

  // Observar cambios en el carrito para aplicar imágenes
  function observeCart() {
    try {
      const body = document.getElementById('cart-items');
      if (!body || !window.MutationObserver) return;
      const obs = new MutationObserver(() => fixCartImagesDom());
      obs.observe(body, { childList: true, subtree: true });
    } catch {}
  }

  document.addEventListener('DOMContentLoaded', function () {
    preventDuplicateCheckoutSubmits();
    observeCart();
    // primera pasada
    fixCartImagesDom();
  });
})();

