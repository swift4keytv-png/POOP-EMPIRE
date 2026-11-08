const GLYPH = { POOP: "💩", CROWN: "👑", COIN: "🪙", GEM: "💎", PANDA: "🐼", BOLT: "⚡", CUP: "🏆" };
const FACES = ["POOP", "CROWN", "COIN", "GEM", "PANDA", "BOLT", "CUP"];
const REDS = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
const DIE = {
    1: "rotateX(0deg) rotateY(0deg)",
    2: "rotateY(90deg)",
    3: "rotateX(-90deg)",
    4: "rotateX(90deg)",
    5: "rotateY(-90deg)",
    6: "rotateY(180deg)",
};

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

function quiet() {
    return localStorage.getItem("poop-sound") === "off";
}

function tone(freq, dur) {
    if (quiet()) return;
    const audio = new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = "triangle";
    osc.frequency.value = freq;
    gain.gain.value = 0.045;
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + dur);
    osc.stop(audio.currentTime + dur);
}

function paintHud(data) {
    const coins = document.querySelector("[data-coins]");
    if (coins && data.coins !== undefined) {
        const from = Number(coins.dataset.value || 0);
        const to = Number(data.coins);
        const start = performance.now();
        const step = (now) => {
            const t = Math.min(1, (now - start) / 700);
            coins.textContent = String(Math.round(from + (to - from) * t));
            if (t < 1) requestAnimationFrame(step);
            else coins.dataset.value = String(to);
        };
        requestAnimationFrame(step);
    }
    const map = { level: "[data-level]", tier: "[data-tier]", games: "[data-games]", total_win: "[data-total]", best: "[data-best]", badges: "[data-badges]", xp: "[data-xp-num]" };
    Object.entries(map).forEach(([key, sel]) => {
        if (data[key] === undefined) return;
        document.querySelectorAll(sel).forEach((node) => { node.textContent = data[key]; });
    });
    if (data.xp_bar !== undefined) {
        const bar = document.querySelector("[data-xp]");
        if (bar) bar.style.width = data.xp_bar + "%";
    }
    if (data.pool !== undefined) {
        const pool = document.querySelector("[data-pool]");
        if (pool) pool.textContent = data.pool;
    }
    if (data.participants !== undefined) {
        const people = document.querySelector("[data-people]");
        if (people) people.textContent = data.participants;
    }
}

function remember(data) {
    const list = document.querySelector("[data-mine]");
    if (!list || !data.detail) return;
    const item = document.createElement("li");
    item.textContent = `${data.detail} · выплата ${data.payout}`;
    const placeholder = list.querySelector("li");
    if (placeholder && placeholder.textContent.includes("ещё нет")) placeholder.remove();
    list.prepend(item);
}

function celebrate(data) {
    (data.new_achievements || []).forEach((title, index) => {
        const pop = document.createElement("div");
        pop.className = "ach-pop";
        pop.style.bottom = 24 + index * 64 + "px";
        pop.textContent = "Достижение: " + title;
        document.body.appendChild(pop);
        setTimeout(() => pop.remove(), 3400);
    });
    if (!data.payout) return;
    for (let i = 0; i < 16; i += 1) {
        const coin = document.createElement("span");
        coin.className = "coin-burst";
        coin.textContent = i % 4 === 0 ? "💩" : "🪙";
        coin.style.left = 20 + Math.random() * 70 + "vw";
        coin.style.top = "-10px";
        document.body.appendChild(coin);
        setTimeout(() => coin.remove(), 1200);
    }
    if (data.big) {
        const layer = document.querySelector("[data-big]");
        layer.hidden = false;
        layer.querySelector("[data-big-title]").textContent = data.won ? "JACKPOT" : "BIG WIN";
        const sum = layer.querySelector("[data-big-sum]");
        let value = 0;
        const timer = setInterval(() => {
            value = Math.min(data.payout, value + Math.ceil(data.payout / 18));
            sum.textContent = String(value);
            if (value >= data.payout) clearInterval(timer);
        }, 40);
        tone(880, 0.4);
    }
}

function say(stage, data, ok) {
    const msg = stage.querySelector("[data-msg]");
    if (!msg) return;
    msg.textContent = ok ? `${data.detail}. Выплата ${data.payout}.` : (data.error || "Ставка не принята");
}

function spinReels(stage, reels, hit) {
    const boxes = stage.querySelectorAll("[data-reel]");
    boxes.forEach((box, index) => {
        const strip = box.querySelector(".strip");
        const faces = Array.from({ length: 14 }, () => GLYPH[FACES[Math.floor(Math.random() * FACES.length)]]);
        faces.push(GLYPH[reels[index]] || "💩");
        strip.innerHTML = faces.map((glyph) => `<span>${glyph}</span>`).join("");
        strip.style.transition = "none";
        strip.style.transform = "translateY(0)";
        box.classList.remove("hit");
        requestAnimationFrame(() => {
            strip.style.transition = `transform ${0.85 + index * 0.28}s cubic-bezier(.15,.8,.2,1)`;
            strip.style.transform = `translateY(-${(faces.length - 1) * 96}px)`;
        });
        setTimeout(() => tone(180 + index * 40, 0.08), 850 + index * 280);
        if (hit && reels[index] === hit) setTimeout(() => box.classList.add("hit"), 900 + index * 280);
    });
    tone(240, 0.2);
    return 850 + 4 * 280;
}

