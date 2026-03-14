export class EntropyChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: '#333',
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { display: false },
                    y: { suggestedMax: 4, grid: { display: false } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    push(val) {
        this.chart.data.labels.push("");
        this.chart.data.datasets[0].data.push(val);
        if (this.chart.data.labels.length > 50) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        this.chart.update();
    }
}