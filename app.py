import streamlit as st
from PIL import Image
import base64
import requests
import os

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="GeoSismicIA – UCE",
    layout="wide"
)

BACKEND_ENDPOINT = "https://soniagualan.app.n8n.cloud/webhook/seismic-upload"

# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------
def img_to_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# --------------------------------------------------
# CARGA DE LOGOS (Manejo de errores si no existen)
# --------------------------------------------------
uce_b64 = img_to_base64("assets/uce.jpg")
geo_b64 = img_to_base64("assets/geologia.jpg")

# --------------------------------------------------
# ESTILOS
# --------------------------------------------------
st.markdown("""
<style>
body { font-family: Arial; }
.header {
    background-color: #0B3C5D;
    padding: 16px;
    border-radius: 14px;
    color: white;
    text-align: center;
}
.linea {
    border-top: 3px solid #0B3C5D;
    margin: 18px 0;
}
.bloque {
    background-color: #F4F6F8;
    padding: 18px;
    border-radius: 12px;
}
.titulo_azul {
    background-color:#0B3C5D;
    color:white;
    padding:10px 14px;
    border-radius:10px;
    font-weight:bold;
}
.small_note {
    font-size: 13px;
    color: #334155;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# ENCABEZADO
# --------------------------------------------------
c1, c2, c3 = st.columns([1, 6, 1])

with c1:
    if geo_b64:
        st.markdown(
            f"<img src='data:image/jpg;base64,{geo_b64}' width='110'>",
            unsafe_allow_html=True
        )

with c2:
    st.markdown("""
    <div class="header">
        <h2>Universidad Central del Ecuador</h2>
        <h3>Facultad de Ingeniería en Geología</h3>
        <h4>Carrera de Geología</h4>
        <h1>GeoSismicIA</h1>
    </div>
    """, unsafe_allow_html=True)

with c3:
    if uce_b64:
        st.markdown(
            f"<img src='data:image/jpg;base64,{uce_b64}' width='110' style='float:right'>",
            unsafe_allow_html=True
        )

st.markdown("<div class='linea'></div>", unsafe_allow_html=True)

# --------------------------------------------------
# DESCRIPCIÓN
# --------------------------------------------------
st.markdown("""
<div class="bloque">
<b>GeoSismicIA</b> es una herramienta académica para el
<b>análisis automático de líneas sísmicas</b>.
<br><br>
El sistema procesa la imagen de forma autónoma y entrega
resultados preliminares para apoyo didáctico.
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# INPUT DE USUARIO
# --------------------------------------------------
st.markdown("<div class='titulo_azul'>Carga de línea sísmica</div>", unsafe_allow_html=True)
st.markdown("<div class='bloque'>", unsafe_allow_html=True)

archivo = st.file_uploader(
    "Selecciona una línea sísmica (PNG / JPG)",
    type=["png", "jpg", "jpeg"]
)

st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# VISTA PREVIA
# --------------------------------------------------
if archivo is not None:
    img = Image.open(archivo).convert("RGB")
    st.subheader("Vista previa de la línea sísmica")
    st.image(img, use_container_width=True)

# --------------------------------------------------
# LÓGICA DE ENVÍO Y PROCESAMIENTO
# --------------------------------------------------
if archivo is not None:
    if st.button("Analizar línea sísmica"):
        with st.spinner("Analizando línea sísmica..."):
            try:
                # REINICIAMOS EL POINTER DEL ARCHIVO PARA LEERLO DESDE CERO
                archivo.seek(0)
                
                response = requests.post(
                    BACKEND_ENDPOINT,
                    files={
                        "data": archivo.getvalue()  # ✅ CAMBIO CRÍTICO: 'data' coincide con n8n
                    },
                    timeout=120  # Tiempo de espera aumentado para procesos de IA
                )

                if response.status_code != 200:
                    st.error(f"Error en el servidor (n8n): {response.status_code} - Verifica que el Webhook esté escuchando.")
                else:
                    st.success("Análisis completado")
                    
                    try:
                        result = response.json()

                        # -----------------------------
                        # RESULTADOS
                        # -----------------------------
                        st.markdown("<div class='titulo_azul'>Resultados del análisis</div>", unsafe_allow_html=True)

                        # IMAGEN PROCESADA
                        if "imagen_procesada" in result:
                            st.image(
                                base64.b64decode(result["imagen_procesada"]),
                                caption="Resultado automático",
                                use_container_width=True
                            )

                        # DESCRIPCIÓN
                        if "descripcion" in result:
                            st.subheader("Descripción preliminar")
                            st.write(result["descripcion"])

                        # PDF
                        if "pdf" in result:
                            st.download_button(
                                "Descargar informe técnico (PDF)",
                                data=base64.b64decode(result["pdf"]),
                                file_name="reporte_sismico.pdf",
                                mime="application/pdf"
                            )
                    except ValueError:
                        st.warning("n8n respondió correctamente (200) pero no devolvió JSON válido. Revisa el nodo final 'Respond to Webhook' en n8n.")

            except Exception as e:
                st.error(f"Fallo de conexión con n8n: {str(e)}")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("<div class='linea'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="bloque">
<b>Enfoque académico</b><br>
Aplicación diseñada como apoyo didáctico para estudiantes de Geología.
</div>
""", unsafe_allow_html=True)
