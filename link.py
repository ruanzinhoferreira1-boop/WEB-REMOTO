
import asyncio
import math
import socket

import pyautogui
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="LINK v0.3")
controle_em_uso = asyncio.Lock()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

PAGINA = r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1, maximum-scale=1">
    <title>LINK v0.3</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: #0e1626;
            color: #f5f8fc;
            font-family: system-ui, Arial, sans-serif;
        }

        main {
            max-width: 500px;
            padding: 24px 16px 42px;
            margin: auto;
        }

        h1 {
            margin: 0;
            color: #86e1ce;
            font-size: 38px;
            letter-spacing: 3px;
        }

        .sub {
            margin: 4px 0 18px;
            color: #acbcd1;
            font-size: 14px;
        }

        #status {
            background: #1b2a3e;
            color: #86e1ce;
            padding: 13px;
            border-radius: 12px;
            margin-bottom: 16px;
        }

        #touchpad {
            height: 50vh;
            min-height: 270px;
            max-height: 420px;
            border: 1px solid #4c7186;
            background: linear-gradient(
                140deg, #2b415a, #1b2a40
            );
            border-radius: 18px;
            display: grid;
            place-items: center;
            text-align: center;
            padding: 18px;
            color: #b7d1e0;
            user-select: none;
            touch-action: none;
        }

        .buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 14px;
        }

        button {
            min-height: 54px;
            padding: 12px 8px;
            border: 0;
            border-radius: 12px;
            background: #30465f;
            color: white;
            font-size: 15px;
            font-weight: 600;
            touch-action: manipulation;
        }

        button:active {
            background: #42627a;
        }

        .wide {
            grid-column: 1 / -1;
        }

        #hold.active {
            background: #82e0cb;
            color: #112030;
        }

        .hint {
            color: #a7b9cb;
            font-size: 13px;
            line-height: 1.55;
        }
    </style>
</head>

<body>
<main>
    <h1>WEB REMOTO</h1>

    <p class="sub">
        Controle remoto do computador - v0.3
    </p>

    <div id="status">Conectando...</div>

    <div id="touchpad">
        1 dedo: mover ou tocar para clicar<br>
        2 dedos: rolar a página<br>
        Toque longo: segurar e arrastar
    </div>

    <div class="buttons">
        <button id="left">Clique esquerdo</button>
        <button id="right">Clique direito</button>

        <button id="double" class="wide">
            Clique duplo
        </button>

        <button id="hold" class="wide"
                aria-pressed="false">
            Travar clique para arrastar
        </button>

        <button id="up">Rolar para cima</button>
        <button id="down">Rolar para baixo</button>
    </div>

    <p class="hint">
        Segure o dedo no touchpad por meio segundo
        e mova para arrastar. Solte o dedo para
        liberar o clique.
    </p>
</main>

