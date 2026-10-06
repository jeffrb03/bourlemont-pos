import { api, authState } from "./api.js";

// ─────────────────────────────────────────────
// Constantes de Persistencia en localStorage
// ─────────────────────────────────────────────
const STORAGE_KEY = "bourlemont_active_order";
const BOTTLE_SVG = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 200" fill="none"><rect x="30" y="0" width="20" height="30" rx="4" fill="%2363522A"/><path d="M25 30 Q20 60 18 90 L18 170 Q18 180 40 180 Q62 180 62 170 L62 90 Q60 60 55 30 Z" fill="%232A2416" stroke="%2363522A" stroke-width="2"/><path d="M26 110 Q40 100 54 110" stroke="%23D4AF37" stroke-width="1.5" stroke-linecap="round"/><path d="M26 125 Q40 115 54 125" stroke="%23D4AF37" stroke-width="1" stroke-linecap="round" opacity="0.5"/></svg>`;

// ─────────────────────────────────────────────
// Estado Central del POS
// ─────────────────────────────────────────────
const state = {
    user: null,
    products: [],
    filteredProducts: [],
    activeCategory: "TODOS",
    searchQuery: "",
    order: {
        table: "Barra 360 - Asiento 1",
        items: [] // { product, quantity }
    },
    selectedPaymentMethod: "EFECTIVO",
    tipPercentage: 10,
    nitDebounceTimer: null
};

// ─────────────────────────────────────────────
// Inicialización
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    if (!authState.isAuthenticated()) {
        window.location.href = "/index.html";
        return;
    }

    state.user = authState.getUser();
    renderHeaderUser();

    // Recuperar comanda activa desde localStorage (resiliencia ante apagones)
    restoreOrderFromStorage();

    initEventListeners();

    await loadProducts();
});

// ─────────────────────────────────────────────
// Header: usuario activo
// ─────────────────────────────────────────────
function renderHeaderUser() {
    const userNameEl = document.getElementById("header-user-name");
    const userRoleEl = document.getElementById("header-user-role");
    const adminLinks = document.querySelectorAll(".admin-only");

    if (userNameEl) userNameEl.textContent = state.user.nombre;
    if (userRoleEl) userRoleEl.textContent = state.user.rol;

    if (!authState.isAdmin()) {
        adminLinks.forEach(el => el.style.display = "none");
    }
}

// ─────────────────────────────────────────────
// Persistencia localStorage
// ─────────────────────────────────────────────
function saveOrderToStorage() {
    try {
        const payload = {
            table: state.order.table,
            tipPercentage: state.tipPercentage,
            selectedPaymentMethod: state.selectedPaymentMethod,
            // Guardar solo el id y datos esenciales para rehydratar sin imagen
            items: state.order.items.map(it => ({
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
                },
                quantity: it.quantity
            }))
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (e) {
        console.warn("No se pudo persistir la comanda:", e);
    }
}

function restoreOrderFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (saved && saved.items && saved.items.length > 0) {
            state.order.items = saved.items;
            state.order.table = saved.table || state.order.table;
            state.tipPercentage = saved.tipPercentage ?? 10;
            state.selectedPaymentMethod = saved.selectedPaymentMethod || "EFECTIVO";

            // Sincronizar selector de mesa
            const tableSelect = document.getElementById("table-select");
            if (tableSelect) tableSelect.value = state.order.table;

            showToast(`Comanda restaurada con ${saved.items.length} ítem(s) desde la última sesión.`, "success");
        }
    } catch (e) {
        console.warn("No se pudo restaurar comanda:", e);
        localStorage.removeItem(STORAGE_KEY);
    }
}

function clearOrderStorage() {
    localStorage.removeItem(STORAGE_KEY);
}

// ─────────────────────────────────────────────
// Catálogo de Productos
// ─────────────────────────────────────────────
async function loadProducts() {
    try {
        state.products = await api.getProductos();
        applyFilter();
        // Re-render comanda (en caso de restauración desde storage, hay que ligar los objetos)
        renderOrderItems();
    } catch (err) {
        showToast("Error al cargar catálogo de productos", "danger");
    }
}

function applyFilter() {
    state.filteredProducts = state.products.filter(p => {
        if (p.categoria === "INSUMOS_BASE") return false;
        const matchCategory = state.activeCategory === "TODOS" || p.categoria === state.activeCategory;
        const matchSearch = p.nombre.toLowerCase().includes(state.searchQuery.toLowerCase());
        return matchCategory && matchSearch;
    });
    renderProductGrid();
}

function getProductImageSrc(product) {
    if (product.imagen_url && product.imagen_url.trim()) {
        return `/static/${product.imagen_url}`;
    }
    return BOTTLE_SVG;
}

