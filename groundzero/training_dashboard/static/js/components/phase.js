export class PhaseChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Opening', 'Midgame', 'Endgame'],
                datasets: [
                    {
                        // OUTER RING: Global Accumulation
                        label: 'Global',
                        data: [1, 1, 1],
                        backgroundColor: ['#1e293b', '#334155', '#0f172a'], // Muted Slate/Navy
                        borderWidth: 1,
                        borderColor: '#000',
                        weight: 1
                    },
                    {
                        // INNER RING: Recent Trend
                        label: 'Recent',
                        data: [1, 1, 1],
                        backgroundColor: ['#2dd4bf', '#22d3ee', '#38bdf8'], // "DeepMind" Teal/Cyan
                        borderWidth: 1,
                        borderColor: '#000',
                        weight: 0.7
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%', 
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleFont: { family: 'Monaco, monospace' },
                        bodyFont: { family: 'Monaco, monospace' },
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label} ${ctx.label}: ${ctx.parsed.toFixed(1)}s`
                        }
                    }
                },
                animation: { duration: 400 }
            }
        });
    }

    update(phaseData) {
        if (!phaseData || !phaseData.global || !phaseData.recent) return;
        
        this.chart.data.datasets[0].data = [
            phaseData.global.opening, 
            phaseData.global.midgame, 
            phaseData.global.endgame
        ];

        this.chart.data.datasets[1].data = [
            phaseData.recent.opening, 
            phaseData.recent.midgame, 
            phaseData.recent.endgame
        ];

        this.chart.update('none'); 
    }

    reset() {
        this.chart.data.datasets[0].data = [1, 1, 1];
        this.chart.data.datasets[1].data = [1, 1, 1];
        this.chart.update();
    }
}