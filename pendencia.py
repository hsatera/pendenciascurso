import streamlit as st
import pandas as pd
import numpy as np
import io
import tempfile
import os
from datetime import datetime

st.set_page_config(page_title="Monitoramento de Alunos", layout="wide")
st.title("📊 Sistema de Monitoramento de Alunos")
st.markdown("---")

# Função para carregar e processar o arquivo Excel (versão robusta)
@st.cache_data
def processar_excel(uploaded_file):
    try:
        # Criar um arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        try:
            # Primeiro, tentar detectar o formato
            file_size = os.path.getsize(tmp_path)
            st.info(f"📏 Tamanho do arquivo: {file_size / 1024:.2f} KB")
            
            # Tentar diferentes métodos de leitura
            df = None
            error_messages = []
            
            # Método 1: Tentar com engine automática
            try:
                df = pd.read_excel(
                    tmp_path, 
                    sheet_name="Monitoramento", 
                    header=None,
                    engine=None  # Pandas tentará detectar automaticamente
                )
                st.success("✅ Arquivo lido com engine automática")
            except Exception as e1:
                error_messages.append(f"Engine automática: {str(e1)}")
                
                # Método 2: Tentar com xlrd especificamente para .xls
                try:
                    df = pd.read_excel(
                        tmp_path, 
                        sheet_name="Monitoramento", 
                        header=None,
                        engine='xlrd'
                    )
                    st.success("✅ Arquivo lido com engine xlrd")
                except Exception as e2:
                    error_messages.append(f"Engine xlrd: {str(e2)}")
                    
                    # Método 3: Tentar ler como .xlsx mesmo se for .xls
                    try:
                        # Tentar forçar a leitura como .xlsx
                        df = pd.read_excel(
                            tmp_path, 
                            sheet_name="Monitoramento", 
                            header=None,
                            engine='openpyxl'
                        )
                        st.success("✅ Arquivo lido como .xlsx com openpyxl")
                    except Exception as e3:
                        error_messages.append(f"Engine openpyxl: {str(e3)}")
                        
                        # Método 4: Tentar ler o arquivo binário diretamente
                        try:
                            from io import BytesIO
                            # Reabrir o arquivo em modo binário
                            with open(tmp_path, 'rb') as f:
                                file_content = f.read()
                            
                            # Tentar detectar se é realmente um arquivo Excel
                            if file_content[:8] == b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1':
                                st.info("📄 Arquivo reconhecido como OLE2 (formato .xls antigo)")
                            
                            # Usar BytesIO para leitura
                            excel_data = BytesIO(file_content)
                            df = pd.read_excel(
                                excel_data, 
                                sheet_name="Monitoramento", 
                                header=None
                            )
                            st.success("✅ Arquivo lido via BytesIO")
                        except Exception as e4:
                            error_messages.append(f"BytesIO: {str(e4)}")
                            st.error("❌ Todas as tentativas de leitura falharam")
                            for i, msg in enumerate(error_messages, 1):
                                st.write(f"{i}. {msg}")
                            return None, None
            
            # Verificar se o DataFrame foi carregado
            if df is None or df.empty:
                st.error("❌ O arquivo está vazio ou não pôde ser lido")
                return None, None
            
            st.info(f"✅ Dimensões do arquivo: {df.shape[0]} linhas × {df.shape[1]} colunas")
            
            # Mostrar prévia das primeiras linhas para debug
            with st.expander("🔍 Prévia dos dados brutos (para debug)"):
                st.dataframe(df.head(10))
            
            # Processar os cabeçalhos dos módulos (primeira linha)
            modulos_info = []
            current_modulo = None
            
            # A primeira linha (índice 0) contém os nomes dos módulos
            for idx, col in enumerate(df.columns):
                cell_value = df.iloc[0, idx] if idx < len(df.columns) else None
                
                if pd.notna(cell_value) and isinstance(cell_value, str) and "Módulo" in cell_value:
                    current_modulo = cell_value
                elif pd.isna(cell_value) and current_modulo:
                    # Continua no mesmo módulo
                    pass
                else:
                    current_modulo = None
                
                if current_modulo:
                    modulos_info.append(current_modulo)
                else:
                    modulos_info.append(None)
            
            # A segunda linha (índice 1) contém os tipos de avaliação
            tipos_avaliacao = df.iloc[1].tolist() if len(df) > 1 else [""] * len(df.columns)
            
            # Criar nomes de colunas combinados
            novos_nomes = []
            for i in range(len(df.columns)):
                if i < 5:  # Primeiras 5 colunas são informações básicas
                    nome_base = str(df.columns[i]) if i < len(df.columns) else f"Col{i}"
                    nome_tipo = tipos_avaliacao[i] if i < len(tipos_avaliacao) and pd.notna(tipos_avaliacao[i]) else nome_base
                    novos_nomes.append(nome_tipo)
                else:
                    modulo = modulos_info[i] if modulos_info[i] else "Sem Módulo"
                    tipo = tipos_avaliacao[i] if i < len(tipos_avaliacao) and pd.notna(tipos_avaliacao[i]) else "Sem Tipo"
                    novos_nomes.append(f"{modulo} | {tipo}")
            
            # Pular as duas primeiras linhas de cabeçalho
            df_data = df.iloc[2:].reset_index(drop=True)
            df_data.columns = novos_nomes
            
            # Renomear colunas básicas
            if len(df_data.columns) >= 5:
                df_data = df_data.rename(columns={
                    df_data.columns[0]: "Aluno",
                    df_data.columns[1]: "Equipe",
                    df_data.columns[2]: "Supervisor",
                    df_data.columns[3]: "Tutor",
                    df_data.columns[4]: "Último acesso na plataforma"
                })
            
            # Extrair informações dos módulos para análise
            modulos_data = []
            for col in df_data.columns[5:]:  # Ignorar as 5 primeiras colunas
                if "|" in col:
                    partes = col.split("|")
                    if len(partes) == 2:
                        modulo = partes[0].strip()
                        tipo = partes[1].strip()
                        modulos_data.append({
                            "coluna": col,
                            "modulo": modulo,
                            "tipo_avaliacao": tipo,
                            "modulo_numero": int(modulo.split()[1]) if len(modulo.split()) > 1 and modulo.split()[1].isdigit() else 0
                        })
            
            modulos_df = pd.DataFrame(modulos_data).sort_values("modulo_numero")
            
            return df_data, modulos_df
            
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("💡 Dicas para resolver:")
        st.write("1. Tente salvar o arquivo como .xlsx (Excel mais recente)")
        st.write("2. Verifique se o arquivo não está corrompido")
        st.write("3. Tente abrir e salvar novamente no Excel")
        return None, None

