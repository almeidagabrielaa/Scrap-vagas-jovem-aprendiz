/** Peças repetidas em todas as seções do painel de filtros. */
import type { ReactNode } from "react";
import type { Busca } from "../tipos";

/** O que toda seção recebe: a busca atual, como mudá-la e se há uma busca em andamento (trava os campos). */
export interface PropsSecao {
  busca: Busca;
  mudar: (parcial: Partial<Busca>) => void;
  rodando: boolean;
}

export function Secao({ titulo, contador, children }: { titulo: string; contador?: number; children: ReactNode }) {
  return (
    <fieldset>
      <legend>
        {titulo} {contador ? <span className="contador">{contador}</span> : null}
      </legend>
      {children}
    </fieldset>
  );
}

export function Ajuda({ children }: { children: ReactNode }) {
  return <p className="ajuda">{children}</p>;
}

interface PropsMarcavel {
  marcado: boolean;
  aoClicar: () => void;
  desabilitado?: boolean;
}

/** Botão redondo que liga/desliga (bairros, cidades vizinhas). */
export function Chip({ marcado, aoClicar, desabilitado, children }: PropsMarcavel & { children: ReactNode }) {
  return (
    <button
      type="button"
      className={`chip${marcado ? " marcado" : ""}`}
      aria-pressed={marcado}
      disabled={desabilitado}
      onClick={aoClicar}
    >
      {children}
    </button>
  );
}

/** Cartão grande que liga/desliga (tipo de vaga, distrito). */
export function CartaoOpcao({
  marcado,
  aoClicar,
  desabilitado,
  titulo,
  detalhe,
}: PropsMarcavel & { titulo: ReactNode; detalhe?: ReactNode }) {
  return (
    <button
      type="button"
      className={`cartao-opcao${marcado ? " marcado" : ""}`}
      aria-pressed={marcado}
      disabled={desabilitado}
      onClick={aoClicar}
    >
      <strong>{titulo}</strong>
      {detalhe && <span>{detalhe}</span>}
    </button>
  );
}

/** Caixa de seleção com texto e, opcionalmente, uma explicação menor embaixo. */
export function Opcao({
  id,
  marcado,
  aoMudar,
  desabilitado,
  children,
  detalhe,
}: {
  id: string;
  marcado: boolean;
  aoMudar: (marcado: boolean) => void;
  desabilitado?: boolean;
  children: ReactNode;
  detalhe?: ReactNode;
}) {
  return (
    <label className={`opcao${desabilitado ? " desabilitada" : ""}`}>
      <input id={id} type="checkbox" checked={marcado} onChange={(e) => aoMudar(e.target.checked)} disabled={desabilitado} />
      <span>
        {children}
        {detalhe && <small className="detalhe-opcao">{detalhe}</small>}
      </span>
    </label>
  );
}
