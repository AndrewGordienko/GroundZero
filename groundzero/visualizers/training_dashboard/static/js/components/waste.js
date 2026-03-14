export class WasteChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Unproductive Search (%)',
                    data: [],
                    borderColor: '#ff0000',
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { display: false }, y: { min: 0, max: 100 } },
                plugins: { legend: { display: false } }
            }
        });
    }

    push(sims, uniqueNodes) {
        // High waste = Sims are high but unique nodes are low (re-treading ground)
        const waste = ((sims - uniqueNodes) / sims) * 100;
        this.chart.data.labels.push("");
        this.chart.data.datasets[0].data.push(waste);
        if (this.chart.data.labels.length > 50) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        this.chart.update();
    }
}