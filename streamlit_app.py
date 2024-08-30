import streamlit as st
import requests
import json
from datetime import datetime

# Obtener la fecha actual
fecha_actual = datetime.now().strftime("%d de %B de %Y")

# Mostrar título, descripción y fecha de búsqueda
st.title("🚗 Asistente de Búsqueda de Automóviles Usados en EE.UU.")
st.write(
    f"Fecha de búsqueda: {fecha_actual}\n\n"
    "Este asistente te ayudará a encontrar automóviles usados en venta en Estados Unidos basados en tus preferencias. "
    "Utilizamos inteligencia artificial para procesar tu información y realizar búsquedas personalizadas. "
    "Se mostrarán resultados de vehículos disponibles a la fecha de hoy."
)

def obtener_claves_api():
    # Obtener claves API de los secretos de Streamlit
    return st.secrets["TOGETHER_API_KEY"], st.secrets["SERPER_API_KEY"]

# Configurar los endpoints de API y headers
together_url = "https://api.together.xyz/v1/chat/completions"
serper_url = "https://google.serper.dev/search"

def configurar_headers(api_key, content_type="application/json"):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type
    }

# Obtener claves API
together_api_key, serper_api_key = obtener_claves_api()
together_headers = configurar_headers(together_api_key)
serper_headers = configurar_headers(serper_api_key, content_type="application/json")

# Función para realizar búsqueda en Google usando la API de Serper
def busqueda_google(consulta):
    payload = json.dumps({"q": consulta})
    try:
        response = requests.post(serper_url, headers=serper_headers, data=payload)
        response.raise_for_status()  # Maneja errores HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error durante la búsqueda en Serper: {e}")
        return {"organic": []}

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
    try:
        response = requests.post(together_url, headers=together_headers, json=payload, stream=True)
        response.raise_for_status()
        return response.text  # Preferimos text ya que es texto continuo
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener respuesta del LLM: {e}")
        return ""

# Inicializar variables de estado de sesión
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "info_usuario" not in st.session_state:
    st.session_state.info_usuario = {}
if "etapa_dialogo" not in st.session_state:
    st.session_state.etapa_dialogo = 0

# Lista de preguntas
preguntas = [
    "¿Qué marca y modelo de automóvil estás buscando?",
    "¿En qué rango de años estás interesado? (Por ejemplo: 2015-2020)",
    "¿Cuál es tu presupuesto máximo en dólares?",
    "¿En qué estados de EE.UU. estás buscando el vehículo? (Puedes seleccionar varios)",
    "¿Tienes alguna preferencia en cuanto a características específicas? (Por ejemplo: bajo kilometraje, tipo de transmisión, color, etc.)",
]

# Lista de estados de EE.UU.
estados_eeuu = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

# Mostrar mensajes del chat
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# Diálogo principal
def mostrar_pregunta_actual():
    with st.chat_message("assistant"):
        st.markdown(preguntas[st.session_state.etapa_dialogo])

def manejar_respuesta_usuario(respuesta_usuario):
    with st.chat_message("user"):
        if isinstance(respuesta_usuario, list):
            st.markdown(", ".join(respuesta_usuario))
        else:
            st.markdown(respuesta_usuario)

    respuesta_guardada = ", ".join(respuesta_usuario) if isinstance(respuesta_usuario, list) else respuesta_usuario

    st.session_state.mensajes.append({"role": "user", "content": respuesta_guardada})

    info_usuario = st.session_state.info_usuario
    if st.session_state.etapa_dialogo == 0:
        info_usuario["marca_modelo"] = respuesta_guardada
    elif st.session_state.etapa_dialogo == 1:
        info_usuario["rango_años"] = respuesta_guardada
    elif st.session_state.etapa_dialogo == 2:
        info_usuario["presupuesto"] = respuesta_guardada
    elif st.session_state.etapa_dialogo == 3:
        info_usuario["estados"] = respuesta_usuario  # Guardamos la lista de estados seleccionados
    elif st.session_state.etapa_dialogo == 4:
        info_usuario["caracteristicas"] = respuesta_guardada

    st.session_state.etapa_dialogo += 1
    st.rerun()

