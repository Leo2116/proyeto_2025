// static/js/app.js

document.addEventListener('DOMContentLoaded', () => {
  // ==========================
  // DOM refs (búsqueda + UI)
  // ==========================
  const searchBar     = document.getElementById('search-bar');        // legacy (oculto)
  const searchBtn     = document.getElementById('search-btn');        // puede no existir
  const heroInput     = document.getElementById('search-input');
  const heroBtn       = document.getElementById('execute-search-btn');
  const legacyInput   = document.getElementById('search-input-legacy');
  const legacyBtn     = document.getElementById('execute-search-btn-legacy');

  const productBox    = document.getElementById('product-results');
  const statusMessage = document.getElementById('status-message');

  // Auth UI (modal único)
  const authModal   = document.getElementById('auth-modal');
  const authClose   = document.getElementById('auth-close');
  const tabLogin    = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');

  const loginForm   = document.getElementById('login-form');
  const loginError  = document.getElementById('login-error');
  // reCAPTCHA widget ids (render explícito)
  let loginRecaptchaId = null;
  let registerRecaptchaId = null;

  function getGre() {
    try {
      if (window.grecaptcha) {
        return window.grecaptcha.enterprise || window.grecaptcha;
      }
    } catch {}
    return null;
  }

  const registerForm = document.getElementById('register-form');
  const registerMsg  = document.getElementById('register-msg');
  const registerErr  = document.getElementById('register-error');

  const userBtn = document.getElementById('user-btn');
  const profileModal = document.getElementById('profile-modal');
  const profileClose = document.getElementById('profile-close');
  const profileOk    = document.getElementById('profile-ok');
  const profileLogout= document.getElementById('profile-logout');
  const profName     = document.getElementById('profile-nombre');
  const profEmail    = document.getElementById('profile-email');
  const profVerif    = document.getElementById('profile-verificado');
  const adminBtn = document.getElementById('admin-btn');

  // Carrito
  const cartBtn     = document.getElementById('cart-btn');
  const cartBadge   = document.getElementById('cart-badge');
  const drawer      = document.getElementById('cart-drawer');
  const drawerClose = document.getElementById('cart-close');
  const drawerBody  = document.getElementById('cart-items');
  const drawerTotal = document.getElementById('cart-total');
  const drawerClear = document.getElementById('cart-clear');
  const drawerBuy   = document.getElementById('cart-buy');
  const backdrop    = document.getElementById('drawer-backdrop');

  const API_PRODUCTS = '/api/v1/catalogo/productos';

  // ==========================
  // Helpers
  // ==========================
  const fmtQ = n => `Q${(Number(n) || 0).toFixed(2)}`;

  function showStatus(msg, isError = false) {
    if (!statusMessage) return;
    statusMessage.textContent = msg;
    statusMessage.classList.remove('hidden');
    statusMessage.style.backgroundColor = isError ? '#f8d7da' : '#d4edda';
    statusMessage.style.color = isError ? '#721c24' : '#155724';
  }
  function hideStatus() { statusMessage?.classList.add('hidden'); }

  async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...opts
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
    return data;
  }

  // ==========================
  // Productos
  // ==========================
  function normalizeProduct(p) {
    const id =
      p.id || p.id_producto || p.sku || p.isbn ||
      (p.nombre ? p.nombre.toLowerCase().replace(/\s+/g, '_') : null) ||
      Math.random().toString(36).slice(2);

    const nombre = p.nombre || p.titulo || 'Producto';
    const precio = Number(p.precio || p.price || 0);
    const tipo   = p.tipo || (p.isbn ? 'Libro' : 'UtilEscolar');

    let img = p.portada_url || p.imagen_url || `/static/img/productos/${id}.png`;
    return { id, nombre, precio, tipo, portada_url: img };
  }

  function productCardHTML(prod) {
    const { id, nombre, precio, tipo, portada_url } = prod;
    const safeAlt = nombre.replace(/"/g, '&quot;');
    return `
      <article class="product-card" data-id="${id}">
        <img src="${portada_url}" alt="${safeAlt}" class="product-img"
             onerror="this.onerror=null;this.src='${(String(tipo).toLowerCase().includes('libro') ? '/static/img/productos/categoria_libros.png' : '/static/img/productos/categoria_utiles.png')}';">
        <div class="product-info">
          <span class="product-type">${tipo}</span>
          <h2 class="product-name">${nombre}</h2>
          <p class="product-price">${fmtQ(precio)}</p>
          <button class="add-to-cart-btn"><i class="ph-plus"></i> Añadir</button>
        </div>
      </article>
    `;
  }

  async function loadProducts(query = '') {
    if (productBox) productBox.innerHTML = '';
    showStatus(query ? `Buscando "${query}"…` : 'Cargando productos…');

    try {
      const url = query ? `${API_PRODUCTS}?q=${encodeURIComponent(query)}` : API_PRODUCTS;
      const data = await fetchJSON(url);
      hideStatus();

      if (!Array.isArray(data) || data.length === 0) {
        showStatus(query ? `No se encontraron productos para "${query}".` : 'No hay productos para mostrar.', true);
        return;
      }

      const normalized = data.map(normalizeProduct);
      if (productBox) productBox.innerHTML = normalized.map(productCardHTML).join('');
    } catch (err) {
      console.error('Error al cargar productos:', err);
      showStatus(`Error al cargar productos: ${err.message}`, true);
    }
  }

  // Categorías: clic para cargar consulta predefinida
  document.addEventListener('click', (e) => {
    const card = e.target.closest && e.target.closest('.category-card');
    if (!card) return;
    const q = card.getAttribute('data-query') || '';
    loadProducts(q);
    document.getElementById('product-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // ==========================
  // Búsqueda
  // ==========================
  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      searchBar.classList.toggle('search-bar-visible');
      if (searchBar.classList.contains('search-bar-visible')) heroInput?.focus();
    });
  }

  function triggerSearch() {
    const q = (heroInput?.value || '').trim();
    if (q) {
      loadProducts(q);
      if (window.innerWidth < 768) searchBar?.classList.remove('search-bar-visible');
    }
  }
  heroBtn?.addEventListener('click', triggerSearch);
  heroInput?.addEventListener('keydown', e => { if (e.key === 'Enter') triggerSearch(); });
  if (legacyInput) heroInput?.addEventListener('input', () => { legacyInput.value = heroInput.value; });
  if (legacyBtn) legacyBtn.addEventListener('click', triggerSearch);

  // ==========================
  // Auth (me / login / logout / register)
  // ==========================
  function waitForRecaptcha(cb, tries = 0) {
    const gre = getGre();
    if (gre && typeof gre.render === 'function') return cb();
    if (tries > 25) return; // ~5s
    setTimeout(() => waitForRecaptcha(cb, tries + 1), 200);
  }

  function ensureRecaptchaRendered(form, assignId) {
    try {
      const holder = form?.querySelector('.g-recaptcha');
      if (!holder) return;
      // Si ya tiene iframe, se considera renderizado
      const already = holder.querySelector('iframe');
      if (already) return;
      const sitekey = holder.getAttribute('data-sitekey');
      if (!sitekey) return;
      waitForRecaptcha(() => {
        const gre = getGre();
        const id = gre.render(holder, { sitekey });
        if (typeof assignId === 'function') assignId(id);
      });
    } catch {}
  }

  function resetRecaptcha(id) {
    try {
      if (id !== null) {
        const gre = getGre();
        if (gre && typeof gre.reset === 'function') gre.reset(id);
        else if (window.grecaptcha && typeof window.grecaptcha.reset === 'function') window.grecaptcha.reset(id);
      }
    } catch {}
  }

  function openAuth()  {
    authModal?.classList.remove('hidden');
    // Renderizar el reCAPTCHA del tab visible
    if (!loginForm?.classList.contains('hidden')) {
      ensureRecaptchaRendered(loginForm, (id) => { loginRecaptchaId = id; });
    } else if (!registerForm?.classList.contains('hidden')) {
      ensureRecaptchaRendered(registerForm, (id) => { registerRecaptchaId = id; });
    }
  }
  function closeAuth() { authModal?.classList.add('hidden'); }
  authClose?.addEventListener('click', closeAuth);
  function openProfile() { const m = document.getElementById('profile-modal'); if (m) m.classList.remove('hidden'); }
  function closeProfile(){ const m = document.getElementById('profile-modal'); if (m) m.classList.add('hidden'); }
  document.getElementById('profile-close')?.addEventListener('click', closeProfile);
  document.getElementById('profile-ok')?.addEventListener('click', closeProfile);
  document.getElementById('profile-logout')?.addEventListener('click', async () => {
    try { await fetch('/api/v1/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' }); }
    finally { closeProfile(); location.reload(); }
  });
  userBtn?.addEventListener('click', openAuth);

  function showLoginTab() {
    tabLogin?.setAttribute('aria-selected','true');
    tabRegister?.setAttribute('aria-selected','false');
    loginForm?.classList.remove('hidden');
    registerForm?.classList.add('hidden');
    // Asegurar render del reCAPTCHA en Login
    ensureRecaptchaRendered(loginForm, (id) => { loginRecaptchaId = id; });
  }
  function showRegisterTab() {
    tabLogin?.setAttribute('aria-selected','false');
    tabRegister?.setAttribute('aria-selected','true');
    loginForm?.classList.add('hidden');
    registerForm?.classList.remove('hidden');
    // Asegurar render del reCAPTCHA en Registro
    ensureRecaptchaRendered(registerForm, (id) => { registerRecaptchaId = id; });
  }
  tabLogin?.addEventListener('click', showLoginTab);
  tabRegister?.addEventListener('click', showRegisterTab);

  async function refreshUser() {
    try {
      const me = await fetchJSON('/api/v1/auth/me');
      if (me.authenticated && me.user) {
        const nombre = me.user.nombre || me.user.email || 'Usuario';
        if (userBtn) {
          userBtn.innerHTML = `<i class="ph-user"></i> <span style="font-size:.9rem;margin-left:.35rem;">${nombre}</span>`;
          userBtn.onclick = async () => {
            try {
              const m = await fetchJSON('/api/v1/auth/me');
              const u = (m && m.user) || {};
              document.getElementById('profile-nombre')?.appendChild(document.createTextNode(''));
              if (document.getElementById('profile-nombre')) document.getElementById('profile-nombre').textContent = u.nombre || 'Usuario';
              if (document.getElementById('profile-email')) document.getElementById('profile-email').textContent = u.email || '-';
              if (document.getElementById('profile-verificado')) document.getElementById('profile-verificado').textContent = (u.verificado ? 'Sí' : 'No');
              await loadUserOrders(u.email);
            } catch {}
            const pm = document.getElementById('profile-modal'); if (pm) pm.classList.remove('hidden');
          };
        }
      } else {
        if (userBtn) {
          userBtn.innerHTML = `<i class="ph-user"></i>`;
          userBtn.onclick = openAuth;
        }
      }
    } catch {
      // deja el botón por defecto
    }
  }

  // LOGIN
  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError?.classList.add('hidden');
    try {
      const email = (document.getElementById('login-email')?.value || '').trim();
      const password = (document.getElementById('login-password')?.value || '');
      if (!email || !password) throw new Error('Ingresa email y contraseña.');

      let recaptcha;
      try {
        const gre = getGre();
        if (gre && loginRecaptchaId !== null) {
          recaptcha = gre.getResponse(loginRecaptchaId);
        }
        if (!recaptcha) {
          const ta = loginForm?.querySelector('textarea.g-recaptcha-response');
          recaptcha = ta && ta.value ? ta.value : undefined;
        }
        // Si hay un widget visible pero sin token, evita enviar hasta que el usuario lo complete
        if (!recaptcha && loginForm?.querySelector('.g-recaptcha')) {
          throw new Error('Completa el reCAPTCHA.');
        }
      } catch {}

      await fetchJSON('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password, recaptcha })
      });
      closeAuth();
      refreshUser();
      // Si es administrador, redirigir al panel de ventas (/admin)
      try {
        const adm = await fetchJSON('/api/v1/admin/check');
        if (adm && adm.admin) {
          window.location.href = '/admin';
          return;
        }
      } catch {}
      // reset para siguientes intentos
      resetRecaptcha(loginRecaptchaId);
    } catch (err) {
      if (loginError) {
        const msg = err && err.message ? err.message : 'Credenciales inválidas';
        loginError.textContent = msg;
        loginError.classList.remove('hidden');
        // permitir reintento
        resetRecaptcha(loginRecaptchaId);

        // Si requiere verificación, muestra botón para reenviar el correo
        if (/verificar/i.test(msg) && /correo/i.test(msg)) {
          let btn = document.getElementById('resend-verif-btn');
          if (!btn) {
            btn = document.createElement('button');
            btn.id = 'resend-verif-btn';
            btn.type = 'button';
            btn.className = 'btn-secondary';
            btn.style.marginTop = '.5rem';
            btn.textContent = 'Reenviar verificación';
            // Insertar después del párrafo de error
            try { loginError.insertAdjacentElement('afterend', btn); } catch {}

            btn.addEventListener('click', async () => {
              btn.disabled = true;
              const currentEmail = (document.getElementById('login-email')?.value || '').trim();
              try {
                await fetchJSON('/api/v1/auth/resend-verification', {
                  method: 'POST',
                  body: JSON.stringify({ email: currentEmail })
                });
                loginError.textContent = 'Te enviamos un nuevo correo de verificación. Revisa SPAM.';
              } catch (e2) {
                loginError.textContent = (e2 && e2.message) ? e2.message : 'No se pudo reenviar la verificación.';
              } finally {
                btn.disabled = false;
              }
            });
          }
        }
      }
    }
  });

  // REGISTRO
  registerForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    registerMsg?.classList.add('hidden');
    registerErr?.classList.add('hidden');

    const nombre = (document.getElementById('register-nombre')?.value || '').trim();
    const email  = (document.getElementById('register-email')?.value || '').trim();
    const p1     = (document.getElementById('register-password')?.value || '');
    const p2     = (document.getElementById('register-password2')?.value || '');

    if (!nombre || !email || !p1 || !p2) {
      if (registerErr) { registerErr.textContent = 'Completa todos los campos.'; registerErr.classList.remove('hidden'); }
      return;
    }
    if (p1 !== p2) {
      if (registerErr) { registerErr.textContent = 'Las contraseñas no coinciden.'; registerErr.classList.remove('hidden'); }
      return;
    }

    try {
      let recaptcha;
      try {
        const gre = getGre();
        if (gre && registerRecaptchaId !== null) {
          recaptcha = gre.getResponse(registerRecaptchaId);
        }
        if (!recaptcha) {
          const ta = registerForm?.querySelector('textarea.g-recaptcha-response');
          recaptcha = ta && ta.value ? ta.value : undefined;
        }
        if (!recaptcha && registerForm?.querySelector('.g-recaptcha')) {
          throw new Error('Completa el reCAPTCHA.');
        }
      } catch {}
      const resp = await fetchJSON('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ nombre, email, password: p1, recaptcha })
      });
      if (resp?.ok || resp?.mensaje) {
        if (registerMsg) { registerMsg.textContent = '¡Registro exitoso! Revisa tu correo para verificar la cuenta.'; registerMsg.classList.remove('hidden'); }
        // Cambiamos a pestaña Login para que pueda entrar tras verificar
        showLoginTab();
        setTimeout(() => { /* opcional: cerrar modal */ }, 1200);
      }
      // reset tras envío
      resetRecaptcha(registerRecaptchaId);
    } catch (err) {
      if (registerErr) { registerErr.textContent = err.message || 'No se pudo registrar.'; registerErr.classList.remove('hidden'); }
      // permitir reintento
      resetRecaptcha(registerRecaptchaId);
    }
  });

  // ==========================
  // Carrito
  // ==========================
  function openCart()  { drawer?.classList.add('open'); backdrop?.classList.remove('hidden'); try{ document.body.classList.add('drawer-open'); }catch(_){} }
  function closeCart() { drawer?.classList.remove('open'); backdrop?.classList.add('hidden'); try{ document.body.classList.remove('drawer-open'); }catch(_){} }
  cartBtn?.addEventListener('click', openCart);
  drawerClose?.addEventListener('click', closeCart);
  backdrop?.addEventListener('click', closeCart);

  async function loadCart() {
    try {
      const cart = await fetchJSON('/api/v1/cart');
      renderCart(cart);
    } catch {}
  }

  function renderCart(cart) {
    const items = Object.values(cart || {});
    const total = items.reduce((s, it) => s + (Number(it.precio) || 0) * (it.cantidad || 0), 0);

    if (drawerBody) {
      drawerBody.innerHTML = items.map(it => `
        <div class="cart-item">
          <img src="" alt="${(it.nombre || '').replace(/"/g,'&quot;')}">
          <div style="flex:1">
            <div class="name">${it.nombre || 'Producto'}</div>
            <div class="price">${fmtQ(it.precio)}</div>
            <div class="qty">
              <button data-dec="${it.id}">-</button>
              <span>${it.cantidad}</span>
              <button data-inc="${it.id}">+</button>
              <button data-del="${it.id}" style="margin-left:.5rem">Eliminar</button>
            </div>
          </div>
        </div>
      `).join('') || `<p class="muted">Tu carrito está vacío.</p>`;
    }

    if (drawerTotal) drawerTotal.textContent = fmtQ(total);
    if (drawerBuy) drawerBuy.disabled = items.length === 0;

    const count = items.reduce((s, it) => s + (it.cantidad || 0), 0);
    if (cartBadge) {
      if (count > 0) {
        cartBadge.textContent = String(count);
        cartBadge.classList.remove('hidden');
      } else {
        cartBadge.classList.add('hidden');
      }
    }

    drawerBody?.querySelectorAll('[data-inc]').forEach(b => b.onclick = () => updateQty(b.dataset.inc, +1));
    drawerBody?.querySelectorAll('[data-dec]').forEach(b => b.onclick = () => updateQty(b.dataset.dec, -1));
    drawerBody?.querySelectorAll('[data-del]').forEach(b => b.onclick = () => removeItem(b.dataset.del));
  }

  async function updateQty(id, delta) {
    try {
      const cart = await fetchJSON('/api/v1/cart');
      const cur = cart[id]?.cantidad || 0;
      const next = cur + delta;
      await fetchJSON('/api/v1/cart/update', { method: 'POST', body: JSON.stringify({ id, cantidad: next }) });
      loadCart();
    } catch {}
  }

  async function removeItem(id) {
    await fetchJSON('/api/v1/cart/remove', { method: 'POST', body: JSON.stringify({ id }) });
    loadCart();
  }

  drawerClear?.addEventListener('click', async () => {
    await fetchJSON('/api/v1/cart/clear', { method: 'POST' });
    loadCart();
  });

  // Checkout (Stripe/PayPal)
  async function getCartSnapshot() {
    try {
      const cart = await fetchJSON('/api/v1/cart');
      const arr = Object.values(cart || {});
      const total = arr.reduce((s, it) => s + (Number(it.precio) || 0) * (it.cantidad || 0), 0);
      return { items: arr, total };
    } catch {
      return { items: [], total: 0 };
    }
  }

  // ==== Checkout con formulario dentro del drawer ====
  function renderCheckoutForm(items, total) {
    const count = items.reduce((s, it) => s + (it.cantidad || 0), 0);
    return `
      <form id="checkout-form" class="checkout-form">
        <h3>Finalizar compra</h3>
        <p class="muted">${count} artículo(s) — Total: <strong>${fmtQ(total)}</strong></p>

        <section>
          <h4>Método de pago</h4>
          <label class="radio"><input type="radio" name="pago" value="stripe" checked> Tarjeta (Stripe)</label>
          <label class="radio"><input type="radio" name="pago" value="paypal"> PayPal</label>
        </section>

        <section>
          <h4>Entrega</h4>
          <label class="radio"><input type="radio" name="entrega" value="domicilio" checked> Entrega a domicilio</label>
          <label class="radio"><input type="radio" name="entrega" value="recoger"> Recoger en tienda</label>
          <div>
            <input type="text" id="entrega-nombre" placeholder="Nombre completo" required>
          </div>
          <div id="entrega-dirblock" class="entrega-datos">
            <input type="tel" id="entrega-telefono" placeholder="Teléfono">
            <textarea id="entrega-direccion" placeholder="Dirección completa" rows="2" required></textarea>
          </div>
        </section>

        <section>
          <h4>Datos de factura</h4>
          <div class="grid2">
            <input type="text" id="fact-nit" placeholder="NIT (C/F por defecto)" value="C/F" required>
            <input type="email" id="fact-email" placeholder="Email (opcional)">
          </div>
        </section>

        <div class="checkout-actions">
          <button type="button" id="checkout-cancel" class="btn-secondary">Volver al carrito</button>
          <button type="submit" id="checkout-submit" class="btn-primary">Confirmar y pagar</button>
        </div>
      </form>
    `;
  }

  async function openCheckoutForm() {
    const snap = await getCartSnapshot();
    if (!snap.items.length || snap.total <= 0) return;
    if (drawerBody) drawerBody.innerHTML = renderCheckoutForm(snap.items, snap.total);
    // Ocultar acciones del footer durante checkout
    try { drawerBuy.style.display = 'none'; } catch {}
    try { drawerClear.style.display = 'none'; } catch {}

    // Toggle dirección según entrega
    const entregaDir = document.getElementById('entrega-dirblock');
    const nombreInput = document.getElementById('entrega-nombre');
    drawerBody?.querySelectorAll('input[name="entrega"]').forEach(r => {
      r.addEventListener('change', () => {
        const val = drawerBody.querySelector('input[name="entrega"]:checked')?.value;
        if (val === 'recoger') {
          entregaDir?.classList.add('hidden');
          try { document.getElementById('entrega-direccion').required = false; } catch {}
        } else {
          entregaDir?.classList.remove('hidden');
          try { document.getElementById('entrega-direccion').required = true; } catch {}
        }
        try { if (nombreInput) nombreInput.required = true; } catch {}
      });
    });

    // Cancelar
    const cancelBtn = document.getElementById('checkout-cancel');
    cancelBtn?.addEventListener('click', () => exitCheckoutForm());

    // Submit
    const form = document.getElementById('checkout-form');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const metodo = drawerBody.querySelector('input[name="pago"]:checked')?.value || 'stripe';
      const entrega = drawerBody.querySelector('input[name="entrega"]:checked')?.value || 'domicilio';
      const nit = (document.getElementById('fact-nit')?.value || 'C/F').trim() || 'C/F';
      const email = (document.getElementById('fact-email')?.value || '').trim() || undefined;
      const entregaPayload = (function(){
        const base = { metodo: entrega, nombre: document.getElementById('entrega-nombre')?.value || undefined };
        if (entrega === 'domicilio') {
          base.telefono = document.getElementById('entrega-telefono')?.value || undefined;
          base.direccion = document.getElementById('entrega-direccion')?.value || undefined;
        }
        return base;
      })();
      try {
        showStatus('Procesando pago...', false);
        if (metodo === 'stripe') {
          const resp = await crearPaymentIntentStripe(snap.total);
          if (!resp?.clientSecret) throw new Error('No se obtuvo clientSecret');
        } else {
          const resp = await crearOrderPayPal(snap.total, 'GTQ');
          const approveUrl = resp?.approveUrl; if (approveUrl) window.open(approveUrl, '_blank');
        }
        // Crear factura local (incluye nit y metadatos básicos)
        const inv = await crearFacturaLocal(snap.items, email, nit, entregaPayload, metodo);
        await fetchJSON('/api/v1/cart/clear', { method: 'POST' });
        await loadCart();
        // Mostrar acciones de post-compra dentro del drawer
        if (drawerBody) {
          const fid = inv && inv.id ? inv.id : null;
          const printUrl = fid ? `/api/v1/facturas/print/${fid}` : null;
          drawerBody.innerHTML = `
            <div class="checkout-success">
              <h3>¡Compra completada!</h3>
              <p class="muted">Factura <strong>${(inv && inv.numero_factura) ? inv.numero_factura : ''}</strong> — Total <strong>${fmtQ(inv && inv.total ? inv.total : snap.total)}</strong></p>
              <div class="checkout-actions">
                <button id="success-close" class="btn-secondary">Cerrar</button>
                <button id="success-json" class="btn-secondary">Descargar JSON</button>
                <button id="success-print" class="btn-primary">Imprimir / PDF</button>
              </div>
            </div>`;
          const btnClose = document.getElementById('success-close');
          const btnJson = document.getElementById('success-json');
          const btnPrint = document.getElementById('success-print');
          btnClose?.addEventListener('click', () => { exitCheckoutForm(); });
          btnJson?.addEventListener('click', async () => {
            try {
              const snapshot = JSON.parse(localStorage.getItem('lastInvoice')||'null') || inv || {};
              const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = `${(inv && inv.numero_factura) ? inv.numero_factura : 'factura'}.json`;
              document.body.appendChild(a); a.click(); setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 300);
            } catch {}
          });
          btnPrint?.addEventListener('click', () => { if (printUrl) window.open(printUrl, '_blank'); });
          try { if (printUrl) window.open(printUrl, '_blank'); } catch {}
        }
        // Restaurar acciones del footer
        try { drawerBuy.style.display = ''; } catch {}
        try { drawerClear.style.display = ''; } catch {}
        showStatus('Compra completada. Factura creada.', false);
        setTimeout(hideStatus, 4500);
      } catch (err) {
        console.error('Checkout error:', err);
        showStatus(err?.message || 'Error en el checkout.', true);
        setTimeout(hideStatus, 2500);
      }
    });
  }

  function exitCheckoutForm() {
    try { drawerBuy.style.display = ''; } catch {}
    try { drawerClear.style.display = ''; } catch {}
    loadCart();
  }

  drawerBuy?.addEventListener('click', async () => { openCheckoutForm(); });

  // Delegación: click en “Añadir”
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.add-to-cart-btn');
    if (!btn) return;

    const card   = btn.closest('.product-card');
    const id     = card?.dataset?.id;
    const nombre = card?.querySelector('.product-name')?.textContent?.trim() || 'Producto';
    const precio = parseFloat((card?.querySelector('.product-price')?.textContent || 'Q0').replace(/[^\d.]/g, '')) || 0;
    const img    = card?.querySelector('img')?.getAttribute('src');

    await fetchJSON('/api/v1/cart/add', {
      method: 'POST',
      body: JSON.stringify({ id, nombre, precio, portada_url: img, cantidad: 1 })
    });

    await loadCart();
    openCart();
  });

  // ==========================
  // Init
  // ==========================
  refreshUser();
  loadCart();
  loadProducts('');

  // ==========================
  // Integraciones (helpers)
  // ==========================
  async function buscarLibros(q) {
    const url = `/api/v1/books?q=${encodeURIComponent(q || '')}`;
    return fetchJSON(url);
  }
  async function consultarPostal(codigo) {
    const url = `/api/v1/postal/${encodeURIComponent(String(codigo || '').trim())}`;
    const data = await fetchJSON(url);
    console.log('Postal GT:', data);
    showStatus(`CP ${data.codigo}: ${data.ciudad || ''}, ${data.estado || ''}`, false);
    setTimeout(hideStatus, 2500);
    return data;
  }
  async function crearPaymentIntentStripe(total) {
    const data = await fetchJSON('/api/v1/payments/stripe/create-payment-intent', {
      method: 'POST',
      body: JSON.stringify({ total: Number(total) || 0 })
    });
    console.log('Stripe clientSecret:', data.clientSecret);
    return data;
  }
  async function crearOrderPayPal(total, currency = 'GTQ') {
    const data = await fetchJSON('/api/v1/payments/paypal/create-order', {
      method: 'POST',
      body: JSON.stringify({ total: Number(total) || 0, currency })
    });
    console.log('PayPal order:', data);
    return data;
  }
  async function crearFacturaLocal(items, email, nit, entrega, pagoMetodo) {
    const payload = {
      items: Array.isArray(items) ? items : [],
      email,
      nit,
      entrega: entrega || undefined,
      pago: pagoMetodo ? { metodo: pagoMetodo } : undefined,
    };
    const data = await fetchJSON('/api/v1/facturas', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    console.log('Factura creada:', data);
    try {
      const snapshot = {
        factura: data,
        items: items,
        nit,
        email,
        entrega: entrega || null,
        pago: pagoMetodo ? { metodo: pagoMetodo } : null,
        createdAt: new Date().toISOString(),
      };
      localStorage.setItem('lastInvoice', JSON.stringify(snapshot));
      // Ya no se descarga JSON automáticamente si no hay email
    } catch {}
    return data;
  }

  async function enviarChatGPT(mensaje, opts = {}) {
    const body = { mensaje, ...opts };
    const data = await fetchJSON('/api/v1/ia/chat', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    console.log('Assistant:', data);
    return data?.message || data?.respuesta;
  }

  // Exponer helpers para pruebas desde consola del navegador
  window.buscarLibros = buscarLibros;
  window.consultarPostal = consultarPostal;
  window.crearPaymentIntentStripe = crearPaymentIntentStripe;
  window.crearOrderPayPal = crearOrderPayPal;
  window.crearFacturaLocal = crearFacturaLocal;
  window.enviarChatGPT = enviarChatGPT;
});
  const profileOrdersState = { page: 1, from: '', to: '', total: 0, email: '' };
  async function loadUserOrders(email, { append = false } = {}){
    const wrap = document.getElementById('profile-orders');
    const moreBtn = document.getElementById('orders-more-btn');
    const fromInput = document.getElementById('orders-from-date');
    const toInput = document.getElementById('orders-to-date');
    if (!wrap) return;
    profileOrdersState.email = email || profileOrdersState.email || '';
    const from = (fromInput?.value || profileOrdersState.from || '').trim();
    const to = (toInput?.value || profileOrdersState.to || '').trim();
    const page = append ? (profileOrdersState.page + 1) : 1;
    if (!append) wrap.innerHTML = '<div class="muted">Cargando compras...</div>';
    try {
      const params = new URLSearchParams();
      params.set('email', profileOrdersState.email);
      params.set('limit', '10');
      params.set('page', String(page));
      if (from) params.set('from', from);
      if (to) params.set('to', to);
      const res = await fetchJSON(`/api/v1/facturas?${params.toString()}`);
      const items = (res && res.items) || [];
      profileOrdersState.page = page;
      profileOrdersState.total = (res && res.total) || 0;
      profileOrdersState.from = from; profileOrdersState.to = to;
      const html = items.map(it => `
        <div class="order-item" style="border:1px solid var(--border-color);border-radius:8px;padding:.5rem;display:flex;justify-content:space-between;align-items:center;gap:.5rem;">
          <div>
            <div><strong>${it.numero_factura || ''}</strong></div>
            <div class="muted">${(it.fecha||'').replace('T',' ').substring(0,16)} · ${it.pago_metodo || '-'} · Total ${fmtQ(it.total||0)}</div>
          </div>
          <div style="display:flex;gap:.4rem;white-space:nowrap;">
            <a class="btn-secondary" href="${it.print_url}" target="_blank">Imprimir/PDF</a>
            <button class="btn-secondary order-json" data-fid="${it.id}">JSON</button>
          </div>
        </div>`).join('');
      if (append) wrap.insertAdjacentHTML('beforeend', html); else wrap.innerHTML = html || '<div class="muted">No tienes compras registradas.</div>';
      wrap.querySelectorAll('.order-json').forEach(btn => {
        btn.addEventListener('click', async () => {
          const fid = btn.getAttribute('data-fid');
          try {
            const inv = await fetchJSON(`/api/v1/facturas/${encodeURIComponent(fid)}`);
            const blob = new Blob([JSON.stringify(inv, null, 2)], { type: 'application/json' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            const num = (inv && inv.numero_factura) ? inv.numero_factura : `factura_${fid}`;
            a.download = `${num}.json`;
            document.body.appendChild(a); a.click(); setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 300);
          } catch(e){}
        });
      });
      // Toggle 'Ver más'
      if (moreBtn) {
        const loaded = profileOrdersState.page * 10;
        moreBtn.style.display = (loaded < profileOrdersState.total) ? '' : 'none';
        moreBtn.onclick = () => loadUserOrders(profileOrdersState.email, { append: true });
      }
    } catch(e) {
      wrap.innerHTML = '<div class="error">No se pudieron cargar las compras.</div>';
      if (moreBtn) moreBtn.style.display = 'none';
    }
  }

  // Filtro de fechas en perfil
  document.getElementById('orders-filter-btn')?.addEventListener('click', async () => {
    await loadUserOrders(profileOrdersState.email, { append: false });
  });
