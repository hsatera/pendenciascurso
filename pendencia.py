import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide", page_title="Monitoramento de Pendências")

def process_data(file):
    # Resetar o ponteiro do arquivo para leitura
    file.seek(0)
    
    # Lendo apenas a primeira linha para mapear os módulos
    # O CSV tem células vazias entre os nomes dos módulos
    header_raw = pd.read_csv(file, nrows=0)
    header_módulos = header_raw.columns.tolist()
    
    # Resetar novamente para ler os dados reais
    file.seek(0)
    # Pula a primeira linha (Módulos) e usa a segunda como cabeçalho de colunas
    df = pd.read_csv(file, skiprows=1)
    
    # --- Lógica de Mapeamento de Módulos ---
    current_mod = "Geral"
    mod_mapping = []
    for col in header_módulos:
        # Se a coluna não for "Unnamed", atualiza o nome do módulo atual
        if "Unnamed" not in str(col) and str(col).strip() != "":
            current_mod = col
        mod_mapping.append(current_mod)
    
    # Lista para armazenar pendências
    pendencias = []
    
    # Colunas que identificam o aluno (não são atividades)
    cols_ignore = ['Aluno', 'Equipe', 'Supervisor', 'Tutor', 'Último acesso na plataforma', 'Acessos']
    
    # Varrer o dataframe
    for index, row in df.iterrows():
        for i, col_name in enumerate(df.columns):
            # Ignora colunas de info e colunas geradas automaticamente sem nome
            if col_name not in cols_ignore and "Unnamed" not in col_name:
                valor = str(row[col_name]).strip().upper()
                
                if valor in ['AG', 'NA']:
                    pendencias.append({
                        'Aluno': row['Aluno'] if 'Aluno' in row else "N/A",
                        'Tutor': row['Tutor'] if 'Tutor' in row else "N/A",
                        'Equipe': row['Equipe'] if 'Equipe' in row else "N/A",
                        'Módulo': mod_mapping[i] if i < len(mod_mapping) else "Geral",
                        'Atividade': col_name,
                        'Status': valor
                    })
    
    return df, pd.DataFrame(pendencias)

# --- Interface ---
st.title("🚩 Painel de Pendências (AG/NA)")
st.markdown("Suba o arquivo CSV extraído da plataforma para visualizar as atividades faltantes.")

uploaded_file = st.file_uploader("Escolha o arquivo CSV", type="csv")

if uploaded_file:
    with st.spinner('Processando dados...'):
        df_raw, df_pendencias = process_data(uploaded_file)
    
    if df_pendencias.empty:
        st.success("✅ Nenhuma pendência (AG ou NA) encontrada nos módulos!")
    else:
        # --- Sidebar Filtros ---
        st.sidebar.header("Filtros de Visão")
        
        tutor_list = sorted(df_pendencias['Tutor'].unique().astype(str))
        tutor_sel = st.sidebar.multiselect("Filtrar por Tutor", options=tutor_list)
        
        mod_list = sorted(df_pendencias['Módulo'].unique().astype(str))
        mod_sel = st.sidebar.multiselect("Filtrar por Módulo", options=mod_list)
        
        # Aplicar Filtros
        dff = df_pendencias.copy()
        if tutor_sel:
            dff = dff[dff['Tutor'].isin(tutor_sel)]
        if mod_sel:
            dff = dff[dff['Módulo'].isin(mod_sel)]

        # --- Dashboard ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Pendências", len(dff))
        c2.metric("Alunos Pendentes", dff['Aluno'].nunique())
        c3.metric("Módulos com Pendência", dff['Módulo'].nunique())

        st.divider()

        col_left, col_right = st.columns(2)
        
        with col_left:
            if not dff.empty:
                fig_tutor = px.bar(
                    dff.groupby('Tutor').size().reset_index(name='Qtd'), 
                    x='Tutor', y='Qtd', 
                    title="Pendências por Tutor",
                    color_discrete_sequence=['#FF4B4B']
                )
                st.plotly_chart(fig_tutor, use_container_width=True)
            
        with col_right:
            if not dff.empty:
                # Top 10 módulos com mais pendências para não poluir o gráfico
                df_mod_chart = dff.groupby('Módulo').size().reset_index(name='Qtd').sort_values('Qtd', ascending=True)
                fig_mod = px.bar(
                    df_mod_chart.tail(15), 
                    y='Módulo', x='Qtd', 
                    orientation='h', 
                    title="Top 15 Módulos com Pendências"
                )
                st.plotly_chart(fig_mod, use_container_width=True)

        # --- Tabela Detalhada ---
        st.subheader("📋 Detalhamento por Atividade")
        st.dataframe(
            dff[['Aluno', 'Tutor', 'Módulo', 'Atividade', 'Status', 'Equipe']], 
            use_container_width=True,
            hide_index=True
        )
        
        # Download
        csv = dff.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório de Pendências (CSV)",
            data=csv,
            file_name="relatorio_pendencias.csv",
            mime="text/csv",
        )
