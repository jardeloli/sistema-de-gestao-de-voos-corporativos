/* Interações leves da interface. Tudo aqui é melhoria progressiva:
   sem JavaScript, os formulários continuam funcionando e o servidor valida tudo. */
(function () {
  "use strict";

  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const num = (el) => parseFloat(String(el && el.value || "").replace(",", ".")) || 0;

  // Leva o foco ao resumo de erros após um envio inválido (leitores de tela anunciam)
  const resumo = document.getElementById("resumo-erros");
  if (resumo) resumo.focus();

  // Confirmação antes de ações destrutivas
  document.querySelectorAll("form[data-confirmar]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
    });
  });

  // Contador de passageiros x capacidade da aeronave (agendamento)
  const capEl = document.getElementById("capacidades");
  const aeronave = document.getElementById("id_aeronave");
  const contador = document.getElementById("contador-pax");
  if (capEl && aeronave && contador) {
    const capacidades = JSON.parse(capEl.textContent);
    const caixas = document.querySelectorAll('input[name="passageiros"]');
    const atualizar = () => {
      const marcados = [...caixas].filter((c) => c.checked).length;
      const cap = capacidades[aeronave.value];
      if (!cap) {
        contador.textContent = `${marcados} ${marcados === 1 ? "passageiro marcado" : "passageiros marcados"}. Selecione a aeronave para ver a capacidade.`;
        contador.classList.remove("text-danger");
        return;
      }
      const excedeu = marcados > cap;
      contador.textContent = excedeu
        ? `${marcados} marcados — a aeronave comporta ${cap}. Desmarque ${marcados - cap}.`
        : `${marcados} de ${cap} lugares ocupados.`;
      contador.classList.toggle("text-danger", excedeu);
      contador.classList.toggle("fw-bold", excedeu);
    };
    aeronave.addEventListener("change", atualizar);
    caixas.forEach((c) => c.addEventListener("change", atualizar));
    atualizar();
  }

  // Prévia do valor total do abastecimento (o servidor recalcula ao salvar)
  const litros = document.getElementById("id_quantidade_litros");
  const precoLitro = document.getElementById("id_valor_litro");
  const total = document.getElementById("valor-total");
  if (litros && precoLitro && total) {
    const calc = () => {
      const v = num(litros) * num(precoLitro);
      total.textContent = v > 0 ? brl.format(v) : "—";
    };
    [litros, precoLitro].forEach((el) => el.addEventListener("input", calc));
    calc();
  }

  // Prévia do consumo médio ao registrar o voo realizado
  const horas = document.getElementById("id_horas_voo");
  const consumo = document.getElementById("id_combustivel_consumido");
  const previa = document.getElementById("consumo-previa");
  if (horas && consumo && previa) {
    const calc = () => {
      const h = num(horas), l = num(consumo);
      previa.textContent = h > 0 && l > 0 ? `Consumo médio: ${(l / h).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} L/h` : "";
    };
    [horas, consumo].forEach((el) => el.addEventListener("input", calc));
    calc();
  }
})();