let auto = false;
let busy = false;
let wheelAngle = 0;
let choice = "red";

function currentStage() {
    return document.querySelector(".stage:not([hidden])");
}

async function play(game) {
    const stage = document.querySelector(`[data-stage="${game === "vip" ? "vip" : game}"]`);
    if (!stage || busy) return;
    busy = true;
    if (document.querySelector(".casino-app").dataset.auth !== "1") {
        window.location.href = "/login?next=/casino";
        return;
    }
    const bet = stage.querySelector("[data-bet]")?.value || 10;
    const payload = { game, bet, token: crypto.randomUUID() };
    if (game === "roulette") payload.choice = choice;
    if (game === "dice") payload.guess = stage.querySelector("[data-guess]").value;
    let ok = false;
    let data = {};
    try {
        const response = await postJson(game === "roulette" ? "/api/casino/roulette" : game === "dice" ? "/api/casino/dice" : game === "panda" ? "/api/casino/panda" : "/api/casino/slots", payload);
        ok = response.ok;
        data = response.data;
    } catch (error) {
        say(stage, { error: "Сервер не ответил. Ставка не повторялась." }, false);
        busy = false;
        auto = false;
        return;
    }
    if (!ok) {
        say(stage, data, false);
        busy = false;
        auto = false;
        return;
    }
    let wait = 400;
    if (game === "slots" || game === "vip") wait = spinReels(stage, data.reels || [], data.hit);
    if (game === "golden") {
        const orb = stage.querySelector("[data-orb]");
        orb.classList.add("rush");
        wait = 1600;
        setTimeout(() => orb.classList.remove("rush"), wait);
        tone(520, 0.3);
    }
    if (game === "jackpot") {
        stage.querySelector("[data-vault]").classList.toggle("open", !!data.won);
        tone(data.won ? 760 : 160, 0.35);
        if (data.won) {
            const last = document.querySelector("[data-last]");
            if (last) last.textContent = `вы · ${data.payout}`;
        }
    }
    if (game === "roulette") {
        const step = 360 / 37;
        const mid = data.number * step + step / 2;
        const target = (360 - mid + 360) % 360;
        let delta = target - (wheelAngle % 360);
        if (delta <= 0) delta += 360;
        wheelAngle += delta + 360 * 5;
        const wheel = stage.querySelector("[data-wheel]");
        wheel.style.transition = "transform 4.4s cubic-bezier(.12,.7,.08,1)";
        wheel.style.transform = `rotate(${wheelAngle}deg)`;
        tone(300, 0.5);
        wait = 4500;
        setTimeout(() => {
            tone(640, 0.15);
            const pocket = stage.querySelector("[data-pocket]");
            if (pocket) pocket.textContent = `${data.number} · ${data.color}`;
        }, wait);
    }
    if (game === "dice") {
        stage.querySelectorAll("[data-die]").forEach((cube, index) => {
            const hops = [DIE[1 + (index % 6)], DIE[6 - index], DIE[data.dice[index]]];
            hops.forEach((face, hop) => {
                setTimeout(() => {
                    cube.style.transform = face + (hop < 2 ? " translateY(-70px)" : " translateY(0)");
                    tone(200 + hop * 80, 0.08);
                }, hop * 420);
            });
        });
        wait = 2100;
    }
    setTimeout(() => {
        say(stage, data, true);
        paintHud(data);
        remember(data);
        celebrate(data);
        if (data.payout) tone(720, 0.25);
        busy = false;
        if (auto && (game === "slots") && !data.big) play("slots");
    }, wait);
}

function buildWheel() {
    const wheel = document.querySelector("[data-stage='roulette'] [data-wheel]");
    if (!wheel) return;
    const stops = [];
    for (let number = 0; number < 37; number += 1) {
        const color = number === 0 ? "#e6c36a" : REDS.has(number) ? "#9b1c2e" : "#161616";
        stops.push(`${color} ${(number / 37) * 360}deg ${((number + 1) / 37) * 360}deg`);
    }
    wheel.style.background = `conic-gradient(${stops.join(",")})`;
}

