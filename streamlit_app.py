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
if st.session_state.etapa_dialogo < len(preguntas):
    # Mostrar la pregunta actual
    with st.chat_message("assistant"):
        st.markdown(preguntas[st.session_state.etapa_dialogo])
    
    # Esperar la respuesta del usuario
    if st.session_state.etapa_dialogo == 3:  # Pregunta sobre los estados
        respuesta_usuario = st.multiselect("Selecciona uno o más estados:", estados_eeuu, key=f"multiselect_{st.session_state.etapa_dialogo}")
    else:
        respuesta_usuario = st.text_input("Tu respuesta aquí", key=f"input_{st.session_state.etapa_dialogo}")
    
    # Procesar la respuesta cuando se presiona Enter
    if respuesta_usuario:
        # Mostrar la respuesta del usuario
        with st.chat_message("user"):
            if isinstance(respuesta_usuario, list):
                st.markdown(", ".join(respuesta_usuario))
            else:
                st.markdown(respuesta_usuario)
        
        # Guardar la respuesta
        if isinstance(respuesta_usuario, list):
            respuesta_guardada = ", ".join(respuesta_usuario)
        else:
            respuesta_guardada = respuesta_usuario

        st.session_state.mensajes.append({"role": "user", "content": respuesta_guardada})
        
        if st.session_state.etapa_dialogo == 0:
            st.session_state.info_usuario["marca_modelo"] = respuesta_guardada
        elif st.session_state.etapa_dialogo == 1:
            st.session_state.info_usuario["rango_años"] = respuesta_guardada
        elif st.session_state.etapa_dialogo == 2:
            st.session_state.info_usuario["presupuesto"] = respuesta_guardada
        elif st.session_state.etapa_dialogo == 3:
            st.session_state.info_usuario["estados"] = respuesta_usuario  # Guardamos la lista de estados seleccionados
        elif st.session_state.etapa_dialogo == 4:
            st.session_state.info_usuario["caracteristicas"] = respuesta_guardada
        
        # Avanzar a la siguiente etapa
        st.session_state.etapa_dialogo += 1
        st.rerun()

elif st.session_state.etapa_dialogo == len(preguntas):
    # Checkbox para vehículos chocados
    st.session_state.info_usuario["interes_chocados"] = st.checkbox("¿Estás interesado en vehículos que hayan sufrido choques o percances y que por eso estén en venta a precios muy bajos?")

    # Procesar la información y buscar automóviles
    info_usuario = st.session_state.info_usuario
    estados_seleccionados = " OR ".join(info_usuario['estados'])
    consulta_busqueda = f"used {info_usuario['marca_modelo']} for sale {info_usuario['rango_años']} under {info_usuario['presupuesto']} in ({estados_seleccionados}) {info_usuario['caracteristicas']}"
    
    if info_usuario['interes_chocados']:
        consulta_busqueda += " salvage title"

    try:
        resultados_busqueda = busqueda_google(consulta_busqueda)
    except Exception as e:
        st.error(f"Error durante la búsqueda en Google: {str(e)}")
        resultados_busqueda = {"organic": []}

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
    Verifica cuidadosamente que los enlaces proporcionados sean correctos y lleven a páginas de anuncios existentes y relevantes.
    """

    mensajes = [
        {"role": "system", "content": "Eres un asistente de búsqueda de automóviles usados muy útil. Proporciona información detallada y precisa sobre vehículos basada en las preferencias del usuario y los resultados de la búsqueda. Responde siempre en español y asegúrate de incluir solo vehículos disponibles actualmente en los estados seleccionados por el usuario y dentro del presupuesto especificado. Para cada vehículo descrito, proporciona un enlace directo y específico al anuncio de ese vehículo en particular, verificando que el enlace sea válido y esté activo."},
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
                respuesta_completa = "Lo siento, no pude encontrar automóviles usados que coincidan con tus criterios. Por favor, intenta ampliar tu búsqueda o consultar más tarde."

        except Exception as e:
            respuesta_completa = f"Ocurrió un error al procesar tu solicitud: {str(e)}"

        marcador_mensaje.markdown(respuesta_completa)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta_completa})
    st.session_state.etapa_dialogo += 1

# Botón para iniciar una nueva búsqueda de automóviles
if st.button("Iniciar nueva búsqueda de automóviles"):
    st.session_state.mensajes = []
    st.session_state.info_usuario = {}
    st.session_state.etapa_dialogo = 0
    st.rerun()
