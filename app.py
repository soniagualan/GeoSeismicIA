import streamlit as st
from PIL import Image
import base64
import requests
import os
import io
import numpy as np  # Asegúrate de tener numpy instalado
from pathlib import Path
from datetime import datetime

# --- LIBRERÍAS PARA PDF ---
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# --------------------------------------------------
# 1. CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="GeoSismicIA – UCE",
    layout="wide"
)

# URL DE TU WEBHOOK EN N8N
BACKEND_ENDPOINT = "https://soniagualan.app.n8n.cloud/webhook-test/seismic-upload"

# --------------------------------------------------
# 2. FUNCIONES DE GENERACIÓN DE PDF (MODIFICADO PARA PAGINACIÓN)
# --------------------------------------------------
def build_pdf(out_path, logo_left_path, logo_right_path, titulo_reporte, img_original_path, img_resultado_path, texto):
    """
    Genera un PDF multipágina. Si el contenido excede una hoja, crea una nueva automáticamente.
    """
    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(out_path, pagesize=A4)
    W, H = A4
    M = 40          # Margen izquierdo/derecho
    MARGIN_BOTTOM = 50  # Margen inferior antes de saltar de página

    # --- FUNCIÓN INTERNA: DIBUJAR ENCABEZADO ---
    # Esta función se llamará cada vez que creemos una página nueva
    def draw_header(c):
        y_top = H - M
        
        # Función auxiliar para poner logos
        def draw_logo_header(path, x, y_pos, size=70):
            p = Path(path)
            if p.exists():
                try:
                    c.drawImage(ImageReader(str(p)), x, y_pos - size, width=size, height=size, mask="auto")
                except Exception:
                    pass

        # Dibujar Logos
        draw_logo_header(logo_left_path, M, y_top, 70)
        draw_logo_header(logo_right_path, W - M - 70, y_top, 70)

        # Texto del Encabezado
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 20, "Universidad Central del Ecuador")
        c.setFont("Helvetica", 11)
        c.drawCentredString(W / 2, y_top - 38, "Carrera de Geología")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 58, "GeoSismicIA")
        c.drawCentredString(W / 2, y_top - 78, titulo_reporte)

        # Línea divisoria
        c.line(M, y_top - 95, W - M, y_top - 95)
        
        # Retorna la posición Y donde empezaremos a escribir contenido
        return y_top - 115

    # --- FUNCIÓN INTERNA: VERIFICAR ESPACIO (SALTO DE PÁGINA) ---
    def check_space(c, current_y, needed_space):
        """
        Si la posición actual (current_y) menos el espacio necesario es menor al margen,
        crea una nueva página y reinicia el encabezado.
        """
        if current_y - needed_space < MARGIN_BOTTOM:
            # Pie de página antes de saltar
            c.setFont("Helvetica-Oblique", 9)
            c.drawCentredString(W / 2, 25, 'Continúa en la siguiente página...')
            
            c.showPage() # <--- AQUÍ SE CREA LA NUEVA HOJA
            return draw_header(c) # <--- DIBUJA EL ENCABEZADO Y RETORNA LA Y DE ARRIBA
        return current_y

    # --- FUNCIÓN INTERNA: DIBUJAR TEXTO LARGO ---
    def draw_smart_text(c, x, y, text, max_chars=100, line_height=12):
        c.setFont("Helvetica", 10)
        text_safe = str(text) if text else "Sin descripción."
        
        # Procesar por párrafos
        for paragraph in text_safe.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                y -= line_height
                y = check_space(c, y, line_height) # Chequeo rápido
                continue

            # Procesar palabra por palabra para ajustar ancho
            words = paragraph.split()
            line = ""
            for w in words:
                test_line = (line + " " + w).strip()
                # Si la línea cabe, seguimos sumando palabras
                if len(test_line) <= max_chars:
                    line = test_line
                else:
                    # Si no cabe, imprimimos la línea actual
                    y = check_space(c, y, line_height) # ¿Cabe en la hoja?
                    c.drawString(x, y, line)
                    y -= line_height
                    line = w # La palabra que sobró inicia la nueva línea
            
            # Imprimir lo que quedó en el buffer 'line'
            if line:
                y = check_space(c, y, line_height)
                c.drawString(x, y, line)
                y -= line_height
            
            y -= 4 # Espacio extra entre párrafos
        return y

    # --- FUNCIÓN INTERNA: DIBUJAR IMAGEN ---
    def draw_smart_image(c, path, x, y, max_h=200):
        p = Path(path)
        if not p.exists():
            c.drawString(x, y, "[Imagen no encontrada]")
            return y - 20
        
        # Verificamos si la imagen cabe completa
        y = check_space(c, y, max_h + 30)

        try:
            img = ImageReader(str(p))
            iw, ih = img.getSize()
            max_w = W - 2 * M
            scale = min(max_w / iw, max_h / ih)
            nw, nh = iw * scale, ih * scale
            
            # Dibujamos imagen centrada
            c.drawImage(img, x + (max_w - nw) / 2, y - nh, width=nw, height=nh, mask="auto")
            return y - nh
        except:
            return y - 20

    # ================= EJECUCIÓN DEL REPORTE =================
    
    # 1. Inicializar primera página
    y = draw_header(c)

    # 2. Imagen Original
    y = check_space(c, y, 20)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "1) Sección sísmica original")
    y -= 15
    y = draw_smart_image(c, img_original_path, M, y, max_h=200)
    y -= 15

    # 3. Imagen Procesada
    y = check_space(c, y, 20)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "2) Interpretación de Sismofacies (IA)")
    y -= 15
    y = draw_smart_image(c, img_resultado_path, M, y, max_h=200)
    y -= 15

    # 4. Interpretación (Texto) - AQUÍ ES DONDE SUELE OCURRIR EL CORTE
    y = check_space(c, y, 20)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "3) Interpretación Geológica")
    y -= 15
    
    # Llamamos a la función inteligente de texto
    y = draw_smart_text(c, M, y, texto, max_chars=100, line_height=12)

    # Pie de página final
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, 25, 'Procesado con "GeoSismicIA"')

    c.showPage()
    c.save()

