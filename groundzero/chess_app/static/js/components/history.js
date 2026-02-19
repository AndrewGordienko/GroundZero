export class MoveHistory {
    constructor(containerId, onGoto) {
        this.container = document.getElementById(containerId);
        this.onGoto = onGoto;
    }

    render(moves, times, currentView) {
        if (!this.container) return;
        this.container.innerHTML = "";
        const maxT = Math.max(...times, 0.5);

        for (let i = 0; i < moves.length; i += 2) {
            const row = document.createElement("div");
            row.className = "move-row";
            
            const num = document.createElement("div");
            num.className = "m-num";
            num.textContent = `${Math.floor(i / 2) + 1}.`;

            row.append(
                num,
                this.createCell(moves[i], times[i], maxT, i + 1, currentView),
                this.createCell(moves[i + 1], times[i + 1], maxT, i + 2, currentView)
            );
            this.container.appendChild(row);
        }
        this.container.scrollTop = this.container.scrollHeight;
    }

    createCell(san, time, maxT, ply, current) {
        const cell = document.createElement("div");
        cell.className = `m-cell ${current === ply ? 'active' : ''}`;
        if (!san) return cell;

        cell.onclick = () => this.onGoto(ply);
        
        const sanText = document.createElement("span");
        sanText.textContent = san;
        
        const bar = document.createElement("div");
        bar.className = "time-bar-bg";
        const fill = document.createElement("div");
        fill.className = "time-bar-fill";
        fill.style.width = `${Math.min(100, (time / maxT) * 100)}%`;
        
        bar.appendChild(fill);
        cell.append(sanText, bar);
        return cell;
    }
}