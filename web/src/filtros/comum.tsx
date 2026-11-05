/** Peças repetidas em todas as seções do painel de filtros. */
import { useEffect, useState, type ReactNode } from "react";
import type { Busca } from "../tipos";

/**
 * Campo de número que deixa digitar à vontade: guarda o texto enquanto a pessoa digita e só repassa o valor
 * quando ele fica válido (entre `min` e `max`). Assim "17" pode ser digitado mesmo com o "1" sozinho inválido.
 * Usa teclado numérico no celular (inputMode) em vez de type="number", que no Android/iOS se comporta mal.
 */
export function CampoNumero({
  id,
  valor,
  aoMudar,
  min,
  max,
  placeholder,
  desabilitado,
  vazioVale,
}: {
  id: string;
  valor: number | null;
  aoMudar: (valor: number | null) => void;
  min: number;
  max: number;
  placeholder?: string;
  desabilitado?: boolean;
  /** O que vale com o campo vazio: null (ex.: idade não informada) ou um número padrão. */
  vazioVale: number | null;
}) {
  const [texto, setTexto] = useState(valor === null ? "" : String(valor));
  const valido = (t: string) => t !== "" && Number(t) >= min && Number(t) <= max;

  // Mudança vinda de fora (ex.: "Zerar filtros"): atualiza o texto. Não mexe enquanto a pessoa está no meio
  // de um número ainda inválido, senão o campo apagaria o que ela acabou de digitar.
  useEffect(() => {
    setTexto((atual) => {
      if (valor === null) return valido(atual) ? "" : atual;
      return Number(atual) === valor ? atual : String(valor);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valor]);

  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      pattern="[0-9]*"
      autoComplete="off"
      maxLength={String(max).length}
      placeholder={placeholder}
      value={texto}
      disabled={desabilitado}
      aria-invalid={texto !== "" && !valido(texto)}
      onChange={(e) => {
        const t = e.target.value.replace(/\D/g, "");
        setTexto(t);
        if (valido(t)) aoMudar(Number(t));
        // Vazio só vira "não informado" na hora quando isso é permitido (idade). Com padrão (raio), espera a
        // pessoa sair do campo: apagar para redigitar não pode encher o campo de novo no meio da digitação.
        else if (t === "" && vazioVale === null) aoMudar(null);
      }}
      onBlur={() => {
        if (valido(texto) || (texto === "" && vazioVale === null)) return;
        // Saiu com o campo vazio ou fora da faixa: vale o padrão (se vazio) ou o último valor válido.
        const final = texto === "" ? vazioVale : valor;
        if (final !== valor) aoMudar(final);
        setTexto(final === null ? "" : String(final));
      }}
    />
  );
}

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
