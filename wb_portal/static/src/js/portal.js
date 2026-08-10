/** @odoo-module **/

import { whenReady } from "@odoo/owl";

/**
 * WB HR Employee Portal — frontend polish (Odoo 18).
 *
 * Features:
 *  - Portal check-in / check-out with browser geolocation.
 *  - Per-user theme presets (persisted in the session).
 *  - Confirmation dialogs before approving / refusing a leave request.
 *  - Leave form date-sync helper and document upload label.
 */

const WB_THEMES = {
    default: {
        label: "Indigo (Default)",
        vars: {}, // empty = fall back to the admin theme
    },
    ocean: {
        label: "Ocean Blue",
        vars: {
            "--wb-primary": "#2563eb",
            "--wb-primary-strong": "#1a4fc4",
            "--wb-accent": "#60a5fa",
            "--wb-primary-soft": "#e8f0fe",
            "--wb-bg-soft": "#f2f6fd",
            "--wb-page-bg": "#eaf0fa",
        },
    },
    emerald: {
        label: "Emerald",
        vars: {
            "--wb-primary": "#0f9d58",
            "--wb-primary-strong": "#0b7a44",
            "--wb-accent": "#66d9a8",
            "--wb-primary-soft": "#e4f6ee",
            "--wb-bg-soft": "#f2faf6",
            "--wb-page-bg": "#eaf6f0",
        },
    },
    sunset: {
        label: "Sunset",
        vars: {
            "--wb-primary": "#e8590c",
            "--wb-primary-strong": "#b8480a",
            "--wb-accent": "#ffa94d",
            "--wb-primary-soft": "#fdeee2",
            "--wb-bg-soft": "#fdf5ee",
            "--wb-page-bg": "#fbefe4",
        },
    },
    midnight: {
        label: "Midnight (Dark)",
        vars: {
            "--wb-primary": "#8b7cf7",
            "--wb-primary-strong": "#6f5ef0",
            "--wb-accent": "#a29bfe",
            "--wb-primary-soft": "#2c2747",
            "--wb-bg-soft": "#1d2233",
            "--wb-page-bg": "#10131f",
            "--wb-card-bg": "#171b2b",
            "--wb-ink": "#e8eaf2",
            "--wb-muted": "#8b93a7",
            "--wb-border": "#2a3044",
            "--wb-track": "#262c40",
            "--wb-success-soft": "#12352e",
            "--wb-warning-soft": "#3a2d12",
            "--wb-danger-soft": "#3a1c1c",
            "--wb-info-soft": "#152c47",
        },
    },
};

const wbAppliedThemeKeys = new Set();

const WB_THEME_ROOT = ".wb-app, .wb-page";

function wbApplyTheme(preset) {
    const theme = WB_THEMES[preset] || WB_THEMES.default;
    const roots = document.querySelectorAll(WB_THEME_ROOT);
    roots.forEach((root) => {
        wbAppliedThemeKeys.forEach((key) => root.style.removeProperty(key));
        wbAppliedThemeKeys.clear();
        for (const [key, value] of Object.entries(theme.vars)) {
            root.style.setProperty(key, value);
            wbAppliedThemeKeys.add(key);
        }
    });
    const pageBg = theme.vars["--wb-page-bg"];
    if (pageBg) {
        document.body.style.backgroundColor = pageBg;
    } else {
        document.body.style.backgroundColor = "";
    }
}

async function wbSaveTheme(preset) {
    try {
        await fetch("/wb/theme/set", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": window.odoo?.csrf_token || "",
            },
            body: JSON.stringify({ preset }),
        });
    } catch (err) {
        // Silent — theme still applies for the current page.
    }
}

