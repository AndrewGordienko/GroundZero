export class GameGallery {
    constructor(elementId, onClickCallback) {
        this.container = document.getElementById(elementId);
        this.onClick = onClickCallback;
        this.renderedIds = new Set();
    }

    render(games) {
        if (!games || games.length === 0) return;

        // Only update if the first game is new to prevent flickering
        const latestId = games[0].id;
        if (this.lastId === latestId) return;
        this.lastId = latestId;

        this.container.innerHTML = '';
        
        games.forEach(game => {
            const card = document.createElement('div');
            card.className = 'game-card';
            
            // Color code the result
            let resultColor = '#666';
            if (game.result === '1-0') resultColor = '#4caf50';
            if (game.result === '0-1') resultColor = '#f44336';

            card.innerHTML = `
                <div class="game-card-header">
                    <span style="color: ${resultColor}">●</span> ${game.result}
                </div>
                <div class="game-card-meta">
                    Moves: ${game.moves}<br>
                    ID: ${game.id.split('_')[1]}
                </div>
            `;

            card.onclick = () => {
                // Highlight selected
                document.querySelectorAll('.game-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                
                // Trigger the history load
                this.onClick(game.history);
            };

            this.container.appendChild(card);
        });
    }
}