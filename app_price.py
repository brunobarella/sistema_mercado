import streamlit as st
import pandas as pd
from database_manager import DatabaseManager
import datetime
pd.set_option("display.precision", 2)

def calcular_preco_otimizado(df, chaves=['Product_line'],months=3):
    """
    Função de exemplo para calcular um preço otimizado, com base nos últimos 'months' meses.
    - Converte coluna 'Date' para datetime.
    - Filtra as vendas nesse período (últimos 3 meses por padrão).
    - Agrupa por Product_line e Unit_price.
    - Calcula quantidade acumulada e custo médio (cost = Unit_price - gross_income).
    - Cria uma nova coluna que multiplica a quantidade acumulada pelo custo médio.
    
    Retorna um DataFrame com as colunas:
        [Product_line, Unit_price, qtd_acumulada, custo_medio, valor_novo]
    """
    # Converte a coluna Date para datetime (caso não esteja ainda).
    df['Date'] = pd.to_datetime(df['Date'])

    # Define a data de corte para filtrar os últimos 'months' meses.
    cutoff_date = df['Date'].max() - pd.DateOffset(months=months)

    # Filtra somente as vendas nesse período
    df_filtrado = df[df['Date'] >= cutoff_date]
    
    # Ordena por Product_line e depois por Unit_price
    chave_order = chaves+['Unit_price']
    df_filtrado.sort_values(by=chave_order, ascending=False, inplace=True)

    
    
    # Calcula a quantidade cumulativa (cumsum) por Product_line
    df_filtrado["qtd_cumsum"] = df_filtrado.groupby(chaves)["Quantity"].cumsum()

    # Agora agrupamos por Product_line e Unit_price
    df_grouped = df_filtrado.groupby(chave_order, as_index=False).agg(
        qtd_cumsum=("qtd_cumsum", "last"),    # Pega o último valor da coluna qtd_cumsum
    )

    df_cost = df.groupby(chaves, as_index=False)['cost'].last()

    df_grouped = df_grouped.merge(df_cost, how='left')


    df_grouped['profit'] = df_grouped['Unit_price']-df_grouped['cost']

    # Nova coluna: valor_novo = qtd_cumsum * custo_medio (exemplo)
    df_grouped["profit_esperado"] = df_grouped["qtd_cumsum"] * df_grouped["profit"]
    
    # pegando as demandas normalizadas
    df_max_demand=df_grouped.groupby(chaves, as_index=False)['qtd_cumsum'].max().rename(columns={'qtd_cumsum':'max_demand'})
    df_grouped = df_grouped.merge(df_max_demand, how='left')
    
    df_grouped['% Demanda Capturada'] = (df_grouped['qtd_cumsum']*100/df_grouped['max_demand']).round(1)
    
    idx = df_grouped.groupby(chaves)['profit_esperado'].idxmax()
    
    df_last_price = df.groupby(chaves, as_index=False)['Unit_price'].last().rename(columns={'Unit_price':'Último Preço'})
    df_grouped = df_grouped.merge(df_last_price, how='left')
    
    chaves_demanda = chaves + ['% Demanda Capturada']
    df_demanda_atual = df_grouped[df_grouped["Unit_price"]==df_grouped['Último Preço']][
                                                chaves_demanda].rename(columns={'% Demanda Capturada':'% Demanda Atual Capturada'})
    
    df_grouped = df_grouped.merge(df_demanda_atual, how='left')
    df_grouped = df_grouped.loc[idx]
    
    
    
    df_grouped['Diferença % Preço'] = ((df_grouped['Unit_price'] - df_grouped['Último Preço'])*100/df_grouped['Último Preço']).round(1)
    df_grouped['Diferença % Demanda'] = ((df_grouped['% Demanda Capturada'] - df_grouped['% Demanda Atual Capturada'])*100/df_grouped['% Demanda Atual Capturada']).round(1)
    df_grouped.rename(columns={'Unit_price':'Melhor Preço', 'Product_line':'Produto'},inplace=True)
    if 'City' in df_grouped.columns:
        df_grouped.rename(columns={'City':'Cidade'},inplace=True)
        df_returned = df_grouped[['Produto','Cidade','Melhor Preço','Último Preço', 'Diferença % Preço','% Demanda Capturada','% Demanda Atual Capturada','Diferença % Demanda']]
    else:
        df_returned = df_grouped[['Produto','Melhor Preço','Último Preço', 'Diferença % Preço','% Demanda Capturada','% Demanda Atual Capturada','Diferença % Demanda']]
    
    
    return df_returned


def main():
    st.set_page_config(layout="wide")
    
    # SIDEBAR
    st.sidebar.title("OTM de Precos")
    
    options = st.sidebar.multiselect(
        "Qual Nível da Otimização de Preços",
        [
            "Produto",
            "Cidade",
        ],default='Produto'
    )
    
    if st.sidebar.button("Atualizar Preços"):
        # Se clicar, atualiza a página
        st.rerun()

    # TÍTULO PRINCIPAL
    st.title("Otimização de Preços")

    # Instancia o gerenciador do banco de dados
    db = DatabaseManager()

    # Seção para exibir todos os dados em formato de tabela
    st.subheader("Tabela de Vendas")
    data = db.get_all_data()

    # Nomes das colunas existentes no seu banco
    columns_names = [
        "Invoice_ID",
        "Branch",
        "City",
        "Customer_type",
        "Gender",
        "Product_line",
        "Unit_price",
        "Quantity",
        "Tax_5",
        "Total",
        "Date",
        "Time",
        "Payment",
        "cogs",
        "gross_margin_percentage",
        "gross_income",
        "Rating"
    ]

    # Converte em DataFrame e seleciona as colunas desejadas
    df = pd.DataFrame(data, columns=columns_names)[
        ["Product_line", 'City', "Date", "Unit_price", "Quantity", "gross_income"]
    ]

    # Cria coluna de custo (exemplo)
    df['cost'] = df['Unit_price'] - df['gross_income']

    # CENTRALIZAÇÃO DA TABELA
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.dataframe(df, column_config={"Name": st.column_config.Column(width="large")},)

        # EXEMPLO DE USO DA FUNÇÃO DE PREÇO OTIMIZADO
        st.subheader("Cálculo de Preço Otimizado (Exemplo)")
        
        dic = {'Produto':'Product_line', 'Cidade':'City'}
        opcoes_normalizadas = [dic.get(n, n) for n in options]
        
        if opcoes_normalizadas != []:
        
            df_otimizado = calcular_preco_otimizado(df, chaves=opcoes_normalizadas, months=3)
            st.write("Abaixo, o resultado do agrupamento por produto e preço, considerando últimos 3 meses:")
            df_otimizado = df_otimizado.style.map(lambda x: f"background-color: {'green' if x>=0 else 'red' if x<0 else 'gray'}", 
                                                subset=['Diferença % Preço', 'Diferença % Demanda'])
            st.dataframe(df_otimizado, column_config={"Name": st.column_config.Column(width="large")},)

if __name__ == "__main__":
    main()