/**
 * Bourlemont POS - Dashboard & Arqueos (JavaScript Module)
 * Gestiona métricas en tiempo real, arqueo ciego y reportes de auditoría Excel.
 */
import { api, authState } from "./api.js";

export async function initDashboard() {
  if (!authState.isAuthenticated()) {
    window.location.href = "/index.html";
    return;
  }

  if (!authState.isAdmin()) {
    alert("Acceso denegado: El dashboard requiere credenciales de Administrador.");
    window.location.href = "/pos.html";
    return;
  }

  const u = authState.getUser();
  if (u) {
    const nameEl = document.getElementById("header-user-name");
    const roleEl = document.getElementById("header-user-role");
    if (nameEl) nameEl.textContent = u.nombre;
    if (roleEl) roleEl.textContent = u.rol === "ADMIN" ? "ADMINISTRADOR" : "BARTENDER";
  }

  // Event Listeners
  const formCierre = document.getElementById("form-cierre-caja");
  if (formCierre) {
    formCierre.addEventListener("submit", handleCierreCaja);
  }

  const btnExportExcel = document.getElementById("btn-export-excel");
  if (btnExportExcel) {
    btnExportExcel.addEventListener("click", descargarReporteExcel);
  }

  // Interacción Tarjeta Comandas Abiertas
  const cardComandas = document.getElementById("card-comandas-abiertas");
  if (cardComandas) {
    cardComandas.addEventListener("click", mostrarComandasAbiertasModal);
  }

  // Logout Superior
  const topLogoutBtn = document.getElementById("top-logout-btn");
  if (topLogoutBtn) {
    topLogoutBtn.addEventListener("click", () => {
      authState.clear();
      window.location.href = "/index.html";
    });
  }

  // Cerrar modales
  document.querySelectorAll(".modal-close").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = document.getElementById("modal-comandas-abiertas");
      if (modal) modal.classList.add("hidden");
    });
  });

  const modalComandas = document.getElementById("modal-comandas-abiertas");
  if (modalComandas) {
    modalComandas.addEventListener("click", e => {
      if (e.target === modalComandas) modalComandas.classList.add("hidden");
    });
  }

  initModalAnulacion();

  await loadDashboard();
  await loadCajaStatus();
}

/**
 * Carga métricas del dashboard calculando comandas abiertas únicas del turno actual
 */
export async function loadDashboard() {
  try {
    const metrics = await api.getDashboardMetrics();
    
    const totalEl = document.getElementById("stat-total");
    const ordenesEl = document.getElementById("stat-ordenes");
    const ticketEl = document.getElementById("stat-ticket");
    const abiertasEl = document.getElementById("stat-abiertas");
    const alertasEl = document.getElementById("stat-alertas");

    if (totalEl) totalEl.textContent = `Q ${metrics.total_recaudado.toFixed(2)}`;
    if (ordenesEl) ordenesEl.textContent = metrics.ordenes_cerradas;
    if (ticketEl) ticketEl.textContent = `Q ${metrics.ticket_promedio.toFixed(2)}`;
    if (alertasEl) alertasEl.textContent = metrics.alertas_stock_critico;

    // Conteo quirúrgico de comandas abiertas pertenecientes al turno activo actual
    let comandasAbiertasCount = metrics.ordenes_abiertas;
    try {
      const [ordenesAbiertas, cajaRes] = await Promise.all([
        api.getOrdenes("ABIERTA"),
        api.getCajaActual()
      ]);

      if (cajaRes && cajaRes.abierto && cajaRes.arqueo) {
        const tApertura = new Date(cajaRes.arqueo.fecha_apertura).getTime();
        const unicas = new Set(
          ordenesAbiertas
            .filter(o => o.estado === "ABIERTA" && new Date(o.fecha_creacion).getTime() >= tApertura)
            .map(o => o.id_orden)
        );
        comandasAbiertasCount = unicas.size;
      } else {
        const unicas = new Set(
          ordenesAbiertas
            .filter(o => o.estado === "ABIERTA")
            .map(o => o.id_orden)
        );
        comandasAbiertasCount = unicas.size;
      }
    } catch (e) {
      console.warn("[Dashboard] Usando conteo del backend:", e);
    }

    if (abiertasEl) abiertasEl.textContent = comandasAbiertasCount;

    // Rendimiento de Bartenders
    const bBody = document.getElementById("bartenders-table-body");
    if (bBody && metrics.rendimiento_bartenders) {
      bBody.innerHTML = metrics.rendimiento_bartenders.map(b => `
        <tr class="hover:bg-surface-container-high/40 transition-colors">
          <td class="py-3 px-3 font-semibold text-on-surface">
            ${b.nombre} <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-primary/15 text-primary ml-1">${b.rol}</span>
          </td>
          <td class="py-3 px-3 text-on-surface-variant">${b.ordenes_atendidas}</td>
          <td class="py-3 px-3 font-bold text-primary text-right">Q ${b.total_vendido.toFixed(2)}</td>
        </tr>
      `).join("");
    }

  } catch (err) {
    console.error("Error al cargar dashboard:", err);
  }
}

