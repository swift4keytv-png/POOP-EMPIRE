const canvas = document.getElementById("market");
const chart = new Chart(canvas, {
    type: "line",
    data: {
        labels: (window.PEG_HISTORY || []).map((_, index) => index + 1),
        datasets: [{ label: "PEG", data: window.PEG_HISTORY || [], borderColor: "#e0b44a", tension: 0.25, pointRadius: 0 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { display: false } } },
});

function csrf() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
}

function money(kop) {
    const rub = Math.floor(Math.abs(kop) / 100);
    return rub.toLocaleString("ru-RU") + " ₽";
}

async function deal(ticker, side) {
    const response = await fetch("/api/exchange/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ ticker, side, qty: 1 }),
    });
    const data = await response.json();
    const balance = document.querySelector("[data-balance]");
    if (balance && data.balance !== undefined) balance.textContent = money(data.balance);
    if (!data.ok) window.alert(data.error || "Сделка не прошла");
    else {
        const list = document.querySelector("[data-portfolio]");
        if (list) {
            const item = document.createElement("li");
            item.textContent = `${data.side} ${data.ticker} · теперь ${data.shares} шт.`;
            list.prepend(item);
        }
    }
}

document.querySelectorAll("[data-buy]").forEach((button) => button.addEventListener("click", () => deal(button.dataset.buy, "buy")));
document.querySelectorAll("[data-sell]").forEach((button) => button.addEventListener("click", () => deal(button.dataset.sell, "sell")));

document.querySelector("[data-find]")?.addEventListener("input", (event) => {
    const query = event.target.value.toLowerCase();
    document.querySelectorAll("[data-row]").forEach((row) => {
        row.hidden = query && !row.textContent.toLowerCase().includes(query);
    });
});

let filter = "all";
document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
        filter = button.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("on"));
        button.classList.add("on");
        document.querySelectorAll("[data-row]").forEach((row) => {
            const change = Number(row.dataset.change);
            row.hidden = (filter === "up" && change < 0) || (filter === "down" && change >= 0);
        });
    });
});

setInterval(async () => {
    const response = await fetch("/api/exchange/quotes?ticker=PEG");
    const data = await response.json();
    if (!data.ok) return;
    chart.data.datasets[0].data = data.history;
    chart.data.labels = data.history.map((_, index) => index + 1);
    chart.update();
    data.quotes.forEach((quote) => {
        const row = document.querySelector(`[data-ticker="${quote.ticker}"]`);
        if (!row) return;
        row.dataset.change = quote.change;
        const price = row.querySelector("[data-price]");
        if (price) price.textContent = money(quote.price);
    });
}, 20000);
