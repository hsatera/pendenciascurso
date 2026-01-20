import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Painel de Monitoramento Acadêmico",
    page_icon="📊",
    layout="wide"
)

# Título do aplicativo
st.title("📊 Painel de Monitoramento Acadêmico")
st.markdown("Análise de atividades faltantes (AG e NA) por aluno, tutor e módulo")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload do arquivo CSV", type=['csv'])

def process_file(file_content):
    """Processa o arquivo CSV e retorna um DataFrame das faltas"""
    try:
        # Ler o arquivo
        df = pd.read_csv(io.StringIO(file_content), header=1, low_memory=False)
        
        # Remover linhas totalmente vazias
        df = df.dropna(how='all')
        
        # Informações dos alunos
        info_columns = ['Aluno', 'Equipe', 'Supervisor', 'Tutor', 'Último acesso na plataforma']
        
        # Garantir que as colunas de informações existem
        for col in info_columns:
            if col not in df.columns:
                st.error(f"Coluna '{col}' não encontrada no arquivo.")
                return pd.DataFrame()
        
        # Processar o cabeçalho para identificar módulos
        header_lines = file_content.split('\n')
        if len(header_lines) < 1:
            st.error("Arquivo vazio ou formato inválido.")
            return pd.DataFrame()
        
        module_header = header_lines[0].split(',')
        
        # Criar mapeamento de módulos
        module_mapping = {}
        current_module = ""
        
        for i, col in enumerate(module_header):
            col_str = str(col).strip()
            if 'Módulo' in col_str and col_str:
                current_module = col_str
            if current_module:
                module_mapping[i] = current_module
        
        # Coletar registros de faltas
        records = []
        
        for idx, row in df.iterrows():
            aluno = row['Aluno']
            tutor = row['Tutor'] if pd.notna(row['Tutor']) else "Não informado"
            
            # Processar cada coluna de dados
            for i, col_name in enumerate(df.columns):
                if col_name not in info_columns:
                    # Obter módulo
                    modulo = module_mapping.get(i, "Módulo Desconhecido")
                    
                    # Obter valor
                    valor = row[col_name]
                    
                    # Verificar se é AG, NA ou vazio
                    if pd.isna(valor):
                        records.append({
                            'Aluno': aluno,
                            'Tutor': tutor,
                            'Módulo': modulo,
                            'Atividade': col_name,
                            'Status': 'NA',
                            'Valor': 'NA'
                        })
                    else:
                        valor_str = str(valor).strip().upper()
                        if valor_str in ['AG', 'NA', 'N/A', '']:
                            status = 'AG' if valor_str == 'AG' else 'NA'
                            records.append({
                                'Aluno': aluno,
                                'Tutor': tutor,
                                'Módulo': modulo,
                                'Atividade': col_name,
                                'Status': status,
                                'Valor': valor_str
                            })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return pd.DataFrame()