/**
 * Carga el estado del turno actual de caja y el historial de arqueos
 */
export async function loadCajaStatus() {
  try {
    const res = await api.getCajaActual();
    const infoEl = document.getElementById("caja-estado-info");
    const btnCerrar = document.getElementById("btn-cerrar-caja");

    if (infoEl) {
      if (res.abierto) {
        const a = res.arqueo;
        const hora = new Date(a.fecha_apertura).toLocaleTimeString("es-GT");
        infoEl.innerHTML = `
          <div class="flex items-center gap-2 mb-1">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="text-emerald-400 font-bold uppercase text-xs">Turno Activo Abierto</span>
          </div>
          <div>
            Apertura a las <strong>${hora}</strong> por <strong>${a.nombre_usuario || 'Admin'}</strong>.<br>
            Fondo inicial en gaveta: <strong class="text-primary">Q ${parseFloat(a.fondo_inicial).toFixed(2)}</strong>.
          </div>
        `;
        if (btnCerrar) btnCerrar.disabled = false;
      } else {
        infoEl.innerHTML = `
          <div class="flex items-center gap-2 mb-1">
            <span class="w-2 h-2 rounded-full bg-red-400"></span>
            <span class="text-red-400 font-bold uppercase text-xs">Caja Cerrada</span>
          </div>
          <div>No hay turno activo actualmente en esta terminal.</div>
        `;
        if (btnCerrar) btnCerrar.disabled = true;
      }
    }

    // Historial de Arqueos
    const historial = await api.getHistorialCaja();
    const hBody = document.getElementById("arqueos-table-body");
    if (hBody && Array.isArray(historial)) {
      hBody.innerHTML = historial.map(h => {
        const fApertura = new Date(h.fecha_apertura).toLocaleString("es-GT");
        const fCierre = h.fecha_cierre ? new Date(h.fecha_cierre).toLocaleString("es-GT") : "-";
        const dif = h.diferencia_efectivo !== null ? parseFloat(h.diferencia_efectivo) : null;
        let difBadge = "-";
        if (dif !== null) {
          if (dif === 0) difBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400">Exacto (Q 0.00)</span>`;
          else if (dif > 0) difBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300">+Q ${dif.toFixed(2)} (Sobrante)</span>`;
          else difBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/15 text-red-300">-Q ${Math.abs(dif).toFixed(2)} (Faltante)</span>`;
        }

        return `
          <tr class="hover:bg-surface-container-high/40 transition-colors text-sm">
            <td class="py-2.5 px-3 font-mono text-primary font-semibold">#${h.id_arqueo}</td>
            <td class="py-2.5 px-3 font-medium text-on-surface">${h.nombre_usuario || '-'}</td>
            <td class="py-2.5 px-3 text-xs text-on-surface-variant">${fApertura}</td>
            <td class="py-2.5 px-3 text-xs text-on-surface-variant">${fCierre}</td>
            <td class="py-2.5 px-3">Q ${parseFloat(h.fondo_inicial).toFixed(2)}</td>
            <td class="py-2.5 px-3">${h.efectivo_declarado !== null ? 'Q ' + parseFloat(h.efectivo_declarado).toFixed(2) : '-'}</td>
            <td class="py-2.5 px-3">${h.efectivo_teorico_sistema !== null ? 'Q ' + parseFloat(h.efectivo_teorico_sistema).toFixed(2) : '-'}</td>
            <td class="py-2.5 px-3">${difBadge}</td>
            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded-full text-xs font-semibold ${h.estado === 'ABIERTO' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-primary/15 text-primary'}">${h.estado}</span></td>
          </tr>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Error al cargar estado de caja:", err);
  }
}

/**
 * Cierre ciego de caja
 */
async function handleCierreCaja(e) {
  e.preventDefault();
  const efec = parseFloat(document.getElementById("cierre-efectivo").value);
  const tarj = parseFloat(document.getElementById("cierre-tarjetas").value);

  if (isNaN(efec) || isNaN(tarj)) {
    alert("Por favor ingresa los montos contados en efectivo y vouchers.");
    return;
  }

  if (!window.confirm("¿Confirmas el arqueo ciego y el cierre de turno de caja?")) return;

  try {
    const res = await api.cierreCaja(efec, tarj);
    const resultBox = document.getElementById("arqueo-resultado-box");
    const dif = parseFloat(res.diferencia_efectivo);
    
    if (resultBox) {
      resultBox.style.display = "block";
      resultBox.innerHTML = `
        <h4 class="text-on-surface font-bold text-base mb-2">Resultado del Arqueo #${res.id_arqueo}</h4>
        <p class="text-on-surface-variant">Efectivo Físico Declarado: <strong class="text-on-surface">Q ${efec.toFixed(2)}</strong></p>
        <p class="text-on-surface-variant">Efectivo Teórico Sistema: <strong class="text-on-surface">Q ${parseFloat(res.efectivo_teorico_sistema).toFixed(2)}</strong></p>
        <p class="mt-2 text-base">Diferencia de Caja: 
          <strong class="${dif >= 0 ? 'text-emerald-400' : 'text-red-400'} font-bold">
            ${dif >= 0 ? '+' : ''}Q ${dif.toFixed(2)}
          </strong>
        </p>
      `;
    }

    await loadCajaStatus();
    await loadDashboard();
  } catch (err) {
    alert("Error al cerrar caja: " + err.message);
  }
}

/**
 * Descarga de Excel de Auditoría autenticada con Bearer Token
 */
export async function descargarReporteExcel() {
  const btn = document.getElementById("btn-export-excel");
  const originalText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-title-lg">sync</span><span>Generando Libro Excel...</span>`;
  }
  try {
    const tokenAdmin = authState.getToken();
    const response = await fetch("/api/v1/reportes/ventas/excel", {
      headers: {
        "Authorization": "Bearer " + tokenAdmin
      }
    });
    if (!response.ok) {
      throw new Error(`Error ${response.status}: no se pudo descargar el reporte`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Bourlemont_Auditoria_Ventas_${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Error al descargar Excel: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}

/**
 * Visualización interactiva y gestión de comandas abiertas en modal
 */
export async function mostrarComandasAbiertasModal() {
  const modal = document.getElementById("modal-comandas-abiertas");
  const listaContainer = document.getElementById("lista-comandas-abiertas");
  const totalCountEl = document.getElementById("total-comandas-modal-count");

  if (!modal) return;
  modal.classList.remove("hidden");

  if (listaContainer) {
    listaContainer.innerHTML = `
      <div class="text-center py-8 text-on-surface-variant text-sm flex items-center justify-center gap-2">
        <span class="material-symbols-outlined animate-spin text-primary">sync</span>
        <span>Cargando comandas abiertas en servicio...</span>
      </div>`;
  }

  try {
    const ordenes = await api.getOrdenes("ABIERTA");
    const abiertas = ordenes.filter(o => o.estado === "ABIERTA");

    if (totalCountEl) {
      totalCountEl.textContent = `${abiertas.length} comanda${abiertas.length === 1 ? '' : 's'} activa${abiertas.length === 1 ? '' : 's'}`;
    }

    if (!abiertas || abiertas.length === 0) {
      listaContainer.innerHTML = `
        <div class="text-center py-10 text-on-surface-variant">
          <span class="material-symbols-outlined text-4xl text-amber-400/40 mb-2 block">table_restaurant</span>
          <p class="font-semibold text-on-surface">No hay comandas abiertas en este momento.</p>
          <p class="text-xs text-on-surface-variant mt-1">Todas las mesas han sido liquidadas o no se han iniciado comandas.</p>
        </div>`;
      return;
    }

    listaContainer.innerHTML = abiertas.map(o => {
      const fecha = new Date(o.fecha_creacion).toLocaleTimeString("es-GT", { hour: '2-digit', minute: '2-digit' });
      const itemsCount = (o.items || []).reduce((acc, it) => acc + (it.cantidad || 0), 0);
      const itemsList = (o.items || []).map(it => `${it.cantidad}x ${it.nombre_producto}`).join(", ");
      const totalQ = parseFloat(o.total || 0).toFixed(2);

      return `
        <div class="bg-surface-container/80 border border-white/5 hover:border-amber-400/40 rounded-xl p-3.5 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <span class="font-bold text-on-surface text-sm flex items-center gap-1.5">
                <span class="material-symbols-outlined text-amber-400 text-base">table_restaurant</span>
                <span>${o.numero_mesa || 'Barra'}</span>
              </span>
              <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary uppercase">
                #${o.id_orden}
              </span>
              <span class="text-xs text-on-surface-variant flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">person</span>
                <span>${o.nombre_usuario_creacion || 'Bartender'}</span>
              </span>
              <span class="text-[11px] text-on-surface-variant/80">(${fecha})</span>
            </div>
            <div class="text-xs text-on-surface-variant truncate max-w-md" title="${itemsList}">
              ${itemsCount} productos: <span class="text-on-surface">${itemsList || 'Sin items'}</span>
            </div>
            <div class="text-xs font-bold text-primary mt-1">
              Total acumulado: <span class="text-sm font-currency-display text-primary">Q ${totalQ}</span>
            </div>
          </div>

          <div class="flex items-center gap-2 self-end sm:self-center shrink-0">
            <button class="btn-cargar-pos px-3 py-1.5 rounded-xl bg-primary text-on-primary text-xs font-bold hover:brightness-110 active:scale-95 transition-all flex items-center gap-1" data-id="${o.id_orden}">
              <span class="material-symbols-outlined text-sm">point_of_sale</span>
              <span>Cargar al POS</span>
            </button>
            <button class="btn-anular-orden px-3 py-1.5 rounded-xl bg-error/15 text-error hover:bg-error hover:text-on-error text-xs font-semibold active:scale-95 transition-all flex items-center gap-1 border border-error/20" data-id="${o.id_orden}" data-mesa="${o.numero_mesa || ''}">
              <span class="material-symbols-outlined text-sm">cancel</span>
              <span>Anular</span>
            </button>
          </div>
        </div>
      `;
    }).join("");

    // Listeners Cargar al POS
    listaContainer.querySelectorAll(".btn-cargar-pos").forEach(btn => {
      btn.addEventListener("click", () => {
        const idOrden = parseInt(btn.getAttribute("data-id"), 10);
        const orden = abiertas.find(x => x.id_orden === idOrden);
        if (!orden) return;

        const ordenPos = {
          id_orden: orden.id_orden,
          table: orden.numero_mesa || "Barra 360 - Asiento 1",
          items: (orden.items || []).map(it => ({
            product: {
              id_producto: it.id_producto,
              nombre: it.nombre_producto,
              precio_venta: parseFloat(it.precio_unitario || 0),
              categoria: "COCTELES_AUTOR",
              tipo: "FINAL",
              stock_ml: 1000,
              stock_minimo_ml: 750
            },
            quantity: it.cantidad
          }))
        };

        localStorage.setItem("bourlemont_orden_activa", JSON.stringify(ordenPos));
        window.location.href = "/pos.html";
      });
    });

    // Listeners Anular Comanda
    listaContainer.querySelectorAll(".btn-anular-orden").forEach(btn => {
      btn.addEventListener("click", () => {
        const idOrden = parseInt(btn.getAttribute("data-id"), 10);
        const mesa = btn.getAttribute("data-mesa") || "";
        confirmarAnulacionComanda(idOrden, mesa, btn);
      });
    });

  } catch (err) {
    listaContainer.innerHTML = `<div class="text-center py-6 text-error text-sm">Error al cargar comandas: ${err.message}</div>`;
  }
}

let comandaToAnular = null;

function confirmarAnulacionComanda(idOrden, mesa, btn) {
  const modal = document.getElementById("modal-confirm-anular-comanda");
  if (!modal) return;
  comandaToAnular = { idOrden, mesa, btn };
  modal.classList.remove("hidden");
}

function initModalAnulacion() {
  const modal = document.getElementById("modal-confirm-anular-comanda");
  const btnCancel = document.getElementById("btn-cancelar-anulacion");
  const btnConfirm = document.getElementById("btn-confirmar-anulacion");

  if (!modal) return;

  const cerrar = () => {
    modal.classList.add("hidden");
    comandaToAnular = null;
  };

  btnCancel?.addEventListener("click", cerrar);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) cerrar();
  });

  btnConfirm?.addEventListener("click", async () => {
    if (!comandaToAnular) return;
    const { idOrden, btn } = comandaToAnular;
    try {
      btnConfirm.disabled = true;
      btnConfirm.textContent = "Anulando...";
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Anulando...";
      }
      await api.anularOrden(idOrden);
      cerrar();
      await loadDashboard();
      await mostrarComandasAbiertasModal();
    } catch (err) {
      alert("Error al anular comanda: " + err.message);
      if (btn) btn.disabled = false;
    } finally {
      btnConfirm.disabled = false;
      btnConfirm.textContent = "Confirmar Anulación";
    }
  });
}

// Inicialización automática si se importa como script de página
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initDashboard);
}
