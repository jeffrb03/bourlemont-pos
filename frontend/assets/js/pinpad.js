import { api, authState } from "./api.js";

document.addEventListener("DOMContentLoaded", () => {
    // Si ya tiene sesión válida, redirigir a pos.html
    if (authState.isAuthenticated()) {
        window.location.href = "/pos.html";
        return;
    }

    const pinDisplay = document.getElementById("pin-display");
    const pinDots = document.querySelectorAll(".pin-dot");
    const errorMsg = document.getElementById("login-error");
    const modeTabs = document.querySelectorAll(".auth-mode-tab");
    const pinSection = document.getElementById("pin-section");
    const adminSection = document.getElementById("admin-section");
    const adminForm = document.getElementById("admin-form");

    let currentPin = "";

    function updatePinDots() {
        pinDots.forEach((dot, index) => {
            if (index < currentPin.length) {
                dot.classList.add("filled");
            } else {
                dot.classList.remove("filled");
            }
        });
    }

    async function handlePinSubmit() {
        if (currentPin.length !== 4) return;
        
        errorMsg.textContent = "";
        errorMsg.style.display = "none";

        try {
            const res = await api.loginPin(currentPin);
            // Éxito: redirección inmediata
            window.location.href = "/pos.html";
        } catch (err) {
            currentPin = "";
            updatePinDots();
            errorMsg.textContent = err.message || "PIN inválido";
            errorMsg.style.display = "block";
            // Efecto de vibración
            pinDisplay.classList.add("shake");
            setTimeout(() => pinDisplay.classList.remove("shake"), 400);
        }
    }

    // Manejo de pulsaciones táctiles en el teclado 3x4
    const keyButtons = document.querySelectorAll(".pin-key");
    keyButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const val = btn.getAttribute("data-val");

            if (val === "clear") {
                currentPin = "";
                updatePinDots();
                errorMsg.style.display = "none";
                return;
            }

            if (val === "back") {
                currentPin = currentPin.slice(0, -1);
                updatePinDots();
                return;
            }

            if (currentPin.length < 4 && /^\d$/.test(val)) {
                currentPin += val;
                updatePinDots();

                if (currentPin.length === 4) {
                    setTimeout(handlePinSubmit, 150);
                }
            }
        });
    });

    // Soporte para teclado físico (0-9, Backspace, Escape)
    window.addEventListener("keydown", (e) => {
        if (adminSection.style.display !== "none") return;

        if (/^[0-9]$/.test(e.key)) {
            if (currentPin.length < 4) {
                currentPin += e.key;
                updatePinDots();
                if (currentPin.length === 4) {
                    setTimeout(handlePinSubmit, 150);
                }
            }
        } else if (e.key === "Backspace") {
            currentPin = currentPin.slice(0, -1);
            updatePinDots();
        } else if (e.key === "Escape" || e.key.toLowerCase() === "c") {
            currentPin = "";
            updatePinDots();
            errorMsg.style.display = "none";
        }
    });

    // Alternar entre PIN Rápido y Credenciales Admin
    modeTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            modeTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            const mode = tab.getAttribute("data-mode");

            errorMsg.style.display = "none";
            if (mode === "admin") {
                pinSection.style.display = "none";
                adminSection.style.display = "block";
            } else {
                adminSection.style.display = "none";
                pinSection.style.display = "block";
                currentPin = "";
                updatePinDots();
            }
        });
    });

    // Envío del formulario de Admin
    if (adminForm) {
        adminForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const nombre = document.getElementById("admin-user").value.trim();
            const password = document.getElementById("admin-pass").value;

            errorMsg.style.display = "none";
            try {
                await api.loginAdmin(nombre, password);
                window.location.href = "/pos.html";
            } catch (err) {
                errorMsg.textContent = err.message || "Credenciales de administrador incorrectas";
                errorMsg.style.display = "block";
            }
        });
    }
});
