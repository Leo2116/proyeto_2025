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

  const registerForm = document.getElementById('register-form');
  const registerMsg  = document.getElementById('register-msg');
  const registerErr  = document.getElementById('register-error');

  const userBtn = document.getElementById('user-btn');

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
             onerror="this.onerror=null;this.src='https://placehold.co/280x200?text=${encodeURIComponent(tipo)}';">
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
  function openAuth()  { authModal?.classList.remove('hidden'); }
  function closeAuth() { authModal?.classList.add('hidden'); }
  authClose?.addEventListener('click', closeAuth);
  userBtn?.addEventListener('click', openAuth);

  function showLoginTab() {
    tabLogin?.setAttribute('aria-selected','true');
    tabRegister?.setAttribute('aria-selected','false');
    loginForm?.classList.remove('hidden');
    registerForm?.classList.add('hidden');
  }
  function showRegisterTab() {
    tabLogin?.setAttribute('aria-selected','false');
    tabRegister?.setAttribute('aria-selected','true');
    loginForm?.classList.add('hidden');
    registerForm?.classList.remove('hidden');
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
            try { await fetchJSON('/api/v1/auth/logout', { method: 'POST' }); }
            finally { location.reload(); }
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

      await fetchJSON('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      closeAuth();
      refreshUser();
    } catch (err) {
      if (loginError) {
        loginError.textContent = err.message || 'Credenciales inválidas';
        loginError.classList.remove('hidden');
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
      const resp = await fetchJSON('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ nombre, email, password: p1 })
      });
      if (resp?.ok || resp?.mensaje) {
        if (registerMsg) { registerMsg.textContent = '¡Registro exitoso! Revisa tu correo para verificar la cuenta.'; registerMsg.classList.remove('hidden'); }
        // Cambiamos a pestaña Login para que pueda entrar tras verificar
        showLoginTab();
        setTimeout(() => { /* opcional: cerrar modal */ }, 1200);
      }
    } catch (err) {
      if (registerErr) { registerErr.textContent = err.message || 'No se pudo registrar.'; registerErr.classList.remove('hidden'); }
    }
  });

  // ==========================
  // Carrito
  // ==========================
  function openCart()  { drawer?.classList.add('open'); backdrop?.classList.remove('hidden'); }
  function closeCart() { drawer?.classList.remove('open'); backdrop?.classList.add('hidden'); }
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

  drawerBuy?.addEventListener('click', async () => {
    const { items, total } = await getCartSnapshot();
    if (!items.length || total <= 0) return;

    // Elección simple sin SDKs: prompt
    let metodo = (window.prompt('Método de pago: stripe | paypal', 'stripe') || '').trim().toLowerCase();
    if (metodo !== 'stripe' && metodo !== 'paypal') {
      showStatus('Método inválido. Usa "stripe" o "paypal".', true);
      setTimeout(hideStatus, 1800);
      return;
    }

    try {
      showStatus('Procesando pago...', false);
      if (metodo === 'stripe') {
        const resp = await crearPaymentIntentStripe(total);
        if (!resp?.clientSecret) throw new Error('No se obtuvo clientSecret');
        const email = window.prompt('Email para la factura (opcional)') || undefined;
        await crearFacturaLocal(items, email);
        await fetchJSON('/api/v1/cart/clear', { method: 'POST' });
        await loadCart();
        showStatus('Stripe OK (simulado). Factura creada. Revisa consola.', false);
      } else {
        const resp = await crearOrderPayPal(total, 'GTQ');
        const approveUrl = resp?.approveUrl;
        const email = window.prompt('Email para la factura (opcional)') || undefined;
        await crearFacturaLocal(items, email);
        await fetchJSON('/api/v1/cart/clear', { method: 'POST' });
        await loadCart();
        if (approveUrl) window.open(approveUrl, '_blank');
        showStatus('PayPal OK (simulado). Factura creada. Revisa consola.', false);
      }
      setTimeout(hideStatus, 2500);
    } catch (err) {
      console.error('Checkout error:', err);
      showStatus(err?.message || 'Error en el checkout.', true);
      setTimeout(hideStatus, 2500);
    }
  });

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
  async function crearFacturaLocal(items, email) {
    const payload = { items: Array.isArray(items) ? items : [], email };
    const data = await fetchJSON('/api/v1/facturas', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    console.log('Factura creada:', data);
    return data;
  }

  // Exponer helpers para pruebas desde consola del navegador
  window.buscarLibros = buscarLibros;
  window.consultarPostal = consultarPostal;
  window.crearPaymentIntentStripe = crearPaymentIntentStripe;
  window.crearOrderPayPal = crearOrderPayPal;
  window.crearFacturaLocal = crearFacturaLocal;
});
