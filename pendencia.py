import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime

st.set_page_config(page_title="Monitoramento de Alunos", layout="wide")
st.title("📊 Sistema de Monitoramento de Alunos")
st.markdown("---")

# Função para carregar e processar o arquivo Excel
@st.cache_data
def processar_excel(uploaded_file):
    try:
        # Ler o arquivo Excel
        df = pd.read_excel(uploaded_file, sheet_name="Monitoramento")
        
        # Identificar os cabeçalhos dos módulos (primeira linha)
        modulos_info = []
        current_modulo = None
        
        # A primeira linha contém os nomes dos módulos
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
        
        # A segunda linha contém os tipos de avaliação
        tipos_avaliacao = df.iloc[1].tolist() if len(df) > 1 else [""] * len(df.columns)
        
        # Criar nomes de colunas combinados
        novos_nomes = []
        for i in range(len(df.columns)):
            if i < 5:  # Primeiras 5 colunas são informações básicas
                novos_nomes.append(tipos_avaliacao[i] if pd.notna(tipos_avaliacao[i]) else df.columns[i])
            else:
                modulo = modulos_info[i] if modulos_info[i] else "Sem Módulo"
                tipo = tipos_avaliacao[i] if pd.notna(tipos_avaliacao[i]) else "Sem Tipo"
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
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
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
                            "Aluno": df.loc[idx, "Aluno"],
                            "Tutor": df.loc[idx, "Tutor"],
                            "Módulo": col.split("|")[0].strip(),
                            "Tipo Avaliação": col.split("|")[1].strip(),
                            "Status": valor_str,
                            "Valor": valor_str
                        })
    
    return pd.DataFrame(atividades_especiais)

# Interface principal
uploaded_file = st.file_uploader("📂 Carregar arquivo Excel de monitoramento", type=["xls", "xlsx"])

if uploaded_file is not None:
    df, modulos_info = processar_excel(uploaded_file)
    
    if df is not None and modulos_info is not None:
        st.success(f"✅ Arquivo carregado com sucesso! {len(df)} alunos encontrados.")
        
        # Sidebar com filtros
        with st.sidebar:
            st.header("🔍 Filtros")
            
            # Filtro por Tutor
            tutores = sorted(df["Tutor"].dropna().unique())
            tutor_selecionado = st.multiselect("Selecione o(s) Tutor(es):", tutores, default=[])
            
            # Filtro por Equipe
            equipes = sorted(df["Equipe"].dropna().unique())
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
        
        if tutor_selecionado:
            df_filtrado = df_filtrado[df_filtrado["Tutor"].isin(tutor_selecionado)]
        
        if equipe_selecionada:
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
                st.metric("Total de Tutores", len(df_filtrado["Tutor"].unique()))
            with col3:
                st.metric("Total de Equipes", len(df_filtrado["Equipe"].unique()))
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
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
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
                st.subheader("📊 Distribuição por Módulo")
                dist_modulo = atividades_filtradas.groupby(["Módulo", "Status"]).size().reset_index(name="Quantidade")
                st.bar_chart(dist_modulo.pivot(index="Módulo", columns="Status", values="Quantidade").fillna(0))
                
                # Download dos dados
                csv_atividades = atividades_filtradas.to_csv(index=False).encode('utf-8')
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
            
            # Selecionar módulo para análise detalhada
            modulo_analise = st.selectbox(
                "Selecione um módulo para análise detalhada:",
                modulos_info["modulo"].unique()
            )
            
            if modulo_analise:
                # Encontrar colunas deste módulo
                colunas_modulo = modulos_info[modulos_info["modulo"] == modulo_analise]["coluna"].tolist()
                
                # Dados do módulo selecionado
                dados_modulo = df_filtrado[["Aluno", "Tutor", "Equipe"] + colunas_modulo]
                
                st.write(f"### Dados do {modulo_analise}")
                st.dataframe(dados_modulo, use_container_width=True)
                
                # Análise estatística
                st.write("### 📈 Análise Estatística")
                
                # Converter valores numéricos
                for col in colunas_modulo:
                    # Tentar converter para numérico, manter strings onde não for possível
                    dados_modulo[col] = pd.to_numeric(dados_modulo[col], errors='coerce')
                
                # Calcular estatísticas para cada tipo de avaliação
                stats_data = []
                for col in colunas_modulo:
                    if "|" in col:
                        tipo = col.split("|")[1].strip()
                        valores = dados_modulo[col].dropna()
                        
                        if len(valores) > 0 and valores.dtype in [np.float64, np.int64]:
                            stats_data.append({
                                "Tipo Avaliação": tipo,
                                "Média": valores.mean(),
                                "Mediana": valores.median(),
                                "Mínimo": valores.min(),
                                "Máximo": valores.max(),
                                "Desvio Padrão": valores.std(),
                                "Total Avaliados": len(valores)
                            })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True)
                else:
                    st.info("Não há dados numéricos para análise estatística neste módulo.")
        
        with tab4:
            st.subheader("👤 Detalhes por Aluno")
            
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
                    st.info(f"**Equipe:** {aluno_data['Equipe']}")
                
                with col_i2:
                    st.info(f"**Supervisor:** {aluno_data['Supervisor']}")
                    st.info(f"**Tutor:** {aluno_data['Tutor']}")
                
                with col_i3:
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
        
        # Seção de métricas gerais
        st.sidebar.markdown("---")
        st.sidebar.subheader("📈 Métricas Gerais")
        
        # Calcular métricas
        total_alunos = len(df_filtrado)
        total_modulos = len(modulos_info["modulo"].unique())
        
        # Contar atividades AG e NA
        atividades_especiais = extrair_atividades_especiais(df_filtrado)
        total_ag = len(atividades_especiais[atividades_especiais["Status"] == "AG"])
        total_na = len(atividades_especiais[atividades_especiais["Status"] == "NA"])
        
        st.sidebar.metric("Alunos Filtrados", total_alunos)
        st.sidebar.metric("Módulos", total_modulos)
        st.sidebar.metric("Atividades AG", total_ag)
        st.sidebar.metric("Atividades NA", total_na)
        
    else:
        st.error("❌ Erro ao processar o arquivo. Verifique o formato.")
else:
    st.info("👆 Por favor, carregue um arquivo Excel para começar.")
    
    # Mostrar exemplo da estrutura esperada
    with st.expander("📋 Estrutura esperada do arquivo"):
        st.write("""
        O arquivo deve conter uma planilha com a seguinte estrutura:
        
        1. **Primeira linha:** Nomes dos módulos (ex: "Módulo 1 - Políticas Públicas de Saúde")
        2. **Segunda linha:** Tipos de avaliação (ex: "Desafio", "Avaliação de Fórum", "Prova Online", "Nota Final")
        3. **Terceira linha em diante:** Dados dos alunos
        
        Colunas esperadas:
        - Coluna A: Aluno
        - Coluna B: Equipe
        - Coluna C: Supervisor
        - Coluna D: Tutor
        - Coluna E: Último acesso na plataforma
        - Colunas F em diante: Notas dos módulos
        
        Valores especiais:
        - **AG**: Aguardando avaliação
        - **NA**: Não disponível/ausente
        """)
