import streamlit as st
from PIL import Image
import base64
import requests
import os
import io
import numpy as np
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
    page_title="GeoSeismicAI – UCE",
    layout="wide"
)

# URL DE TU WEBHOOK EN N8N
BACKEND_ENDPOINT = "https://soniagualan.app.n8n.cloud/webhook-test/seismic-upload"

# --------------------------------------------------
# 2. FUNCIONES DE GENERACIÓN DE PDF (MODIFICADO: IMÁGENES HORIZONTALES)
# --------------------------------------------------
def build_pdf(out_path, logo_left_path, logo_right_path, titulo_reporte, img_original_path, img_resultado_path, texto):
    """
    Genera un PDF multipágina con imágenes dispuestas horizontalmente.
    """
    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(out_path, pagesize=A4)
    W, H = A4
    M = 40              # Margen
    MARGIN_BOTTOM = 50  # Margen inferior para salto

    # --- HELPER: DIBUJAR ENCABEZADO ---
    def draw_header(c):
        y_top = H - M
        
        def draw_logo_header(path, x, y_pos, size=70):
            p = Path(path)
            if p.exists():
                try:
                    c.drawImage(ImageReader(str(p)), x, y_pos - size, width=size, height=size, mask="auto")
                except Exception: pass

        draw_logo_header(logo_left_path, M, y_top, 70)
        draw_logo_header(logo_right_path, W - M - 70, y_top, 70)

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 20, "Universidad Central del Ecuador")
        c.setFont("Helvetica", 11)
        c.drawCentredString(W / 2, y_top - 38, "Carrera de Geología")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, y_top - 58, "GeoSeismicAI")
        c.drawCentredString(W / 2, y_top - 78, titulo_reporte)

        c.line(M, y_top - 95, W - M, y_top - 95)
        return y_top - 115

    # --- HELPER: VERIFICAR ESPACIO (SALTO DE PÁGINA) ---
    def check_space(c, current_y, needed_space):
        if current_y - needed_space < MARGIN_BOTTOM:
            c.setFont("Helvetica-Oblique", 9)
            c.drawCentredString(W / 2, 25, 'Continúa en la siguiente página...')
            c.showPage()
            return draw_header(c)
        return current_y

    # --- HELPER: DIBUJAR TEXTO LARGO ---
    def draw_smart_text(c, x, y, text, max_chars=100, line_height=12):
        c.setFont("Helvetica", 10)
        text_safe = str(text) if text else "Sin descripción."
        for paragraph in text_safe.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                y -= line_height
                y = check_space(c, y, line_height)
                continue
            words = paragraph.split()
            line = ""
            for w in words:
                test_line = (line + " " + w).strip()
                if len(test_line) <= max_chars:
                    line = test_line
                else:
                    y = check_space(c, y, line_height)
                    c.drawString(x, y, line)
                    y -= line_height
                    line = w
            if line:
                y = check_space(c, y, line_height)
                c.drawString(x, y, line)
                y -= line_height
            y -= 4
        return y

    # --- NUEVO HELPER: DIBUJAR IMAGEN EN UNA CAJA ESPECÍFICA ---
    # Este helper coloca la imagen en una posición X dada, ajustándola a un ancho/alto máximo
    def draw_image_side_by_side(c, path, x_pos, y_top, box_width, box_height):
        p = Path(path)
        if not p.exists():
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(x_pos, y_top - 10, "[Img no encontrada]")
            return y_top - 20
        
        try:
            img = ImageReader(str(p))
            iw, ih = img.getSize()
            # Calcular escala para que quepa en la caja
            scale = min(box_width / iw, box_height / ih)
            nw, nh = iw * scale, ih * scale
            
            # Centrar horizontalmente dentro de su caja
            x_centered = x_pos + (box_width - nw) / 2
            
            # Dibujar imagen
            c.drawImage(img, x_centered, y_top - nh, width=nw, height=nh, mask="auto")
            
            # Retornar la posición Y inferior real de esta imagen
            return y_top - nh
        except:
            return y_top - 20

    # ================= EJECUCIÓN DEL REPORTE =================
    
    # 1. Inicializar primera página
    y = draw_header(c)

    # --- SECCIÓN DE IMÁGENES HORIZONTALES ---
    
    # Configuración de dimensiones
    GAP = 20 # Espacio entre las dos imágenes
    available_width = W - 2 * M
    img_box_width = (available_width - GAP) / 2 # Ancho para cada imagen
    max_img_height = 180 # Altura máxima permitida

    # Verificar espacio para todo el bloque (título + imágenes)
    y = check_space(c, y, 30 + max_img_height)

    # Título unificado
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "1) Análisis Visual: Sección Original (Izq.) vs. Interpretación (Der.)")
    y -= 20 # Bajar Y para empezar a dibujar imágenes

    # Coordenadas X para izquierda y derecha
    x_left = M
    x_right = M + img_box_width + GAP

    # Dibujar Imagen Izquierda (Original) y obtener su Y inferior
    y_bottom1 = draw_image_side_by_side(c, img_original_path, x_left, y, img_box_width, max_img_height)

    # Dibujar Imagen Derecha (Procesada) y obtener su Y inferior
    y_bottom2 = draw_image_side_by_side(c, img_resultado_path, x_right, y, img_box_width, max_img_height)

    # El nuevo Y será el punto más bajo de las dos imágenes más un margen
    y = min(y_bottom1, y_bottom2) - 25


    # --- SECCIÓN DE TEXTO ---
    # 2. Interpretación (Texto)
    y = check_space(c, y, 20)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "2) Interpretación Geológica")
    y -= 15
    
    # Llamamos a la función inteligente de texto
    y = draw_smart_text(c, M, y, texto, max_chars=100, line_height=12)

    # Pie de página final
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, 25, 'Procesado con "GeoSeismicAI"')

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
    if mask.ndim == 3:
        mask_gray = mask[:, :, 0]
    else:
        mask_gray = mask

    colored_mask = np.zeros((mask_gray.shape[0], mask_gray.shape[1], 3), dtype=np.uint8)

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

