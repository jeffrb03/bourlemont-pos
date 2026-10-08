/**
 * Bourlemont POS — pos.js v3.0
 * Punto de Venta Táctil con Escandallo Algorítmico
 * IVA Guatemala: Decreto 27-92 (IVA incluido en precio, NO se suma al total)
 */
import { api, authState } from "./api.js";

// ─────────────────────────────────────────────────────────────
// Constantes
// ─────────────────────────────────────────────────────────────
const STORAGE_KEY = "bourlemont_orden_activa";

// Silueta SVG de botella (fallback cuando imagen_url es nula o falla)
const BOTTLE_SVG_URL = `data:image/svg+xml;utf8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 200" fill="none">
  <rect x="30" y="0" width="20" height="28" rx="4" fill="%2363522A"/>
  <path d="M26 28 Q20 55 18 90 L18 170 Q18 182 40 182 Q62 182 62 170 L62 90 Q60 55 54 28 Z"
        fill="%232A2416" stroke="%2363522A" stroke-width="2"/>
  <path d="M24 108 Q40 98 56 108" stroke="%23D4AF37" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M26 122 Q40 114 54 122" stroke="%23D4AF37" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <path d="M28 136 Q40 130 52 136" stroke="%23D4AF37" stroke-width="0.8" stroke-linecap="round" opacity="0.3"/>
</svg>
`)}`;

// ─────────────────────────────────────────────────────────────
// Estado Central
// ─────────────────────────────────────────────────────────────
const state = {
    user: null,
    products: [],
    filteredProducts: [],
    activeCategory: "TODOS",
    searchQuery: "",
    order: {
        id_orden: null,
        table: "Barra 360 - Asiento 1",
        items: []   // [{ product: {...}, quantity: Number }]
    },
    selectedPaymentMethod: "EFECTIVO",
    tipPercentage: 10,
    nitDebounceTimer: null
};

// ─────────────────────────────────────────────────────────────
// Inicialización
// ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    if (!authState.isAuthenticated()) {
        window.location.href = "/index.html";
        return;
    }

    state.user = authState.getUser();
    renderHeaderUser();
    restoreOrderFromStorage();
    initEventListeners();

    await cargarProductos();
});

// ─────────────────────────────────────────────────────────────
// Header
// ─────────────────────────────────────────────────────────────
function renderHeaderUser() {
    const nameEl = document.getElementById("header-user-name");
    const roleEl = document.getElementById("header-user-role");
    if (nameEl) nameEl.textContent = state.user.nombre;
    if (roleEl) {
        roleEl.textContent = state.user.rol === "ADMIN" ? "ADMINISTRADOR" : "BARTENDER";
    }

    if (!authState.isAdmin()) {
        document.querySelectorAll(".admin-only").forEach(el => (el.style.display = "none"));
    }
}

// ─────────────────────────────────────────────────────────────
// Persistencia localStorage (resiliencia ante cortes)
// ─────────────────────────────────────────────────────────────
function saveOrderToStorage() {
    try {
        const snapshot = {
            id_orden: state.order.id_orden || null,
            table: state.order.table,
            tipPercentage: state.tipPercentage,
            selectedPaymentMethod: state.selectedPaymentMethod,
            items: state.order.items.map(it => ({
                quantity: it.quantity,
                product: {
                    id_producto: it.product.id_producto,
                    nombre: it.product.nombre,
                    precio_venta: it.product.precio_venta,
                    categoria: it.product.categoria,
                    tipo: it.product.tipo,
                    stock_ml: it.product.stock_ml,
                    stock_minimo_ml: it.product.stock_minimo_ml,
                    unidad_medida: it.product.unidad_medida,
                    imagen_url: it.product.imagen_url || null
                }
            }))
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch (e) {
        console.warn("[POS] No se pudo persistir la comanda:", e);
    }
}

function restoreOrderFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (!saved?.items?.length) return;

        state.order.id_orden = saved.id_orden || null;
        state.order.items = saved.items || [];
        state.order.table = saved.table || state.order.table;
        state.tipPercentage = saved.tipPercentage ?? 10;
        state.selectedPaymentMethod = saved.selectedPaymentMethod || "EFECTIVO";

        const tableSelect = document.getElementById("table-select");
        if (tableSelect) tableSelect.value = state.order.table;

        showToast(
            `Comanda restaurada con ${saved.items.length} ítem(s) de la sesión anterior.`,
            "success"
        );
    } catch (e) {
        console.warn("[POS] Error restaurando comanda:", e);
    }
}

function clearOrderStorage() {
    localStorage.removeItem(STORAGE_KEY);
}

// ─────────────────────────────────────────────────────────────
// Catálogo de Productos
// ─────────────────────────────────────────────────────────────
async function cargarProductos() {
    try {
        state.products = await api.getProductos();
        applyFilter();
        renderOrderItems(); // Re-renderiza por si vienen de storage
    } catch (err) {
        showToast("Error al cargar catálogo: " + (err.message || "sin conexión"), "danger");
    }
}
const loadProducts = cargarProductos;
window.cargarProductos = cargarProductos;
window.loadProducts = loadProducts;

function applyFilter() {
    state.filteredProducts = state.products.filter(p => {
        // Excluir insumos base no comercializables (precio <= 0)
        if (p.categoria === "INSUMOS_BASE" && parseFloat(p.precio_venta || 0) <= 0) return false;
        if (parseFloat(p.precio_venta || 0) <= 0) return false;

        let matchCat = false;
        if (state.activeCategory === "TODOS") {
            matchCat = true;
        } else {
            const pCat = (p.categoria || "").toUpperCase();
            const aCat = (state.activeCategory || "").toUpperCase();
            matchCat = pCat === aCat || pCat.includes(aCat) || aCat.includes(pCat);
        }

        const matchQ = (p.nombre || "").toLowerCase().includes(state.searchQuery.toLowerCase());
        return matchCat && matchQ;
    });
    renderProductGrid();
}

function getImgSrc(producto) {
    if (producto.imagen_url && producto.imagen_url.trim()) {
        const raw = producto.imagen_url.trim();
        if (raw.startsWith("http://") || raw.startsWith("https://") || raw.startsWith("data:")) {
            return raw;
        }
        if (raw.startsWith("/")) {
            return raw;
        }
        if (raw.startsWith("assets/")) {
            return `/${raw}`;
        }
        return `/assets/img/${raw}`;
    }
    return BOTTLE_SVG_URL;
}

function renderProductGrid() {
    const grid = document.getElementById("catalogo-productos") || document.getElementById("products-grid");
    if (!grid) return;

    if (state.filteredProducts.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;color:var(--text-tertiary);padding:50px 20px;">
                <div style="font-size:44px;margin-bottom:14px;opacity:.35;">🍾</div>
                <div>No se encontraron productos en esta categoría.</div>
            </div>`;
        return;
    }

    // Construir HTML como string compacto responsivo
    const html = state.filteredProducts.map(p => {
        const isLow = p.stock_ml > 0 && p.stock_ml <= p.stock_minimo_ml;
        const isNeg = p.stock_ml < 0;
        const imgSrc = getImgSrc(p);

        let stockTag = "";
        if (isNeg) stockTag = `<span class="product-stock-tag low">⚠ Sin Stock</span>`;
        else if (isLow) stockTag = `<span class="product-stock-tag low">⚠ Bajo</span>`;

        const catClass = p.categoria.toLowerCase().replace(/_/g, "-");

        return `
        <div class="product-card ${catClass}" data-id="${p.id_producto}" tabindex="0" role="button"
             aria-label="${escHtml(p.nombre)} — Q ${parseFloat(p.precio_venta).toFixed(2)}">
            <div class="product-card-img-wrap">
                <img src="${imgSrc}"
                     alt="${escHtml(p.nombre)}"
                     class="product-card-img"
                     loading="lazy"
                     onerror="this.onerror=null; this.src='/assets/img/cocktail-fallback.svg';" />
            </div>
            <div class="product-card-body">
                <div class="product-title font-serif font-bold text-primary">${escHtml(p.nombre)}</div>
                <div class="product-meta">
                    <span>${p.categoria.replace(/_/g, " ")}</span>
                    ${p.tipo === "COMPUESTO" ? "<span>·</span><span>Escandallo ml</span>" : ""}
                </div>
            </div>
            <div class="product-price-row">
                <span class="product-price font-bold text-primary">Q ${parseFloat(p.precio_venta).toFixed(2)}</span>
                ${stockTag}
            </div>
        </div>`;
    }).join("");

    grid.innerHTML = html;

    // Adjuntar listeners
    grid.querySelectorAll(".product-card").forEach(card => {
        const handler = () => {
            const id = parseInt(card.getAttribute("data-id"), 10);
            const prod = state.products.find(p => p.id_producto === id);
            if (prod) {
                addItemToOrder(prod);
                // Efecto haptic visual
                card.classList.add("pressed");
                setTimeout(() => card.classList.remove("pressed"), 150);
            }
        };
        card.addEventListener("click", handler);
        card.addEventListener("keydown", e => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handler();
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────
// Gestión de Comanda
// ─────────────────────────────────────────────────────────────
function addItemToOrder(product) {
    const existing = state.order.items.find(it => it.product.id_producto === product.id_producto);
    if (existing) {
        existing.quantity += 1;
    } else {
        state.order.items.push({ product, quantity: 1 });
    }
    renderOrderItems();
    saveOrderToStorage();
}

function updateItemQuantity(productId, delta) {
    const item = state.order.items.find(it => it.product.id_producto === productId);
    if (!item) return;
    item.quantity = Math.max(0, item.quantity + delta);
    if (item.quantity === 0) {
        state.order.items = state.order.items.filter(it => it.product.id_producto !== productId);
    }
    renderOrderItems();
    saveOrderToStorage();
}

function removeItemFromOrder(productId) {
    state.order.items = state.order.items.filter(it => it.product.id_producto !== productId);
    renderOrderItems();
    saveOrderToStorage();
}

/**
 * Cálculo Fiscal Guatemala — Decreto 27-92
 * IVA (12%) ya está INCLUIDO en el precio de carta. NO se suma al total.
 *
 * Total Venta = Σ(precio × cantidad) + Propina seleccionada
 * Desglose informativo:
 *   base_imponible = Total_productos / 1.12
 *   monto_iva      = Total_productos - base_imponible
 * La propina voluntaria no genera IVA.
 */
function calculateOrderTotals() {
    const totalProductos = state.order.items.reduce(
        (acc, it) => acc + parseFloat(it.product.precio_venta) * it.quantity,
        0
    );

    const baseImponible = totalProductos / 1.12;  // IVA incluido → base imponible
    const montoIva = totalProductos - baseImponible; // Desglose informativo
    const propina = totalProductos * (state.tipPercentage / 100);
    const totalFinal = totalProductos + propina;   // Total venta: productos + propina (sin doble IVA)

    return { totalProductos, baseImponible, montoIva, propina, totalFinal };
}

function renderOrderItems() {
    const container = document.getElementById("order-items-list");
    const checkoutBtn = document.getElementById("btn-cobrar") || document.getElementById("checkout-btn");
    const subIvaEl = document.getElementById("order-subtotal-sin-iva");
    const ivaEl = document.getElementById("order-iva");
    const totalEl = document.getElementById("order-total");

    if (!container) return;

    if (state.order.items.length === 0) {
        container.innerHTML = `
          <div class="empty-order-state" id="empty-order-state" style="display:flex;">
            <div class="empty-icon">🥂</div>
            <div style="font-size: 15px; font-weight: 600; color: #FFF;">Comanda Vacía</div>
            <p style="font-size: 13px; max-width: 200px; color: var(--text-secondary);">
              Selecciona productos de la carta para agregar a la cuenta.
            </p>
          </div>`;

        if (checkoutBtn) {
            checkoutBtn.disabled = true;
            checkoutBtn.textContent = "Cobrar Orden (Q 0.00)";
        }
        if (subIvaEl) subIvaEl.textContent = "Q 0.00";
        if (ivaEl) ivaEl.textContent = "Q 0.00";
        if (totalEl) totalEl.textContent = "Q 0.00";
        return;
    }

    const { totalProductos, baseImponible, montoIva } = calculateOrderTotals();

    // Construir lista de ítems mediante HTML seguro
    const itemsHtml = state.order.items.map(it => {
        const sub = (parseFloat(it.product.precio_venta) * it.quantity).toFixed(2);
        return `
        <div class="order-item-row" data-id="${it.product.id_producto}">
            <div class="order-item-info">
                <div class="order-item-name">${escHtml(it.product.nombre)}</div>
                <div class="order-item-unit-price">Q ${parseFloat(it.product.precio_venta).toFixed(2)} c/u</div>
            </div>
            <div class="order-item-qty-controls">
                <button class="qty-btn" data-action="dec" data-id="${it.product.id_producto}">−</button>
                <span class="qty-value">${it.quantity}</span>
                <button class="qty-btn" data-action="inc" data-id="${it.product.id_producto}">+</button>
            </div>
            <div class="order-item-subtotal">Q ${sub}</div>
            <button class="delete-item-btn" data-action="del" data-id="${it.product.id_producto}" title="Quitar">✕</button>
        </div>`;
    }).join("");

    container.innerHTML = itemsHtml;

    // Listeners qty +/-
    container.querySelectorAll(".qty-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = parseInt(btn.getAttribute("data-id"), 10);
            const action = btn.getAttribute("data-action");
            updateItemQuantity(id, action === "inc" ? 1 : -1);
        });
    });

    // Listeners eliminar
    container.querySelectorAll(".delete-item-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            removeItemFromOrder(parseInt(btn.getAttribute("data-id"), 10));
        });
    });

    // Actualizar totales en el pie de la comanda
    if (subIvaEl) subIvaEl.textContent = `Q ${baseImponible.toFixed(2)}`;
    if (ivaEl) ivaEl.textContent = `Q ${montoIva.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `Q ${totalProductos.toFixed(2)}`;

    if (checkoutBtn) {
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = `Cobrar Orden (Q ${totalProductos.toFixed(2)})`;
    }
}

// ─────────────────────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────────────────────
function initEventListeners() {
    // Categorías
    document.querySelectorAll(".category-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".category-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            state.activeCategory = tab.getAttribute("data-cat");
            applyFilter();
        });
    });

    // Búsqueda en tiempo real
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
        searchInput.addEventListener("input", e => {
            state.searchQuery = e.target.value;
            applyFilter();
        });
    }

    // Selector de mesa
    const tableSelect = document.getElementById("table-select");
    if (tableSelect) {
        tableSelect.value = state.order.table;
        tableSelect.addEventListener("change", e => {
            state.order.table = e.target.value;
            saveOrderToStorage();
        });
    }

    // Abrir modal de cobro (#btn-cobrar / #checkout-btn)
    const checkoutBtn = document.getElementById("btn-cobrar") || document.getElementById("checkout-btn");
    if (checkoutBtn) {
        checkoutBtn.addEventListener("click", () => {
            if (state.order.items.length > 0) openCheckoutModal();
        });
    }

    // Cerrar modales (delegación de eventos)
    document.addEventListener("click", e => {
        if (e.target.matches(".modal-close, .modal-cancel")) {
            document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
        }
        // Click en overlay fondo
        if (e.target.matches(".modal-overlay")) {
            e.target.classList.remove("active");
        }
    });

    // Métodos de pago
    document.querySelectorAll(".payment-method-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".payment-method-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.selectedPaymentMethod = btn.getAttribute("data-method");
        });
    });

    // CF rápido
    const cfBtn = document.getElementById("btn-cf-fast");
    if (cfBtn) {
        cfBtn.addEventListener("click", () => {
            const nitInput = document.getElementById("fel-nit");
            const nomInput = document.getElementById("fel-nombre");
            if (nitInput) nitInput.value = "CF";
            if (nomInput) nomInput.value = "CONSUMIDOR FINAL";
        });
    }

    // NIT con Debounce 400ms
    const nitInput = document.getElementById("fel-nit");
    const nomInput = document.getElementById("fel-nombre");
    if (nitInput && nomInput) {
        nitInput.addEventListener("input", () => {
            clearTimeout(state.nitDebounceTimer);
            const nit = nitInput.value.trim();

            if (!nit || nit.toUpperCase() === "CF") {
                nomInput.value = "CONSUMIDOR FINAL";
                return;
            }
            if (nit.length < 6) return;

            nomInput.placeholder = "Buscando en padrón…";

            state.nitDebounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/v1/auth/nit/${encodeURIComponent(nit)}`, {
                        headers: { Authorization: `Bearer ${authState.getToken()}` }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        nomInput.value = data.nombre || "";
                    }
                } catch {
                    // Sin conexión: dejar vacío para ingreso manual
                    nomInput.value = "";
                } finally {
                    nomInput.placeholder = "Nombre Receptor";
                }
            }, 400);
        });
    }

    // Botones de propina
    document.querySelectorAll(".tip-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tip-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.tipPercentage = parseInt(btn.getAttribute("data-tip"), 10);
            updateCheckoutTotals();
        });
    });

    // Botón Guardar Comanda Abierta en BD
    const btnGuardarComanda = document.getElementById("btn-guardar-comanda");
    if (btnGuardarComanda) btnGuardarComanda.addEventListener("click", guardarComandaAbierta);

    // Confirmar cobro
    const confirmBtn = document.getElementById("confirm-payment-btn");
    if (confirmBtn) confirmBtn.addEventListener("click", handleExecutePayment);

    // Imprimir ticket
    function imprimirTicket() {
        window.print();
    }
    window.imprimirTicket = imprimirTicket;

    const printBtn = document.getElementById("print-ticket-btn");
    if (printBtn) printBtn.addEventListener("click", imprimirTicket);

    // Botón Nueva Orden (Barra lateral)
    const btnNuevaOrden = document.getElementById("btn-nueva-orden");
    if (btnNuevaOrden) {
        btnNuevaOrden.addEventListener("click", (e) => {
            e.preventDefault();
            iniciarNuevaOrden();
        });
    }

    // Logout / Bloquear sesión (Barra lateral y Barra superior)
    const logoutBtns = document.querySelectorAll("#logout-btn, #top-logout-btn");
    logoutBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            saveOrderToStorage(); // Preservar comanda intacta para el próximo bartender
            authState.clear();
            window.location.href = "/index.html";
        });
    });
}