function renderProductGrid() {
    const grid = document.getElementById("products-grid");
    if (!grid) return;

    if (state.filteredProducts.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; color: var(--text-tertiary); padding: 40px;">
                <div style="font-size: 36px; margin-bottom: 12px; opacity: 0.4;">🍾</div>
                No se encontraron productos en esta categoría.
            </div>`;
        return;
    }

    grid.innerHTML = state.filteredProducts.map(p => {
        const isLow = p.stock_ml > 0 && p.stock_ml <= p.stock_minimo_ml;
        const isNegative = p.stock_ml < 0;

        let stockLabel = "";
        if (p.unidad_medida === "ml" && p.stock_ml > 0) {
            stockLabel = `${(p.stock_ml / 750).toFixed(1)} bot`;
        } else if (p.tipo === "COMPUESTO") {
            stockLabel = "Escandallo";
        }

        const imgSrc = getProductImageSrc(p);
        const stockStatusClass = isNegative ? "low" : (isLow ? "low" : "");

        return `
            <div class="product-card ${p.categoria.toLowerCase().replace('_', '-')}" data-id="${p.id_producto}" tabindex="0" role="button">
                <div class="product-card-img-wrap">
                    <img src="${imgSrc}" 
                         alt="${escapeHtml(p.nombre)}" 
                         class="product-card-img"
                         onerror="this.src='${BOTTLE_SVG}'">
                </div>
                <div class="product-card-body">
                    <div class="product-title">${escapeHtml(p.nombre)}</div>
                    <div class="product-meta">
                        <span>${p.categoria}</span>
                        ${stockLabel ? `<span>·</span><span>${stockLabel}</span>` : ""}
                    </div>
                </div>
                <div class="product-price-row">
                    <span class="product-price">Q ${parseFloat(p.precio_venta).toFixed(2)}</span>
                    ${isNegative ? `<span class="product-stock-tag low">⚠ Sin Stock</span>` : 
                      (isLow ? `<span class="product-stock-tag low">⚠ Bajo</span>` : "")}
                </div>
            </div>
        `;
    }).join("");

    // Eventos haptic click
    grid.querySelectorAll(".product-card").forEach(card => {
        const activate = () => {
            const id = parseInt(card.getAttribute("data-id"));
            const prod = state.products.find(p => p.id_producto === id);
            if (prod) {
                addItemToOrder(prod);
                card.classList.add("pressed");
                setTimeout(() => card.classList.remove("pressed"), 150);
            }
        };
        card.addEventListener("click", activate);
        card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") activate(); });
    });
}

// ─────────────────────────────────────────────
// Gestión de la Comanda
// ─────────────────────────────────────────────
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
    item.quantity += delta;
    if (item.quantity <= 0) {
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

function calculateOrderTotals() {
    const subtotalBruto = state.order.items.reduce((acc, it) => {
        return acc + (parseFloat(it.product.precio_venta) * it.quantity);
    }, 0);

    const subtotalSinIva = subtotalBruto / 1.12;
    const iva = subtotalBruto - subtotalSinIva;
    const tip = subtotalBruto * (state.tipPercentage / 100);
    const grandTotal = subtotalBruto + tip;

    return { subtotalBruto, subtotalSinIva, iva, tip, grandTotal };
}

function renderOrderItems() {
    const container = document.getElementById("order-items-list");
    const emptyState = document.getElementById("empty-order-state");
    const checkoutBtn = document.getElementById("checkout-btn");
    const subtotalSinIvaEl = document.getElementById("order-subtotal-sin-iva");
    const ivaEl = document.getElementById("order-iva");
    const totalEl = document.getElementById("order-total");

    if (state.order.items.length === 0) {
        if (emptyState) emptyState.style.display = "flex";
        if (container) container.innerHTML = "";
        if (container && emptyState) container.appendChild(emptyState);
        if (checkoutBtn) {
            checkoutBtn.disabled = true;
            checkoutBtn.textContent = "Cobrar Orden (Q 0.00)";
        }
        if (subtotalSinIvaEl) subtotalSinIvaEl.textContent = "Q 0.00";
        if (ivaEl) ivaEl.textContent = "Q 0.00";
        if (totalEl) totalEl.textContent = "Q 0.00";
        return;
    }

    if (emptyState) emptyState.style.display = "none";

    const { subtotalBruto, subtotalSinIva, iva } = calculateOrderTotals();

    container.innerHTML = state.order.items.map(it => {
        const itemSub = (parseFloat(it.product.precio_venta) * it.quantity).toFixed(2);
        return `
            <div class="order-item-row" data-id="${it.product.id_producto}">
                <div class="order-item-info">
                    <div class="order-item-name">${escapeHtml(it.product.nombre)}</div>
                    <div class="order-item-unit-price">Q ${parseFloat(it.product.precio_venta).toFixed(2)} c/u</div>
                </div>
                <div class="order-item-qty-controls">
                    <button class="qty-btn" data-action="dec" data-id="${it.product.id_producto}">−</button>
                    <span class="qty-value">${it.quantity}</span>
                    <button class="qty-btn" data-action="inc" data-id="${it.product.id_producto}">+</button>
                </div>
                <div class="order-item-subtotal">Q ${itemSub}</div>
                <button class="delete-item-btn" data-action="del" data-id="${it.product.id_producto}" title="Quitar">✕</button>
            </div>
        `;
    }).join("");

    container.querySelectorAll(".qty-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = parseInt(btn.getAttribute("data-id"));
            const action = btn.getAttribute("data-action");
            updateItemQuantity(id, action === "inc" ? 1 : -1);
        });
    });

    container.querySelectorAll(".delete-item-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = parseInt(btn.getAttribute("data-id"));
            removeItemFromOrder(id);
        });
    });

    if (subtotalSinIvaEl) subtotalSinIvaEl.textContent = `Q ${subtotalSinIva.toFixed(2)}`;
    if (ivaEl) ivaEl.textContent = `Q ${iva.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `Q ${subtotalBruto.toFixed(2)}`;

    if (checkoutBtn) {
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = `Cobrar Orden (Q ${subtotalBruto.toFixed(2)})`;
    }
}

// ─────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────
function initEventListeners() {
    // Categorías
    const tabs = document.querySelectorAll(".category-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            state.activeCategory = tab.getAttribute("data-cat");
            applyFilter();
        });
    });

    // Búsqueda
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            state.searchQuery = e.target.value;
            applyFilter();
        });
    }

    // Mesa / Ubicación
    const tableInput = document.getElementById("table-select");
    if (tableInput) {
        tableInput.value = state.order.table;
        tableInput.addEventListener("change", (e) => {
            state.order.table = e.target.value;
            saveOrderToStorage();
        });
    }

    // Checkout
    const checkoutBtn = document.getElementById("checkout-btn");
    const checkoutModal = document.getElementById("checkout-modal");
    if (checkoutBtn && checkoutModal) {
        checkoutBtn.addEventListener("click", () => {
            if (state.order.items.length === 0) return;
            openCheckoutModal();
        });
    }

    // Cerrar modales (cierra todos los .modal-overlay activos)
    document.querySelectorAll(".modal-close, .modal-cancel").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
        });
    });

    // Métodos de pago
    document.querySelectorAll(".payment-method-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".payment-method-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.selectedPaymentMethod = btn.getAttribute("data-method");
        });
    });

    // Botón rápido CF
    const cfBtn = document.getElementById("btn-cf-fast");
    if (cfBtn) {
        cfBtn.addEventListener("click", () => {
            document.getElementById("fel-nit").value = "CF";
            document.getElementById("fel-nombre").value = "CONSUMIDOR FINAL";
        });
    }

    // ── NIT con Debounce 400ms y autocompletado simulado ──
    const nitInput = document.getElementById("fel-nit");
    const nombreInput = document.getElementById("fel-nombre");
    if (nitInput && nombreInput) {
        nitInput.addEventListener("input", () => {
            clearTimeout(state.nitDebounceTimer);
            const nit = nitInput.value.trim();

            if (!nit || nit === "CF" || nit === "cf") {
                nombreInput.value = "CONSUMIDOR FINAL";
                return;
            }

            if (nit.length < 6) return;

            // Indica que está buscando
            nombreInput.placeholder = "Buscando en SAT…";
            nombreInput.value = "";

            state.nitDebounceTimer = setTimeout(async () => {
                try {
                    // Intentar lookup en backend (/api/v1/auth/nit/{nit})
                    const res = await fetch(`/api/v1/auth/nit/${encodeURIComponent(nit)}`, {
                        headers: { "Authorization": `Bearer ${authState.getToken()}` }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        nombreInput.value = data.nombre || "";
                        nombreInput.placeholder = "Nombre Receptor";
                    } else {
                        throw new Error("no found");
                    }
                } catch {
                    // Fallback: mantener nombre en blanco para escritura manual
                    nombreInput.value = "";
                    nombreInput.placeholder = "Nombre Receptor (ingresar manualmente)";
                }
            }, 400);
        });
    }

    // Propina
    document.querySelectorAll(".tip-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tip-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.tipPercentage = parseInt(btn.getAttribute("data-tip"));
            updateCheckoutTotals();
        });
    });

    // Confirmar Cobro
    const confirmPaymentBtn = document.getElementById("confirm-payment-btn");
    if (confirmPaymentBtn) {
        confirmPaymentBtn.addEventListener("click", handleExecutePayment);
    }

    // Imprimir Ticket
    const printTicketBtn = document.getElementById("print-ticket-btn");
    if (printTicketBtn) {
        printTicketBtn.addEventListener("click", () => window.print());
    }

    // Logout / Bloquear
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            // Preservar la comanda activa para cuando el sucesor regrese
            saveOrderToStorage();
            authState.clear();
            window.location.href = "/index.html";
        });
    }
}