# Função para extrair as atividades especiais (AG, NA)
def extrair_atividades_especiais(df):
    atividades_especiais = []
    
    for col in df.columns[5:]:  # Colunas de módulos
        if "|" in col:
            for idx, valor in df[col].items():
                if pd.notna(valor):
                    valor_str = str(valor).strip().upper()
                    if valor_str in ["AG", "NA"]:
                        atividades_especiais.append({
                            "Aluno": df.loc[idx, "Aluno"] if "Aluno" in df.columns else "Desconhecido",
                            "Tutor": df.loc[idx, "Tutor"] if "Tutor" in df.columns else "Desconhecido",
                            "Módulo": col.split("|")[0].strip(),
                            "Tipo Avaliação": col.split("|")[1].strip(),
                            "Status": valor_str,
                            "Valor": valor_str
                        })
    
    return pd.DataFrame(atividades_especiais)

# Interface principal
uploaded_file = st.file_uploader("📂 Carregar arquivo Excel de monitoramento", type=["xls", "xlsx"])

if uploaded_file is not None:
    st.info(f"📁 Arquivo carregado: {uploaded_file.name}")
    
    # Botão para converter para .xlsx se necessário
    if uploaded_file.name.endswith('.xls'):
        st.warning("⚠️ Arquivo .xls detectado. Se houver problemas, tente:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔧 Tentar reparar leitura"):
                st.info("Tentando métodos alternativos de leitura...")
    
    df, modulos_info = processar_excel(uploaded_file)
    
    if df is not None and modulos_info is not None:
        st.success(f"✅ Arquivo processado com sucesso! {len(df)} alunos encontrados.")
        
        # Sidebar com filtros
        with st.sidebar:
            st.header("🔍 Filtros")
            
            # Filtro por Tutor
            tutores = sorted(df["Tutor"].dropna().unique()) if "Tutor" in df.columns else []
            tutor_selecionado = st.multiselect("Selecione o(s) Tutor(es):", tutores, default=[])
            
            # Filtro por Equipe
            equipes = sorted(df["Equipe"].dropna().unique()) if "Equipe" in df.columns else []
            equipe_selecionada = st.multiselect("Selecione a(s) Equipe(s):", equipes, default=[])
            
            # Filtro por Status de Atividade
            st.subheader("Filtrar por Status")
            filtrar_ag = st.checkbox("Mostrar apenas AG", value=False)
            filtrar_na = st.checkbox("Mostrar apenas NA", value=False)
            
            # Filtro por Módulo
            st.subheader("Filtrar por Módulo")
            modulos = sorted(modulos_info["modulo"].unique())
            modulo_selecionado = st.multiselect("Selecione o(s) Módulo(s):", modulos, default=[])
            
            # Filtro por Tipo de Avaliação
            tipos = sorted(modulos_info["tipo_avaliacao"].unique())
            tipo_selecionado = st.multiselect("Selecione o(s) Tipo(s) de Avaliação:", tipos, default=[])
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if tutor_selecionado and "Tutor" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["Tutor"].isin(tutor_selecionado)]
        
        if equipe_selecionada and "Equipe" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["Equipe"].isin(equipe_selecionada)]
        
        # Tabs para diferentes visualizações
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Visão Geral", 
            "🚨 Atividades AG/NA", 
            "📊 Análise por Módulo", 
            "👤 Detalhes por Aluno"
        ])
        
        with tab1:
            st.subheader("📋 Visão Geral dos Alunos")
            
            # Mostrar estatísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Alunos", len(df_filtrado))
            with col2:
                tutores_count = len(df_filtrado["Tutor"].unique()) if "Tutor" in df_filtrado.columns else 0
                st.metric("Total de Tutores", tutores_count)
            with col3:
                equipes_count = len(df_filtrado["Equipe"].unique()) if "Equipe" in df_filtrado.columns else 0
                st.metric("Total de Equipes", equipes_count)
            with col4:
                # Contar AGs e NAs
                atividades_especiais = extrair_atividades_especiais(df_filtrado)
                total_ag = len(atividades_especiais[atividades_especiais["Status"] == "AG"])
                total_na = len(atividades_especiais[atividades_especiais["Status"] == "NA"])
                st.metric("AG/NA", f"{total_ag}/{total_na}")
            
            # Tabela de alunos filtrada
            st.dataframe(
                df_filtrado,
                use_container_width=True,
                height=400
            )
            
            # Opção para download
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Baixar dados filtrados (CSV)",
                data=csv,
                file_name="alunos_filtrados.csv",
                mime="text/csv"
            )
        
        with tab2:
            st.subheader("🚨 Atividades com Status AG ou NA")
            
            atividades_especiais = extrair_atividades_especiais(df_filtrado)
            
            if len(atividades_especiais) > 0:
                # Filtros adicionais para esta aba
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    status_filtro = st.multiselect(
                        "Status:",
                        ["AG", "NA"],
                        default=["AG", "NA"]
                    )
                
                with col_f2:
                    if len(atividades_especiais) > 0:
                        modulos_filtro = st.multiselect(
                            "Módulos:",
                            sorted(atividades_especiais["Módulo"].unique()),
                            default=sorted(atividades_especiais["Módulo"].unique())
                        )
                
                # Aplicar filtros
                atividades_filtradas = atividades_especiais.copy()
                if status_filtro:
                    atividades_filtradas = atividades_filtradas[atividades_filtradas["Status"].isin(status_filtro)]
                if 'modulos_filtro' in locals() and modulos_filtro:
                    atividades_filtradas = atividades_filtradas[atividades_filtradas["Módulo"].isin(modulos_filtro)]
                
                # Mostrar tabela
                st.dataframe(
                    atividades_filtradas,
                    use_container_width=True,
                    column_config={
                        "Aluno": st.column_config.TextColumn(width="large"),
                        "Tutor": st.column_config.TextColumn(width="medium"),
                        "Módulo": st.column_config.TextColumn(width="large"),
                        "Status": st.column_config.TextColumn(width="small"),
                        "Valor": st.column_config.TextColumn(width="small")
                    }
                )
                
                # Estatísticas
                st.subheader("📈 Estatísticas das Atividades AG/NA")
                
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    ag_count = len(atividades_filtradas[atividades_filtradas["Status"] == "AG"])
                    st.metric("Total AG", ag_count)
                
                with col_a2:
                    na_count = len(atividades_filtradas[atividades_filtradas["Status"] == "NA"])
                    st.metric("Total NA", na_count)
                
                with col_a3:
                    st.metric("Total Geral", len(atividades_filtradas))
                
                # Gráfico de distribuição por módulo
                if len(atividades_filtradas) > 0:
                    st.subheader("📊 Distribuição por Módulo")
                    dist_modulo = atividades_filtradas.groupby(["Módulo", "Status"]).size().reset_index(name="Quantidade")
                    if not dist_modulo.empty:
                        pivot_data = dist_modulo.pivot(index="Módulo", columns="Status", values="Quantidade").fillna(0)
                        st.bar_chart(pivot_data)
                
                # Download dos dados
                csv_atividades = atividades_filtradas.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar atividades AG/NA (CSV)",
                    data=csv_atividades,
                    file_name="atividades_ag_na.csv",
                    mime="text/csv"
                )
            else:
                st.info("✅ Nenhuma atividade com status AG ou NA encontrada nos filtros atuais.")
        
        with tab3:
            st.subheader("📊 Análise por Módulo")
            
            if len(modulos_info) > 0:
                # Selecionar módulo para análise detalhada
                modulo_analise = st.selectbox(
                    "Selecione um módulo para análise detalhada:",
                    modulos_info["modulo"].unique()
                )
                
                if modulo_analise:
                    # Encontrar colunas deste módulo
                    colunas_modulo = modulos_info[modulos_info["modulo"] == modulo_analise]["coluna"].tolist()
                    
                    if colunas_modulo:
                        # Dados do módulo selecionado
                        dados_modulo = df_filtrado[["Aluno", "Tutor", "Equipe"] + colunas_modulo]
                        
                        st.write(f"### Dados do {modulo_analise}")
                        st.dataframe(dados_modulo, use_container_width=True)
                        
                        # Análise estatística
                        st.write("### 📈 Análise Estatística")
                        
                        # Converter valores numéricos
                        stats_data = []
                        for col in colunas_modulo:
                            if col in dados_modulo.columns:
                                # Tentar converter para numérico, manter strings onde não for possível
                                dados_modulo[col] = pd.to_numeric(dados_modulo[col], errors='coerce')
                                valores = dados_modulo[col].dropna()
                                
                                if len(valores) > 0:
                                    if "|" in col:
                                        tipo = col.split("|")[1].strip()
                                    else:
                                        tipo = col
                                    
                                    stats_data.append({
                                        "Tipo Avaliação": tipo,
                                        "Média": f"{valores.mean():.2f}",
                                        "Mediana": f"{valores.median():.2f}",
                                        "Mínimo": f"{valores.min():.2f}",
                                        "Máximo": f"{valores.max():.2f}",
                                        "Desvio Padrão": f"{valores.std():.2f}",
                                        "Total Avaliados": len(valores)
                                    })
                        
                        if stats_data:
                            stats_df = pd.DataFrame(stats_data)
                            st.dataframe(stats_df, use_container_width=True)
                        else:
                            st.info("Não há dados numéricos para análise estatística neste módulo.")
                    else:
                        st.warning(f"Nenhuma coluna encontrada para o módulo {modulo_analise}")
            else:
                st.info("Nenhuma informação de módulo disponível.")
        
        with tab4:
            st.subheader("👤 Detalhes por Aluno")
            
            if len(df_filtrado) > 0:
                # Selecionar aluno
                aluno_selecionado = st.selectbox(
                    "Selecione um aluno:",
                    df_filtrado["Aluno"].unique()
                )
                
                if aluno_selecionado:
                    aluno_data = df_filtrado[df_filtrado["Aluno"] == aluno_selecionado].iloc[0]
                    
                    # Informações básicas
                    col_i1, col_i2, col_i3 = st.columns(3)
                    with col_i1:
                        st.info(f"**Aluno:** {aluno_data['Aluno']}")
                        if "Equipe" in aluno_data:
                            st.info(f"**Equipe:** {aluno_data['Equipe']}")
                    
                    with col_i2:
                        if "Supervisor" in aluno_data:
                            st.info(f"**Supervisor:** {aluno_data['Supervisor']}")
                        if "Tutor" in aluno_data:
                            st.info(f"**Tutor:** {aluno_data['Tutor']}")
                    
                    with col_i3:
                        if "Último acesso na plataforma" in aluno_data:
                            st.info(f"**Último acesso:** {aluno_data['Último acesso na plataforma']}")
                    
                    # Notas por módulo
                    st.subheader("📚 Desempenho por Módulo")
                    
                    notas_data = []
                    for col in df_filtrado.columns[5:]:  # Colunas de módulos
                        if "|" in col and col in aluno_data:
                            modulo = col.split("|")[0].strip()
                            tipo = col.split("|")[1].strip()
                            valor = aluno_data[col]
                            
                            if pd.notna(valor):
                                notas_data.append({
                                    "Módulo": modulo,
                                    "Tipo de Avaliação": tipo,
                                    "Nota/Status": str(valor)
                                })
                    
                    if notas_data:
                        notas_df = pd.DataFrame(notas_data)
                        st.dataframe(notas_df, use_container_width=True)
                    else:
                        st.warning("Nenhuma nota encontrada para este aluno.")
            else:
                st.info("Nenhum aluno disponível nos filtros atuais.")
        
        # Seção de métricas gerais
        st.sidebar.markdown("---")
        st.sidebar.subheader("📈 Métricas Gerais")
        
        # Calcular métricas
        total_alunos = len(df_filtrado)
        total_modulos = len(modulos_info["modulo"].unique()) if len(modulos_info) > 0 else 0
        
        # Contar atividades AG e NA
        atividades_especiais = extrair_atividades_especiais(df_filtrado)
        total_ag = len(atividades_especiais[atividades_especiais["Status"] == "AG"])
        total_na = len(atividades_especiais[atividades_especiais["Status"] == "NA"])
        
        st.sidebar.metric("Alunos Filtrados", total_alunos)
        st.sidebar.metric("Módulos", total_modulos)
        st.sidebar.metric("Atividades AG", total_ag)
        st.sidebar.metric("Atividades NA", total_na)
        
    else:
        st.error("❌ Não foi possível processar o arquivo. Veja as opções abaixo:")
        
        # Opções de solução
        with st.expander("🛠️ Soluções para arquivos problemáticos"):
            st.write("""
            ## Problemas comuns e soluções:
            
            **1. Arquivo .xls corrompido:**
            - Abra no Excel e salve como **.xlsx**
            - Tente usar "Reparar" no Excel
            
            **2. Problema de compatibilidade:**
            - O arquivo pode ser de uma versão muito antiga do Excel
            - Converta para .xlsx ou .csv
            
            **3. Formato não suportado:**
            - Verifique se o arquivo é realmente um Excel
            - Tente abrir com LibreOffice e exportar
            
            **4. Alternativa rápida:**
            - Use o Google Sheets para abrir e exportar como .xlsx
            """)
            
            # Opção para converter manualmente
            st.info("💡 **Dica rápida:**")
            st.write("1. Abra o arquivo no Excel")
            st.write("2. Vá em 'Arquivo' → 'Salvar Como'")
            st.write("3. Escolha 'Excel Workbook (*.xlsx)'")
            st.write("4. Tente carregar o novo arquivo aqui")
            
else:
    st.info("👆 Por favor, carregue um arquivo Excel (.xls ou .xlsx) para começar.")
    
    # Mostrar exemplo da estrutura esperada
    with st.expander("📋 Estrutura esperada do arquivo"):
        st.write("""
        ## Formato recomendado:
        - **.xlsx** (Excel moderno) - MELHOR OPÇÃO
        - .xls (Excel antigo) - pode ter problemas
        
        ## Estrutura esperada:
        
        1. **Primeira linha:** Nomes dos módulos 
           (ex: "Módulo 1 - Políticas Públicas de Saúde")
           
        2. **Segunda linha:** Tipos de avaliação 
           (ex: "Desafio", "Avaliação de Fórum", "Prova Online", "Nota Final")
           
        3. **Terceira linha em diante:** Dados dos alunos
        
        ## Colunas esperadas:
        - A: Aluno
        - B: Equipe
        - C: Supervisor
        - D: Tutor
        - E: Último acesso na plataforma
        - F em diante: Notas dos módulos
        
        ## Valores especiais:
        - **AG**: Aguardando avaliação
        - **NA**: Não disponível/ausente
        """)
