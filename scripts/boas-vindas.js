// Boas-vindas e tutorial do escritório (API de scripts do WorkAdventure).
//
// - Primeira visita: o tutorial abre sozinho, esteja a pessoa onde estiver.
// - Ao entrar na recepção: popup de boas-vindas com o nome da pessoa e o botão "Ver tutorial".
// - No balcão da recepção: "aperte ESPAÇO" para rever o tutorial.
//
// As áreas "recepcao" e "balcao" e o objeto "popupRecepcao" ficam na camada floorLayer do mapa.

const CHAVE_TUTORIAL = "majuTutorialVisto";

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

WA.onInit().then(() => {
    const primeiraVisita = !jaViuTutorial();

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
