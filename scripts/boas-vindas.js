// Boas-vindas e tutorial do escritório (API de scripts do WorkAdventure).
//
// - Primeira visita: o tutorial abre sozinho, esteja a pessoa onde estiver.
// - Ao entrar na recepção: popup de boas-vindas com o nome da pessoa e o botão "Ver tutorial".
// - No balcão da recepção: "aperte ESPAÇO" para rever o tutorial.
//
// - Mesa de cada pessoa: quem tem mesa definida em scripts/mesas.json e nasce na recepção
//   (link sem #) é levado direto para a própria mesa. Convidados continuam na recepção.
//
// As áreas "recepcao" e "balcao" e o objeto "popupRecepcao" ficam na camada floorLayer do mapa.

const CHAVE_TUTORIAL = "majuTutorialVisto";
const T = 32;
const RECEPCAO = { x0: 44 * T, y0: 3 * T, x1: 58 * T, y1: 11 * T };   // mesma área "recepcao" do mapa

// ---- mesa de cada pessoa

// SHA-256 em JS puro, usado só se crypto.subtle não existir no iframe do script.
function sha256Puro(texto) {
    const bytes = new TextEncoder().encode(texto);
    const K = [];
    const H = [];
    const primo = (n) => { for (let d = 2; d * d <= n; d++) if (n % d === 0) return false; return true; };
    const frac = (x) => ((x - Math.floor(x)) * 0x100000000) >>> 0;
    for (let n = 2, i = 0; i < 64; n++) {
        if (!primo(n)) continue;
        if (i < 8) H[i] = frac(Math.pow(n, 1 / 2));
        K[i++] = frac(Math.pow(n, 1 / 3));
    }
    const len = bytes.length;
    const total = ((len + 9 + 63) >> 6) << 6;
    const msg = new Uint8Array(total);
    msg.set(bytes);
    msg[len] = 0x80;
    const bits = len * 8;
    msg[total - 4] = (bits >>> 24) & 0xff; msg[total - 3] = (bits >>> 16) & 0xff;
    msg[total - 2] = (bits >>> 8) & 0xff; msg[total - 1] = bits & 0xff;
    msg[total - 5] = Math.floor(bits / 0x100000000) & 0xff;
    const r = (x, n) => (x >>> n) | (x << (32 - n));
    const w = new Array(64);
    for (let off = 0; off < total; off += 64) {
        for (let i = 0; i < 16; i++) {
            w[i] = (msg[off + i * 4] << 24) | (msg[off + i * 4 + 1] << 16) | (msg[off + i * 4 + 2] << 8) | msg[off + i * 4 + 3];
        }
        for (let i = 16; i < 64; i++) {
            const s0 = r(w[i - 15], 7) ^ r(w[i - 15], 18) ^ (w[i - 15] >>> 3);
            const s1 = r(w[i - 2], 17) ^ r(w[i - 2], 19) ^ (w[i - 2] >>> 10);
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
        }
        let [a, b, c, d, e, f, g, h] = H;
        for (let i = 0; i < 64; i++) {
            const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
            const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
            h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
        }
        [a, b, c, d, e, f, g, h].forEach((v, i) => { H[i] = (H[i] + v) | 0; });
    }
    return H.map((v) => (v >>> 0).toString(16).padStart(8, "0")).join("");
}

async function sha256(texto) {
    if (globalThis.crypto && crypto.subtle) {
        const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
        return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
    }
    return sha256Puro(texto);
}

function naRecepcao(pos) {
    return pos.x >= RECEPCAO.x0 && pos.x < RECEPCAO.x1 && pos.y >= RECEPCAO.y0 && pos.y < RECEPCAO.y1;
}

// Devolve true se levou a pessoa para a mesa dela.
async function irParaMinhaMesa() {
    const ids = [WA.player.id, WA.player.uuid].filter((v) => typeof v === "string" && v.trim() !== "");
    if (ids.length === 0) {
        console.info("[mesas] conta sem identificador (convidado/anônimo): fica na recepção");
        return false;
    }
    const resp = await fetch(new URL("scripts/mesas.json", WA.room.mapURL).toString(), { cache: "no-cache" });
    const tabela = await resp.json();
    let ponto;
    for (const id of ids) {
        ponto = tabela.pessoas[await sha256(tabela.sal + id.trim().toLowerCase())];
        if (ponto) break;
    }
    console.info(`[mesas] identificador desta conta: ${ids.join(" / ")} -> ${ponto || "sem mesa definida"}`);
    if (!ponto || !tabela.pontos[ponto]) return false;

    const pos = await WA.player.getPosition();
    if (!naRecepcao(pos)) return false;   // entrou com #ponto no link ou já está em outro lugar
    const [x, y] = tabela.pontos[ponto];
    await WA.player.teleport(x, y);
    return true;
}

// ---- boas-vindas e tutorial

let popupAberto;
let mensagemBalcao;
let tutorialAbertoEm = 0;   // evita abrir o popup junto com o tutorial da primeira visita

function urlTutorial() {
    return new URL("tutorial/index.html", WA.room.mapURL).toString();
}

function jaViuTutorial() {
    try {
        return WA.player.state[CHAVE_TUTORIAL] === true;
    } catch (e) {
        return false;
    }
}

function marcarTutorialVisto() {
    try {
        WA.player.state.saveVariable(CHAVE_TUTORIAL, true, { public: false, persist: true, scope: "world" });
    } catch (e) {
        try {
            WA.player.state[CHAVE_TUTORIAL] = true;
        } catch (e2) {
            // sem persistência disponível: o tutorial pode reaparecer na próxima visita
        }
    }
}

function fecharPopup() {
    if (popupAberto) {
        popupAberto.close();
        popupAberto = undefined;
    }
}

function abrirTutorial() {
    fecharPopup();
    tutorialAbertoEm = Date.now();
    WA.ui.modal.openModal({
        title: "Como funciona o escritório",
        src: urlTutorial(),
        allow: null,
        allowApi: false,
        position: "center",
    });
    marcarTutorialVisto();
}

WA.onInit().then(async () => {
    const primeiraVisita = !jaViuTutorial();

    // Antes de ligar o popup da recepção, para quem vai para a mesa não ver o popup piscar.
    try {
        await irParaMinhaMesa();
    } catch (e) {
        console.error("[mesas]", e);
    }

    WA.room.area.onEnter("recepcao").subscribe(() => {
        if (popupAberto || Date.now() - tutorialAbertoEm < 5000) return;
        popupAberto = WA.ui.openPopup(
            "popupRecepcao",
            `Olá, ${WA.player.name}! Bem-vindo(a) à MAJU Assessoria & Consultoria Empresarial.`,
            [
                { label: "Ver tutorial", className: "primary", callback: () => abrirTutorial() },
                { label: "Agora não", className: "normal", callback: () => fecharPopup() },
            ],
        );
    });
    WA.room.area.onLeave("recepcao").subscribe(() => fecharPopup());

    WA.room.area.onEnter("balcao").subscribe(() => {
        mensagemBalcao = WA.ui.displayActionMessage({
            message: "Aperte ESPAÇO para ver como funciona o escritório",
            callback: () => abrirTutorial(),
        });
    });
    WA.room.area.onLeave("balcao").subscribe(() => {
        if (mensagemBalcao) {
            mensagemBalcao.remove();
            mensagemBalcao = undefined;
        }
    });

    if (primeiraVisita) {
        abrirTutorial();
    }
}).catch((e) => console.error("[boas-vindas]", e));
