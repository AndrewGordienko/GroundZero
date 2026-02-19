export class SearchHeatmap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    }

    render(heatmapData) {
        if (!this.container) return;
        this.container.innerHTML = "";
        
        const data = heatmapData || {};
        
        // Render 8x8 grid from Rank 8 down to 1
        for (let r = 8; r >= 1; r--) {
            for (let f = 0; f < 8; f++) {
                const sq = this.files[f] + r;
                const cell = document.createElement("div");
                cell.className = "h-cell";
                
                // Scale intensity (adjust 1.5 multiplier based on your MCTS visit distribution)
                const intensity = (data[sq] !== undefined) ? data[sq] * 1.5 : 0;
                cell.style.background = `rgba(255, 87, 34, ${Math.min(0.8, intensity)})`; 
                
                this.container.appendChild(cell);
            }
        }
    }
}