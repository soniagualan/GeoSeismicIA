import streamlit as st
from PIL import Image
import base64
import requests
import os

# --------------------------------------------------
# 1. CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="GeoSismicIA – UCE",
    layout="wide"
)

# URL DE TU WEBHOOK EN N8N (Producción)
BACKEND_ENDPOINT = "https://soniagualan.app.n8n.cloud/webhook-test/seismic-upload"

# --------------------------------------------------
# 2. FUNCIONES AUXILIARES
# --------------------------------------------------
def img_to_base64(path):
    """Convierte una imagen local a base64 para mostrarla en HTML."""
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# --------------------------------------------------
# 3. CARGA DE LOGOS
# --------------------------------------------------
# Asegúrate de que la carpeta 'assets' exista junto a este archivo
uce_b64 = img_to_base64("assets/uce.jpg")
geo_b64 = img_to_base64("assets/geologia.jpg")

# --------------------------------------------------
# 4. ESTILOS CSS
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
# 5. ENCABEZADO INSTITUCIONAL
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
# 6. DESCRIPCIÓN
# --------------------------------------------------
st.markdown("""
<div class="bloque">
<b>GeoSismicIA</b> es una herramienta académica para el
<b>análisis automático de líneas sísmicas</b>.
<br><br>
El sistema procesa la imagen de forma autónoma (N8N + IA Agéntica) y entrega
resultados preliminares para apoyo didáctico.
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 7. INPUT DE USUARIO (SUBIDA DE ARCHIVO)
# --------------------------------------------------
st.markdown("<div class='titulo_azul'>Carga de línea sísmica</div>", unsafe_allow_html=True)
st.markdown("<div class='bloque'>", unsafe_allow_html=True)

archivo = st.file_uploader(
    "Selecciona una línea sísmica (PNG / JPG)",
    type=["png", "jpg", "jpeg"]
)

st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# 8. VISTA PREVIA
# --------------------------------------------------
if archivo is not None:
    # Mostramos la imagen cargada
    img = Image.open(archivo).convert("RGB")
    st.subheader("Vista previa de la línea sísmica")
    st.image(img, use_container_width=True)

# --------------------------------------------------
# 9. LÓGICA DE ENVÍO Y PROCESAMIENTO
# --------------------------------------------------
if archivo is not None:
    if st.button("Analizar línea sísmica"):
        with st.spinner("Conectando con el Orquestador N8N..."):
            try:
                # A. PREPARAR LA IMAGEN (Convertir a Base64)
                archivo.seek(0)
                image_bytes = archivo.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                # B. CREAR EL PAQUETE JSON (Payload)
                # Esto es lo que leerá n8n con {{ $json.body.image }}
                payload = {
                    "image": image_base64,
                    "filename": archivo.name,
                    "mode": "standard"
                }

                # C. ENVIAR A N8N (POST request)
                # Usamos json=payload para asegurar el formato correcto
                response = requests.post(
                    BACKEND_ENDPOINT,
                    json=payload, 
                    timeout=180  # 3 minutos de espera máx.
                )

                # D. VALIDAR RESPUESTA HTTP
                if response.status_code != 200:
                    st.error(f"Error en el servidor (n8n): {response.status_code}. Verifica que el workflow esté activo.")
                else:
                    st.success("Análisis completado exitosamente.")
                    
                    try:
                        # E. PROCESAR RESPUESTA JSON DE N8N
                        result = response.json()

                        st.markdown("<div class='titulo_azul'>Resultados del análisis</div>", unsafe_allow_html=True)
                        st.write("---")

                        # 1. MOSTRAR IMAGEN PROCESADA (Si existe)
                        if "imagen_procesada" in result:
                            img_data = result["imagen_procesada"]
                            # Limpieza defensiva por si viene con header data:image
                            if "," in img_data:
                                img_data = img_data.split(",")[1]
                                
                            st.subheader("Interpretación de Sismofacies")
                            st.image(
                                base64.b64decode(img_data),
                                caption="Resultado generado por IA",
                                use_container_width=True
                            )

                        # 2. MOSTRAR DESCRIPCIÓN (Si existe)
                        if "descripcion" in result:
                            st.subheader("Informe Técnico Preliminar")
                            st.info(result["descripcion"])

                        # 3. BOTÓN DE DESCARGA PDF (Si existe)
                        if "pdf" in result:
                            pdf_data = result["pdf"]
                            if "," in pdf_data:
                                pdf_data = pdf_data.split(",")[1]

                            st.download_button(
                                label="📥 Descargar Informe Completo (PDF)",
                                data=base64.b64decode(pdf_data),
                                file_name="reporte_sismico_final.pdf",
                                mime="application/pdf"
                            )

                    except ValueError:
                        st.warning("El servidor n8n respondió (200 OK) pero no envió un JSON válido. Revisa el nodo final 'Respond to Webhook'.")

            except Exception as e:
                st.error(f"Fallo crítico de conexión: {str(e)}")

# --------------------------------------------------
# 10. PIE DE PÁGINA
# --------------------------------------------------
st.markdown("<div class='linea'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="bloque">
<b>Enfoque académico</b><br>
Aplicación diseñada como tesis de grado - Universidad Central del Ecuador.
</div>
""", unsafe_allow_html=True)
