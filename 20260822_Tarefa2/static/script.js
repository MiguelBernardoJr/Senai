// script.js
// ---------------------------------------------------------
// Lógica de front-end:
// - Envia o formulário (nome da classe + imagens) para o backend.
// - Atualiza a lista de classes na tela.
// - NOVO na Fase 2: aciona o treinamento do modelo e mostra o
//   resultado (acurácia) quando terminar.
// ---------------------------------------------------------

// Elementos da Fase 1.
const formulario = document.getElementById("formulario-upload");
const mensagemStatus = document.getElementById("mensagem-status");
const corpoTabela = document.getElementById("corpo-tabela-classes");
const nenhumaClasseTexto = document.getElementById("nenhuma-classe");

// Elementos novos da Fase 2 (treinamento).
const botaoTreinar = document.getElementById("botao-treinar");
const mensagemTreinamento = document.getElementById("mensagem-treinamento");

// ---------------------------------------------------------
// Função: mostra uma mensagem de sucesso ou erro em uma caixinha
// qualquer da tela (reaproveitada pelo upload e pelo treinamento).
// ---------------------------------------------------------
function mostrarMensagem(elemento, texto, tipo) {
    // tipo pode ser "sucesso", "erro" ou "info"
    elemento.textContent = texto;
    elemento.className = tipo;
}

// ---------------------------------------------------------
// Função: busca no backend a lista de classes e monta a tabela.
// ---------------------------------------------------------
async function atualizarListaDeClasses() {
    try {
        const resposta = await fetch("/classes");
        const dados = await resposta.json();

        corpoTabela.innerHTML = "";

        if (dados.classes.length === 0) {
            nenhumaClasseTexto.style.display = "block";
            return;
        }

        nenhumaClasseTexto.style.display = "none";

        dados.classes.forEach((classe) => {
            const linha = document.createElement("tr");

            const colunaNome = document.createElement("td");
            colunaNome.textContent = classe.nome;

            const colunaQuantidade = document.createElement("td");
            colunaQuantidade.textContent = classe.quantidade;

            linha.appendChild(colunaNome);
            linha.appendChild(colunaQuantidade);
            corpoTabela.appendChild(linha);
        });

    } catch (erro) {
        console.error("Erro ao buscar classes:", erro);
        mostrarMensagem(mensagemStatus, "Não foi possível carregar a lista de classes.", "erro");
    }
}

// ---------------------------------------------------------
// Evento: quando o formulário de upload for enviado.
// ---------------------------------------------------------
formulario.addEventListener("submit", async function (evento) {
    evento.preventDefault();

    const dadosDoFormulario = new FormData(formulario);

    try {
        const resposta = await fetch("/upload", {
            method: "POST",
            body: dadosDoFormulario
        });

        const resultado = await resposta.json();

        if (resposta.ok && resultado.sucesso) {
            mostrarMensagem(mensagemStatus, resultado.mensagem, "sucesso");
            formulario.reset();
            atualizarListaDeClasses();
        } else {
            mostrarMensagem(mensagemStatus, resultado.mensagem || "Erro ao enviar imagens.", "erro");
        }

    } catch (erro) {
        console.error("Erro ao enviar formulário:", erro);
        mostrarMensagem(mensagemStatus, "Erro de conexão com o servidor.", "erro");
    }
});

// ---------------------------------------------------------
// NOVO (Fase 2): evento de clique no botão "Treinar Modelo".
// ---------------------------------------------------------
botaoTreinar.addEventListener("click", async function () {
    // Desabilita o botão enquanto treina, para evitar cliques duplicados.
    botaoTreinar.disabled = true;
    mostrarMensagem(
        mensagemTreinamento,
        "Treinando... isso pode levar alguns minutos, aguarde.",
        "info"
    );

    try {
        const resposta = await fetch("/treinar", {
            method: "POST"
        });

        const resultado = await resposta.json();

        if (resposta.ok && resultado.sucesso) {
            const texto =
                `Modelo treinado com sucesso! ` +
                `Acurácia: ${resultado.acuracia}% ` +
                `(${resultado.quantidade_de_imagens} imagens, ` +
                `${resultado.classes.length} classes, ` +
                `${resultado.epocas} épocas).`;

            mostrarMensagem(mensagemTreinamento, texto, "sucesso");
        } else {
            mostrarMensagem(
                mensagemTreinamento,
                resultado.mensagem || "Erro ao treinar o modelo.",
                "erro"
            );
        }

    } catch (erro) {
        console.error("Erro ao treinar modelo:", erro);
        mostrarMensagem(
            mensagemTreinamento,
            "Erro de conexão com o servidor durante o treinamento.",
            "erro"
        );
    } finally {
        botaoTreinar.disabled = false;
    }
});

// ---------------------------------------------------------
// Quando a página carregar pela primeira vez, já mostramos
// as classes que já existirem.
// ---------------------------------------------------------
document.addEventListener("DOMContentLoaded", atualizarListaDeClasses);
