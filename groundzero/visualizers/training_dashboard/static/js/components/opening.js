// static/js/components/opening.js
export class OpeningChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: '#4F46E5', // Indigo
                    borderRadius: 4,
                    barThickness: 12
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal bars
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { beginAtZero: true, grid: { display: false }, ticks: { display: false } },
                    y: { grid: { display: false }, ticks: { color: '#475569', font: { family: 'Monaco', size: 10 } } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    update(openingData) {
        if (!openingData) return;
        // Sort and take top 8 moves
        const sorted = Object.entries(openingData)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 8);

        this.chart.data.labels = sorted.map(d => d[0].toUpperCase());
        this.chart.data.datasets[0].data = sorted.map(d => d[1]);
        this.chart.update('none'); // Update without animation for speed
    }
}