// ─────────────────────────────────────────────
// Modal de Cobro
// ─────────────────────────────────────────────
function openCheckoutModal() {
    const modal = document.getElementById("checkout-modal");
    updateCheckoutTotals();

    // Restaurar propina activa visualmente
    document.querySelectorAll(".tip-btn").forEach(b => {
        b.classList.remove("active");
        if (parseInt(b.getAttribute("data-tip")) === state.tipPercentage) {
            b.classList.add("active");
        }
    });

    modal.classList.add("active");
}

function updateCheckoutTotals() {
    const { subtotalBruto, tip, grandTotal } = calculateOrderTotals();
    const modalSub = document.getElementById("modal-subtotal");
    const modalTip = document.getElementById("modal-tip");
    const modalTotal = document.getElementById("modal-total");

    if (modalSub) modalSub.textContent = `Q ${subtotalBruto.toFixed(2)}`;
    if (modalTip) modalTip.textContent = `Q ${tip.toFixed(2)}`;
    if (modalTotal) modalTotal.textContent = `Q ${grandTotal.toFixed(2)}`;
}

// ─────────────────────────────────────────────
// Transacción de Cobro
// ─────────────────────────────────────────────
async function handleExecutePayment() {
    const confirmBtn = document.getElementById("confirm-payment-btn");
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `<span class="spinner-inline"></span> Procesando Escandallos y FEL…`;

    try {
        const { subtotalBruto, tip } = calculateOrderTotals();
        const nit = (document.getElementById("fel-nit")?.value.trim()) || "CF";
        const nombre = (document.getElementById("fel-nombre")?.value.trim()) || "CONSUMIDOR FINAL";

        // 1. Crear Orden
        const createdOrder = await api.createOrden(
            state.order.table,
            state.order.items.map(it => ({
                id_producto: it.product.id_producto,
                cantidad: it.quantity
            }))
        );

        // 2. Cobrar con deducción atómica de inventario
        const resCobro = await api.cobrarOrden(createdOrder.id_orden, {
            metodo_pago: state.selectedPaymentMethod,
            monto_pagado: subtotalBruto,
            propina: tip,
            nit_receptor: nit,
            nombre_receptor: nombre
        });

        // Cerrar modal de cobro
        document.getElementById("checkout-modal").classList.remove("active");

        // Mostrar Ticket Térmico
        showTicketModal(resCobro.ticket_termico, resCobro.alertas_inventario);

        // Limpiar comanda y storage
        state.order.items = [];
        renderOrderItems();
        clearOrderStorage();

        // Recargar inventario actualizado
        await loadProducts();

    } catch (err) {
        showToast(err.message || "Error al procesar el cobro", "danger");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Confirmar y Emitir Factura";
    }
}

