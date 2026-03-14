export class WorkerList {
    constructor(containerId, onSelect) {
        this.container = document.getElementById(containerId);
        this.onSelect = onSelect;
    }

    render(workers, activeId) {
        if (!this.container) return;

        Object.entries(workers).forEach(([id, stats]) => {
            let card = document.getElementById(`worker-card-${id}`);
            
            if (!card) {
                card = document.createElement('div');
                card.id = `worker-card-${id}`;
                card.className = 'worker-card';
                card.onclick = () => this.onSelect(id);
                this.container.appendChild(card);
            }

            const isActive = id === activeId;
            card.classList.toggle('active', isActive);
            
            // Log-style row content
            card.innerHTML = `
                <div class="worker-row-header">
                    <span class="id">ACTOR_0${id}</span>
                    <span class="status-tag">${stats.status}</span>
                </div>
                <div class="meta">${stats.fen ? stats.fen.substring(0, 35) : 'Initializing...'}</div>
            `;
        });
    }
}