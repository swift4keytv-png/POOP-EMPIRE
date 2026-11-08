function csrf() {
    const node = document.querySelector('meta[name="csrf-token"]');
    return node ? node.content : "";
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
        },
        body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data };
}

document.querySelectorAll("[data-close-ad]").forEach((button) => {
    button.addEventListener("click", async () => {
        await postJson("/api/ad/close", {});
        const ad = document.getElementById("tishka-ad");
        if (ad) ad.remove();
    });
});

const secretBox = document.querySelector("[data-secret-box]");
document.querySelectorAll("[data-secret]").forEach((secretButton) => {
    secretButton.addEventListener("click", () => secretBox && secretBox.showModal());
});
if (secretBox) {
    document.querySelector("[data-secret-close]")?.addEventListener("click", () => secretBox.close());
    secretBox.addEventListener("click", (event) => {
        if (event.target === secretBox) secretBox.close();
    });
}

const pandaPanel = document.querySelector("[data-panda-panel]");
const pandaLog = document.querySelector("[data-panda-log]");
const PANDA_HELLO = "Здравствуйте! 🐼 Добро пожаловать в POOP EMPIRE GROUP!\n\nЯ — Панда штаба, ваш виртуальный помощник. Чем могу вам помочь сегодня?\n\nМогу рассказать о наших компаниях, помочь найти товары, подсказать информацию о доставке, заказах и последних новостях империи!";
function bubble(role, text, links) {
    if (!pandaLog) return;
    const node = document.createElement("div");
    node.className = "bubble " + (role === "user" ? "user" : "from-desk");
    node.textContent = text;
    (links || []).forEach((item) => {
        const link = document.createElement("a");
        link.href = item.href;
        link.textContent = " " + item.label;
        node.appendChild(document.createElement("br"));
        node.appendChild(link);
    });
    pandaLog.appendChild(node);
    pandaLog.scrollTop = pandaLog.scrollHeight;
}
function greetPanda() {
    bubble("panda", PANDA_HELLO);
}
async function openPanda() {
    if (!pandaPanel || !pandaPanel.hidden) return;
    pandaPanel.hidden = false;
    if (!pandaLog || pandaLog.childElementCount) return;
    const response = await fetch("/api/panda/history");
    const data = await response.json().catch(() => ({}));
    (data.history || []).forEach((line) => bubble(line.role === "user" ? "user" : "panda", line.text));
    if (!pandaLog.childElementCount) greetPanda();
}
function closePanda() {
    if (pandaPanel) pandaPanel.hidden = true;
}
async function askPanda(text) {
    bubble("user", text);
    const wait = document.createElement("p");
    wait.className = "typing";
    wait.textContent = "Панда думает...";
    pandaLog.appendChild(wait);
    const { data } = await postJson("/api/panda", { message: text });
    wait.remove();
    bubble("panda", data.reply || "Панда молчит.", data.links || []);
}
document.querySelector("[data-panda-open]")?.addEventListener("click", () => { openPanda(); });
document.querySelector("[data-panda-close]")?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    closePanda();
});
document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !pandaPanel || pandaPanel.hidden) return;
    if (document.querySelector("dialog[open]")) return;
    closePanda();
});
document.querySelector("[data-panda-clear]")?.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    await postJson("/api/panda/clear", {});
    if (pandaLog) pandaLog.innerHTML = "";
    greetPanda();
});
document.querySelector("[data-more]")?.addEventListener("click", (event) => {
    event.preventDefault();
    const box = document.querySelector("[data-more-box]");
    if (box) box.hidden = !box.hidden;
});
document.querySelectorAll("[data-chip]").forEach((button) => {
    button.addEventListener("click", () => askPanda(button.textContent));
});
const pandaForm = document.querySelector("[data-panda-form]");
if (pandaForm) {
    pandaForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = pandaForm.querySelector("input");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        await askPanda(text);
    });
}

const search = document.querySelector("[data-suggest]");
if (search) {
    const box = search.parentElement.querySelector(".suggest");
    search.addEventListener("input", async () => {
        if (search.value.trim().length < 2) {
            box.hidden = true;
            return;
        }
        const response = await fetch("/api/suggest?q=" + encodeURIComponent(search.value));
        const data = await response.json();
        box.innerHTML = (data.items || []).map((item) => `<a href="/product/${item.slug}">${item.name}</a>`).join("");
        box.hidden = !data.items.length;
    });
}

document.querySelectorAll("[data-count]").forEach((node) => {
    const target = Number(node.dataset.count || 0);
    const strong = node.querySelector("strong");
    const start = performance.now();
    const tick = (now) => {
        const progress = Math.min(1, (now - start) / 1200);
        const value = Math.round(target * (1 - Math.pow(1 - progress, 3)));
        strong.textContent = value.toLocaleString("ru-RU") + " ₽";
        if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
});