# --------------------------------------------------
# 3. FUNCIONES AUXILIARES
# --------------------------------------------------
def img_to_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def colorize_mask(mask):
    """
    Convierte una máscara de clases (0–13) a una máscara RGB con 14 colores
    """
    if mask.ndim == 3:
        mask_gray = mask[:, :, 0]
    else:
        mask_gray = mask

    colored_mask = np.zeros((mask_gray.shape[0], mask_gray.shape[1], 3), dtype=np.uint8)

    # Diccionario CLASE → COLOR (RGB)
    class_colors = {
        0:  (0, 0, 0),         # Fondo
        1:  (165, 42, 42),     # Caotico_AA_FB_D
        2:  (0, 0, 255),       # Caotico_AB_FB_D
        3:  (128, 0, 128),     # Paralelo_contorsionado_AA_FA_D
        4:  (245, 222, 179),   # Paralelo_contorsionado_AB_FB_C
        5:  (255, 165, 0),     # Paralelo_AA_FA_C
        6:  (255, 255, 0),     # Paralelo_AA_FB_C
        7:  (0, 255, 255),     # Paralelo_AB_FA_C
        8:  (255, 0, 255),     # Paralelo_AB_FB_C
        9:  (220, 20, 60),     # Paralelo_AB_FB_D
        10: (0, 0, 200),       # Subparalelo_AA_FA_C
        11: (255, 182, 193),   # Subparalelo_AA_FA_D
        12: (255, 69, 0),      # Subparalelo_AA_FB_D
        13: (0, 255, 180),     # Subparalelo_AB_FB_D
        14: (34, 139, 34),     # Subparalelo_AB_FA_D
    }

    for class_id, color in class_colors.items():
        colored_mask[mask_gray == class_id] = color

    return colored_mask

