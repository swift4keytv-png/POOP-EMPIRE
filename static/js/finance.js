const data = JSON.parse(document.getElementById("fin-data").textContent);
const gold = "#e0b44a";
const ink = "#f6f1e6";
const grid = "rgba(224,180,74,0.15)";
Chart.defaults.color = ink;
Chart.defaults.borderColor = grid;
Chart.defaults.font.family = "Manrope, Segoe UI, sans-serif";

function line(id, labels, values, label) {
    const node = document.getElementById(id);
    if (!node) return;
    new Chart(node, {
        type: "line",
        data: { labels, datasets: [{ label, data: values, borderColor: gold, backgroundColor: "rgba(224,180,74,0.15)", fill: true, tension: 0.25 }] },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
}

line("chartRevenue", data.labels, data.revenue, "Выручка");
line("chartProfit", data.months, data.profit, "Прибыль");
line("chartOrders", data.labels, data.orders, "Заказы");

const cats = document.getElementById("chartCats");
if (cats) {
    new Chart(cats, {
        type: "bar",
        data: { labels: data.cats, datasets: [{ data: data.catValues, backgroundColor: gold }] },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
}
const exp = document.getElementById("chartExpense");
if (exp) {
    new Chart(exp, {
        type: "doughnut",
        data: { labels: data.expenses, datasets: [{ data: data.expenseValues, backgroundColor: ["#e0b44a", "#8fd0a8", "#c47b5a", "#f6f1e6"] }] },
    });
}
