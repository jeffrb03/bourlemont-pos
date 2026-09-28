/**
 * Bourlemont Champagne Bar - Centralized Fetch API Client
 */

const API_BASE = "/api/v1";

export const authState = {
    getToken() {
        return localStorage.getItem("bourlemont_token");
    },
    setToken(token) {
        localStorage.setItem("bourlemont_token", token);
    },
    getUser() {
        const u = localStorage.getItem("bourlemont_user");
        return u ? JSON.parse(u) : null;
    },
    setUser(user) {
        localStorage.setItem("bourlemont_user", JSON.stringify(user));
    },
    clear() {
        localStorage.removeItem("bourlemont_token");
        localStorage.removeItem("bourlemont_user");
    },
    isAuthenticated() {
        return !!this.getToken();
    },
    isAdmin() {
        const u = this.getUser();
        return u && u.rol === "ADMIN";
    }
};

async function request(endpoint, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    const token = authState.getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            authState.clear();
            if (!window.location.pathname.endsWith("index.html") && window.location.pathname !== "/") {
                window.location.href = "/index.html";
            }
            throw new Error("Sesión expirada o no autorizada.");
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Error en la solicitud del servidor.");
        }
        return data;
    } catch (err) {
        console.error(`API Error [${endpoint}]:`, err);
        throw err;
    }
}

export const api = {
    // Autenticación
    async loginPin(pin) {
        const res = await request("/auth/login-pin", {
            method: "POST",
            body: JSON.stringify({ pin })
        });
        authState.setToken(res.access_token);
        authState.setUser(res.usuario);
        return res;
    },

    async loginAdmin(nombre, password) {
        const res = await request("/auth/login-admin", {
            method: "POST",
            body: JSON.stringify({ nombre, password })
        });
        authState.setToken(res.access_token);
        authState.setUser(res.usuario);
        return res;
    },

    async getMe() {
        return request("/auth/me");
    },

    async getUsuarios() {
        return request("/auth/usuarios");
    },

    // Inventario y Productos
    async getProductos(categoria = null, tipo = null) {
        let qs = "";
        const params = [];
        if (categoria) params.push(`categoria=${categoria}`);
        if (tipo) params.push(`tipo=${tipo}`);
        if (params.length) qs = `?${params.join("&")}`;
        return request(`/inventario/productos${qs}`);
    },

    async createProducto(data) {
        return request("/inventario/productos", {
            method: "POST",
            body: JSON.stringify(data)
        });
    },

    async updateProducto(id, data) {
        return request(`/inventario/productos/${id}`, {
            method: "PUT",
            body: JSON.stringify(data)
        });
    },

    async getRecetas() {
        return request("/inventario/recetas");
    },

    async asignarReceta(data) {
        return request("/inventario/recetas", {
            method: "POST",
            body: JSON.stringify(data)
        });
    },

    // Órdenes y Comandas
    async getOrdenes(estado = null) {
        const qs = estado ? `?estado=${estado}` : "";
        return request(`/ordenes${qs}`);
    },

    async getOrden(id) {
        return request(`/ordenes/${id}`);
    },

    async createOrden(numero_mesa, items) {
        return request("/ordenes", {
            method: "POST",
            body: JSON.stringify({ numero_mesa, items })
        });
    },

    async cobrarOrden(id_orden, cobroData) {
        return request(`/ordenes/${id_orden}/cobrar`, {
            method: "POST",
            body: JSON.stringify(cobroData)
        });
    },

    async anularOrden(id_orden) {
        return request(`/ordenes/${id_orden}/anular`, {
            method: "POST"
        });
    },

    // Caja y Arqueo
    async getCajaActual() {
        return request("/caja/actual");
    },

    async aperturaCaja(fondo_inicial) {
        return request("/caja/apertura", {
            method: "POST",
            body: JSON.stringify({ fondo_inicial })
        });
    },

    async cierreCaja(efectivo_declarado, tarjetas_declarado) {
        return request("/caja/cierre", {
            method: "POST",
            body: JSON.stringify({ efectivo_declarado, tarjetas_declarado })
        });
    },

    async getHistorialCaja() {
        return request("/caja/historial");
    },

    // Auditoría
    async getPagosAuditoria() {
        return request("/auditoria/pagos");
    },

    async cambiarMetodoPago(id_pago, nuevo_metodo_pago, motivo) {
        return request("/auditoria/cambiar-metodo-pago", {
            method: "POST",
            body: JSON.stringify({ id_pago, nuevo_metodo_pago, motivo })
        });
    },

    async getLogsAuditoria() {
        return request("/auditoria/logs");
    },

    // Métricas y Reportes
    async getDashboardMetrics() {
        return request("/reportes/dashboard");
    },

    descargarExcelUrl() {
        const token = authState.getToken();
        return `/api/v1/reportes/ventas/excel`;
    }
};