// ─────────────────────────────────────────────────────────────
// Iniciar Nueva Orden (Limpia comanda y activa selector de mesa)
// ─────────────────────────────────────────────────────────────
function iniciarNuevaOrden() {
    state.order = {
        id_orden: null,
        table: "Barra 360 - Asiento 1",
        items: []
    };
    clearOrderStorage();
    renderOrderItems();
    const tableSelect = document.getElementById("table-select");
    if (tableSelect) {
        tableSelect.disabled = false;
        tableSelect.value = "Barra 360 - Asiento 1";
        state.order.table = "Barra 360 - Asiento 1";
        tableSelect.focus();
    }
    // Cerrar cualquier modal que pudiera estar activo
    document.querySelectorAll(".modal-overlay").forEach(m => {
        m.classList.remove("active");
        m.classList.add("hidden");
    });
    showToast("Comanda vaciada. Lista para registrar nueva mesa.", "info");
}
window.iniciarNuevaOrden = iniciarNuevaOrden;

// ─────────────────────────────────────────────────────────────
// Guardar Comanda Abierta en Base de Datos
// ─────────────────────────────────────────────────────────────
async function guardarComandaAbierta() {
    if (!state.order.items.length) {
        showToast("Agrega al menos un producto a la comanda antes de guardarla.", "warning");
        return;
    }

    const btn = document.getElementById("btn-guardar-comanda");
    const origText = btn ? btn.textContent : "";
    if (btn) {
        btn.disabled = true;
        btn.textContent = "💾 Guardando comanda...";
    }

    try {
        const itemsPayload = state.order.items.map(it => ({
            id_producto: it.product.id_producto,
            cantidad: it.quantity
        }));

        if (state.order.id_orden) {
            const updated = await api.updateOrden(state.order.id_orden, state.order.table, itemsPayload);
            showToast(`✓ Comanda #${updated.id_orden} actualizada como ABIERTA (${state.order.table}).`, "success");
        } else {
            const created = await api.createOrden(state.order.table, itemsPayload);
            state.order.id_orden = created.id_orden;
            showToast(`✓ Comanda #${created.id_orden} guardada como ABIERTA (${state.order.table}).`, "success");
        }
        saveOrderToStorage();
    } catch (err) {
        showToast("Error al guardar comanda en base de datos: " + err.message, "danger");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = origText;
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Modal de Cobro (#modal-cobro / #checkout-modal)
// ─────────────────────────────────────────────────────────────
function openCheckoutModal() {
    updateCheckoutTotals();

    // Restaurar propina activa
    document.querySelectorAll(".tip-btn").forEach(b => {
        b.classList.toggle("active", parseInt(b.getAttribute("data-tip"), 10) === state.tipPercentage);
    });

    const modal = document.getElementById("modal-cobro") || document.getElementById("checkout-modal");
    if (modal) {
        modal.classList.add("active");
        modal.classList.remove("hidden");
    }
}

function updateCheckoutTotals() {
    const { totalProductos, propina, totalFinal } = calculateOrderTotals();

    const sub = document.getElementById("modal-subtotal");
    const tip = document.getElementById("modal-tip");
    const tot = document.getElementById("modal-total");

    if (sub) sub.textContent = `Q ${totalProductos.toFixed(2)}`;
    if (tip) tip.textContent = `Q ${propina.toFixed(2)}`;
    if (tot) tot.textContent = `Q ${totalFinal.toFixed(2)}`;
}

// ─────────────────────────────────────────────────────────────
// Ejecución del Cobro (ACID + Escandallo)
// ─────────────────────────────────────────────────────────────
async function handleExecutePayment() {
    const confirmBtn = document.getElementById("confirm-payment-btn");
    if (!confirmBtn) return;

    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `<span class="spinner-inline"></span> Procesando Escandallos y FEL…`;

    try {
        const { totalProductos, propina } = calculateOrderTotals();
        const nit = (document.getElementById("fel-nit")?.value.trim()) || "CF";
        const nombre = (document.getElementById("fel-nombre")?.value.trim()) || "CONSUMIDOR FINAL";

        // 1. Obtener o crear orden abierta en backend
        let orderId = state.order.id_orden;
        const itemsPayload = state.order.items.map(it => ({
            id_producto: it.product.id_producto,
            cantidad: it.quantity
        }));

        if (!orderId) {
            const createdOrder = await api.createOrden(state.order.table, itemsPayload);
            orderId = createdOrder.id_orden;
        } else {
            await api.updateOrden(orderId, state.order.table, itemsPayload);
        }

        // 2. Cobrar con deducción atómica de inventario
        const resCobro = await api.cobrarOrden(orderId, {
            metodo_pago: state.selectedPaymentMethod,
            monto_pagado: totalProductos,
            propina: propina,
            nit_receptor: nit,
            nombre_receptor: nombre
        });

        // 3. Cerrar modal de cobro (#modal-cobro / #checkout-modal)
        const modalCobro = document.getElementById("modal-cobro") || document.getElementById("checkout-modal");
        if (modalCobro) modalCobro.classList.remove("active");

        // 4. Mostrar ticket térmico con su QR (sin appendChild de strings)
        showTicketModal(resCobro.ticket_termico, resCobro.alertas_inventario);

        // 5. Limpiar comanda de la pantalla
        state.order.items = [];
        state.order.id_orden = null;
        renderOrderItems();

        // 6. Y SOLO ENTONCES se borra de localStorage.removeItem('bourlemont_orden_activa')
        localStorage.removeItem(STORAGE_KEY);

        // 7. Recargar stocks actualizados
        await loadProducts();

    } catch (err) {
        showToast(err.message || "Error al procesar el cobro. Intenta nuevamente.", "danger");
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "Confirmar y Emitir Factura";
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Asegurar existencia en el DOM de #ticket-modal y contenedores
// ─────────────────────────────────────────────────────────────
function ensureTicketModalInDOM() {
    let modal = document.getElementById("ticket-modal");
    if (!modal) {
        const modalHtml = `
  <div id="ticket-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="ticket-modal-title">
    <div class="modal-content" style="max-width: 480px;">
      <div class="modal-header">
        <h3 class="modal-title" id="ticket-modal-title">🖨️ Ticket &amp; Factura FEL</h3>
        <button class="modal-close" aria-label="Cerrar">&times;</button>
      </div>

      <div id="ticket-inventory-alerts" class="badge badge-warning"
           style="display: none; width: 100%; margin-bottom: 12px; padding: 10px; text-align: left; line-height: 1.5; font-size: 13px; text-transform: none; border-radius: var(--radius-md);">
      </div>

      <div id="ticket-printable-area" class="ticket-printable-area">
        <pre id="ticket-content-box" class="thermal-ticket-box"></pre>
        <div id="ticket-qr-container" class="ticket-qr-container"></div>
      </div>

      <div style="display: flex; gap: 10px; margin-top: 18px;">
        <button type="button" class="btn modal-close" style="flex: 1;">Cerrar</button>
        <button type="button" id="print-ticket-btn" class="btn btn-gold" style="flex: 2;">
          🖨️ Imprimir Ticket (80mm)
        </button>
      </div>
    </div>
  </div>`;
        document.body.insertAdjacentHTML("beforeend", modalHtml);
        modal = document.getElementById("ticket-modal");

        // Listeners del modal generado dinámicamente
        const printBtn = modal.querySelector("#print-ticket-btn");
        if (printBtn) printBtn.addEventListener("click", imprimirTicket);

        modal.querySelectorAll(".modal-close").forEach(btn => {
            btn.addEventListener("click", () => {
                modal.classList.remove("active");
                modal.classList.add("hidden");
            });
        });
    } else {
        // Asegurar que exista contenedor QR si no estaba presente
        if (!document.getElementById("ticket-qr-container")) {
            const ticketBox = document.getElementById("ticket-content-box");
            if (ticketBox) {
                ticketBox.insertAdjacentHTML("afterend", '<div id="ticket-qr-container" class="ticket-qr-container"></div>');
            }
        }
        // Asegurar que exista envoltorio ticket-printable-area
        const ticketBox = document.getElementById("ticket-content-box");
        const qrContainer = document.getElementById("ticket-qr-container");
        if (ticketBox && !document.getElementById("ticket-printable-area")) {
            const printableArea = document.createElement("div");
            printableArea.id = "ticket-printable-area";
            printableArea.className = "ticket-printable-area";
            ticketBox.parentNode.insertBefore(printableArea, ticketBox);
            printableArea.appendChild(ticketBox);
            if (qrContainer) printableArea.appendChild(qrContainer);
        }
    }
    return modal;
}

function ensureToastContainerInDOM() {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        Object.assign(container.style, {
            position: "fixed",
            bottom: "28px",
            right: "28px",
            zIndex: "9999",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            pointerEvents: "none"
        });
        document.body.appendChild(container);
    }
    return container;
}

function generateQrSvg() {
    return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="110" height="110" style="display:block;margin:0 auto;background:#fff;">
        <!-- Finder top-left -->
        <rect x="10" y="10" width="24" height="24" fill="#000" rx="2" />
        <rect x="14" y="14" width="16" height="16" fill="#fff" />
        <rect x="18" y="18" width="8" height="8" fill="#000" />
        <!-- Finder top-right -->
        <rect x="66" y="10" width="24" height="24" fill="#000" rx="2" />
        <rect x="70" y="14" width="16" height="16" fill="#fff" />
        <rect x="74" y="18" width="8" height="8" fill="#000" />
        <!-- Finder bottom-left -->
        <rect x="10" y="66" width="24" height="24" fill="#000" rx="2" />
        <rect x="14" y="70" width="16" height="16" fill="#fff" />
        <rect x="18" y="74" width="8" height="8" fill="#000" />
        <!-- Timing & Alignment -->
        <rect x="42" y="12" width="4" height="4" fill="#000" />
        <rect x="50" y="12" width="4" height="4" fill="#000" />
        <rect x="58" y="12" width="4" height="4" fill="#000" />
        <rect x="12" y="42" width="4" height="4" fill="#000" />
        <rect x="12" y="50" width="4" height="4" fill="#000" />
        <rect x="12" y="58" width="4" height="4" fill="#000" />
        <rect x="44" y="44" width="12" height="12" fill="#000" rx="1" />
        <rect x="48" y="48" width="4" height="4" fill="#fff" />
        <!-- Data pixels simulation -->
        <rect x="38" y="22" width="4" height="4" fill="#000" />
        <rect x="46" y="26" width="4" height="4" fill="#000" />
        <rect x="54" y="22" width="4" height="4" fill="#000" />
        <rect x="38" y="34" width="4" height="4" fill="#000" />
        <rect x="46" y="38" width="4" height="4" fill="#000" />
        <rect x="62" y="38" width="4" height="4" fill="#000" />
        <rect x="26" y="46" width="4" height="4" fill="#000" />
        <rect x="34" y="54" width="4" height="4" fill="#000" />
        <rect x="62" y="46" width="4" height="4" fill="#000" />
        <rect x="70" y="50" width="4" height="4" fill="#000" />
        <rect x="78" y="42" width="4" height="4" fill="#000" />
        <rect x="86" y="46" width="4" height="4" fill="#000" />
        <rect x="62" y="58" width="4" height="4" fill="#000" />
        <rect x="74" y="58" width="4" height="4" fill="#000" />
        <rect x="82" y="54" width="4" height="4" fill="#000" />
        <rect x="38" y="66" width="4" height="4" fill="#000" />
        <rect x="46" y="74" width="4" height="4" fill="#000" />
        <rect x="54" y="66" width="4" height="4" fill="#000" />
        <rect x="42" y="82" width="4" height="4" fill="#000" />
        <rect x="50" y="86" width="4" height="4" fill="#000" />
        <rect x="58" y="82" width="4" height="4" fill="#000" />
        <rect x="66" y="70" width="4" height="4" fill="#000" />
        <rect x="78" y="70" width="4" height="4" fill="#000" />
        <rect x="86" y="74" width="4" height="4" fill="#000" />
        <rect x="70" y="82" width="4" height="4" fill="#000" />
        <rect x="82" y="86" width="4" height="4" fill="#000" />
    </svg>
    <div class="ticket-qr-caption">VERIFICADOR SAT DTE · GUATEMALA</div>`;
}

// ─────────────────────────────────────────────────────────────
// Modal Ticket Térmico
// ─────────────────────────────────────────────────────────────
function showTicketModal(ticketText, alertas) {
    const modal = document.getElementById("ticket-modal") || ensureTicketModalInDOM();
    const ticketBox = document.getElementById("ticket-content-box");
    const alertsBox = document.getElementById("ticket-inventory-alerts");
    const qrContainer = document.getElementById("ticket-qr-container");

    if (ticketBox) {
        ticketBox.textContent = ticketText || "(Sin contenido de ticket)";
    }

    if (qrContainer) {
        qrContainer.innerHTML = "";
        qrContainer.insertAdjacentHTML("beforeend", generateQrSvg());
    }

    if (alertsBox) {
        if (alertas && alertas.length > 0) {
            alertsBox.innerHTML = "";
            const alertsHtml = alertas.map(a => `<div>⚠ ${escHtml(a)}</div>`).join("");
            alertsBox.insertAdjacentHTML("beforeend", alertsHtml);
            alertsBox.style.display = "block";
        } else {
            alertsBox.style.display = "none";
        }
    }

    modal.classList.add("active");
    modal.classList.remove("hidden");
    const overlay = modal.querySelector(".modal-overlay");
    if (overlay) {
        overlay.classList.add("active");
        overlay.classList.remove("hidden");
    }
}

// ─────────────────────────────────────────────────────────────
// Toast Notifications (sin appendChild de strings)
// ─────────────────────────────────────────────────────────────
function showToast(message, type = "success") {
    const container = ensureToastContainerInDOM();

    // Eliminar toast anterior si existe
    container.querySelector(".bl-toast")?.remove();

    // Crear el elemento de forma segura con document.createElement
    const toast = document.createElement("div");
    toast.className = `bl-toast badge badge-${type}`;
    toast.textContent = message;

    Object.assign(toast.style, {
        pointerEvents: "auto",
        padding: "14px 22px",
        fontSize: "14px",
        boxShadow: "0 8px 32px rgba(0,0,0,.6)",
        borderRadius: "var(--radius-md, 8px)",
        maxWidth: "360px",
        lineHeight: "1.45",
        animation: "toastIn 0.3s cubic-bezier(0.2,0.8,0.2,1)",
        transition: "opacity .3s, transform .3s"
    });

    // Inserción segura al contenedor de notificaciones
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// ─────────────────────────────────────────────────────────────
// Utilidades
// ─────────────────────────────────────────────────────────────
function escHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
