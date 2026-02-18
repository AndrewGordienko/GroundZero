const API = {
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