export class EngineStats {
    constructor() {
        this.nodes = {
            winRate: document.getElementById("win-rate"),
            sims: document.getElementById("sim-count"),
            depth: document.getElementById("depth-val"),
            pvTable: document.getElementById("pv-table")
        };
    }

    update(stats) {
        if (!stats) return;
        if (this.nodes.winRate) this.nodes.winRate.textContent = stats.win_prob + "%";
        if (this.nodes.sims) this.nodes.sims.textContent = stats.simulations;
        if (this.nodes.depth) this.nodes.depth.textContent = stats.depth;

        if (this.nodes.pvTable && stats.top_lines) {
            this.nodes.pvTable.innerHTML = stats.top_lines.map(l => `
                <div class="pv-row" style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #f9f9f9; font-size:11px;">
                    <span style="font-family:monospace; font-weight:700;">${l.line}</span>
                    <span style="color:#999; font-size:10px;">Q: ${l.q.toFixed(2)} | ${l.visits}s</span>
                </div>
            `).join('');
        }
    }
}