def display_metrics(faltas_df, student_info):
    """Exibe métricas principais"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Atividades Faltantes", len(faltas_df))
    
    with col2:
        ag_count = len(faltas_df[faltas_df['Status'] == 'AG'])
        st.metric("Atividades AG", ag_count)
    
    with col3:
        na_count = len(faltas_df[faltas_df['Status'] == 'NA'])
        st.metric("Atividades NA", na_count)
    
    with col4:
        alunos_afetados = faltas_df['Aluno'].nunique()
        st.metric("Alunos Afetados", alunos_afetados)

def create_filters(faltas_df):
    """Cria os filtros na sidebar"""
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por tutor
    tutores = ['Todos'] + sorted(faltas_df['Tutor'].dropna().unique().tolist())
    tutor_selecionado = st.sidebar.selectbox("Selecione o Tutor:", tutores)
    
    # Filtro por status
    status_opcoes = ['Todos', 'AG', 'NA']
    status_selecionado = st.sidebar.selectbox("Selecione o Status:", status_opcoes)
    
    # Filtro por módulo
    modulos = ['Todos'] + sorted(faltas_df['Módulo'].dropna().unique().tolist())
    modulo_selecionado = st.sidebar.selectbox("Selecione o Módulo:", modulos)
    
    # Aplicar filtros
    df_filtrado = faltas_df.copy()
    
    if tutor_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Tutor'] == tutor_selecionado]
    
    if status_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Status'] == status_selecionado]
    
    if modulo_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Módulo'] == modulo_selecionado]
    
    return df_filtrado, tutor_selecionado, status_selecionado, modulo_selecionado

def display_tab1(df_filtrado):
    """Exibe a aba 'Por Aluno'"""
    st.subheader("📋 Atividades Faltantes por Aluno")
    
    # Agrupar por aluno
    faltas_por_aluno = df_filtrado.groupby(['Aluno', 'Tutor', 'Status']).size().reset_index(name='Quantidade')
    faltas_por_aluno = faltas_por_aluno.sort_values('Quantidade', ascending=False)
    
    # Exibir tabela
    if not faltas_por_aluno.empty:
        st.dataframe(
            faltas_por_aluno,
            column_config={
                "Aluno": "Aluno",
                "Tutor": "Tutor",
                "Status": "Status",
                "Quantidade": st.column_config.NumberColumn("Faltas", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Gráfico
        top_alunos = faltas_por_aluno.head(20)
        fig = px.bar(
            top_alunos,
            x='Aluno',
            y='Quantidade',
            color='Status',
            title="Top 20 Alunos com Mais Atividades Faltantes",
            labels={'Quantidade': 'Número de Atividades Faltantes'},
            color_discrete_map={'AG': '#FF6B6B', 'NA': '#4ECDC4'}
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")

def display_tab2(df_filtrado):
    """Exibe a aba 'Por Tutor'"""
    st.subheader("👨‍🏫 Atividades Faltantes por Tutor")
    
    # Agrupar por tutor
    faltas_por_tutor = df_filtrado.groupby(['Tutor', 'Status']).size().reset_index(name='Quantidade')
    faltas_por_tutor = faltas_por_tutor.sort_values('Quantidade', ascending=False)
    
    # Exibir tabela
    if not faltas_por_tutor.empty:
        st.dataframe(
            faltas_por_tutor,
            column_config={
                "Tutor": "Tutor",
                "Status": "Status",
                "Quantidade": st.column_config.NumberColumn("Faltas", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Gráfico
        fig = px.bar(
            faltas_por_tutor,
            x='Tutor',
            y='Quantidade',
            color='Status',
            title="Atividades Faltantes por Tutor",
            labels={'Quantidade': 'Número de Atividades Faltantes'},
            color_discrete_map={'AG': '#FF6B6B', 'NA': '#4ECDC4'}
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")

def display_tab3(df_filtrado):
    """Exibe a aba 'Por Módulo'"""
    st.subheader("📚 Atividades Faltantes por Módulo")
    
    # Agrupar por módulo
    faltas_por_modulo = df_filtrado.groupby(['Módulo', 'Status']).size().reset_index(name='Quantidade')
    faltas_por_modulo = faltas_por_modulo.sort_values('Quantidade', ascending=False)
    
    # Exibir tabela
    if not faltas_por_modulo.empty:
        st.dataframe(
            faltas_por_modulo,
            column_config={
                "Módulo": "Módulo",
                "Status": "Status",
                "Quantidade": st.column_config.NumberColumn("Faltas", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Gráfico
        fig = px.bar(
            faltas_por_modulo,
            x='Módulo',
            y='Quantidade',
            color='Status',
            title="Atividades Faltantes por Módulo",
            labels={'Quantidade': 'Número de Atividades Faltantes'},
            color_discrete_map={'AG': '#FF6B6B', 'NA': '#4ECDC4'}
        )
        fig.update_layout(xaxis_tickangle=-45, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")

def display_tab4(df_filtrado):
    """Exibe a aba 'Análise Detalhada'"""
    st.subheader("📊 Análise Detalhada das Faltas")
    
    if not df_filtrado.empty:
        # Exibir o DataFrame completo
        st.dataframe(
            df_filtrado,
            column_config={
                "Aluno": "Aluno",
                "Tutor": "Tutor",
                "Módulo": "Módulo",
                "Atividade": "Atividade",
                "Status": "Status",
                "Valor": "Valor Original"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Opção para download
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download dos Dados Filtrados",
            data=csv,
            file_name=f"faltas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Estatísticas adicionais
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alunos_com_faltas = df_filtrado['Aluno'].nunique()
            st.metric("Alunos com Faltas", alunos_com_faltas)
        
        with col2:
            modulos_com_faltas = df_filtrado['Módulo'].nunique()
            st.metric("Módulos com Faltas", modulos_com_faltas)
        
        with col3:
            atividades_diferentes = df_filtrado['Atividade'].nunique()
            st.metric("Tipos de Atividades", atividades_diferentes)
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")

def display_sidebar_stats(faltas_df):
    """Exibe estatísticas na sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Estatísticas Gerais")
    st.sidebar.write(f"**Total de registros:** {len(faltas_df)}")
    st.sidebar.write(f"**Alunos únicos:** {faltas_df['Aluno'].nunique()}")
    st.sidebar.write(f"**Tutores únicos:** {faltas_df['Tutor'].nunique()}")
    st.sidebar.write(f"**Módulos únicos:** {faltas_df['Módulo'].nunique()}")
    
    # Distribuição de status
    if not faltas_df.empty:
        ag_count = len(faltas_df[faltas_df['Status'] == 'AG'])
        na_count = len(faltas_df[faltas_df['Status'] == 'NA'])
        st.sidebar.write(f"**AG:** {ag_count} ({ag_count/len(faltas_df)*100:.1f}%)")
        st.sidebar.write(f"**NA:** {na_count} ({na_count/len(faltas_df)*100:.1f}%)")

