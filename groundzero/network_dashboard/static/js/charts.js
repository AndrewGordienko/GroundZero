const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
        x: { display: false },
        y: { 
            grid: { color: '#f5f5f5', drawBorder: false },
            ticks: { color: '#bbb', font: { size: 9 } }
        }
    },
    plugins: { legend: { display: false } }
};

function initChart(id, color, fill = false) {
    const ctx = document.getElementById(id).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: color,
                borderWidth: 1.5,
                fill: fill,
                backgroundColor: color + '11',
                pointRadius: 0,
                tension: 0.2
            }]
        },
        options: baseOptions
    });
}

const mainLossChart = initChart('mainLossChart', '#111', true);
const pLossChart    = initChart('pLossChart', '#111');
const vLossChart    = initChart('vLossChart', '#111');
const lrChart       = initChart('lrChart', '#bbbbbb');