function wbInjectThemePicker() {
    const root = document.querySelector(WB_THEME_ROOT);
    if (!root) {
        return; // only on HR portal pages
    }
    const current = root?.dataset?.wbTheme || "default";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "wb-theme-btn";
    btn.setAttribute("aria-label", "Change theme");
    btn.innerHTML = '<i class="fa fa-paint-brush"/>';
    btn.addEventListener("click", () => {
        panel.classList.toggle("open");
    });

    const panel = document.createElement("div");
    panel.className = "wb-theme-panel";
    panel.innerHTML = `<div class="wb-theme-panel-title">Theme</div>`;
    Object.entries(WB_THEMES).forEach(([key, theme]) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "wb-theme-option" + (key === current ? " active" : "");
        item.dataset.preset = key;
        item.textContent = theme.label;
        item.addEventListener("click", () => {
            wbApplyTheme(key);
            wbSaveTheme(key);
            document.querySelectorAll(".wb-theme-option").forEach((el) =>
                el.classList.toggle("active", el.dataset.preset === key)
            );
            if (key === "default") {
                // Reload so the server-injected admin theme takes over cleanly.
                location.reload();
            }
        });
        panel.appendChild(item);
    });
    document.body.appendChild(btn);
    document.body.appendChild(panel);
    document.addEventListener("click", (evt) => {
        if (!btn.contains(evt.target) && !panel.contains(evt.target)) {
            panel.classList.remove("open");
        }
    });
}

// ---------------------------------------------------------------------------
// Notification center (bell dropdown) + browser notifications
// ---------------------------------------------------------------------------
async function wbPost(path, payload) {
    return fetch(path, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": window.odoo?.csrf_token || "",
        },
        body: JSON.stringify(payload || {}),
    }).then((r) => r.json());
}

// Position the notification tray so it is ALWAYS fully inside the viewport
// (fixes the tray being cut off on the left of the sidebar/navbar).
function wbPositionNotifPanel(bell, panel) {
    const rect = bell.getBoundingClientRect();
    const margin = 8;
    const vw = window.innerWidth || document.documentElement.clientWidth || 0;
    const panelW = 340;

    // Desired offset from the viewport's right edge (tray right edge follows
    // the bell's right edge with a small gap).
    let right = vw - rect.right + 4;
    // Clamp so the tray never goes off-screen on either side:
    const maxRight = Math.max(margin, vw - panelW - margin);
    right = Math.min(Math.max(right, margin), maxRight);

    panel.style.position = "fixed";
    panel.style.top = rect.bottom + 8 + "px";
    panel.style.right = right + "px";
    panel.style.left = "auto";
    panel.style.width = Math.min(panelW, Math.max(260, vw - 2 * margin)) + "px";
}

function wbInitNotifications() {
    document.querySelectorAll(".wb-notif").forEach((box) => {
        const bell = box.querySelector(".js-wb-notif-toggle");
        const panel = box.querySelector(".wb-notif-panel");
        if (!bell || !panel) {
            return;
        }
        const close = () => panel.classList.remove("open");
        bell.addEventListener("click", (evt) => {
            evt.stopPropagation();
            const willOpen = !panel.classList.contains("open");
            panel.classList.toggle("open", willOpen);
            if (willOpen) {
                wbPositionNotifPanel(bell, panel);
            }
        });
        // Re-position the open tray when the window is resized/scrolled.
        window.addEventListener("resize", () => {
            if (panel.classList.contains("open")) {
                wbPositionNotifPanel(bell, panel);
            }
        });
        document.addEventListener("click", (evt) => {
            if (!panel.contains(evt.target) && !bell.contains(evt.target)) {
                close();
            }
        });
        document.addEventListener("keydown", (evt) => {
            if (evt.key === "Escape") {
                close();
            }
        });

        // Mark a single notification as read before navigating to its target.
        panel.querySelectorAll(".wb-notif-item").forEach((item) => {
            item.addEventListener("click", () => {
                const id = item.dataset?.id;
                if (id) {
                    wbPost("/wb/notifications/read", { notification_id: Number(id) })
                        .then(() => {});
                }
            });
        });

        // Mark all as read.
        const markAll = panel.querySelector(".js-wb-notif-read-all");
        if (markAll) {
            markAll.addEventListener("click", (evt) => {
                evt.preventDefault();
                evt.stopPropagation();
                wbPost("/wb/notifications/read", {}).then(() => {
                    box.querySelectorAll(".wb-notif-item").forEach((el) =>
                        el.classList.remove("unread")
                    );
                    box.querySelectorAll(".wb-notif-badge").forEach((b) => b.remove());
                    markAll.style.display = "none";
                });
            });
        }
    });
}