def create_overlay_from_mask(img_original, mask_img, alpha=0.6):
    """
    Crea un overlay respetando EXACTAMENTE los colores de la máscara.
    """
    # Convertir a arrays
    base = np.array(img_original).astype(np.float32)
    mask = np.array(mask_img).astype(np.float32)

    # Normalizar tamaños por seguridad
    if base.shape != mask.shape:
        mask = np.array(mask_img.resize(img_original.size)).astype(np.float32)

    # Detectar píxeles de máscara (no negros)
    mask_gray = mask.mean(axis=2)
    mask_area = mask_gray > 5  # umbral bajo

    # Copia base
    overlay = base.copy()

    # Mezcla SOLO donde hay máscara
    overlay[mask_area] = (
        (1 - alpha) * base[mask_area] +
        alpha * mask[mask_area]
    )

    overlay = np.clip(overlay, 0, 255).astype(np.uint8)
    return Image.fromarray(overlay)

# --------------------------------------------------
# 4. CARGA DE LOGOS
# --------------------------------------------------
# Rutas a los assets
LOGO_UCE_PATH = "assets/uce.png"
LOGO_GEO_PATH = "assets/geologia.png"

uce_b64 = img_to_base64(LOGO_UCE_PATH)
geo_b64 = img_to_base64(LOGO_GEO_PATH)

# --------------------------------------------------
# 5. ESTILOS CSS
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
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 6. ENCABEZADO INSTITUCIONAL
# --------------------------------------------------
c1, c2, c3 = st.columns([1, 6, 1])

with c1:
    if uce_b64:
        st.markdown(f"<img src='data:image/jpg;base64,{uce_b64}' width='200'>", unsafe_allow_html=True)

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
    if geo_b64:
        st.markdown(f"<img src='data:image/jpg;base64,{geo_b64}' width='200' style='float:right'>", unsafe_allow_html=True)

st.markdown("<div class='linea'></div>", unsafe_allow_html=True)

