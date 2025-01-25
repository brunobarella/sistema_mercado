import streamlit as st
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd
from io import BytesIO

# Carregar os dados
data = pd.read_csv('supermarket_sales.csv')

# Configurar o título
st.title("💡 Sistema Inteligente de Recomendação de Produtos")

# Exibir as colunas disponíveis para análise
columns = ['Branch', 'Gender', 'Customer type']
selected_columns = st.multiselect('Selecione as variáveis para segmentação:', columns, default=columns)

# Verificar se o usuário selecionou as variáveis
if selected_columns:
    # Filtrar as combinações únicas de subclasses
    unique_combinations = data[selected_columns].drop_duplicates()

    # Lista para armazenar todas as recomendações
    all_recommendations = []

    # Loop para gerar recomendações por cada combinação de subclasses
    for _, row in unique_combinations.iterrows():
        filters = {col: row[col] for col in selected_columns}
        filtered_data = data.copy()

        # Aplicar filtros de subclasses
        for col, value in filters.items():
            filtered_data = filtered_data[filtered_data[col] == value]

        # Agrupamento mais amplo
        transactions = filtered_data.groupby(['Branch', 'Customer type', 'Date'])['Product line'].apply(list).tolist()
        #st.write(f"### Média de itens por transação para {filters}: {sum(len(t) for t in transactions) / len(transactions):.2f}")

        # Converter para formato binário
        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_ary, columns=te.columns_)

        # Aplicar Apriori com suporte mínimo reduzido
        frequent_itemsets = apriori(df, min_support=0.0001, use_colnames=True)

        # Gerar regras de associação
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.01, num_itemsets=len(frequent_itemsets))
        rules = rules[(rules['antecedents'].apply(len) == 1) & (rules['consequents'].apply(len) == 1)]  # Filtrar para pares
        rules = rules[rules['lift'] > 1.0]  # Filtrar regras com lift > 1.0

        # Adicionar informações de contexto às regras
        for col, value in filters.items():
            rules[col] = value

        # Adicionar as regras geradas ao DataFrame geral
        all_recommendations.append(rules)
        
        

        # Exibir Recomendações Humanizadas
        st.write(f"### Recomendações Personalizadas para {filters}:")
        top_recommendations = rules.sort_values(by='confidence', ascending=False).head(5)

        if not top_recommendations.empty:
            for _, rule in top_recommendations.iterrows():
                antecedent = list(rule['antecedents'])[0]
                consequent = list(rule['consequents'])[0]
                confidence = round(rule['confidence'] * 100, 2)
                
                # Resposta humanizada usando formatação mais natural
                st.write(f"✨ **Insight**: No supermercado **{filters['Branch']}**, clientes do gênero **{filters['Gender']}** que são **{filters['Customer type']}** frequentemente compram produtos da categoria **{antecedent}**.")
                st.write(f"📊 **Dados**: Existe uma chance de {confidence}% desses clientes também comprarem produtos da categoria **{consequent}**.")
                st.write(f"🛒 **Recomendação**: Considere criar campanhas que combinem essas categorias, como promoções ou combos, para maximizar o potencial de vendas.")
                st.write("---")

        else:
            st.write("🤷‍♂️ Nenhuma recomendação relevante encontrada para esta combinação.")

    # Combinar todas as recomendações em um único DataFrame
    all_recommendations_df = pd.concat(all_recommendations, ignore_index=True)
    

    # Função para converter DataFrame em Excel
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Recomendações')
        processed_data = output.getvalue()
        return processed_data

    # Baixar todas as recomendações
    st.write("### 📥 Baixar Todas as Recomendações")
    if not all_recommendations_df.empty:
        excel_data = convert_df_to_excel(all_recommendations_df)
        st.download_button(label="Baixar Recomendações em Excel",
                           data=excel_data,
                           file_name='recomendacoes_subclasses.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
else:
    st.write("Selecione pelo menos uma variável para segmentação.")
