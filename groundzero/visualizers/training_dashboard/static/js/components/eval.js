export class EvalChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Win Prob',
                    data: [],
                    borderColor: '#111',
                    borderWidth: 1.5,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.2 // Slight curve for a "medical monitor" feel
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false, // Performance: don't animate every 1s update
                scales: {
                    x: { display: false },
                    y: { 
                        min: 0, 
                        max: 100,
                        grid: { color: '#f5f5f5' },
                        ticks: { font: { size: 9 } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    push(val) {
        this.chart.data.labels.push("");
        this.chart.data.datasets[0].data.push(val);

        // Keep a rolling window of 60 data points (approx 1 minute of history)
        if (this.chart.data.labels.length > 60) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        this.chart.update();
    }

    reset() {
        this.chart.data.labels = [];
        this.chart.data.datasets[0].data = [];
        this.chart.update();
    }
}