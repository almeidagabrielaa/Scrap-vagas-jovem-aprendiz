/** Guia do primeiro trampo: o básico de cada contrato, documentos, currículo e cuidado com golpes. */
import { useState } from "react";

const MODELO_CURRICULO = `SEU NOME COMPLETO
Cidade/UF · (22) 90000-0000 · seuemail@exemplo.com
Idade: 17 anos

OBJETIVO
Primeira oportunidade como Jovem Aprendiz (ou estágio / meio período) na área de [atendimento, administração, loja...].

ESCOLARIDADE
Ensino médio – cursando o [2º] ano, turno da [manhã] · Escola [nome], [cidade]
Previsão de conclusão: [dezembro de 2027]

CURSOS E CERTIFICADOS
[Informática básica / Pacote Office] – [instituição], [ano], [carga horária]
[Inglês básico] – [instituição ou online], [ano]

EXPERIÊNCIAS (não precisa ser emprego!)
Voluntário(a) em [igreja, ONG, projeto da escola] – [o que você fazia], [período]
Ajudo no comércio da família – atendimento ao cliente e caixa, [período]
Representante de turma / grêmio estudantil, [ano]

HABILIDADES
Comunicação e atendimento ao público · Pontualidade · Trabalho em equipe
Uso de celular e computador (Word, Excel, redes sociais)

DISPONIBILIDADE
Turno da [tarde], de segunda a sexta.`;

interface Bloco {
  emoji: string;
  titulo: string;
  itens: string[];
}

const BLOCOS: Bloco[] = [
  {
    emoji: "🎓",
    titulo: "Jovem aprendiz (Lei 10.097/2000)",
    itens: [
      "De 14 a 24 anos (pessoa com deficiência não tem limite de idade).",
      "Carteira assinada, salário mínimo/hora garantido, FGTS, 13º e férias.",
      "Contrato de até 2 anos, com curso teórico junto (as horas do curso contam como trabalho).",
      "Até 6 horas por dia. Quem já terminou o fundamental pode fazer até 8, contando o curso. Hora extra é proibida.",
      "Se ainda não terminou o ensino médio, precisa estar matriculado(a) e indo à escola.",
    ],
  },
  {
    emoji: "📚",
    titulo: "Estágio (Lei 11.788/2008)",
    itens: [
      "Pra quem está matriculado(a) no ensino médio, técnico ou faculdade. Não é carteira assinada.",
      "Até 6 horas por dia e 30 por semana (4h/20h no fundamental EJA e na educação especial).",
      "No estágio não obrigatório, bolsa e auxílio-transporte são obrigatórios, e a empresa paga seguro contra acidentes.",
      "Depois de 1 ano, direito a 30 dias de recesso remunerado. No máximo 2 anos na mesma empresa.",
    ],
  },
  {
    emoji: "⏰",
    titulo: "Meio período e primeiro emprego",
    itens: [
      "Carteira assinada normal, com jornada menor (part-time): até 30 horas por semana.",
      "Comum em loja, restaurante, atendimento e promoção de vendas: bom pra conciliar com a escola.",
      "Menor de 18 anos não pode trabalhar à noite (22h às 5h) nem em local perigoso ou insalubre.",
    ],
  },
  {
    emoji: "🗂️",
    titulo: "Documentos pra deixar prontos",
    itens: [
      "RG e CPF (o número da carteira de trabalho agora é o CPF).",
      "Carteira de Trabalho Digital: baixa o app e entra com a conta gov.br.",
      "Comprovante de residência e declaração de matrícula da escola (pede na secretaria).",
      "Conta no banco no teu nome (dá pra abrir conta digital de graça; menor de 18 com o responsável).",
      "A partir de 18: título de eleitor e, pros homens, certificado de reservista.",
    ],
  },
  {
    emoji: "🗣️",
    titulo: "Na entrevista",
    itens: [
      "Pesquisa a empresa antes e chega 10 minutos adiantado(a).",
      "Fala de escola, trabalho voluntário, ajuda em casa ou no negócio da família: tudo isso é experiência.",
      "Treina a resposta pra “por que você quer essa vaga?” e “fala um pouco de você”.",
      "No fim, pergunta algo (horário, o que vai aprender). Mostra interesse.",
    ],
  },
  {
    emoji: "🚨",
    titulo: "Cuidado com golpe",
    itens: [
      "Vaga de verdade nunca cobra taxa, curso obrigatório pago, “kit” ou exame pra contratar.",
      "CIEE, Isbet, Espro e Renapsi não cobram nada de quem se candidata.",
      "Desconfia de salário alto demais pra pouca tarefa e de quem pede código do WhatsApp ou senha.",
      "Entrevista é em lugar público ou na empresa. Avisa alguém de casa onde vai.",
    ],
  },
];

export function Guia() {
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(MODELO_CURRICULO);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
    } catch {
      baixar(); // sem permissão de área de transferência: entrega o arquivo
    }
  }

  function baixar() {
    const url = URL.createObjectURL(new Blob([MODELO_CURRICULO], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "modelo-curriculo-primeiro-emprego.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="guia">
      <header>
        <h2>📘 Guia do primeiro trampo</h2>
        <p className="sub">O básico pra se candidatar com confiança. Funciona até sem internet, se tu instalar o app.</p>
      </header>
      <div className="guia-blocos">
        {BLOCOS.map((b) => (
          <article key={b.titulo} className="guia-bloco">
            <h3>
              {b.emoji} {b.titulo}
            </h3>
            <ul>
              {b.itens.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
      <article className="guia-bloco curriculo">
        <h3>📝 Modelo de currículo pra quem nunca trabalhou</h3>
        <p className="nota">Troca o que está entre [colchetes], salva em PDF e manda. Uma página só, sem foto.</p>
        <pre>{MODELO_CURRICULO}</pre>
        <div className="vaga-acoes">
          <button type="button" className="botao-pequeno ativo" onClick={copiar}>
            {copiado ? "✅ Copiado!" : "Copiar modelo"}
          </button>
          <button type="button" className="botao-pequeno" onClick={baixar}>
            Baixar .txt
          </button>
        </div>
      </article>
      <p className="nota">
        Resumo das leis, sem substituir o texto oficial. Na dúvida, confirma com a escola, o CIEE/Isbet ou o RH da empresa.
      </p>
    </section>
  );
}