<script>
    const pad = document.getElementById("touchpad");
    const status = document.getElementById("status");
    const holdButton = document.getElementById("hold");

    const dedos = new Map();

    let ws = null;
    let pronto = false;
    let segurando = false;
    let travado = false;
    let multiplosDedos = false;
    let temporizador = null;

    let inicioX = 0;
    let inicioY = 0;
    let inicioTempo = 0;
    let somaRolagem = 0;

    function enviar(mensagem) {
        if (
            !pronto ||
            !ws ||
            ws.readyState !== WebSocket.OPEN
        ) {
            return false;
        }

        ws.send(JSON.stringify(mensagem));
        return true;
    }

    function cancelarTempo() {
        if (temporizador !== null) {
            clearTimeout(temporizador);
        }

        temporizador = null;
    }

    function atualizarTrava() {
        holdButton.classList.toggle("active", travado);

        holdButton.setAttribute(
            "aria-pressed",
            String(travado)
        );

        holdButton.textContent = travado
            ? "Soltar clique"
            : "Travar clique para arrastar";
    }

    function soltarSeNecessario() {
        if (segurando && !travado) {
            enviar({type: "mouse_up"});

            segurando = false;
            status.textContent = "Conectado ao PC";
        }
    }

    function conectar() {
        ws = new WebSocket(
            "ws://" + location.host + "/ws"
        );

        ws.onmessage = (evento) => {
            const mensagem = JSON.parse(evento.data);

            if (mensagem.type === "ready") {
                pronto = true;
                status.textContent = "Conectado ao PC";
            }

            else if (mensagem.type === "error") {
                status.textContent = mensagem.message;
            }
        };

        ws.onerror = () => {
            status.textContent = "Erro na conexão";
        };

        ws.onclose = () => {
            cancelarTempo();

            pronto = false;
            segurando = false;
            travado = false;

            dedos.clear();
            atualizarTrava();

            status.textContent =
                "Desconectado. Atualize a página.";
        };
    }

    function ativarToqueLongo() {
        cancelarTempo();

        temporizador = setTimeout(() => {
            temporizador = null;

            if (
                dedos.size === 1 &&
                !multiplosDedos &&
                !segurando &&
                !travado
            ) {
                if (enviar({type: "mouse_down"})) {
                    segurando = true;

                    status.textContent =
                        "Clique segurado: arraste o dedo";
                }
            }
        }, 500);
    }

    pad.addEventListener("pointerdown", (e) => {
        if (
            e.pointerType === "mouse" &&
            e.button !== 0
        ) {
            return;
        }

        dedos.set(e.pointerId, {
            x: e.clientX,
            y: e.clientY
        });

        pad.setPointerCapture(e.pointerId);

        if (dedos.size === 1) {
            multiplosDedos = false;

            inicioX = e.clientX;
            inicioY = e.clientY;
            inicioTempo = Date.now();

            if (!travado) {
                ativarToqueLongo();
            }
        }

        else {
            multiplosDedos = true;
            cancelarTempo();
            soltarSeNecessario();

            somaRolagem = 0;
        }
    });

    pad.addEventListener("pointermove", (e) => {
        const anterior = dedos.get(e.pointerId);

        if (!anterior) {
            return;
        }

        const dx = e.clientX - anterior.x;
        const dy = e.clientY - anterior.y;

        dedos.set(e.pointerId, {
            x: e.clientX,
            y: e.clientY
        });

        if (dedos.size >= 2) {
            somaRolagem += dy / dedos.size;

            const passos = Math.trunc(
                somaRolagem / 1.0
            );

            if (passos !== 0) {
                enviar({
                    type: "wheel",
                    steps: Math.max(
                        -100,
                        Math.min(100, passos)
                    )
                });

                somaRolagem -= passos * 1.0;
            }

            return;
        }

        const distancia = Math.hypot(
            e.clientX - inicioX,
            e.clientY - inicioY
        );

        if (distancia > 10) {
            cancelarTempo();
        }

        if (
            !multiplosDedos &&
            (dx !== 0 || dy !== 0)
        ) {
            enviar({
                type: "move",
                dx: dx,
                dy: dy
            });
        }
    });

    function encerrarDedo(e) {
        if (!dedos.has(e.pointerId)) {
            return;
        }

        const eraUnico = dedos.size === 1;

        const distancia = Math.hypot(
            e.clientX - inicioX,
            e.clientY - inicioY
        );

        cancelarTempo();

        if (
            eraUnico &&
            !multiplosDedos &&
            !segurando &&
            !travado &&
            distancia < 10 &&
            Date.now() - inicioTempo < 350 &&
            e.type === "pointerup"
        ) {
            enviar({
                type: "click",
                button: "left"
            });
        }

        dedos.delete(e.pointerId);

        if (dedos.size === 0) {
            soltarSeNecessario();

            multiplosDedos = false;
            somaRolagem = 0;
        }
    }

    pad.addEventListener(
        "pointerup",
        encerrarDedo
    );

    pad.addEventListener(
        "pointercancel",
        encerrarDedo
    );

    document.getElementById("left").onclick = () => {
        enviar({
            type: "click",
            button: "left"
        });
    };

    document.getElementById("right").onclick = () => {
        enviar({
            type: "click",
            button: "right"
        });
    };

    document.getElementById("double").onclick = () => {
        enviar({
            type: "click",
            button: "double"
        });
    };

    document.getElementById("up").onclick = () => {
        enviar({
            type: "wheel",
            steps: 100
        });
    };

    document.getElementById("down").onclick = () => {
        enviar({
            type: "wheel",
            steps: -100
        });
    };

    holdButton.onclick = () => {
        if (!pronto) {
            return;
        }

        if (segurando) {
            enviar({type: "mouse_up"});

            segurando = false;
            travado = false;
        }

        else if (enviar({type: "mouse_down"})) {
            segurando = true;
            travado = true;
        }

        atualizarTrava();
    };

    function liberarAoSair() {
        cancelarTempo();

        if (segurando) {
            enviar({type: "mouse_up"});
        }

        segurando = false;
        travado = false;

        atualizarTrava();
    }

    window.addEventListener(
        "blur",
        liberarAoSair
    );

    document.addEventListener(
        "visibilitychange",
        () => {
            if (document.hidden) {
                liberarAoSair();
            }
        }
    );

    conectar();
