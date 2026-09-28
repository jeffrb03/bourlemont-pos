import { api, authState } from "./api.js";

// Estado local de la comanda activa
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
    tipPercentage: 10
};

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Verificación de sesión
    if (!authState.isAuthenticated()) {
        window.location.href = "/index.html";
        return;
    }

    state.user = authState.getUser();
    renderHeaderUser();

    // 2. Inicializar eventos
    initEventListeners();

    // 3. Cargar catálogo de productos
    await loadProducts();
});

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

async function loadProducts() {
    try {
        state.products = await api.getProductos();
        applyFilter();
    } catch (err) {
        showToast("Error al cargar catálogo de productos", "danger");
    }
}

function applyFilter() {
    state.filteredProducts = state.products.filter(p => {
        // Filtrar insumos puros para que no abarroten la carta de venta directa
        if (p.categoria === "INSUMOS_BASE") return false;

        const matchCategory = state.activeCategory === "TODOS" || p.categoria === state.activeCategory;
        const matchSearch = p.nombre.toLowerCase().includes(state.searchQuery.toLowerCase());
        return matchCategory && matchSearch;
    });

    renderProductGrid();
}

function renderProductGrid() {
    const grid = document.getElementById("products-grid");
    if (!grid) return;

    if (state.filteredProducts.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; color: var(--text-tertiary); padding: 40px;">
                No se encontraron productos en esta categoría.
            </div>`;
        return;
    }

    grid.innerHTML = state.filteredProducts.map(p => {
        const isLow = p.stock_ml > 0 && p.stock_ml <= p.stock_minimo_ml;
        const isNegative = p.stock_ml < 0;
        
        let stockLabel = "";
        if (p.unidad_medida === "ml" && p.stock_ml > 0) {
            stockLabel = `${(p.stock_ml / 750).toFixed(1)} bot (${p.stock_ml}ml)`;
        } else if (p.tipo === "COMPUESTO") {
            stockLabel = "Escandallo ml";
        }

        return `
            <div class="product-card ${p.categoria.toLowerCase()}" data-id="${p.id_producto}">
                <div>
                    <div class="product-title">${escapeHtml(p.nombre)}</div>
                    <div class="product-meta">
                        <span>${p.categoria}</span>
                        ${stockLabel ? `<span>·</span><span>${stockLabel}</span>` : ""}
                    </div>
                </div>
                <div class="product-price-row">
                    <span class="product-price">Q ${parseFloat(p.precio_venta).toFixed(2)}</span>
                    ${isNegative ? `<span class="product-stock-tag low">⚠️ Sin Stock</span>` : 
                      (isLow ? `<span class="product-stock-tag low">⚠️ Stock Bajo</span>` : "")}
                </div>
            </div>
        `;
    }).join("");

    // Eventos de selección para agregar a la comanda
    grid.querySelectorAll(".product-card").forEach(card => {
        card.addEventListener("click", () => {
            const id = parseInt(card.getAttribute("data-id"));
            const prod = state.products.find(p => p.id_producto === id);
            if (prod) {
                addItemToOrder(prod);
            }
        });
    });
}

function addItemToOrder(product) {
    const existing = state.order.items.find(it => it.product.id_producto === product.id_producto);
    if (existing) {
        existing.quantity += 1;
    } else {
        state.order.items.push({
            product,
            quantity: 1
        });
    }
    renderOrderItems();
}

function updateItemQuantity(productId, delta) {
    const item = state.order.items.find(it => it.product.id_producto === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
        state.order.items = state.order.items.filter(it => it.product.id_producto !== productId);
    }
    renderOrderItems();
}

function removeItemFromOrder(productId) {
    state.order.items = state.order.items.filter(it => it.product.id_producto !== productId);
    renderOrderItems();
}

function calculateOrderTotals() {
    const subtotalBruto = state.order.items.reduce((acc, it) => {
        return acc + (parseFloat(it.product.precio_venta) * it.quantity);
    }, 0);

    const subtotalSinIva = subtotalBruto / 1.12;
    const iva = subtotalBruto - subtotalSinIva;
    const tip = (subtotalBruto * (state.tipPercentage / 100));
    const grandTotal = subtotalBruto + tip;

    return {
        subtotalBruto,
        subtotalSinIva,
        iva,
        tip,
        grandTotal
    };
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
        if (container) {
            container.innerHTML = "";
            container.appendChild(emptyState);
        }
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
                    <button class="qty-btn" data-action="dec" data-id="${it.product.id_producto}">-</button>
                    <span class="qty-value">${it.quantity}</span>
                    <button class="qty-btn" data-action="inc" data-id="${it.product.id_producto}">+</button>
                </div>
                <div class="order-item-subtotal">Q ${itemSub}</div>
                <button class="delete-item-btn" data-action="del" data-id="${it.product.id_producto}">✕</button>
            </div>
        `;
    }).join("");

    // Asignar listeners a controles +/-
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
        tableInput.addEventListener("change", (e) => {
            state.order.table = e.target.value;
        });
    }

    // Botón de Cobro -> Abre Modal de Liquidación
    const checkoutBtn = document.getElementById("checkout-btn");
    const checkoutModal = document.getElementById("checkout-modal");
    if (checkoutBtn && checkoutModal) {
        checkoutBtn.addEventListener("click", () => {
            if (state.order.items.length === 0) return;
            openCheckoutModal();
        });
    }

    // Cerrar modales
    document.querySelectorAll(".modal-close, .modal-cancel").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
        });
    });

    // Métodos de pago en modal
    document.querySelectorAll(".payment-method-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".payment-method-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.selectedPaymentMethod = btn.getAttribute("data-method");
        });
    });

    // Botón rápido "CF"
    const cfBtn = document.getElementById("btn-cf-fast");
    if (cfBtn) {
        cfBtn.addEventListener("click", () => {
            document.getElementById("fel-nit").value = "CF";
            document.getElementById("fel-nombre").value = "CONSUMIDOR FINAL";
        });
    }

    // Botones de porcentaje de propina
    document.querySelectorAll(".tip-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tip-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.tipPercentage = parseInt(btn.getAttribute("data-tip"));
            updateCheckoutTotals();
        });
    });

    // Confirmar Cobro Transaccional
    const confirmPaymentBtn = document.getElementById("confirm-payment-btn");
    if (confirmPaymentBtn) {
        confirmPaymentBtn.addEventListener("click", handleExecutePayment);
    }

    // Botón Imprimir Ticket
    const printTicketBtn = document.getElementById("print-ticket-btn");
    if (printTicketBtn) {
        printTicketBtn.addEventListener("click", () => {
            window.print();
        });
    }

    // Salir / Logout
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            authState.clear();
            window.location.href = "/index.html";
        });
    }
}

