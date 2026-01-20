import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide", page_title="Monitoramento de Pendências")

def process_data(file):
    # Lendo as duas primeiras linhas para mapear os módulos
    header_módulos = pd.read_csv(file, nrows=0).columns.tolist()
    # Lendo os dados pulando a primeira linha de títulos de módulos
    df = pd.read_csv(file, skiprows=1)
    
    # Preencher os nomes dos módulos (que estão vazios entre as colunas no CSV original)
    current_mod = ""
    mod_mapping = []
    for col in header_módulos:
        if "Módulo" in str(col):
            current_mod = col
        mod_mapping.append(current_mod)
    
    # Lista para armazenar pendências encontradas
    pendencias = []
    
    # Colunas que não são de atividades
    cols_info = ['Aluno', 'Equipe', 'Supervisor', 'Tutor', 'Último acesso na plataforma']
    
    # Varrer o dataframe em busca de AG e NA
    for index, row in df.iterrows():
        for i, col_name in enumerate(df.columns):
            if col_name not in cols_info:
                valor = str(row[col_name]).strip().upper()
                if valor in ['AG', 'NA']:
                    pendencias.append({
                        'Aluno': row['Aluno'],
                        'Tutor': row['Tutor'],
                        'Equipe': row['Equipe'],
                        'Módulo': mod_mapping[i] if mod_mapping[i] else "Geral",
                        'Atividade': col_name,
                        'Status': valor
                    })
    
    return df, pd.DataFrame(pendencias)

# --- Interface ---
st.title("🚩 Painel de Pendências (AG/NA)")
uploaded_file = st.file_uploader("Suba o arquivo CSV de monitoramento", type="csv")

if uploaded_file:
    df_raw, df_pendencias = process_data(uploaded_file)
    
    if df_pendencias.empty:
        st.success("✅ Nenhuma pendência (AG ou NA) encontrada!")
    else:
        # Filtros na Sidebar
        st.sidebar.header("Filtros")
        tutor_sel = st.sidebar.multiselect("Tutor", options=df_pendencias['Tutor'].unique())
        mod_sel = st.sidebar.multiselect("Módulo", options=df_pendencias['Módulo'].unique())
        
        # Aplicar Filtros
        dff = df_pendencias.copy()
        if tutor_sel: dff = dff[dff['Tutor'].isin(tutor_sel)]
        if mod_sel: dff = dff[dff['Módulo'].isin(mod_sel)]

        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Pendências", len(dff))
        c2.metric("Alunos com Pendência", dff['Aluno'].nunique())
        c3.metric("Módulos com Atraso", dff['Módulo'].nunique())

        # Gráficos
        col_left, col_right = st.columns(2)
        
        with col_left:
            fig_tutor = px.bar(dff.groupby('Tutor').size().reset_index(name='Qtd'), 
                               x='Tutor', y='Qtd', title="Pendências por Tutor", color_discrete_sequence=['#EF553B'])
            st.plotly_chart(fig_tutor, use_container_width=True)
            
        with col_right:
            fig_mod = px.bar(dff.groupby('Módulo').size().reset_index(name='Qtd'), 
                             y='Módulo', x='Qtd', orientation='h', title="Pendências por Módulo")
            st.plotly_chart(fig_mod, use_container_width=True)

        # Tabela Detalhada
        st.subheader("📋 Lista Detalhada de Atividades Faltantes")
        st.dataframe(dff, use_container_width=True)
        
        # Botão para baixar relatório de pendências
        csv = dff.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar Lista de Pendências (CSV)", csv, "pendencias.csv", "text/csv")
