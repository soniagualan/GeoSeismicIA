import streamlit as st
from PIL import Image
import base64
import requests
import os
import io
import numpy as np
import re  # IMPORTANTE: Para detectar los asteriscos ** y #
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
# 2. FUNCIONES DE GENERACIÓN DE PDF
# --------------------------------------------------
def build_pdf(out_path, logo_left_path, logo_right_path, titulo_reporte, img_original_path, img_resultado_path, texto):
    """
    Genera un PDF multipágina interpretando Markdown básico (# Títulos y **Negritas**).
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

    # --- HELPER: DIBUJAR IMAGEN HORIZONTAL ---
    def draw_image_side_by_side(c, path, x_pos, y_top, box_width, box_height):
        p = Path(path)
        if not p.exists():
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(x_pos, y_top - 10, "[Img no encontrada]")
            return y_top - 20
        
        try:
            img = ImageReader(str(p))
            iw, ih = img.getSize()
            scale = min(box_width / iw, box_height / ih)
            nw, nh = iw * scale, ih * scale
            x_centered = x_pos + (box_width - nw) / 2
            c.drawImage(img, x_centered, y_top - nh, width=nw, height=nh, mask="auto")
            return y_top - nh
        except:
            return y_top - 20

    # --- NUEVO HELPER: DIBUJAR TEXTO CON MARKDOWN (AJUSTADO) ---
    def draw_markdown_text(c, x_start, y_start, full_text, max_width, line_height=14):
        y = y_start
        
        lines = full_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                y -= line_height * 0.5 
                continue

            # --- CASO A: ES UN TÍTULO (#) ---
            if line.startswith('#'):
                clean_line = line.replace('#', '').strip()
                
                # CORRECCIÓN: Tamaño 11 (Menor que el título principal de sección)
                c.setFont("Helvetica-Bold", 11) 
                
                y = check_space(c, y, line_height * 1.5)
                c.drawString(x_start, y, clean_line)
                y -= line_height * 1.5 
                continue

            # --- CASO B: TEXTO NORMAL ---
            c.setFont("Helvetica", 10) # Tamaño base
            
            parts = re.split(r'(\*\*.*?\*\*)', line)
            current_x = x_start
            
            for part in parts:
                if not part: continue
                
                is_bold = part.startswith('**') and part.endswith('**')
                text_content = part.replace('**', '') 
                
                if is_bold:
                    c.setFont("Helvetica-Bold", 10) # Negrita mismo tamaño
                else:
                    c.setFont("Helvetica", 10)
                
                words = text_content.split(' ')
                
                for i, word in enumerate(words):
                    word_to_draw = word + " " if i < len(words) - 1 else word
                    if not word_to_draw: continue

                    word_width = c.stringWidth(word_to_draw)
                    
                    if (current_x + word_width) > (x_start + max_width):
                        y -= line_height
                        y = check_space(c, y, line_height)
                        current_x = x_start
                        if is_bold: c.setFont("Helvetica-Bold", 10)
                        else: c.setFont("Helvetica", 10)

                    c.drawString(current_x, y, word_to_draw)
                    current_x += word_width
            
            y -= line_height
            y = check_space(c, y, line_height)

        return y

    # ================= EJECUCIÓN DEL REPORTE =================
    
    y = draw_header(c)

    # --- SECCIÓN DE IMÁGENES ---
    GAP = 20 
    available_width = W - 2 * M
    img_box_width = (available_width - GAP) / 2 
    max_img_height = 180 

    y = check_space(c, y, 30 + max_img_height)

    # Título Sección 1 (Tamaño 12)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, y, "1) Análisis Visual: Sección Original (Izq.) vs. Interpretación (Der.)")
    y -= 20 

    x_left = M
    x_right = M + img_box_width + GAP

    y_bottom1 = draw_image_side_by_side(c, img_original_path, x_left, y, img_box_width, max_img_height)
    y_bottom2 = draw_image_side_by_side(c, img_resultado_path, x_right, y, img_box_width, max_img_height)

    y = min(y_bottom1, y_bottom2) - 25

    # --- SECCIÓN DE TEXTO ---
    y = check_space(c, y, 20)
    
    # CORRECCIÓN: Título Sección 2 (Tamaño 12 - El más grande)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, y, "2) Interpretación Geológica")
    y -= 20
    
    text_safe = str(texto) if texto else "Sin descripción."
    y = draw_markdown_text(c, M, y, text_safe, max_width=available_width, line_height=14)

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

def convert_image_to_bytes(img, format="PNG"):
    """Convierte una imagen PIL a bytes para descarga."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

