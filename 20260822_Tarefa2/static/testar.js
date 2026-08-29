// testar.js
// ---------------------------------------------------------
// Lógica da página de teste (Fase 3, com mensagens de erro melhoradas
// na Fase 4):
// 1. Deixa o usuário escolher uma imagem e mostra uma pré-visualização.
// 2. Envia a imagem para a rota /prever do backend (Flask).
// 3. Recebe as porcentagens de cada classe e desenha um gráfico de
//    barras (Chart.js) com o resultado.
// 4. Se algo der errado (sem modelo treinado, arquivo inválido, erro
//    de conexão, etc.), mostra uma mensagem clara e colorida na tela.
// ---------------------------------------------------------

// Pega os elementos da página que vamos usar.
const inputImagem = document.getElementById("input-imagem");
const botaoAnalisar = document.getElementById("botao-analisar");
const mensagemStatus = document.getElementById("mensagem-status");

const blocoPreview = document.getElementById("bloco-preview");
const previewImagem = document.getElementById("preview-imagem");

const blocoResultado = document.getElementById("bloco-resultado");
const textoResultadoFinal = document.getElementById("texto-resultado-final");
const canvasGrafico = document.getElementById("grafico-porcentagens");

// Guardamos aqui a referência do gráfico atual, para poder destruí-lo
// antes de desenhar um novo (o Chart.js não deixa desenhar dois
// gráficos empilhados no mesmo <canvas>).
let graficoAtual = null;

// ---------------------------------------------------------
// Função: mostra uma mensagem de sucesso, erro ou aviso na caixinha de
// status, reaproveitando as mesmas cores/estilos usados na página
// inicial (classes "sucesso", "erro" e "info" do style.css).
// ---------------------------------------------------------
function mostrarMensagem(texto, tipo) {
    mensagemStatus.textContent = texto;
    mensagemStatus.className = tipo || "";
}

// Sempre que o usuário escolher uma imagem, mostramos uma
// pré-visualização dela na tela.
inputImagem.addEventListener("change", () => {
    const arquivo = inputImagem.files[0];

    // Limpa mensagens e resultados antigos ao trocar de imagem.
    mostrarMensagem("", "");
    blocoResultado.style.display = "none";

    if (!arquivo) {
        blocoPreview.style.display = "none";
        return;
    }

    // FileReader lê o arquivo escolhido e transforma em uma URL que
    // o navegador consegue exibir dentro de uma tag <img>.
    const leitor = new FileReader();
    leitor.onload = (evento) => {
        previewImagem.src = evento.target.result;
        blocoPreview.style.display = "block";
    };
    leitor.onerror = () => {
        mostrarMensagem("Não foi possível ler esse arquivo. Escolha outra imagem.", "erro");
        blocoPreview.style.display = "none";
    };
    leitor.readAsDataURL(arquivo);
});

// Quando o usuário clicar em "Analisar Imagem", enviamos o arquivo
// para o backend e mostramos o resultado.
botaoAnalisar.addEventListener("click", async () => {
    const arquivo = inputImagem.files[0];

    if (!arquivo) {
        mostrarMensagem("Escolha uma imagem antes de analisar.", "erro");
        return;
    }

    mostrarMensagem("Analisando imagem...", "info");
    botaoAnalisar.disabled = true;
    blocoResultado.style.display = "none";

    // FormData é o jeito padrão de enviar arquivos por fetch/AJAX.
    const dadosDoFormulario = new FormData();
    dadosDoFormulario.append("imagem", arquivo);

    try {
        const resposta = await fetch("/prever", {
            method: "POST",
            body: dadosDoFormulario
        });

        const dados = await resposta.json();

        if (!dados.sucesso) {
            // O backend explica o motivo do erro (ex: modelo não
            // treinado, imagem corrompida, arquivo inválido).
            mostrarMensagem(dados.mensagem, "erro");
            return;
        }

        mostrarMensagem("", "");
        mostrarResultado(dados);

    } catch (erro) {
        mostrarMensagem("Erro ao conectar com o servidor. Verifique se o app.py está rodando.", "erro");
        console.error(erro);
    } finally {
        botaoAnalisar.disabled = false;
    }
});

/**
 * Mostra o resultado da previsão na tela: o texto com a classe
 * vencedora e o gráfico de barras com a porcentagem de cada classe.
 */
function mostrarResultado(dados) {
    // Texto em destaque com o resultado final.
    textoResultadoFinal.textContent =
        `Resultado: ${dados.resultado_final} (${dados.porcentagens[dados.resultado_final]}%)`;

    // Prepara os dados no formato que o Chart.js espera: uma lista de
    // nomes (labels) e uma lista de valores (values), na mesma ordem.
    const nomesDasClasses = Object.keys(dados.porcentagens);
    const valoresDasPorcentagens = Object.values(dados.porcentagens);

    // Se já existia um gráfico desenhado antes, destruímos ele para
    // não ficar um gráfico "por cima" do outro.
    if (graficoAtual) {
        graficoAtual.destroy();
    }

    graficoAtual = new Chart(canvasGrafico, {
        type: "bar",
        data: {
            labels: nomesDasClasses,
            datasets: [{
                label: "Confiança (%)",
                data: valoresDasPorcentagens,
                backgroundColor: "rgba(54, 162, 235, 0.6)",
                borderColor: "rgba(54, 162, 235, 1)",
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: "Porcentagem de confiança (%)"
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    blocoResultado.style.display = "block";
}
