import streamlit as st
import requests
import json

# Mostrar título y descripción
st.title("🎓 Asistente de Búsqueda de Becas")
st.write(
    "Este asistente te ayudará a encontrar becas de estudio basadas en tus intereses y antecedentes. "
    "Utilizamos inteligencia artificial para procesar tu información y realizar búsquedas personalizadas."
)

# Obtener claves API de los secretos de Streamlit
together_api_key = st.secrets["TOGETHER_API_KEY"]
serper_api_key = st.secrets["SERPER_API_KEY"]

# Configurar los endpoints de API y headers
together_url = "https://api.together.xyz/v1/chat/completions"
serper_url = "https://google.serper.dev/search"

together_headers = {
    "Authorization": f"Bearer {together_api_key}",
    "Content-Type": "application/json"
}

serper_headers = {
    "X-API-KEY": serper_api_key,
    "Content-Type": "application/json"
}

# Función para realizar búsqueda en Google usando la API de Serper
def busqueda_google(consulta):
    payload = json.dumps({"q": consulta})
    response = requests.post(serper_url, headers=serper_headers, data=payload)
    return response.json()

# Función para obtener respuesta del LLM usando la API de Together
def obtener_respuesta_llm(mensajes):
    payload = {
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "messages": mensajes,
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": ["<|eot_id|>", "<|eom_id|>"],
        "stream": True
    }
    return requests.post(together_url, headers=together_headers, json=payload, stream=True)

# Inicializar variables de estado de sesión
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "info_usuario" not in st.session_state:
    st.session_state.info_usuario = {}
if "etapa_dialogo" not in st.session_state:
    st.session_state.etapa_dialogo = 0

# Lista de preguntas
preguntas = [
    "¿En qué campo de estudio estás interesado?",
    "¿En qué país o región te gustaría estudiar?",
    "¿Qué nivel académico estás buscando? (Por ejemplo: Licenciatura, Maestría, Doctorado, Postdoctorado)",
    "¿Cuál es tu nacionalidad?",
    "¿Estás interesado solo en becas específicas para tu nacionalidad? (Responde Sí o No)"
]

# Mostrar mensajes del chat
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# Diálogo principal
if st.session_state.etapa_dialogo < len(preguntas):
    # Mostrar la pregunta actual
    with st.chat_message("assistant"):
        st.markdown(preguntas[st.session_state.etapa_dialogo])
    
    # Esperar la respuesta del usuario
    respuesta_usuario = st.chat_input("Tu respuesta aquí")
    
    if respuesta_usuario:
        # Mostrar la respuesta del usuario
        with st.chat_message("user"):
            st.markdown(respuesta_usuario)
        
        # Guardar la respuesta
        st.session_state.mensajes.append({"role": "user", "content": respuesta_usuario})
        if st.session_state.etapa_dialogo == 0:
            st.session_state.info_usuario["campo"] = respuesta_usuario
        elif st.session_state.etapa_dialogo == 1:
            st.session_state.info_usuario["ubicacion"] = respuesta_usuario
        elif st.session_state.etapa_dialogo == 2:
            st.session_state.info_usuario["nivel"] = respuesta_usuario
        elif st.session_state.etapa_dialogo == 3:
            st.session_state.info_usuario["nacionalidad"] = respuesta_usuario
        elif st.session_state.etapa_dialogo == 4:
            st.session_state.info_usuario["especifica_nacionalidad"] = respuesta_usuario.lower() in ["sí", "si", "yes", "y", "s"]
        
        # Avanzar a la siguiente etapa
        st.session_state.etapa_dialogo += 1
        st.rerun()

elif st.session_state.etapa_dialogo == len(preguntas):
    # Procesar la información y buscar becas
    info_usuario = st.session_state.info_usuario
    consulta_busqueda = f"becas para {info_usuario['nivel']} en {info_usuario['campo']} en {info_usuario['ubicacion']}"
    if info_usuario.get('especifica_nacionalidad', False):
        consulta_busqueda += f" para estudiantes de {info_usuario['nacionalidad']}"

    try:
        resultados_busqueda = busqueda_google(consulta_busqueda)
    except Exception as e:
        st.error(f"Error durante la búsqueda en Google: {str(e)}")
        resultados_busqueda = {"organic": []}

    contexto = "Resultados de búsqueda para becas:\n"
    for i, resultado in enumerate(resultados_busqueda.get('organic', [])[:5], 1):
        contexto += f"{i}. {resultado.get('title', 'Sin título')}: {resultado.get('snippet', 'Sin descripción')} [Enlace: {resultado.get('link', 'Sin enlace')}]\n"

    prompt = f"""
    Basándote en las siguientes preferencias del usuario y los resultados de búsqueda, recomienda becas adecuadas:
    
    Preferencias del usuario:
    - Campo de estudio: {info_usuario['campo']}
    - Ubicación de estudio deseada: {info_usuario['ubicacion']}
    - Nivel académico: {info_usuario['nivel']}
    - Nacionalidad: {info_usuario['nacionalidad']}
    - Solo interesado en becas específicas para su nacionalidad: {"Sí" if info_usuario.get('especifica_nacionalidad', False) else "No"}

    {contexto}

    Por favor, proporciona una respuesta detallada en español con:
    1. Las oportunidades de becas más relevantes.
    2. Enlaces directos a las instituciones que ofrecen estas becas.
    3. Breves explicaciones de por qué recomiendas cada institución o beca.
    4. Cualquier consejo adicional para el usuario basado en sus preferencias.
    """

    mensajes = [
        {"role": "system", "content": "Eres un asistente de búsqueda de becas muy útil. Proporciona información detallada y precisa sobre becas basada en las preferencias del usuario y los resultados de la búsqueda. Responde siempre en español."},
        {"role": "user", "content": prompt}
    ]

    with st.chat_message("assistant"):
        marcador_mensaje = st.empty()
        respuesta_completa = ""

        try:
            respuesta = obtener_respuesta_llm(mensajes)

            for linea in respuesta.iter_lines():
                if linea:
                    try:
                        datos = linea.decode('utf-8').split('data: ', 1)
                        if len(datos) > 1:
                            fragmento = json.loads(datos[1])
                            if fragmento['choices'][0]['finish_reason'] is None:
                                contenido = fragmento['choices'][0]['delta'].get('content', '')
                                respuesta_completa += contenido
                                marcador_mensaje.markdown(respuesta_completa + "▌")
                    except json.JSONDecodeError:
                        continue

            if not respuesta_completa:
                respuesta_completa = "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."

        except Exception as e:
            respuesta_completa = f"Ocurrió un error al procesar tu solicitud: {str(e)}"

        marcador_mensaje.markdown(respuesta_completa)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta_completa})
    st.session_state.etapa_dialogo += 1

# Botón para iniciar una nueva búsqueda de becas
if st.button("Iniciar nueva búsqueda de becas"):
    st.session_state.mensajes = []
    st.session_state.info_usuario = {}
    st.session_state.etapa_dialogo = 0
    st.rerun()