// ---------------------------------------------------------------------------
// Left sidebar (mobile off-canvas)
// ---------------------------------------------------------------------------
function wbInitSidebar() {
    const app = document.querySelector(".wb-app");
    if (!app) {
        return;
    }
    const isMobile = () => window.innerWidth < 992;
    const syncAria = () => {
        const open = app.classList.contains("sidebar-open") ||
                     app.classList.contains("sidebar-collapsed");
        document.querySelectorAll(".js-wb-sidebar-toggle").forEach((btn) => {
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        });
    };
    document.querySelectorAll(".js-wb-sidebar-toggle").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (isMobile()) {
                // Mobile: off-canvas drawer.
                app.classList.toggle("sidebar-open");
                app.classList.remove("sidebar-collapsed");
            } else {
                // Desktop: collapse / expand the sidebar in place.
                app.classList.toggle("sidebar-collapsed");
                app.classList.remove("sidebar-open");
            }
            syncAria();
        });
    });
    document.querySelectorAll(".js-wb-sidebar-close").forEach((el) => {
        el.addEventListener("click", () => {
            app.classList.remove("sidebar-open");
            syncAria();
        });
    });
    app.querySelectorAll(".wb-sidebar-nav a").forEach((link) => {
        link.addEventListener("click", () => {
            app.classList.remove("sidebar-open");
            syncAria();
        });
    });
    document.addEventListener("keydown", (evt) => {
        if (evt.key === "Escape") {
            app.classList.remove("sidebar-open");
            syncAria();
        }
    });
    // Keep the two modes clean when the viewport crosses the breakpoint.
    window.addEventListener("resize", () => {
        if (isMobile()) {
            app.classList.remove("sidebar-collapsed");
        } else {
            app.classList.remove("sidebar-open");
        }
        syncAria();
    });
    syncAria();
}

function wbMaybeBrowserNotify(title, body) {
    if (!("Notification" in window) || Notification.permission !== "granted") {
        return;
    }
    try {
        new Notification(title, { body });
    } catch (err) {
        // ignore
    }
}

function wbRequestNotifyPermission() {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
    }
}

