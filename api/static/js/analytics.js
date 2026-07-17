document.addEventListener("DOMContentLoaded", () => {
    const charts = window.analyticsCharts || {};
    Object.entries(charts).forEach(([id, rows]) => {
        const canvas = document.getElementById(id);
        if (!canvas || !rows.length || typeof Chart === "undefined") return;
        const growth = id === "growth-chart";
        new Chart(canvas, {
            type: growth ? "line" : (rows.length <= 6 ? "doughnut" : "bar"),
            data: {labels: rows.map(row => row.label), datasets: [{label: "Cards / copies", data: rows.map(row => row.estimated_value ?? row.quantity ?? row.cards ?? 0), backgroundColor: ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#0dcaf0", "#fd7e14", "#20c997"]}]},
            options: {responsive: true, plugins: {legend: {display: !growth}}, onClick: (_, elements) => { if (elements.length && rows[elements[0].index].link) location.href = rows[elements[0].index].link; }},
        });
    });
});
