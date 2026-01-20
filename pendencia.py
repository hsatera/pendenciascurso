import streamlit as st
import pandas as pd
import io
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Painel de Monitoramento Acadêmico",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Painel de Monitoramento Acadêmico")
st.markdown("Análise de atividades faltantes (AG e NA) por aluno, tutor e módulo")

uploaded_file = st.file_uploader("Faça upload do arquivo CSV", type=['csv'])

def process_file(file):
    try:
        # 1. Ler a primeira linha para capturar os Módulos (cabeçalho superior)
        file.seek(0)
        line1 = file.readline().decode('utf-8').split(',')
        
        # 2. Criar mapeamento de módulos (preenchendo os vazios à direita do nome do módulo)
        module_mapping = {}
        current_mod = "Geral"
        for i, val in enumerate(line1):
            clean_val = val.strip().replace('"', '')
            if "Módulo" in clean_val:
                current_mod = clean_val
            module_mapping[i] = current_mod

        # 3. Ler os dados (pulando a primeira linha de módulos)
        file.seek(0)
        df = pd.read_csv(file, skiprows=1, low_memory=False)
        
        # Colunas de informação que não são atividades
        info_columns = ['Aluno', 'Equipe', 'Supervisor', 'Tutor', 'Último acesso na plataforma']
        
        # Verificar colunas essenciais
        for col in ['Aluno', 'Tutor']:
            if col not in df.columns:
                st.error(f"Coluna crítica '{col}' não encontrada!")
                return pd.DataFrame()

        # 4. Coletar registros de faltas (Unpivot manual)
        records = []
        # Identificar colunas que são de atividades (excluir as de info e as Unnamed)
        activity_cols = [c for c in df.columns if c not in info_columns and "Unnamed" not in c]

        for idx, row in df.iterrows():
            aluno = str(row['Aluno'])
            tutor = str(row['Tutor']) if pd.notna(row['Tutor']) else "Sem Tutor"
            
            for col_name in activity_cols:
                # Localizar o índice original da coluna para pegar o Módulo correto
                col_idx = df.columns.get_loc(col_name)
                modulo = module_mapping.get(col_idx, "Geral")
                
                valor = str(row[col_name]).strip().upper()
                
                # Critério de Pendência: AG, NA, N/A ou Vazio (NaN)
                if valor in ['AG', 'NA', 'N/A', 'NAN', '']:
                    status = 'AG' if valor == 'AG' else 'NA'
                    records.append({
                        'Aluno': aluno,
                        'Tutor': tutor,
                        'Módulo': modulo,
                        'Atividade': col_name,
                        'Status': status
                    })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return pd.DataFrame()

if uploaded_file:
    # Processar
    with st.spinner("Analisando dados..."):
        faltas_df = process_file(uploaded_file)

    if not faltas_df.empty:
        # --- MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pendências", len(faltas_df))
        c2.metric("Status AG", len(faltas_df[faltas_df['Status'] == 'AG']))
        c3.metric("Status NA", len(faltas_df[faltas_df['Status'] == 'NA']))
        c4.metric("Alunos Afetados", faltas_df['Aluno'].nunique())

        # --- FILTROS SIDEBAR ---
        st.sidebar.header("🔍 Filtros")
        tutor_list = sorted(faltas_df['Tutor'].unique())
        tutor_sel = st.sidebar.multiselect("Selecione o Tutor:", tutor_list)
        
        mod_list = sorted(faltas_df['Módulo'].unique())
        mod_sel = st.sidebar.multiselect("Selecione o Módulo:", mod_list)

        # Aplicar Filtros
        df_f = faltas_df.copy()
        if tutor_sel:
            df_f = df_f[df_f['Tutor'].isin(tutor_sel)]
        if mod_sel:
            df_f = df_f[df_f['Módulo'].isin(mod_sel)]

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📋 Por Aluno", "👨‍🏫 Por Tutor/Módulo", "📊 Lista Detalhada"])

        with tab1:
            st.subheader("Top Alunos com Pendências")
            rank_aluno = df_f.groupby(['Aluno', 'Status']).size().reset_index(name='Qtd')
            fig_aluno = px.bar(rank_aluno.sort_values('Qtd', ascending=False).head(30), 
                              x='Aluno', y='Qtd', color='Status', barmode='group')
            st.plotly_chart(fig_aluno, use_container_width=True)

        with tab2:
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Pendências por Tutor**")
                st.bar_chart(df_f.groupby('Tutor').size())
            with col_b:
                st.write("**Pendências por Módulo**")
                st.bar_chart(df_f.groupby('Módulo').size())

        with tab3:
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            csv = df_f.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar CSV Filtrado", csv, "pendencias.csv", "text/csv")
    else:
        st.success("Tudo em dia! Nenhuma pendência encontrada.")