def create_overlay_from_mask(img_original, mask_img, alpha=0.4):
    base = np.array(img_original).astype(np.float32)
    mask = np.array(mask_img).astype(np.float32)
    if base.shape != mask.shape:
        mask = np.array(mask_img.resize(img_original.size)).astype(np.float32)
    mask_gray = mask.mean(axis=2)
    mask_area = mask_gray > 5
    overlay = base.copy()
    overlay[mask_area] = (
        (1 - alpha) * base[mask_area] +
        alpha * mask[mask_area]
    )
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)
    return Image.fromarray(overlay)

# --------------------------------------------------
# 4. CARGA DE LOGOS
# --------------------------------------------------
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
    if uce_b64: st.markdown(f"<img src='data:image/jpg;base64,{uce_b64}' width='200'>", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="header">
        <h2>Universidad Central del Ecuador</h2>
        <h3>FIGEMPA</h3>
        <h4>Carrera de Geología</h4>
        <h1>GeoSeismicAI</h1>
    </div>
    """, unsafe_allow_html=True)
with c3:
    if geo_b64: st.markdown(f"<img src='data:image/jpg;base64,{geo_b64}' width='200' style='float:right'>", unsafe_allow_html=True)
st.markdown("<div class='linea'></div>", unsafe_allow_html=True)

# --------------------------------------------------
# 7. DESCRIPCIÓN
# --------------------------------------------------
st.markdown("""
<div class="bloque">
<b>GeoSeismicAI</b> es una herramienta académica para el <b>análisis automático de líneas sísmicas</b>.
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
                archivo.seek(0)
                image_bytes = archivo.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                payload = { "image": image_base64, "filename": archivo.name, "mode": "standard" }
                response = requests.post(BACKEND_ENDPOINT, json=payload, timeout=180)

                if response.status_code != 200:
                    st.error(f"Error en el servidor (n8n): {response.status_code}.")
                else:
                    st.success("Análisis completado exitosamente.")
                    try: 
                        result = response.json()
                        texto_analisis = (result.get("texto_analisis") or result.get("technical_report") or result.get("text") or "Sin análisis generado.")
                        mask_b64 = (result.get("imagen_procesada") or result.get("mask") or result.get("image"))
                        if mask_b64 and "," in mask_b64: mask_b64 = mask_b64.split(",")[1]

                        st.markdown("<div class='titulo_azul'>Resultados del análisis</div>", unsafe_allow_html=True)
                        st.write("---")

                        col_res1, col_res2 = st.columns([1, 1])
                        temp_orig_path = "temp_original.png"
                        temp_proc_path = "temp_procesada.png"
                        pdf_path = "Reporte_GeoSeismicAI.pdf"

                        img_original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                        img_original.save(temp_orig_path)

                        with col_res1:
                            st.subheader("Mapa de Sismofacies")
                            if mask_b64:
                                mask_img = Image.open(io.BytesIO(base64.b64decode(mask_b64))).convert("RGB")
                                mask_array = np.array(mask_img)
                                mask_colored = colorize_mask(mask_array)
                                overlay_img = create_overlay_from_mask(img_original, Image.fromarray(mask_colored), alpha=0.4)
                                st.image(overlay_img, caption="Segmentación IA (Overlay)", use_container_width=True)
                                overlay_img.save(temp_proc_path)
                            else:
                                st.warning("No se recibió máscara procesada. Se usa la imagen original.")
                                img_original.save(temp_proc_path)

                        with col_res2:
                            st.subheader("Interpretación Geológica")
                            st.info(texto_analisis)
                        
                        build_pdf(out_path=pdf_path, logo_left_path=LOGO_UCE_PATH, logo_right_path=LOGO_GEO_PATH,
                                  titulo_reporte="Análisis de Sismofacies", img_original_path=temp_orig_path,
                                  img_resultado_path=temp_proc_path, texto=texto_analisis)
                        
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(label="📄 Descargar Reporte PDF Oficial", data=pdf_file.read(),
                                                   file_name="Reporte_GeoSeismicAI.pdf", mime="application/pdf")
                    except ValueError: st.warning("El servidor respondió pero el formato no es JSON válido.")
                    except Exception as e: st.error(f"Error procesando resultados: {str(e)}")          
            except Exception as e: st.error(f"Fallo de conexión: {str(e)}")

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
