export class LatencyChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Inference (ms)',
                    data: [],
                    borderColor: '#ff4600',
                    backgroundColor: 'rgba(255, 70, 0, 0.1)',
                    fill: true,
                    borderWidth: 1,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { display: false },
                    y: { beginAtZero: true, grid: { color: '#f9f9f9' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    push(ms) {
        this.chart.data.labels.push("");
        this.chart.data.datasets[0].data.push(ms);
        if (this.chart.data.labels.length > 50) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        this.chart.update();
    }
}