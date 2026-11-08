function csrf() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(payload || {}),
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data };
}

function soundOn() {
    return localStorage.getItem("poop-sound") !== "off";
}

function beep(freq) {
    if (!soundOn()) return;
    const audio = new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.frequency.value = freq || 520;
    gain.gain.value = 0.05;
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + 0.18);
}

document.querySelectorAll("[data-sound-toggle]").forEach((button) => {
    const paint = () => { button.textContent = soundOn() ? "Звук: вкл" : "Звук: выкл"; };
    paint();
    button.addEventListener("click", () => {
        localStorage.setItem("poop-sound", soundOn() ? "off" : "on");
        paint();
    });
});

const wheelResult = document.querySelector("[data-wheel-result]");
const spinButton = wheelResult ? document.querySelector("[data-spin]") : null;
if (spinButton && wheelResult) {
    spinButton.addEventListener("click", async () => {
        spinButton.disabled = true;
        const { ok, data } = await postJson("/api/wheel/spin", {});
        const wheel = document.querySelector("[data-wheel]");
        const count = Number(wheel && wheel.dataset.count || 10);
        if (ok && wheel) {
            const turn = 360 * 6 + (360 - (data.index + 0.5) * (360 / count));
            wheel.style.transform = `rotate(${turn}deg)`;
            beep(660);
            window.setTimeout(() => {
                wheelResult.hidden = false;
                wheelResult.textContent = data.title + ". " + data.text;
                const left = document.querySelector("[data-spins]");
                if (left) left.textContent = data.left;
                spinButton.disabled = data.left <= 0;
            }, 4200);
        } else {
            wheelResult.hidden = false;
            wheelResult.textContent = data.error || "Колесо не крутится";
            spinButton.disabled = false;
        }
    });
}

document.querySelectorAll(".pin").forEach((pin) => {
    pin.addEventListener("click", () => {
        const card = document.querySelector("[data-plant]");
        if (!card) return;
        const d = pin.dataset;
        card.innerHTML = `<h2>${d.name}</h2><p>${d.kind} · ${d.city}, ${d.region}</p><p>Основан: ${d.year}. Руководитель: ${d.boss}. Сотрудников: ${d.staff}.</p><p>Мощность: ${d.capacity}</p><p>Продукция: ${d.products}</p><p>Инновация: ${d.innovation}</p><p>Демонстрационная выручка: ${d.revenue}</p><p>Статус: ${d.status}</p>`;
    });
});

function showArrive(text, number) {
    const key = "arrived-" + number;
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, "1");
    const box = document.getElementById("arrive");
    if (!box) return;
    box.querySelector("[data-arrive-text]").textContent = text;
    box.hidden = false;
    beep(880);
}

document.querySelector("[data-arrive-close]")?.addEventListener("click", () => {
    document.getElementById("arrive").hidden = true;
});

async function pollDelivery(node) {
    const number = node.dataset.delivery;
    const response = await fetch("/api/delivery/" + encodeURIComponent(number));
    if (!response.ok) return;
    const data = await response.json();
    node.querySelector("[data-delivery-title]").textContent = data.title;
    node.querySelector("[data-delivery-hint]").textContent = [data.hint, data.note, data.courier ? ("Курьер: " + data.courier + " · " + (data.eta || "")) : ""].filter(Boolean).join(" ");
    const who = node.querySelector("[data-delivery-who]");
    if (who && data.mode === "courier" && data.courier) who.textContent = "POOP DELIVERY · " + data.courier;
    if (who && data.mode === "pickup") who.textContent = "Самовывоз · " + (data.hq || "");
    const scooter = node.querySelector("[data-scooter]");
    const steps = (data.steps || []).length || 6;
    if (scooter) scooter.style.left = ((data.stage + 1) / steps * 100) + "%";
    const list = node.querySelector("[data-delivery-log]");
    if (list) list.innerHTML = (data.events || []).map((event) => `<li>${event.at} · ${event.title}</li>`).join("");
    if (data.done) showArrive(data.banner, number);
}

document.querySelectorAll("[data-delivery]").forEach((node) => {
    pollDelivery(node);
    window.setInterval(() => pollDelivery(node), 3000);
});
