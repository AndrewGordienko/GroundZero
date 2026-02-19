/**
 * API Service for GroundZero
 * Handles all network communication with the Flask backend.
 */
export const API = {
    async getState() {
        const r = await fetch("/state");
        return r.json();
    },
    async move(uci) {
        const r = await fetch("/move", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ uci })
        });
        if (!r.ok) {
            console.error("Move failed", await r.text());
            return { ok: false };
        }
        return r.json();
    },
    async engineMove() {
        const r = await fetch("/engine_move", { method: "POST" });
        return r.json();
    },
    async goto(view) {
        const r = await fetch("/goto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ view })
        });
        return r.json();
    }
};