def colorize_mask(mask):
    if mask.ndim == 3:
        mask_gray = mask[:, :, 0]
    else:
        mask_gray = mask

    colored_mask = np.zeros((mask_gray.shape[0], mask_gray.shape[1], 3), dtype=np.uint8)

    class_colors = {
        0:  (0, 0, 0),         
        1:  (165, 42, 42),     
        2:  (0, 0, 255),       
        3:  (128, 0, 128),     
        4:  (245, 222, 179),   
        5:  (255, 165, 0),     
        6:  (255, 255, 0),     
        7:  (0, 255, 255),     
        8:  (255, 0, 255),     
        9:  (220, 20, 60),     
        10: (0, 0, 200),       
        11: (255, 182, 193),   
        12: (255, 69, 0),      
        13: (0, 255, 180),     
        14: (34, 139, 34),     
    }

    for class_id, color in class_colors.items():
        colored_mask[mask_gray == class_id] = color

    return colored_mask

def create_overlay_from_mask(img_original, mask_img, alpha=0.3):
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
# 4. CARGA DE LOGOS Y ESTILOS
# --------------------------------------------------
LOGO_UCE_PATH = "assets/uce.png"
LOGO_GEO_PATH = "assets/geologia.png"
uce_b64 = img_to_base64(LOGO_UCE_PATH)
geo_b64 = img_to_base64(LOGO_GEO_PATH)

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
# 5. UI PRINCIPAL
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

st.markdown("""
<div class="bloque">
<b>GeoSeismicAI</b> es una herramienta académica para el <b>análisis automático de líneas sísmicas</b>.
<br><br>
El sistema procesa la imagen de forma autónoma (N8N + IA Agéntica) y entrega resultados preliminares para apoyo didáctico.
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='titulo_azul'>Carga de línea sísmica</div>", unsafe_allow_html=True)
st.markdown("<div class='bloque'>", unsafe_allow_html=True)
archivo = st.file_uploader("Selecciona una línea sísmica (PNG / JPG)", type=["png", "jpg", "jpeg"])
st.markdown("</div>", unsafe_allow_html=True)

if archivo is not None:
    img = Image.open(archivo).convert("RGB")
    st.subheader("Vista previa de la línea sísmica")
    st.image(img, use_container_width=True)

# --------------------------------------------------
# 6. LÓGICA DE PROCESAMIENTO
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
                        texto_analisis = (result.get("texto_analisis") or result.get("technical_report") or result.get("report", {}).get("summary") or "Sin análisis generado.")
                        
                        # Extraer imagen/máscara
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
                        
                        # Variables para guardar las imágenes finales
                        final_overlay = None

                        with col_res1:
                            st.subheader("Mapa de Sismofacies")
                            if mask_b64:
                                mask_img = Image.open(io.BytesIO(base64.b64decode(mask_b64))).convert("RGB")
                                mask_array = np.array(mask_img)
                                
                                # 1. Generar Máscara de Color (Solo interna, no se descarga)
                                mask_colored_array = colorize_mask(mask_array)
                                final_mask_colored_internal = Image.fromarray(mask_colored_array)
                                
                                # 2. Generar Overlay (Superposición)
                                final_overlay = create_overlay_from_mask(img_original, final_mask_colored_internal, alpha=0.3)
                                
                                # Mostrar en pantalla
                                st.image(final_overlay, caption="Segmentación IA (Overlay)", use_container_width=True)
                                
                                # Guardar temporalmente para PDF
                                final_overlay.save(temp_proc_path)
                                
                                # --- BOTÓN DE DESCARGA: "Imagen interpretada" ---
                                st.download_button(
                                    label="Imagen interpretada", # CAMBIO SOLICITADO
                                    data=convert_image_to_bytes(final_overlay),
                                    file_name="GeoSeismic_Interpretada.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            else:
                                st.warning("No se recibió máscara procesada. Se usa la imagen original.")
                                img_original.save(temp_proc_path)

                        with col_res2:
                            st.subheader("Interpretación Geológica")
                            st.info(texto_analisis)
                        
                        # GENERAR PDF
                        build_pdf(out_path=pdf_path, logo_left_path=LOGO_UCE_PATH, logo_right_path=LOGO_GEO_PATH,
                                  titulo_reporte="Análisis de Sismofacies", img_original_path=temp_orig_path,
                                  img_resultado_path=temp_proc_path, texto=texto_analisis)
                        
                        st.divider() # Línea visual
                        
                        # BOTÓN DE DESCARGA PDF AL FINAL
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(label="📄 DESCARGAR REPORTE COMPLETO (PDF)", data=pdf_file.read(),
                                                   file_name="Reporte_GeoSeismicAI.pdf", mime="application/pdf",
                                                   use_container_width=True) # Botón ancho
                                                   
                    except Exception as e: st.error(f"Error procesando resultados: {str(e)}")          
            except Exception as e: st.error(f"Fallo de conexión: {str(e)}")

# PIE DE PÁGINA
st.markdown("<div class='linea'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="bloque">
<b>Enfoque académico</b><br>
Aplicación diseñada como trabajo final de Software Aplicado a Geología - Universidad Central del Ecuador.
</div>
""", unsafe_allow_html=True)