# Fluxo principal do aplicativo
if uploaded_file is not None:
    try:
        # Ler conteúdo do arquivo
        file_content = uploaded_file.read().decode('utf-8')
        
        # Processar arquivo
        with st.spinner("Processando arquivo..."):
            faltas_df = process_file(file_content)
        
        if not faltas_df.empty:
            # Obter informações básicas dos alunos
            df_raw = pd.read_csv(io.StringIO(file_content), header=1, low_memory=False)
            info_columns = ['Aluno', 'Equipe', 'Supervisor', 'Tutor', 'Último acesso na plataforma']
            student_info = df_raw[info_columns].copy() if all(col in df_raw.columns for col in info_columns) else pd.DataFrame()
            
            # Exibir métricas
            display_metrics(faltas_df, student_info)
            
            # Criar filtros
            df_filtrado, tutor_sel, status_sel, modulo_sel = create_filters(faltas_df)
            
            # Tabs para diferentes visualizações
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Por Aluno", 
                "👨‍🏫 Por Tutor", 
                "📚 Por Módulo", 
                "📊 Análise Detalhada"
            ])
            
            with tab1:
                display_tab1(df_filtrado)
            
            with tab2:
                display_tab2(df_filtrado)
            
            with tab3:
                display_tab3(df_filtrado)
            
            with tab4:
                display_tab4(df_filtrado)
            
            # Estatísticas na sidebar
            display_sidebar_stats(faltas_df)
            
        else:
            st.success("✅ Nenhuma atividade faltante (AG ou NA) encontrada no arquivo!")
            
            if not student_info.empty:
                st.subheader("📋 Informações Gerais do Arquivo")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total de alunos", len(student_info))
                
                with col2:
                    st.metric("Total de tutores", student_info['Tutor'].nunique())
                
                with col3:
                    st.metric("Equipes", student_info['Equipe'].nunique())
                
                # Mostrar preview dos dados
                with st.expander("Visualizar dados dos alunos"):
                    st.dataframe(student_info.head(10), use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("Certifique-se de que o arquivo está no formato correto. O formato esperado é o CSV exportado do sistema de monitoramento.")

else:
    # Tela inicial com instruções
    st.info("👆 Faça upload de um arquivo CSV no formato do relatório de monitoramento.")
    
    # Instruções em expansores
    with st.expander("📋 Instruções de Uso", expanded=True):
        st.markdown("""
        1. **Faça upload** de um arquivo CSV exportado do sistema de monitoramento
        2. **O aplicativo irá identificar automaticamente** as atividades com status:
           - **AG** (Aguardando)
           - **NA** (Não Disponível/Não Aplicável)
        3. **Use os filtros na barra lateral** para analisar os dados por:
           - Tutor específico
           - Tipo de status (AG ou NA)
           - Módulo específico
        4. **Navegue entre as abas** para diferentes visualizações
        """)
    
    with st.expander("🔍 O que o aplicativo analisa"):
        st.markdown("""
        - **Por Aluno**: Atividades faltantes por aluno, com ranking dos 20 com mais pendências
        - **Por Tutor**: Desempenho de cada tutor, mostrando alunos com pendências
        - **Por Módulo**: Módulos com mais atividades pendentes
        - **Análise Detalhada**: Tabela completa com opção de download
        """)
    
    with st.expander("📁 Formato esperado do arquivo"):
        st.markdown("""
        O arquivo deve conter as seguintes colunas:
        - **Aluno**: Nome do aluno
        - **Equipe**: Código da equipe
        - **Supervisor**: Código do supervisor
        - **Tutor**: Código do tutor
        - **Último acesso na plataforma**: Data/hora do último acesso
        
        E múltiplas colunas para cada módulo, por exemplo:
        - Módulo 1 - Políticas Públicas de Saúde
          - Desafio - avaliativo
          - Avaliação de Fórum - avaliativo
          - Prova Online
          - Nota Final
        """)
    
    with st.expander("🎯 Exemplo de valores que serão detectados"):
        st.markdown("""
        O aplicativo detectará como atividades faltantes:
        - **AG** (em qualquer variação de maiúsculas/minúsculas)
        - **NA** ou **N/A**
        - Células vazias
        - Valores nulos
        """)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    📊 <strong>Painel de Monitoramento Acadêmico</strong> | 
    Desenvolvido para análise de atividades pendentes | 
    Versão 1.0
    </div>
    """,
    unsafe_allow_html=True
)