</script>
</body>
</html>
"""


@app.get("/")
async def inicio():
    return HTMLResponse(PAGINA)


def executar_comando(dados, pressionado):
    tipo = dados.get("type")

    if tipo == "move":
        dx = dados.get("dx")
        dy = dados.get("dy")

        if not all(
            isinstance(n, (int, float))
            and not isinstance(n, bool)
            and math.isfinite(n)
            for n in (dx, dy)
        ):
            return pressionado

        dx = round(
            max(-100, min(100, dx * 1.5))
        )

        dy = round(
            max(-100, min(100, dy * 1.5))
        )

        if dx or dy:
            pyautogui.moveRel(
                dx,
                dy,
                duration=0
            )

    elif tipo == "click" and not pressionado:
        botao = dados.get("button")

        if botao in ("left", "right"):
            pyautogui.click(button=botao)

        elif botao == "double":
            pyautogui.doubleClick(
                interval=0.12
            )

    elif tipo == "wheel":
        passos = dados.get("steps")

        if (
            isinstance(passos, int)
            and not isinstance(passos, bool)
        ):
            pyautogui.scroll(
                max(-600, min(600, passos))
            )

    elif tipo == "mouse_down" and not pressionado:
        pyautogui.mouseDown(button="left")
        pressionado = True

    elif tipo == "mouse_up" and pressionado:
        pyautogui.mouseUp(button="left")
        pressionado = False

    return pressionado


def liberar_botao():
    anterior = pyautogui.FAILSAFE

    try:
        pyautogui.FAILSAFE = False
        pyautogui.mouseUp(button="left")

    finally:
        pyautogui.FAILSAFE = anterior


@app.websocket("/ws")
async def websocket_controle(websocket: WebSocket):
    host = websocket.headers.get("host")
    origem = websocket.headers.get("origin")

    if not host or origem != f"http://{host}":
        await websocket.close(code=1008)
        return

    await websocket.accept()

    if controle_em_uso.locked():
        await websocket.send_json({
            "type": "error",
            "message": "Outro celular está conectado."
        })

        await websocket.close(code=1008)
        return

    async with controle_em_uso:
        pressionado = False

        await websocket.send_json({
            "type": "ready"
        })

        print("Celular conectado ao LINK.")

        try:
            while True:
                dados = await websocket.receive_json()

                if not isinstance(dados, dict):
                    continue

                try:
                    pressionado = await asyncio.to_thread(
                        executar_comando,
                        dados,
                        pressionado
                    )

                except pyautogui.FailSafeException:
                    print(
                        "Parada de emergência ativada."
                    )

                    await websocket.close(code=1008)
                    break

                except Exception as erro:
                    print(
                        "Erro ao executar comando:",
                        erro
                    )

        except (WebSocketDisconnect, ValueError):
            pass

        finally:
            if pressionado:
                await asyncio.to_thread(
                    liberar_botao
                )

            print("Celular desconectado.")


def ip_local():
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        ) as s:
            s.connect(("192.0.2.1", 80))
            return s.getsockname()[0]

    except OSError:
        return "IP_DO_NOTEBOOK"


if __name__ == "__main__":
    print("\n====== LINK v0.3 ======")

    print(
        f"No celular: http://{ip_local()}:8001"
    )

    print(
        "Sem PIN - use apenas em Wi-Fi privado."
    )

    print("Para sair: Ctrl + C\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        access_log=False
    )
