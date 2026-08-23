const TUTORIAL_CONTENT = {
  visao_geral: `
    <h3>Visão geral: as 3 abas do painel</h3>
    <p style="margin:0 0 14px;color:var(--text-muted);">
      O painel tem 3 abas, cada uma respondendo a uma pergunta diferente. Clique em
      <b>"Iniciar simulação"</b> no topo primeiro; todas as abas se alimentam do mesmo stream.
    </p>
    <h4 style="color:var(--teal);margin:14px 0 6px;">1. Visão da Carteira; "Como está minha carteira e o que mudou?"</h4>
    <ol>
      <li><b>6 indicadores de negócio</b> no topo: operações, valor total, PD média da carteira,
        alto risco, quantas aumentaram de risco, quantas estão em análise. Passe o mouse no ícone
        <b>(i)</b> de qualquer um para ver a definição exata.</li>
      <li><b>Distribuição do risco</b>: proporção da carteira em cada faixa (baixo/intermediário/alto).</li>
      <li><b>Evolução do risco</b>: PD média, operações de alto risco ou exposição; alterne pelos botões acima do gráfico.</li>
      <li><b>O que mudou?</b>: quantas operações subiram, ultrapassaram o limite, ou caíram de risco,
        mais uma tabela das mudanças mais relevantes por estado.</li>
      <li><b>Mapa</b>: risco médio por estado, colorido por faixa.</li>
      <li><b>Atenção agora</b>: resumo do que precisa de ação; o botão <b>"Ver operações"</b> leva
        direto para a Aba 2 já filtrada pelas operações que exigem análise.</li>
    </ol>
    <h4 style="color:var(--teal);margin:14px 0 6px;">2. Operações; "Onde devo concentrar minha atenção?"</h4>
    <ol>
      <li>Tabela filtrável por produtor/código, estado, situação e faixa de risco.</li>
      <li><b>Clique em qualquer linha</b> para abrir o detalhe: PD atual e anterior, variação, limite
        de decisão, confiança, e os fatores que mais pesaram na decisão daquela operação específica.</li>
      <li>No detalhe, o botão <b>"Explicar com IA"</b> (se ativado) traduz esses números em um parágrafo,
        sem alterar PD nem decisão. O botão <b>"Como isso é calculado?"</b> mostra a fórmula por trás dos fatores.</li>
      <li><b>Simular cenário ("e se?")</b>: use os presets prontos (queda de commodity, seca, estresse econômico,
        combinado) ou ajuste os campos manualmente; o sistema recalcula o PD das operações recentes sob esse
        cenário e mostra uma tabela comparando PD atual vs. simulado, sem alterar nada de verdade.</li>
    </ol>
    <h4 style="color:var(--teal);margin:14px 0 6px;">3. Aprendizado do Sistema; "O sistema está funcionando e se adaptando?"</h4>
    <ol>
      <li>Indicadores técnicos: acurácia, limite de decisão, mudança detectada, iteração, latência.</li>
      <li><b>Mudança no comportamento do modelo</b>: um selo simples (Estável / Ajuste acionado) com a
        intensidade da mudança e o limite usado na simulação.</li>
      <li><b>Fluxo dos agentes</b>: os 6 agentes: passe o mouse sobre qualquer um para ver o que ele faz.</li>
      <li><b>Aprendizado ao longo das iterações</b> e <b>Previsto vs. Realizado</b>: dois gráficos com
        cards de interpretação em texto simples logo abaixo.</li>
    </ol>`,
  negocios: `
    <h3>Para o Analista de Negócios</h3>
    <ol>
      <li>Clique em <b>"Iniciar simulação"</b> no topo para começar o fluxo contínuo de solicitações de crédito agropecuário.</li>
      <li>Fique na Aba <b>"Visão da Carteira"</b>; ela já responde "como está minha carteira" e "o que mudou" sem exigir nenhum conhecimento técnico.</li>
      <li>Use o bloco <b>"Atenção agora"</b> e o botão <b>"Ver operações"</b> para ir direto ao que precisa de decisão.</li>
      <li>Na Aba <b>"Operações"</b>, use os presets de <b>Simular cenário ("e se?")</b> para ver, sem alterar nada de verdade, como cada operação recente reagiria a uma queda de commodity, seca ou alta de juros.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
  dados: `
    <h3>Para o Analista de Dados</h3>
    <ol>
      <li>Os dados são 100% sintéticos, gerados com seed fixa (42); reprodutíveis via <code>scripts/generate_synthetic_data.py</code>.</li>
      <li>Na Aba <b>"Aprendizado do Sistema"</b>, o gráfico <b>Aprendizado ao longo das iterações</b> mostra acurácia, limite de decisão e mudança detectada (<code>D = |Mt − Mt−1|</code>) por iteração; use os botões de seleção para isolar cada série.</li>
      <li>No detalhe de qualquer operação (Aba <b>"Operações"</b>, clique numa linha), os fatores de risco são a derivada analítica <code>Ai = ∂PD/∂Fi</code> da regressão logística; não SHAP/LIME.</li>
      <li>O histórico <b>Previsto vs. Realizado</b> (<code>GET /api/monitoring/monthly</code>) serve para auditoria e validação externa do modelo.</li>
      <li>Todo o histórico de outcomes fica acessível via <code>GET /api/feedback/history</code> para análises externas.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
  bi: `
    <h3>Para o Analista de BI</h3>
    <ol>
      <li>A Aba <b>"Visão da Carteira"</b> reúne os 6 indicadores de negócio, atualizados em tempo real via WebSocket; pense nela como o "resumo executivo" do painel.</li>
      <li>O <b>mapa</b> é um choropleth por faixa de risco (verde/amarelo/vermelho) por estado; útil para dashboards de exposição geográfica.</li>
      <li>O <b>Histórico Previsto vs. Realizado</b> (Aba "Aprendizado do Sistema") é uma série mensal pronta para virar um relatório recorrente de acompanhamento de carteira.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
  credito: `
    <h3>Para o Analista de Crédito</h3>
    <ol>
      <li>Na Aba <b>"Operações"</b>, clique em qualquer linha da tabela para ver o detalhe completo:
        PD atual, PD anterior, variação, limite de decisão e confiança para aquele produtor específico;
        a decisão segue literalmente: PD &lt; limite → Aprovado, PD = limite → Em análise, PD &gt; limite → Recusado.</li>
      <li>O bloco <b>"Por que o risco mudou?"</b> no detalhe mostra o peso de cada variável (dívida, chuva, preço da commodity etc.); gerado no momento da decisão, não depois.</li>
      <li>Use os filtros da tabela (estado, situação, faixa de risco) para focar no que precisa de atenção.</li>
      <li>Não há regra manual do tipo "seca → recusar"; a simulação "e se?" recalcula o PD real de cada operação sob o cenário, usando o mesmo modelo, sem alterar nada de verdade.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
  carteira: `
    <h3>Para o Gerente de Carteira de Crédito</h3>
    <ol>
      <li>A Aba <b>"Visão da Carteira"</b> é sua tela principal: acompanhe a distribuição de risco e o
        bloco <b>"O que mudou?"</b> para saber se a carteira está piorando ou melhorando.</li>
      <li>O <b>limite de decisão adaptativo</b> (Aba "Aprendizado do Sistema") se move sozinho conforme
        a perda observada: acompanhe o selo de "Mudança no comportamento do modelo"
        para saber quando o sistema se recalibrou.</li>
      <li>O <b>Histórico Previsto vs. Realizado</b> é a ferramenta mais direta para você: se a
        inadimplência real estiver consistentemente acima do previsto, é sinal de antecipar contatos
        de renegociação com os clientes mais expostos.</li>
      <li>Use os presets de <b>Simular cenário ("e se?")</b> (Aba "Operações") para ver, operação por
        operação, como o PD reagiria a um choque de mercado ou clima antes que aconteça de verdade;
        sem alterar nada real na carteira.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
  ceo: `
    <h3>Para o CEO / liderança executiva</h3>
    <ol>
      <li>Esta é uma <b>demonstração funcional de uma arquitetura de paper acadêmico (Kubam, 2024)</b>,
        adaptada ao crédito agropecuário brasileiro, rodando sobre dados 100% sintéticos; não é um
        sistema de produção. Clique no badge <b>"DEMONSTRAÇÃO DA ARQUITETURA"</b> no topo
        para ver o diagrama completo.</li>
      <li>A Aba <b>"Visão da Carteira"</b> já é a visão resumida: exposição, concentração de risco e
        tendência, sem exigir nenhum conhecimento técnico.</li>
      <li>Os indicadores ao vivo são os resultados reais desta demonstração.</li>
      <li>O valor do protótipo é demonstrar decisão de crédito autônoma, explicável e com aprendizagem
        contínua; a base para uma futura avaliação de viabilidade em produção.</li>
    </ol>
    <p style="color:var(--text-dim);font-size:11.5px;margin-top:10px;">Veja a aba "Visão Geral" para uma explicação detalhada de cada seção.</p>`,
};

const Tutorial = {
  init() {
    document.getElementById("btnHelp").addEventListener("click", () => Tour.start());
    document.getElementById("btnHelpDetailed").addEventListener("click", () => this.open());
    document.getElementById("btnCloseHelp").addEventListener("click", () => this.close());
    document.getElementById("helpModal").addEventListener("click", (e) => {
      if (e.target.id === "helpModal") this.close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.close();
    });
    document.querySelectorAll(".mtab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".mtab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        this.render(tab.dataset.persona);
      });
    });
    this.render("visao_geral");
  },
  open() { document.getElementById("helpModal").classList.remove("hidden"); },
  close() { document.getElementById("helpModal").classList.add("hidden"); },
  render(persona) {
    document.getElementById("modalBody").innerHTML = TUTORIAL_CONTENT[persona] || "";
  },
};