# --------------------------------------------------
# 7. DESCRIPCIÓN
# --------------------------------------------------
st.markdown("""
<div class="bloque">
<b>GeoSismicIA</b> es una herramienta académica para el <b>análisis automático de líneas sísmicas</b>.
<br><br>
El sistema procesa la imagen de forma autónoma (N8N + IA Agéntica) y entrega resultados preliminares para apoyo didáctico.
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 8. INPUT DE USUARIO
# --------------------------------------------------
st.markdown("<div class='titulo_azul'>Carga de línea sísmica</div>", unsafe_allow_html=True)
st.markdown("<div class='bloque'>", unsafe_allow_html=True)

archivo = st.file_uploader("Selecciona una línea sísmica (PNG / JPG)", type=["png", "jpg", "jpeg"])

st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# 9. VISTA PREVIA
# --------------------------------------------------
if archivo is not None:
    img = Image.open(archivo).convert("RGB")
    st.subheader("Vista previa de la línea sísmica")
    st.image(img, use_container_width=True)

# --------------------------------------------------
# 10. LÓGICA DE ENVÍO, PROCESAMIENTO Y REPORTE
# --------------------------------------------------
if archivo is not None:
    if st.button("Analizar línea sísmica"):
        with st.spinner("Conectando con el Orquestador N8N y generando reporte..."):
            try:
                # A. Preparar imagen
                archivo.seek(0)
                image_bytes = archivo.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                payload = {
                    "image": image_base64,
                    "filename": archivo.name,
                    "mode": "standard"
                }

                # B. Enviar a N8N
                response = requests.post(BACKEND_ENDPOINT, json=payload, timeout=180)

                if response.status_code != 200:
                    st.error(f"Error en el servidor (n8n): {response.status_code}.")
                else:
                    st.success("Análisis completado exitosamente.")
                                        
                    try: 
                        result = response.json()

                        # --- EXTRACCIÓN DE DATOS ---
                        # Texto: Buscamos 'texto_analisis', 'technical_report', etc.
                        texto_analisis = (
                            result.get("texto_analisis")
                            or result.get("technical_report")
                            or result.get("text")
                            or "Sin análisis generado."
                        )

                        # Imagen Procesada (Máscara)
                        mask_b64 = (
                            result.get("imagen_procesada")
                            or result.get("mask")
                            or result.get("image") # En caso de que n8n mande 'image'
                        )

                        # Limpieza Base64
                        if mask_b64 and "," in mask_b64:
                            mask_b64 = mask_b64.split(",")[1]

                        # --- MOSTRAR RESULTADOS EN PANTALLA ---
                        st.markdown(
                            "<div class='titulo_azul'>Resultados del análisis</div>",
                            unsafe_allow_html=True
                        )
                        st.write("---")

                        col_res1, col_res2 = st.columns([1, 1])

                        temp_orig_path = "temp_original.png"
                        temp_proc_path = "temp_procesada.png"
                        pdf_path = "Reporte_GeoSismicAI.pdf"

                        # Guardar imagen original
                        img_original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                        img_original.save(temp_orig_path)

                        # ===============================
                        # COLUMNA 1 — IMÁGENES (OVERLAY)
                        # ===============================
                        with col_res1:
                            st.subheader("Mapa de Sismofacies")

                            if mask_b64:
                                # Decodificar máscara que viene de n8n
                                mask_img = Image.open(
                                    io.BytesIO(base64.b64decode(mask_b64))
                                ).convert("RGB")

                                # Convertir máscara de clases a colores (función auxiliar)
                                mask_array = np.array(mask_img)
                                mask_colored = colorize_mask(mask_array)

                                # Crear overlay
                                overlay_img = create_overlay_from_mask(
                                     img_original,
                                     Image.fromarray(mask_colored),
                                     alpha=0.6 # Transparencia
                                )

                                st.image(
                                    overlay_img,
                                    caption="Segmentación IA (Overlay)",
                                    use_container_width=True
                                )

                                # Guardamos el overlay para el PDF
                                overlay_img.save(temp_proc_path)
                            else:
                                st.warning("No se recibió máscara procesada. Se usa la imagen original.")
                                img_original.save(temp_proc_path)

                        # ===============================
                        # COLUMNA 2 — TEXTO
                        # ===============================
                        with col_res2:
                            st.subheader("Interpretación Geológica")
                            st.info(texto_analisis)
                        
                        # --- GENERACIÓN DEL PDF ---
                        build_pdf(
                            out_path=pdf_path,
                            logo_left_path=LOGO_UCE_PATH,
                            logo_right_path=LOGO_GEO_PATH,
                            titulo_reporte="Análisis de Sismofacies",
                            img_original_path=temp_orig_path,
                            img_resultado_path=temp_proc_path,
                            texto=texto_analisis
                        )
                        
                        # --- BOTÓN DE DESCARGA ---
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="📄 Descargar Reporte PDF Oficial",
                                    data=pdf_file.read(),
                                    file_name="Reporte_GeoSismicIA.pdf",
                                    mime="application/pdf"
                                )

                    except ValueError:
                        st.warning("El servidor respondió pero el formato no es JSON válido.")
                    except Exception as e:
                         st.error(f"Error procesando resultados: {str(e)}")          
            except Exception as e:
                st.error(f"Fallo de conexión: {str(e)}")

# --------------------------------------------------
# 11. PIE DE PÁGINA
# --------------------------------------------------
st.markdown("<div class='linea'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="bloque">
<b>Enfoque académico</b><br>
Aplicación diseñada como trabajo final de Software Aplicado a Geología - Universidad Central del Ecuador.
</div>
""", unsafe_allow_html=True)
