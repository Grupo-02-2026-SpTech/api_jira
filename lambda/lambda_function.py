    """
    lambda/lambda_function.py
    --------------------------
    AWS Lambda — Camada Silver da arquitetura medalhão.

    Trigger: S3 Event (PutObject) no bucket bronze-gp02
    - Recebe o arquivo stories_bronze_YYYY-MM-DD.csv
    - Aplica os mesmos tratamentos do pipeline/silver.py
    - Gera stories_silver_YYYY-MM-DD.csv
    - Faz upload para o bucket silver-gp02
    """

    import io
    import re
    import os
    import unicodedata
    import boto3
    import pandas as pd
    from datetime import datetime


    # ── Clientes AWS ───────────────────────────────────────────────────────────────

    s3 = boto3.client("s3")

    SILVER_BUCKET = "silver-gp02"

    # ── Valores padrão para nulos ──────────────────────────────────────────────────

    DEFAULTS = {
        "card_id":            "ID_DESCONHECIDO",
        "descricao":          "Sem descrição",
        "data_entrega":       "Sem data",
        "assignee":           "Não atribuído",
        "data_processamento": "Sem data",
    }

    # ── Normalização de caracteres especiais ───────────────────────────────────────

    CHAR_MAP = {
        "→": "->",
        "–": "-",
        "—": "-",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }


    def _normalizar_caracteres(texto: str) -> str:
        for char, substituto in CHAR_MAP.items():
            texto = texto.replace(char, substituto)
        normalizado = []
        for c in texto:
            cat = unicodedata.category(c)
            if cat.startswith(('L', 'N', 'P', 'Z')) or c in '|:.;,!?@#$%&*()-_+=[]{}<>\n\r\t':
                normalizado.append(c)
            else:
                normalizado.append(' ')
        return re.sub(r' {2,}', ' ', ''.join(normalizado)).strip()


    # ── Normalização de Datas ──────────────────────────────────────────────────────

    def _parse_date(value, campo: str = "") -> str:
        default = DEFAULTS.get(campo, "Sem data")

        if pd.isna(value) or str(value).strip() == "":
            return default
        try:
            parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
            if pd.isna(parsed):
                parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
            if pd.isna(parsed):
                print(f"[Silver] Data inválida no campo '{campo}': '{value}' — usando '{default}'.")
                return default

            if campo == "data_entrega" and parsed.date() < datetime.today().date():
                print(f"[Silver] data_entrega '{parsed.strftime('%d/%m/%Y')}' é anterior a hoje.")

            return parsed.strftime("%d/%m/%Y")
        except Exception:
            return default


    # ── Normalização de Texto ──────────────────────────────────────────────────────

    def _clean_text(value, campo: str = "") -> str:
        default = DEFAULTS.get(campo, "")
        if pd.isna(value) or str(value).strip() == "":
            return default
        texto = _normalizar_caracteres(str(value).strip())
        return texto if texto else default


    def _normalizar_assignee(value) -> str:
        default = DEFAULTS["assignee"]
        if pd.isna(value) or str(value).strip() == "":
            return default
        texto = _normalizar_caracteres(str(value).strip())
        if not texto:
            return default
        return texto.title()


    # ── Validação de card_id ───────────────────────────────────────────────────────

    def _validar_card_id(value) -> str:
        default = DEFAULTS["card_id"]
        if pd.isna(value) or str(value).strip() == "":
            print(f"[Silver] card_id vazio encontrado — usando '{default}'.")
            return default
        valor = str(value).strip()
        if not valor.isdigit():
            print(f"[Silver] card_id não numérico: '{valor}' — mantendo valor original.")
        return valor


    # ── Reformatação da Descrição ──────────────────────────────────────────────────

    def _reformatar_descricao(texto: str) -> str:
        linhas = [l.strip() for l in re.split(r"[\r\n]+", texto)]
        linhas = [l for l in linhas if l]

        cabecalho   = []
        historia    = []
        jornada     = {}
        etapa_atual = None
        modo        = "cabecalho"

        MARCADORES_HISTORIA = re.compile(r"^(Como |Quero |Para )", re.IGNORECASE)
        ETAPA_NUMERADA      = re.compile(r"^(\d+)\.\s+(.+)")
        BULLET              = re.compile(r"^[-•]\s+(.+)")

        for linha in linhas:
            if re.search(r"jornada funcional", linha, re.IGNORECASE):
                modo = "jornada"
                continue
            if re.search(r"^história$", linha, re.IGNORECASE):
                modo = "historia"
                continue
            if modo != "jornada" and MARCADORES_HISTORIA.match(linha):
                modo = "historia"

            if modo == "cabecalho":
                cabecalho.append(linha)
            elif modo == "historia":
                historia.append(linha)
            elif modo == "jornada":
                match_etapa  = ETAPA_NUMERADA.match(linha)
                match_bullet = BULLET.match(linha)

                if match_etapa:
                    num          = int(match_etapa.group(1))
                    titulo       = match_etapa.group(2).strip().rstrip(":")
                    etapa_atual  = num
                    jornada[num] = {"titulo": titulo, "itens": []}
                elif match_bullet and etapa_atual is not None:
                    item = match_bullet.group(1).strip()
                    if item:
                        jornada[etapa_atual]["itens"].append(item)
                elif etapa_atual is not None and linha:
                    jornada[etapa_atual]["itens"].append(linha)

        blocos = []

        if cabecalho:
            blocos.append(" | ".join(cabecalho))
        if historia:
            historia_texto = re.sub(r"\s{2,}", " ", " ".join(historia))
            blocos.append(historia_texto)
        for num in sorted(jornada.keys()):
            etapa  = jornada[num]
            titulo = etapa["titulo"]
            itens  = etapa["itens"]
            bloco  = f"{num}. {titulo}: {' | '.join(itens)}" if itens else f"{num}. {titulo}"
            blocos.append(bloco)

        resultado = re.sub(r" {2,}", " ", " | ".join(blocos))
        return resultado.strip()


    def _processar_descricao(value) -> str:
        default = DEFAULTS["descricao"]
        if pd.isna(value) or str(value).strip() == "":
            return default
        texto = _normalizar_caracteres(str(value).strip())
        if not texto:
            return default
        return _reformatar_descricao(texto)


    # ── Processamento Silver ───────────────────────────────────────────────────────

    def _process_stories(df: pd.DataFrame) -> pd.DataFrame:
        print("[Silver] Aplicando transformações e qualidade de dados...")

        for col, default in DEFAULTS.items():
            if col not in df.columns:
                print(f"[Silver] Coluna '{col}' ausente na Bronze — preenchendo com '{default}'.")
                df[col] = default

        total_antes = len(df)

        df["card_id"]            = df["card_id"].apply(_validar_card_id)
        df["descricao"]          = df["descricao"].apply(_processar_descricao)
        df["data_entrega"]       = df["data_entrega"].apply(lambda v: _parse_date(v, "data_entrega"))
        df["assignee"]           = df["assignee"].apply(_normalizar_assignee)
        df["data_processamento"] = df["data_processamento"].apply(lambda v: _parse_date(v, "data_processamento"))

        invalidos = df[df["card_id"] == DEFAULTS["card_id"]]
        if not invalidos.empty:
            print(f"[Silver] {len(invalidos)} registro(s) com card_id inválido removido(s).")
            df = df[df["card_id"] != DEFAULTS["card_id"]]

        df = df.sort_values("data_processamento", ascending=False, na_position="last")
        df = df.drop_duplicates(subset=["card_id"], keep="first")
        df = df.sort_values("card_id").reset_index(drop=True)

        total_depois = len(df)
        print(f"[Silver] {total_depois} stories únicas após deduplicação (removidas: {total_antes - total_depois}).")
        return df


    # ── Handler do Lambda ──────────────────────────────────────────────────────────

    def lambda_handler(event, context):
        """
        Disparado por um evento S3 PutObject no bucket bronze-gp02.
        Espera receber um arquivo no padrão: bronze/stories_bronze_YYYY-MM-DD.csv
        """

        # 1. Extrai bucket e chave do evento S3
        record     = event["Records"][0]
        src_bucket = record["s3"]["bucket"]["name"]
        src_key    = record["s3"]["object"]["key"]  # ex: bronze/stories_bronze_2026-04-05.csv

        print(f"[Lambda] Arquivo recebido: s3://{src_bucket}/{src_key}")

        # 2. Valida se o arquivo segue o padrão esperado
        filename = os.path.basename(src_key)  # stories_bronze_2026-04-05.csv

        match = re.match(r"stories_bronze_(\d{4}-\d{2}-\d{2})\.csv$", filename)
        if not match:
            print(f"[Lambda] Arquivo '{filename}' não segue o padrão esperado. Ignorando.")
            return {"statusCode": 200, "body": "Arquivo ignorado."}

        data_str = match.group(1)  # ex: 2026-04-05

        # 3. Baixa o CSV Bronze direto do S3 para memória
        print(f"[Lambda] Baixando '{src_key}' do bucket '{src_bucket}'...")
        response = s3.get_object(Bucket=src_bucket, Key=src_key)
        conteudo = response["Body"].read().decode("utf-8")

        df_bronze = pd.read_csv(io.StringIO(conteudo), dtype=str, sep=None, engine="python")
        print(f"[Lambda] Bronze carregada: {len(df_bronze)} linhas.")

        # 4. Aplica transformações Silver
        df_silver = _process_stories(df_bronze)

        # 5. Serializa o DataFrame Silver para CSV em memória
        buffer = io.StringIO()
        df_silver.to_csv(buffer, index=False, encoding="utf-8-sig", sep=",", quoting=1)
        csv_bytes = buffer.getvalue().encode("utf-8-sig")

        # 6. Define o nome do arquivo Silver com a mesma data do Bronze
        silver_filename = f"stories_silver_{data_str}.csv"
        silver_key      = f"silver/{silver_filename}"

        # 7. Faz upload para o bucket silver-gp02
        print(f"[Lambda] Enviando '{silver_filename}' para s3://{SILVER_BUCKET}/{silver_key}...")
        s3.put_object(
            Bucket=SILVER_BUCKET,
            Key=silver_key,
            Body=csv_bytes,
            ContentType="text/csv"
        )

        print(f"[Lambda] ✅ Pipeline Silver concluída! → s3://{SILVER_BUCKET}/{silver_key}")

        return {
            "statusCode": 200,
            "body": f"Silver gerada com sucesso: {silver_key}"
        }
