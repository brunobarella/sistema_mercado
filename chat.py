import streamlit as st
import ollama
from typing import Dict, Generator


def ollama_generator(model_name: str, messages: Dict) -> Generator:
    stream = ollama.chat(
        model=model_name, messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']


st.title("Ollama with Streamlit demo")

if "selected_model" not in st.session_state:
    st.session_state.selected_model = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# Obter a lista de modelos
models = ollama.list()["models"]

# Ajustar para acessar o atributo `model` diretamente
st.session_state.selected_model = st.selectbox(
    "Please select the model:", [model.model for model in models])

# Exibir histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada do usuário
if prompt := st.chat_input("How could I help you?"):
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
    st.session_state.messages.append(
        {"role": "assistant", "content": response})
