-- =====================================================================
-- Modelo físico (SQLite) — ICMS x Frota de veículos dos municípios de GO
-- Projeto: Inteligência Fiscal e Socioeconômica com Dados Abertos de Goiás
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS vw_analise_municipio;
DROP TABLE IF EXISTS repasse_icms_mensal;
DROP TABLE IF EXISTS frota_municipio;
DROP TABLE IF EXISTS municipio;

-- Dimensão: um registro por município goiano (chave = nome padronizado)
CREATE TABLE municipio (
    id_municipio INTEGER PRIMARY KEY,
    nome         TEXT    NOT NULL UNIQUE
);

-- Fato 1: repasses de ICMS consolidados por município e mês (fonte: SEFAZ-GO)
CREATE TABLE repasse_icms_mensal (
    id_municipio      INTEGER NOT NULL REFERENCES municipio(id_municipio),
    ano_mes           INTEGER NOT NULL CHECK (ano_mes BETWEEN 200001 AND 209912),
    valor_bruto       REAL    NOT NULL CHECK (valor_bruto >= 0),
    deducao_fundeb    REAL    NOT NULL CHECK (deducao_fundeb >= 0),
    valor_creditado   REAL    NOT NULL CHECK (valor_creditado >= 0),
    qtd_repasses      INTEGER NOT NULL CHECK (qtd_repasses > 0),
    PRIMARY KEY (id_municipio, ano_mes)
);

-- Fato 2: foto da frota de veículos por município (fonte: DETRAN-GO)
CREATE TABLE frota_municipio (
    id_municipio  INTEGER NOT NULL REFERENCES municipio(id_municipio),
    ref_ano_mes   INTEGER NOT NULL,
    frota_ativa   INTEGER NOT NULL CHECK (frota_ativa   >= 0),
    frota_inativa INTEGER NOT NULL CHECK (frota_inativa >= 0),
    passeio       INTEGER NOT NULL CHECK (passeio >= 0),
    moto          INTEGER NOT NULL CHECK (moto    >= 0),
    carga         INTEGER NOT NULL CHECK (carga   >= 0),
    onibus        INTEGER NOT NULL CHECK (onibus  >= 0),
    outros        INTEGER NOT NULL CHECK (outros  >= 0),
    PRIMARY KEY (id_municipio, ref_ano_mes)
);

CREATE INDEX idx_repasse_ano_mes ON repasse_icms_mensal(ano_mes);

-- Visão analítica: ICMS anual x frota (granularidade municipal) — consumida pelo painel
CREATE VIEW vw_analise_municipio AS
SELECT  m.id_municipio,
        m.nome                         AS municipio,
        SUM(r.valor_bruto)             AS icms_bruto_anual,
        SUM(r.deducao_fundeb)          AS icms_fundeb_anual,
        SUM(r.valor_creditado)         AS icms_creditado_anual,
        f.frota_ativa, f.frota_inativa, f.passeio, f.moto, f.carga, f.onibus, f.outros
FROM    municipio m
JOIN    repasse_icms_mensal r ON r.id_municipio = m.id_municipio
JOIN    frota_municipio     f ON f.id_municipio = m.id_municipio
GROUP BY m.id_municipio;