if st.session_state.etapa_dialogo < len(preguntas):
    mostrar_pregunta_actual()

    if st.session_state.etapa_dialogo == 3:  # Pregunta sobre los estados
        respuesta_usuario = st.multiselect("Selecciona uno o más estados:", estados_eeuu, key=f"multiselect_{st.session_state.etapa_dialogo}")
    else:
        respuesta_usuario = st.text_input("Tu respuesta aquí", key=f"input_{st.session_state.etapa_dialogo}")

    if respuesta_usuario:
        manejar_respuesta_usuario(respuesta_usuario)

elif st.session_state.etapa_dialogo == len(preguntas):
    st.session_state.info_usuario["interes_chocados"] = st.checkbox("Estoy interesado en vehículos que hayan sufrido choques o percances y que por eso estén en venta a precios muy bajos.")

    info_usuario = st.session_state.info_usuario
    estados_seleccionados = " OR ".join(info_usuario['estados'])

    consulta_busqueda = f"used {info_usuario['marca_modelo']} for sale {info_usuario['rango_años']} under {info_usuario['presupuesto']} in ({estados_seleccionados}) {info_usuario['caracteristicas']}"

    if info_usuario['interes_chocados']:
        consulta_busqueda += " salvage title"

    resultados_busqueda = busqueda_google(consulta_busqueda)

    contexto = "Resultados de búsqueda para automóviles usados:\n"
    for i, resultado in enumerate(resultados_busqueda.get('organic', [])[:5], 1):
        contexto += f"{i}. {resultado.get('title', 'Sin título')}: {resultado.get('snippet', 'Sin descripción')} [Enlace: {resultado.get('link', 'Sin enlace')}]\n"

    prompt = f"""
    Basándote en las siguientes preferencias del usuario y los resultados de búsqueda, recomienda automóviles usados adecuados que estén disponibles actualmente:

    Preferencias del usuario:
    - Marca y modelo: {info_usuario['marca_modelo']}
    - Rango de años: {info_usuario['rango_años']}
    - Presupuesto máximo: {info_usuario['presupuesto']}
    - Estados de EE.UU.: {', '.join(info_usuario['estados'])}
    - Características específicas: {info_usuario['caracteristicas']}
    - Interés en vehículos chocados o con percances: {"Sí" if info_usuario['interes_chocados'] else "No"}

    {contexto}

    Por favor, proporciona una respuesta detallada en español con:
    1. Los automóviles usados más relevantes que coincidan con las preferencias del usuario y estén dentro del presupuesto máximo especificado.
    2. Para cada vehículo descrito, proporciona un enlace directo y específico al anuncio de ese vehículo en particular, asegurándote de que el enlace sea válido y esté activo.
    3. Precio de cada vehículo, asegurándote de que no exceda el presupuesto máximo del usuario.
    4. Breves descripciones de las características principales de cada vehículo.
    5. Si el usuario está interesado en vehículos chocados, menciona cualquier información relevante sobre el estado del vehículo y los posibles riesgos o beneficios.
    6. Cualquier consejo adicional para el usuario basado en sus preferencias.

    Asegúrate de incluir solo vehículos que estén disponibles actualmente en los estados seleccionados por el usuario y que estén dentro del presupuesto especificado.
    Verifica cuidadosamente que los enlaces proporcionados sean correctos y conduzca al vehículo exacto descrito.
    """

    mensajes = [
        {"role": "system", "content": "Eres un experto en búsqueda de automóviles usados."},
        {"role": "user", "content": prompt},
    ]

    respuesta = obtener_respuesta_llm(mensajes)

    with st.chat_message("assistant"):
        st.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    st.session_state.etapa_dialogo += 1