// ---------------------------------------------------------------------------
// Geolocation & check-in / check-out
// ---------------------------------------------------------------------------
function wbGetPosition() {
    return new Promise((resolve) => {
        if (!("geolocation" in navigator)) {
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => resolve(pos),
            () => resolve(null),
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    });
}

function wbSetGeoStatus(text, kind) {
    const box = document.getElementById("wb_geo_status");
    const label = document.getElementById("wb_geo_status_text");
    if (!box || !label) {
        return;
    }
    box.className = "wb-geo-status wb-geo-status--" + (kind || "idle");
    label.textContent = text;
}

async function wbClockAction(btn) {
    btn.disabled = true;
    btn.classList.add("is-loading");
    wbRequestNotifyPermission();
    const resultBox = document.getElementById("wb_clock_result");
    const showResult = (text, kind) => {
        if (!resultBox) {
            return;
        }
        resultBox.className = "wb-clock-result wb-clock-result--" + (kind || "info");
        resultBox.textContent = text;
    };
    showResult("Please wait…", "info");

    wbSetGeoStatus("Requesting your location…", "loading");
    const pos = await wbGetPosition();
    const payload = {};
    const locSelect = document.getElementById("wb_work_location");
    if (locSelect && locSelect.value) {
        payload.work_location_id = locSelect.value;
    }
    if (pos) {
        payload.latitude = pos.coords.latitude;
        payload.longitude = pos.coords.longitude;
        wbSetGeoStatus("Location detected — verifying…", "ok");
    } else {
        wbSetGeoStatus("Location unavailable (will check without it)", "warn");
    }

    try {
        const resp = await fetch("/attendance/checkin/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": window.odoo?.csrf_token || "",
            },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (data.error) {
            showResult(data.error, "error");
            wbSetGeoStatus("Location required by your work location policy", "error");
            btn.disabled = false;
            btn.classList.remove("is-loading");
            return;
        }
        showResult(data.message + (data.verified ? " · location verified ✓" : ""), "success");
        wbSetGeoStatus(
            data.distance_km
                ? "You are " + data.distance_km + " km from your work location."
                : "Checked in.",
            "ok"
        );
        wbMaybeBrowserNotify(
            data.state === "in" ? "Checked in" : "Checked out",
            data.message
        );
        setTimeout(() => location.reload(), 1000);
    } catch (err) {
        showResult("Something went wrong. Please try again.", "error");
        wbSetGeoStatus("Location unavailable", "error");
        btn.disabled = false;
        btn.classList.remove("is-loading");
    }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
whenReady(() => {
    const doc = document;

    // ---- Theme ----
    const themeRoot = doc.querySelector(WB_THEME_ROOT);
    if (themeRoot) {
        wbApplyTheme(themeRoot.dataset.wbTheme || "default");
    }
    wbInjectThemePicker();

    // ---- Sidebar (left navigation) ----
    wbInitSidebar();

    // ---- Notification center ----
    wbInitNotifications();

    // ---- Check-in / check-out ----
    doc.querySelectorAll(".js-wb-clock").forEach((btn) => {
        btn.addEventListener("click", () => wbClockAction(btn));
    });

    // Pre-fetch the geolocation status once, on the attendance page.
    if (doc.getElementById("wb_geo_status")) {
        wbSetGeoStatus("Checking your location…", "idle");
        wbGetPosition().then((pos) => {
            if (pos) {
                wbSetGeoStatus("Location detected — ready to check in/out.", "ok");
            } else {
                wbSetGeoStatus(
                    "Location unavailable — the check may be refused if your work location enforces it.",
                    "warn"
                );
            }
        });
    }

    // ---- Confirm approve / refuse actions ----
    doc.querySelectorAll(".js-wb-approve, .js-wb-refuse").forEach((el) => {
        el.addEventListener("click", (evt) => {
            const approve = el.classList.contains("js-wb-approve");
            const employee = el.dataset.employee || "this employee";
            const message = approve
                ? `Approve the time off request of ${employee}?`
                : `Refuse the time off request of ${employee}?`;
            if (!window.confirm(message)) {
                evt.preventDefault();
            }
        });
    });

    // ---- Leave form: "To" date never before "From" date ----
    const fromInput = doc.getElementById("wb_leave_from");
    const toInput = doc.getElementById("wb_leave_to");
    if (fromInput && toInput) {
        const sync = () => {
            if (fromInput.value && (!toInput.value || toInput.value < fromInput.value)) {
                toInput.value = fromInput.value;
            }
            toInput.min = fromInput.value;
        };
        fromInput.addEventListener("change", sync);
        fromInput.addEventListener("input", sync);
        sync();
    }

    // ---- Document upload: reflect the chosen file ----
    const fileInput = doc.getElementById("wb_file");
    if (fileInput) {
        const labelSpan = doc.getElementById("wb_file_label")?.querySelector("span");
        fileInput.addEventListener("change", () => {
            if (labelSpan) {
                labelSpan.textContent = fileInput.files.length
                    ? fileInput.files[0].name
                    : "Choose a file";
            }
        });
    }
});
