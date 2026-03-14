async function refresh() {
    try {
        const res = await fetch('/api/data');
        const data = await res.json();
        if (data.iterations.length === 0) return;

        // Text Updates
        document.getElementById('buffer-val').innerText = data.buffer_size;
        document.getElementById('lr-val').innerText = data.lr[data.lr.length - 1].toFixed(6);
        document.getElementById('iter-count').innerText = data.iterations.length;
        
        const lastP = data.p_loss[data.p_loss.length - 1];
        const lastV = data.v_loss[data.v_loss.length - 1];
        document.getElementById('total-loss-val').innerText = (lastP + lastV).toFixed(4);

        // Chart Updates
        mainLossChart.data.labels = data.iterations;
        mainLossChart.data.datasets[0].data = data.p_loss.map((v, i) => v + data.v_loss[i]);
        
        pLossChart.data.labels = data.iterations;
        pLossChart.data.datasets[0].data = data.p_loss;

        vLossChart.data.labels = data.iterations;
        vLossChart.data.datasets[0].data = data.v_loss;
        
        lrChart.data.labels = data.iterations;
        lrChart.data.datasets[0].data = data.lr;

        [mainLossChart, pLossChart, vLossChart, lrChart].forEach(c => c.update('none'));
    } catch (e) { console.log("Sync error"); }
}

setInterval(refresh, 2000);