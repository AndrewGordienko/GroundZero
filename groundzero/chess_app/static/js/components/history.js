export class MoveHistory {
    constructor(containerId, onGoto) {
        this.container = document.getElementById(containerId);
        this.onGoto = onGoto;
    }

    render(moves = [], times = [], currentView = 0) {
        if (!this.container) return;
        
        // Safety check: ensure moves and times are iterables
        const safeMoves = moves || [];
        const safeTimes = times || [];
        
        this.container.innerHTML = "";
        
        // Fix: Math.max(...[]) results in -Infinity. Fallback to 0.5.
        const maxT = safeTimes.length > 0 ? Math.max(...safeTimes, 0.5) : 0.5;

        for (let i = 0; i < safeMoves.length; i += 2) {
            const row = document.createElement("div");
            row.className = "move-row";
            
            const num = document.createElement("div");
            num.className = "m-num";
            num.textContent = `${Math.floor(i / 2) + 1}.`;

            row.append(
                num,
                this.createCell(safeMoves[i], safeTimes[i], maxT, i + 1, currentView),
                this.createCell(safeMoves[i + 1], safeTimes[i + 1], maxT, i + 2, currentView)
            );
            this.container.appendChild(row);
        }
        this.container.scrollTop = this.container.scrollHeight;
    }

    createCell(san, time, maxT, ply, current) {
        const cell = document.createElement("div");
        cell.className = `m-cell ${current === ply ? 'active' : ''}`;
        
        // If there's no move (e.g., Black hasn't moved yet in the pair), return empty cell
        if (!san) return cell;

        cell.onclick = () => this.onGoto(ply);
        
        const sanText = document.createElement("span");
        sanText.textContent = san;
        
        const bar = document.createElement("div");
        bar.className = "time-bar-bg";
        const fill = document.createElement("div");
        fill.className = "time-bar-fill";
        
        // Ensure time is a number before calculating width
        const safeTime = time || 0;
        fill.style.width = `${Math.min(100, (safeTime / maxT) * 100)}%`;
        
        bar.appendChild(fill);
        cell.append(sanText, bar);
        return cell;
    }
}