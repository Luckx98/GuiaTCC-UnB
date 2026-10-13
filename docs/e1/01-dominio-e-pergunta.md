# Domínio e pergunta de gestão

## Problema

A capacidade de leitos do SUS (CNES) e a demanda por internação (SIH/SUS) são acompanhadas em sistemas separados. A falta de leito, principalmente nos picos sazonais (doenças respiratórias no inverno, dengue no verão), só é percebida quando já está acontecendo.

## Pergunta de gestão

> Entre 2021 e 2025, em quais semanas do ano a ocupação estimada de leitos SUS (paciente-dia ÷ leitos cadastrados) ultrapassou 85% em cada região de saúde do DF, e quais causas de internação (CID) concentravam esse excesso?

- **Sujeito:** regiões de saúde do Distrito Federal (7 regiões).
- **Medida:** ocupação estimada = paciente-dia da semana ÷ (leitos SUS cadastrados × 7).
- **Recorte:** semanas de 2021 a 2025, anos completos; o ano corrente entra marcado como provisório.
- **Persona:** gestor da Secretaria de Saúde do DF e da Central de Regulação de Leitos.
- **Uso (E4):** lista mensal de hospitais e regiões acima de 85%, enviada à Central de Regulação.

Goiás entra na carga porque parte dos pacientes internados no DF mora no Entorno, e porque as regiões de saúde de GO servem de comparação.

## Perguntas que a plataforma também deve responder

1. Qual a ocupação estimada de cada hospital por mês e por semana?
2. Quais regiões perderam leitos SUS enquanto as internações cresceram?
3. Existe sazonalidade nas internações por causa? Os picos coincidem com falta de leito?
4. Quantos pacientes são internados fora do município ou da UF de residência?
5. Hospitais que ganharam habilitação de UTI passaram a internar mais casos de alta complexidade?
6. Qual o tempo médio de permanência por tipo de leito e hospital?
7. Qual o custo médio por internação por hospital e procedimento, e como evoluiu?
8. Hospitais que mudaram de gestão (municipal ↔ estadual) mudaram de desempenho?

## Fontes

| Fonte | Conteúdo | Publicação | Acesso |
| --- | --- | --- | --- |
| SIH/SUS — AIH reduzida (RD) | uma linha por internação paga pelo SUS | mensal, por UF e competência | `ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RD{UF}{AAMM}.dbc` |
| CNES — Estabelecimentos (ST) | cadastro de estabelecimentos | mensal | `.../CNES/200508_/Dados/ST/` |
| CNES — Leitos (LT) | leitos existentes, SUS e não SUS por tipo | mensal | `.../CNES/200508_/Dados/LT/` |
| Tabelas auxiliares do SIH | CID-10, municípios, regiões de saúde | eventual | `.../SIHSUS/200801_/Auxiliar/TAB_SIH.zip` |
| Região de saúde dos hospitais do DF | tabela curada pela Squad | — | `dados/referencia/estabelecimento_regiao_saude_df.csv` |

Todas as fontes do DATASUS são públicas, gratuitas e sem login. A chave de junção entre elas é o código CNES do estabelecimento.

**Região de saúde no DF.** O DF é um único município (530010) nas fontes, e o campo de região do CNES é texto livre, quase sempre vazio. A região de cada hospital vem, por isso, de uma tabela curada pela Squad. Nome e bairro vêm da API pública do CNES, e a região segue a composição da SES-DF, com os códigos do DATASUS (53002 a 53008). Em GO, a região vem do município.

**Licença.** Os dados do Portal de Dados Abertos do SUS são publicados sob Creative Commons Atribuição-SemDerivações 3.0. O projeto cita a fonte, publica código e agregados, e não republica a base modificada.
