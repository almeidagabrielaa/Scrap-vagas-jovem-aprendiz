import type { Escolaridade, Opcoes } from "../tipos";
import { Ajuda, Chip, Secao, type PropsSecao } from "./comum";

/** Idade e escolaridade de quem procura: esconde vagas que pedem claramente outra coisa. */
export function SecaoSobreTi({
  busca,
  mudar,
  rodando,
  escolaridades,
  turnos,
}: PropsSecao & { escolaridades: Escolaridade[]; turnos: Opcoes["turnos"] }) {
  return (
    <Secao titulo="🙋 Sobre tu">
      <div className="linha">
        <label className="campo-curto">
          <span>Idade</span>
          <input
            id="idade"
            type="number"
            min={14}
            max={29}
            placeholder="ex.: 17"
            value={busca.idade ?? ""}
            onChange={(e) => {
              const n = Number(e.target.value);
              mudar({ idade: e.target.value && n >= 14 && n <= 29 ? n : null });
            }}
            disabled={rodando}
          />
        </label>
        <label className="campo-longo">
          <span>Escola</span>
          <select
            id="escolaridade"
            value={busca.escolaridade ?? ""}
            onChange={(e) => mudar({ escolaridade: e.target.value || null })}
            disabled={rodando}
          >
            <option value="">Não quero dizer</option>
            {escolaridades.map((e) => (
              <option key={e.nome} value={e.nome}>
                {e.titulo}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grupo-vizinhas">
        <h4>Estudo de</h4>
        <div className="chips">
          {turnos.map((t) => (
            <Chip
              key={t.nome}
              marcado={busca.turno_escola === t.nome}
              desabilitado={rodando}
              aoClicar={() => mudar({ turno_escola: busca.turno_escola === t.nome ? null : t.nome })}
            >
              {t.titulo}
            </Chip>
          ))}
        </div>
      </div>
      <Ajuda>Some com as vagas que pedem outra idade ou escolaridade, ou que caem no horário da tua aula. Se o anúncio não diz, a vaga continua aparecendo.</Ajuda>
    </Secao>
  );
}
