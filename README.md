# Radar Jovem Aprendiz

Busca vagas de **Jovem Aprendiz** na internet a cada execução e filtra por **cidade, distrito e bairro**.
Vem configurado para Cabo Frio (RJ), com o 1º Distrito (Sede) e o 2º Distrito (Tamoios).

## Instalação

Requer Python 3.10 ou mais novo.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Interface web (FMT - jovem aprendiz)

```powershell
radar web
```

Abre `http://127.0.0.1:8000` no navegador. Lá você escolhe cidade, distritos, bairros, "perto de mim" (com raio),
opções e sites, e aperta **Buscar vagas**. O progresso aparece em tempo real e o resultado pode ser filtrado por texto
e baixado em CSV. A última busca fica lembrada no navegador. Para parar o servidor, use Ctrl+C no terminal.

A interface (React + Vite) fica em [web/](web/). Ela já vem compilada em `src/radar/web_dist`. Depois de mudar o código dela:

```powershell
cd web
npm install      # só na primeira vez
npm run build    # recompila para src/radar/web_dist
npm run dev      # ou: modo desenvolvimento em http://localhost:5173 (com `radar web --nao-abrir` rodando)
```

## Uso pela linha de comando

```powershell
# todas as vagas de aprendiz em Cabo Frio
radar buscar

# só o 2º Distrito (Tamoios); aceita número ou nome
radar buscar --distrito 2
radar buscar -d tamoios

# bairros específicos (pode repetir -b)
radar buscar -b Peró -b "São Cristóvão"

# só o que apareceu desde a última execução, salvando em CSV e HTML
radar buscar -d 1 --novas --csv vagas.csv --html vagas.html

# Cabo Frio + Arraial do Cabo + Búzios, e vagas remotas de todo o Brasil (etiqueta "VAGA REMOTA")
radar buscar --vizinha "Arraial do Cabo" --vizinha Búzios --remotas

# todas as vizinhas cadastradas (Arraial, Búzios, São Pedro, Iguaba, Araruama, Saquarema,
# Rio das Ostras, Casimiro de Abreu, Macaé)
radar buscar --vizinhas

# vagas mais perto de você (bairro ou endereço), opcionalmente num raio em km
radar buscar --perto-de Unamar
radar buscar -p "Rua Tal, 100, Peró" --raio 5

# esconder vagas cujo anúncio não informa o bairro
radar buscar -d 2 --somente-com-bairro

# outra cidade (sem distritos/bairros cadastrados, filtra só pela cidade)
radar buscar -c "Macaé" --uf RJ

# listar distritos e bairros conhecidos / fontes consultadas
radar regioes
radar fontes
```

Outras opções: `--fontes gupy,catho` (escolhe sites), `--sem-detalhes` (mais rápido, acha menos bairros),
`--paginas N`, `--json arquivo.json`. Veja `radar buscar --help`.

## Fontes

| Fonte | Como lê | Observação |
| --- | --- | --- |
| Gupy | JSON embutido na página de busca | Ignora vagas encerradas ou com prazo vencido |
| InfoJobs | HTML da busca | Só a 1ª página (as demais são carregadas por JavaScript) |
| Catho | HTML da busca | |
| Trabalha Brasil | HTML da busca | A lista inclui cidades vizinhas; elas são descartadas |
| Vagas.com.br | HTML da busca | Só a 1ª página |

| BNE | JSON embutido na página | Informa home office e às vezes o bairro; mantém anúncios antigos no ar |

Indeed, Glassdoor, Jooble, Adzuna e Nube bloqueiam robôs (HTTP 403) e não são usados. O `robots.txt` do LinkedIn
proíbe robôs na listagem de vagas, então o radar só mostra um link para abrir a mesma busca no LinkedIn.

Anúncios publicados há mais de 180 dias são ignorados (alguns sites não tiram vagas preenchidas do ar).

**Cidades vizinhas** (`--vizinha NOME`, repetível, ou `--vizinhas` para todas; na interface, os botões em "Abre o leque", com Arraial do Cabo e Búzios marcados por padrão): a lista fica em `vizinhas:` no [regioes.yaml](src/radar/regioes.yaml). As vagas delas
aparecem agrupadas por cidade, da mais próxima para a mais distante. Com `--perto-de`, a distância usa o centro da cidade.

