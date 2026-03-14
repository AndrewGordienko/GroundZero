export class DepthChart {
    constructor(id) {
        const ctx = document.getElementById(id).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line', // Line is better for history than Bar
            data: {
                labels: Array(60).fill(""),
                datasets: [{
                    label: 'Depth',
                    data: Array(60).fill(0),
                    borderColor: '#10B981', // Emerald
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 }, // Critical for performance
                scales: {
                    x: { display: false },
                    y: { 
                        beginAtZero: true, 
                        max: 20, 
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { font: { size: 9 } }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    push(val) {
        this.chart.data.datasets[0].data.push(val);
        this.chart.data.datasets[0].data.shift();
        this.chart.update('none');
    }
}