// ─────────────────────────────────────────────
// Modal de Ticket Térmico
// ─────────────────────────────────────────────
function showTicketModal(ticketText, alertas) {
    // El ticket está dentro de #ticket-modal > .modal-overlay
    const ticketOverlay = document.querySelector("#ticket-modal .modal-overlay");
    const ticketBox = document.getElementById("ticket-content-box");
    const alertsBox = document.getElementById("ticket-inventory-alerts");

    if (ticketBox) ticketBox.textContent = ticketText || "(Sin contenido de ticket)";

    if (alertsBox) {
        if (alertas && alertas.length > 0) {
            alertsBox.innerHTML = alertas.map(a => `<div>⚠ ${escapeHtml(a)}</div>`).join("");
            alertsBox.style.display = "block";
        } else {
            alertsBox.style.display = "none";
        }
    }

    if (ticketOverlay) ticketOverlay.classList.add("active");
}

// ─────────────────────────────────────────────
// Toast Notifications
// ─────────────────────────────────────────────
function showToast(message, type = "success") {
    // Remover toast anterior si existe
    const existing = document.querySelector(".bl-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = `bl-toast badge badge-${type}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 28px;
        right: 28px;
        padding: 14px 20px;
        font-size: 14px;
        z-index: 9999;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6);
        border-radius: var(--radius-md);
        max-width: 340px;
        line-height: 1.4;
        animation: toastIn 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = "opacity 0.3s, transform 0.3s";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 300);
    }, 4200);
}

// ─────────────────────────────────────────────
// Escape HTML
// ─────────────────────────────────────────────
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