**Remotas** (`--remotas`): só entram vagas que o site marca como home office: Gupy (modalidade "remoto"), InfoJobs
(etiqueta "Home office") e BNE (campo de home office). A Catho não marca a modalidade de forma confiável e fica de fora.
Vagas de aprendiz remotas são raras, porque o programa costuma exigir atividade presencial.
O radar respeita o `robots.txt` de cada site, se identifica no User-Agent e espera 1 segundo entre requisições ao mesmo site.
Se um site mudar de layout ou sair do ar, os outros continuam e o terminal mostra um aviso.

## Como o bairro é descoberto

A maioria dos sites informa só a cidade. Para cada vaga, o radar abre o anúncio e lê o bloco
`JobPosting` (schema.org), que traz a descrição completa e, às vezes, o endereço com CEP. Depois procura, nesta ordem:

1. **Bairro no endereço, no título ou na descrição** (ex.: "Local: Unamar – Cabo Frio/RJ").
2. **Nome do distrito** no texto (ex.: "Tamoios"): define o distrito, mas não o bairro.
3. **CEP**, consultado no [ViaCEP](https://viacep.com.br) e guardado em cache. Aparece como "(pelo CEP)".
   O texto do anúncio tem prioridade, porque muitas empresas cadastram o CEP da sede ou um CEP genérico.

Nomes de bairro que também são palavras comuns ("Centro", "Passagem", "Dunas", "Palmeiras"...) estão marcados com
`ambiguo: true` e só contam com contexto: "bairro Centro", "Centro, Cabo Frio", "Rua X, 10 - Centro".

O resultado aparece **agrupado por localização**: uma tabela por distrito, com as vagas ordenadas por bairro,
e no fim as vagas cujo anúncio não informa o local. O CSV e o relatório HTML seguem a mesma ordem.

Ao filtrar por distrito ou bairro:

- **Tabelas por distrito**: local confirmado dentro do filtro.
- **Em Cabo Frio, mas o anúncio não diz o bairro**: podem ou não ser na região. Use `--somente-com-bairro` para escondê-las.

Vagas com local confirmado fora do filtro são ocultadas.

## Vagas perto de você

Com `--perto-de`, o resultado vira uma lista única ordenada pela distância em linha reta até o ponto informado:

- **Ponto de referência**: o nome de um bairro cadastrado usa as coordenadas do `regioes.yaml`; qualquer outro texto
  (ex.: "Rua Tal, 100, Peró") é procurado no [OpenStreetMap](https://nominatim.openstreetmap.org).
- **Local da vaga**: se o anúncio traz o endereço, ele é localizado no mapa; senão, usa o centro do bairro
  (aparece com `~`). Se o endereço cair a mais de 4 km do bairro identificado (ruas com nome repetido, como
  "Avenida Central"), vale o bairro.
- Vagas sem bairro nem endereço vão para uma seção "Sem como calcular a distância".
- `--raio 5` esconde as vagas a mais de 5 km.

As consultas ao OpenStreetMap ficam em cache no histórico e respeitam o limite de 1 por segundo do serviço.

Dos 72 bairros de Cabo Frio, 50 têm coordenadas. Elas foram tiradas do OpenStreetMap e conferidas contra o distrito.
Os outros 22 (ex.: Braga, Palmeiras, Long Beach, Santa Margarida) não foram encontrados com confiança. Para incluí-los,
adicione `coordenadas: [latitude, longitude]` no YAML (no Google Maps, clique com o botão direito no lugar para copiar).

## Editar regiões

O arquivo é [src/radar/regioes.yaml](src/radar/regioes.yaml) (ou outro, com `--regioes caminho.yaml`).
A lista de bairros de Cabo Frio veio da base de CEPs dos Correios: os bairros que os Correios marcam com "(Tamoios)"
estão no 2º Distrito.

Para que pontos de referência contem como bairro, adicione apelidos. Exemplo:

```yaml
        - nome: Jardim Esperança
          apelidos: ["Jd. Esperança", "Shopping X"]
```

Para adicionar outra cidade com distritos e bairros, copie o bloco `cabo-frio` e ajuste.

## Histórico

As vagas já exibidas ficam em `~/.radar-aprendiz/radar.db` (SQLite). Por isso o radar marca as **novas**, e `--novas` mostra só elas.
`radar limpar-historico` apaga esse registro.

## Testes

```powershell
pytest
```

Os testes não acessam a internet: usam trechos de HTML no formato real de cada site.