function openCheckoutModal() {
    const modal = document.getElementById("checkout-modal");
    updateCheckoutTotals();
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

async function handleExecutePayment() {
    const confirmBtn = document.getElementById("confirm-payment-btn");
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Procesando Escandallos y FEL...";

    try {
        const { subtotalBruto, tip } = calculateOrderTotals();
        const nit = document.getElementById("fel-nit").value.trim() || "CF";
        const nombre = document.getElementById("fel-nombre").value.trim() || "CONSUMIDOR FINAL";

        // 1. Crear Orden en Backend
        const orderPayload = {
            numero_mesa: state.order.table,
            items: state.order.items.map(it => ({
                id_producto: it.product.id_producto,
                cantidad: it.quantity
            }))
        };

        const createdOrder = await api.createOrden(orderPayload.numero_mesa, orderPayload.items);

        // 2. Ejecutar Cobro Atómico y Deducción de Inventario
        const cobroPayload = {
            metodo_pago: state.selectedPaymentMethod,
            monto_pagado: subtotalBruto,
            propina: tip,
            nit_receptor: nit,
            nombre_receptor: nombre
        };

        const resCobro = await api.cobrarOrden(createdOrder.id_orden, cobroPayload);

        // Cerrar modal de cobro
        document.getElementById("checkout-modal").classList.remove("active");

        // Mostrar Ticket Térmico en Modal
        showTicketModal(resCobro.ticket_termico, resCobro.alertas_inventario);

        // Limpiar comanda
        state.order.items = [];
        renderOrderItems();

        // Recargar inventario para actualizar stocks en pantalla
        await loadProducts();

    } catch (err) {
        showToast(err.message || "Error al procesar el cobro", "danger");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Confirmar y Emitir Factura";
    }
}

function showTicketModal(ticketText, alertas) {
    const ticketModal = document.getElementById("ticket-modal");
    const ticketBox = document.getElementById("ticket-content-box");
    const alertsBox = document.getElementById("ticket-inventory-alerts");

    if (ticketBox) ticketBox.textContent = ticketText;

    if (alertsBox) {
        if (alertas && alertas.length > 0) {
            alertsBox.innerHTML = alertas.map(a => `<div>⚠️ ${escapeHtml(a)}</div>`).join("");
            alertsBox.style.display = "block";
        } else {
            alertsBox.style.display = "none";
        }
    }

    ticketModal.classList.add("active");
}

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `badge badge-${type}`;
    toast.style.position = "fixed";
    toast.style.bottom = "24px";
    toast.style.right = "24px";
    toast.style.padding = "14px 20px";
    toast.style.fontSize = "14px";
    toast.style.zIndex = "9999";
    toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.6)";
    toast.textContent = message;

    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = "opacity 0.3s";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
