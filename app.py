import streamlit as st
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd
from io import BytesIO
import requests

from database_manager import DatabaseManager
import datetime
 
# Configurar o layout como "wide"
st.set_page_config(
    page_title="Plataforma Inteligente para Supermercados",
    layout="wide"
)

# Inicializar variáveis no st.session_state
if "messages" not in st.session_state:
    st.session_state.messages = []  # Inicializar como lista vazia
if "selected_model" not in st.session_state:
    st.session_state.selected_model = ""  # Inicializar como string vazia

# Carregar os dados do CSV (base de dados do supermercado)
data = pd.read_csv('supermarket_sales.csv')

# Transformar os dados em string para contexto no modelo
data_context = data.to_string(index=False)



# Menu lateral usando a sidebar
with st.sidebar:
    # Configurar o título
    st.title("💡 Plataforma Inteligente para Supermercados")
    menu = st.radio(
        "Menu Principal",
        ["Chat Inteligente", "Recomendador de Produtos", "Precificação Dinâmica", "Gestão de Estoque"],
        index=0
    )
    
    
## preco
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
    # st.set_page_config(layout="wide")
    
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

if menu == "Precificação Dinâmica":
    main()


# Configurar cada ferramenta
if menu == "Chat Inteligente":
    # Importações específicas para o chat
    import ollama
    from typing import Dict, Generator
  

 # Adicionar o seletor ao lado da barra lateral
    col1, col2 = st.columns([1, 4])  # Proporções ajustáveis
    with col1:
        st.session_state.selected_model = st.selectbox(
            "Modelo:",
            [model.model for model in ollama.list()["models"]]
        )
    with col2:
        st.write("")  # Espaço vazio para o restante do conteúdo

    # Centralizar o título "Chat Inteligente"
    st.markdown("<h1 style='text-align: center;'>🤖 Chat Inteligente</h1>", unsafe_allow_html=True)
    st.write("<p style='text-align: center;'>Converse com o agente de IA sobre o seu supermercado.</p>", unsafe_allow_html=True)

    # Carregar os dados no backend
    data = pd.read_csv('supermarket_sales.csv')  # Certifique-se de que o arquivo está no mesmo diretório ou especifique o caminho completo

    # Gerar um resumo inicial para passar como contexto
    resumo_categorias = data.groupby("Product line")["Total"].sum().sort_values(ascending=False).to_string()
    resumo_vendas = data.groupby("Product line")["Quantity"].sum().sort_values(ascending=False).to_string()
    resumo_faturamento_mensal = data.groupby(data['Date'].str.slice(3, 10))['Total'].sum().to_string()
    # Formatação de valores monetários no pandas
    # Garantir que a coluna 'Total' seja numérica
    data['Total'] = pd.to_numeric(data['Total'], errors='coerce')

    # Gerar o resumo de faturamento formatado
    resumo_faturamento = data.groupby("Product line")["Total"]\
        .sum()\
        .sort_values(ascending=False)\
        .apply(lambda x: f"R$ {x:,.2f}")\
        .to_string()

    # Prompt estratégico para o modelo
    initial_prompt = f"""
    Você é um assistente estratégico, parte da equipe do supermercado. Sua função é trabalhar junto com os gestores para melhorar a operação e aumentar o desempenho do supermercado. Seu objetivo é fornecer respostas detalhadas, baseadas nos dados fornecidos e no seu amplo conhecimento sobre o setor de supermercados.

    Aqui estão os principais aspectos dos dados do nosso supermercado:
    1. Categorias de produtos disponíveis: {', '.join(data['Product line'].unique())}.
    2. Métodos de pagamento mais utilizados: {', '.join(data['Payment'].unique())}.
    3. Locais das vendas (cidades): {', '.join(data['City'].unique())}.
    4. Gêneros atendidos: {', '.join(data['Gender'].unique())}.
    5. Faturamento por categoria (5 principais):
    {data.groupby("Product line")["Total"].sum().sort_values(ascending=False).head(5).apply(lambda x: f"R$ {x:,.2f}").to_string()}

    Como parte da equipe, seu tom deve ser amigável e colaborativo, sempre oferecendo insights úteis e sugestões práticas. Sempre que falar sobre valores, use o formato da moeda brasileira (R$) para manter consistência com os relatórios internos.

    Você pode ajudar a equipe com perguntas como:
    - Qual é a categoria com maior faturamento? Como aumentar ainda mais suas vendas?
    - Quais produtos devemos colocar em promoção para atrair mais clientes?
    - Como reduzir custos no estoque mantendo a qualidade?
    - Quais são os métodos de pagamento mais vantajosos para o supermercado?
    - Quais tendências sazonais devemos considerar para os próximos meses?
    Suas respostas devem:
    - Ser naturais e diretas, como um colega que conhece bem o supermercado.
    - Apresentar sugestões práticas baseadas nos dados.
    - Evitar frases repetitivas ou "robóticas".
    - Quando falar de valores, sempre usar o formato da moeda brasileira (R$).

    Exemplo de tom e estilo:
    - Pergunta: Qual é a categoria com maior faturamento?
    - Resposta: "A categoria 'Food and beverages' está no topo, com um faturamento de R$ 56.144,84. Isso representa uma grande oportunidade para campanhas específicas nessa área!"


    Seja direto, prático e estratégico, sempre oferecendo recomendações específicas e acionáveis. Nosso objetivo é aumentar o faturamento, melhorar a experiência do cliente e reduzir desperdícios.

    Agora, vamos começar! Responda de forma clara e organizada às perguntas que a equipe lhe fizer.
    """


    # Função para gerar respostas do Ollama
    def ollama_generator(model_name: str, messages: Dict) -> Generator:
        # Inserir o contexto (dados) na primeira interação
        if len(st.session_state.messages) == 1:  # Apenas no primeiro uso
            messages.insert(0, {"role": "system", "content": initial_prompt})
        
        # Chamar o modelo Ollama
        stream = ollama.chat(model=model_name, messages=messages, stream=True)
        for chunk in stream:
            yield chunk['message']['content']

    # Evite exibir o prompt inicial no frontend
    for message in st.session_state.messages:
        if message["role"] != "system":  # Não exibir mensagens do tipo "system"
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Entrada de mensagem do usuário
    if prompt := st.chat_input("Digite sua pergunta:"):
        # Adicionar mensagem do usuário ao histórico
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Exibir mensagem do usuário
        with st.chat_message("user"):
            st.markdown(prompt)

        # Exibir resposta do assistente
        with st.chat_message("assistant"):
            response = st.write_stream(ollama_generator(
                st.session_state.selected_model, st.session_state.messages))

        # Adicionar resposta ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})


elif menu == "Recomendador de Produtos":
    st.header("📦 Recomendador de Produtos")
    st.write("Ferramenta para recomendação de produtos com base nos dados do supermercado.")
    # Carregar os dados
    data = pd.read_csv('supermarket_sales.csv')

    # Configurar o título
    #st.title("💡 Sistema Inteligente de Recomendação de Produtos")

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

    # Aqui você pode chamar diretamente o código do recomendador sem abrir outra GUI.
    # Exemplo de função do recomendador
    #st.info("Funcionalidade do recomendador em desenvolvimento.")



elif menu == "Gestão de Estoque":
    st.header("📊 Gestão de Estoque Inteligente")
    st.write("Identifique produtos com estoque crítico ou excessivo.")
    st.info("Funcionalidade em desenvolvimento.")
