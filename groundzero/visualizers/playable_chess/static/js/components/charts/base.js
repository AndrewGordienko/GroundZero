export class BaseChart {
    constructor(canvasId, label, color) {
        this.ctx = document.getElementById(canvasId)?.getContext('2d');
        this.chart = null;
        this.label = label;
        this.color = color;
    }

    update(labels, data) {
        if (!this.ctx) return;
        if (this.chart) {
            this.chart.data.labels = labels;
            this.chart.data.datasets[0].data = data;
            this.chart.update('none');
        } else {
            this.init(labels, data);
        }
    }

    init(labels, data) {
        this.chart = new Chart(this.ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ label: this.label, data: data, borderColor: this.color }]
            },
            options: { /* your shared minimalist options here */ }
        });
    }
}