function sky() {
    const canvas = document.querySelector("[data-sky]");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const bits = Array.from({ length: 26 }, () => ({
        x: Math.random(),
        y: Math.random(),
        v: 0.0015 + Math.random() * 0.003,
        s: 14 + Math.random() * 12,
        mark: Math.random() > 0.72 ? "💩" : "🪙",
    }));
    const draw = () => {
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        if (canvas.width !== width) canvas.width = width;
        if (canvas.height !== height) canvas.height = height;
        ctx.clearRect(0, 0, width, height);
        if (!document.hidden) {
            bits.forEach((bit) => {
                bit.y += bit.v;
                if (bit.y > 1.05) bit.y = -0.05;
                ctx.font = `${bit.s}px serif`;
                ctx.globalAlpha = 0.45;
                ctx.fillText(bit.mark, bit.x * width, bit.y * height);
            });
        }
        requestAnimationFrame(draw);
    };
    draw();
}

document.querySelectorAll("[data-open]").forEach((button) => {
    button.addEventListener("click", () => {
        document.querySelector("[data-hall]").hidden = true;
        document.querySelectorAll("[data-stage]").forEach((stage) => { stage.hidden = true; });
        document.querySelector(`[data-stage="${button.dataset.open}"]`).hidden = false;
    });
});

document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => {
        auto = false;
        button.closest("[data-stage]").hidden = true;
        document.querySelector("[data-hall]").hidden = false;
    });
});

document.querySelector("[data-big-close]")?.addEventListener("click", () => {
    document.querySelector("[data-big]").hidden = true;
    document.querySelectorAll("[data-stage]").forEach((stage) => { stage.hidden = true; });
    document.querySelector("[data-hall]").hidden = false;
    auto = false;
});

document.querySelectorAll("[data-spin]").forEach((button) => {
    button.addEventListener("click", () => play(button.dataset.spin));
});

document.querySelector("[data-autospin]")?.addEventListener("click", (event) => {
    auto = !auto;
    event.currentTarget.textContent = auto ? "Стоп" : "Авто";
    if (auto) play("slots");
});

document.querySelectorAll("[data-choice]").forEach((button) => {
    button.addEventListener("click", () => {
        choice = button.dataset.choice;
        document.querySelectorAll("[data-choice]").forEach((item) => item.classList.remove("on"));
        button.classList.add("on");
    });
});

document.querySelectorAll("[data-door]").forEach((button) => {
    button.addEventListener("click", async () => {
        const stage = button.closest("[data-stage]");
        if (busy) return;
        busy = true;
        let ok = false;
        let data = {};
        try {
            const response = await postJson("/api/casino/panda", {
            door: button.dataset.door,
            bet: stage.querySelector("[data-bet]").value,
            token: crypto.randomUUID(),
            });
            ok = response.ok;
            data = response.data;
        } catch (error) {
            say(stage, { error: "Сервер не ответил. Ставка не повторялась." }, false);
            busy = false;
            return;
        }
        if (!ok) {
            say(stage, data, false);
            busy = false;
            return;
        }
        const doors = stage.querySelectorAll("[data-door]");
        doors.forEach((door) => {
            door.classList.remove("open");
            door.querySelector("b").textContent = "";
        });
        doors.forEach((door, index) => {
            const prize = data.doors[index];
            door.classList.add("open");
            door.querySelector("b").textContent = `${prize.title} ×${prize.multiplier}`;
        });
        const panda = stage.querySelector("[data-panda]");
        panda.className = "panda-mascot " + (data.mood || "");
        say(stage, data, true);
        paintHud(data);
        remember(data);
        celebrate(data);
        tone(data.mood === "sad" ? 180 : 700, 0.25);
        busy = false;
    });
});

document.querySelector("[data-daily]")?.addEventListener("click", async () => {
    const { ok, data } = await postJson("/api/casino/daily", { token: crypto.randomUUID() });
    paintHud(data);
    const stage = currentStage();
    if (stage) say(stage, ok ? { detail: `Начислено ${data.amount}`, payout: data.amount } : data, ok);
    else if (!ok) window.alert(data.error || "Бонус уже получен");
    if (ok) tone(660, 0.2);
});

const coinBox = document.querySelector("[data-coin-box]");
document.querySelector("[data-coin-open]")?.addEventListener("click", () => coinBox?.showModal());
document.querySelector("[data-coin-close]")?.addEventListener("click", () => coinBox?.close());
document.querySelectorAll("[data-pack]").forEach((button) => {
    button.addEventListener("click", async () => {
        const note = document.querySelector("[data-coin-note]");
        const { ok, data } = await postJson("/api/casino/topup", { pack: button.dataset.pack, token: crypto.randomUUID() });
        if (note) note.textContent = ok ? `Начислено ${data.amount} POOP COINS. Баланс ${data.coins}. Это DEMO.` : (data.error || "Не вышло");
        if (ok) {
            const log = document.querySelector("[data-coin-log]");
            if (log) {
                const item = document.createElement("li");
                item.textContent = `сейчас · topup · ${data.amount} · DEMO-пополнение, без оплаты`;
                log.prepend(item);
            }
        }
        if (ok) {
            paintHud(data);
            tone(720, 0.2);
        }
    });
});

buildWheel();
sky();
