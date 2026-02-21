export class SearchHeatmap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    }

    render(heatmapData) {
        if (!this.container) return;
        
        // DEBUG: Check console for this output
        if (heatmapData && Object.keys(heatmapData).length > 0) {
            const sample = heatmapData['e4'] || 0;
            if (Math.random() > 0.95) console.log("Heatmap Sample (e4):", sample);
        } else {
            return; // Don't clear if there's no data
        }

        this.container.innerHTML = "";
        
        // Force the grid layout via JS to ensure it's not collapsed
        this.container.style.display = "grid";
        this.container.style.gridTemplateColumns = "repeat(8, 1fr)";
        this.container.style.gridTemplateRows = "repeat(8, 1fr)";
        
        for (let r = 8; r >= 1; r--) {
            for (let f = 0; f < 8; f++) {
                const sq = this.files[f] + r;
                const cell = document.createElement("div");
                cell.className = "h-cell";
                
                const intensity = heatmapData[sq] || 0;
                
                // DeepMind Aesthetic: Slate background, Cyan heat
                if (intensity > 0) {
                    // Map 0-1 intensity to a lightness range (20% to 80%)
                    const l = 15 + (intensity * 65);
                    cell.style.backgroundColor = `hsl(180, 75%, ${l}%)`;
                    cell.style.border = "0.5px solid rgba(255,255,255,0.1)";
                } else {
                    cell.style.backgroundColor = "transparent";
                    cell.style.border = "0.5px solid rgba(255,255,255,0.02)";
                }
                
                this.container.appendChild(cell);
            }
        }
    }
}