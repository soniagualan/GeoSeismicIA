import streamlit as st
from PIL import Image
import base64
import requests
import os
import io
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
# Asegúrate de que esta sea la URL correcta (Test o Producción)
BACKEND_ENDPOINT = "https://soniagualan.app.n8n.cloud/webhook-test/seismic-upload"

# --------------------------------------------------
# 2. FUNCIONES DE GENERACIÓN DE PDF
# --------------------------------------------------
def build_pdf(out_path, logo_left_path, logo_right_path, titulo_reporte, img_original_path, img_resultado_path, texto):
    """
    Genera un PDF con el reporte técnico usando ReportLab.
    """
    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(out_path, pagesize=A4)
    W, H = A4
    M = 40  # margen

    # --- Helpers internos ---
    def draw_logo(path, x, y_top, size=100):
        p = Path(path)
        if p.exists():
            try:
                c.drawImage(ImageReader(str(p)), x, y_top - size, width=size, height=size, mask="auto")
            except Exception:
                pass # Si falla el , no detiene el reporte

    def draw_title_center(text, y, font="Helvetica-Bold", size=12):
        c.setFont(font, size)
        c.drawCentredString(W / 2, y, text)

    def draw_line(y):
        c.line(M, y, W - M, y)

    def draw_wrapped_text(x, y, text, max_width_chars=110, line_h=12, font="Helvetica", size=10):
        c.setFont(font, size)
        yy = y
        # Limpieza básica de texto
        text_safe = str(text) if text else "Sin descripción."
        
        for paragraph in text_safe.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                yy -= line_h
                continue

            words = paragraph.split()
            line = ""
            for w in words:
                test = (line + " " + w).strip()
                if len(test) <= max_width_chars:
                    line = test
                else:
                    c.drawString(x, yy, line)
                    yy -= line_h
                    line = w
            if line:
                c.drawString(x, yy, line)
                yy -= line_h
            yy -= 4
        return yy

    def draw_image_fit(path, x, y_top, max_w, max_h):
        p = Path(path)
        if not p.exists():
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(x, y_top - 12, f"[Imagen no disponible: {p.name}]")
            return y_top - 20

        try:
            img = ImageReader(str(p))
            iw, ih = img.getSize()
            scale = min(max_w / iw, max_h / ih)
            nw, nh = iw * scale, ih * scale
            c.drawImage(img, x + (max_w - nw) / 2, y_top - nh, width=nw, height=nh, mask="auto")
            return y_top - nh
        except Exception as e:
            c.drawString(x, y_top - 12, f"[Error cargando imagen]")
            return y_top - 20

    # --- Encabezado ---
    y = H - M
    
    # Dibuja logos si existen
    draw_logo(logo_left_path, M, y, 70)
    draw_logo(logo_right_path, W - M - 70, y, 70)

    draw_title_center("Universidad Central del Ecuador", y - 20, "Helvetica-Bold", 12)
    draw_title_center("Carrera de Geología", y - 38, "Helvetica", 11)
    draw_title_center("GeoSeismicAI", y - 58, "Helvetica-Bold", 12)
    draw_title_center(titulo_reporte, y - 78, "Helvetica-Bold", 12)

    # SE ELIMINÓ LA FECHA AQUÍ SEGÚN SOLICITUD

    draw_line(y - 95)

    # --- Contenido ---
    y = y - 115

    # 1. Imagen Original (Sin modificar)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "1) Sección sísmica original")
    y -= 12
    y = draw_image_fit(img_original_path, M, y, W - 2 * M, 200) - 18

    # 2. Imagen Procesada (Interpretación visual)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "2) Interpretación de Sismofacies (IA)")
    y -= 12
    y = draw_image_fit(img_resultado_path, M, y, W - 2 * M, 200) - 18

    # 3. Interpretación (Texto)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "3) Interpretación Geológica")
    y -= 14
    y = draw_wrapped_text(M, y, texto, max_width_chars=100, line_h=12, font="Helvetica", size=10)

    # --- Pie ---
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, 25, 'Procesado con "GeoSismicIA" - Tesis UCE')

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
import numpy as np
def colorize_mask(mask):
    """
    Convierte una máscara de clases (0–13) a una máscara RGB con 14 colores
    """
    import numpy as np
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
    alpha controla qué tanto se mezcla con la imagen original.
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
# Rutas a los assets (Asegúrate de subirlos a tu GitHub en la carpeta 'assets')
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
                        report = result.get("report", {})

                        # 1. Texto del análisis
                        texto_analisis = (
                            report.get("summary")
                            or report.get("methodology")
                            or "Sin análisis."
                        )

                        # 2. Imagen original (base64 desde n8n)
                        img_original_b64 = result.get("image_original")

                        # 3. Máscara (base64 desde n8n)
                        mask_b64 = result.get("mask")

                        # --- LIMPIEZA BASE64 ---
                        if img_original_b64 and "," in img_original_b64:
                            img_original_b64 = img_original_b64.split(",")[1]

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
                        pdf_path = "Reporte_GeoSismicIA.pdf"

                        # ===============================
                        # COLUMNA 1 — IMÁGENES
                        # ===============================
                        with col_res1:
                            st.subheader("Mapa de Sismofacies")

                            if img_original_b64:
                                img_original = Image.open(
                                    io.BytesIO(base64.b64decode(img_original_b64))
                                ).convert("RGB")
                            else:
                                img_original = Image.open(archivo).convert("RGB")

                            img_original.save(temp_orig_path)

                            if mask_b64:
                                mask_img = Image.open(
                                    io.BytesIO(base64.b64decode(mask_b64))
                                ).convert("RGB")

                                # Convertir máscara de clases a colores
                                mask_array = np.array(mask_img)
                                mask_colored = colorize_mask(mask_array)

                                # Crear overlay con colores de sismofacies
                                overlay_img = create_overlay_from_mask(
                                     img_original,
                                     Image.fromarray(mask_colored)
                                )

                                st.image(
                                    overlay_img,
                                    caption="Segmentación IA (overlay)",
                                    use_container_width=True
                                )

                                overlay_img.save(temp_proc_path)
                            else:
                                st.warning("No se recibió máscara. Se usa la imagen original.")
                                img_original.save(temp_proc_path)

                        # ===============================
                        # COLUMNA 2 — TEXTO
                        # ===============================
                        with col_res2:
                            st.subheader("Interpretación Geológica")
                            st.info(texto_analisis)
                        

                        # --- GENERACIÓN DEL PDF ---
                        if os.path.exists(pdf_path):
                           os.remove(pdf_path)
                        def build_pdf(
                            out_path=pdf_path,
                            logo_left_path=LOGO_UCE_PATH,
                            logo_right_path=LOGO_GEO_PATH,
                            titulo_reporte="Análisis de Sismofacies",
                            img_original_path=temp_orig_path,
                            img_resultado_path=temp_proc_path,
                            texto=texto_analisis
                        ):
                            import re
                            from pathlib import Path
                            from reportlab.lib.pagesizes import A4
                            from reportlab.lib.utils import ImageReader
                            from reportlab.pdfgen import canvas

                            out_path = str(out_path)
                            Path(out_path).parent.mkdir(parents=True, exist_ok=True)

                            c = canvas.Canvas(out_path, pagesize=A4)
                            W, H = A4
                            M = 45

                            def clean_text(t):
                                if not t:
                                   return "Sin interpretación geológica."
                                t = re.sub(r"[#*`]", "", t)
                                return t.strip()

                            texto = clean_text(texto)

                            def draw_logo(path, x, y, size=60):
                                p = Path(path)
                                if p.exists():
                                   c.drawImage(
                                       ImageReader(str(p)),
                                       x,
                                       y - size,
                                       width=size,
                                       height=size,
                                       mask="auto"
                                   )

                            def draw_center(text, y, size=12, bold=False):
                                c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
                                c.drawCentredString(W / 2, y, text)

                            def draw_image(path, x, y, max_w, max_h):
                                p = Path(path)
                                if not p.exists():
                                   c.setFont("Helvetica-Oblique", 9)
                                   c.drawString(x, y - 12, "[Imagen no disponible]")
                                   return y - 20

                                img = ImageReader(str(p))
                                iw, ih = img.getSize()
                                scale = min(max_w / iw, max_h / ih)
                                nw, nh = iw * scale, ih * scale

                                c.drawImage(
                                   img,
                                   x + (max_w - nw) / 2,
                                   y - nh,
                                   width=nw,
                                   height=nh,
                                   mask="auto"
                                )
                                return y - nh

                            def draw_text_block(x, y, text, max_chars=95):
                                c.setFont("Helvetica", 10)
                                line_h = 13

                                for paragraph in text.split("\n"):
                                   words = paragraph.split()
                                   line = ""

                                   for w in words:
                                       test = f"{line} {w}".strip()
                                       if len(test) <= max_chars:
                                          line = test
                                       else:
                                          c.drawString(x, y, line)
                                          y -= line_h
                                          line = w

                                   if line:
                                       c.drawString(x, y, line)
                                       y -= line_h

                                   y -= 6

                                return y
                                #----------ENCABEZADO---------
                            y = H - M

                            draw_logo(logo_left_path, M, y)
                            draw_logo(logo_right_path, W - M - 60, y)

                            draw_center("Universidad Central del Ecuador", y - 10, 12, True)
                            draw_center("Carrera de Geología", y - 28, 11)
                            draw_center("GeoSismicIA", y - 46, 12, True)
                            draw_center(titulo_reporte, y - 64, 12, True)

                            c.line(M, y - 80, W - M, y - 80)
                            y -= 100
                            #---------IMAGENES----------
                            c.setFont("Helvetica-Bold", 11)
                            c.drawString(M, y, "1) Sección sísmica original")
                            c.drawString(W / 2 + 10, y, "2) Interpretación de Sismofacies (IA)")
                            y -= 10

                            img_height = 220

                            y_left = draw_image(
                                img_original_path,
                                M,
                                y,
                                W / 2 - M - 10,
                                img_height
                            )

                            y_right = draw_image(
                                img_resultado_path,
                                W / 2 + 10,
                                y,
                                W / 2 - M - 10,
                                img_height
                            )

                            y = min(y_left, y_right) - 25
                            #----------TEXTO------------
                            c.setFont("Helvetica-Bold", 11)
                            c.drawString(M, y, "3) Interpretación Geológica")
                            y -= 16

                            y = draw_text_block(M, y, texto)
                            #------------PIE----------
                            c.setFont("Helvetica-Oblique", 9)
                            c.drawCentredString(
                                W / 2,
                                30,
                                'Procesado con "GeoSismicIA" - Tesis UCE'
                            )

                            c.showPage()
                            c.save()
                
                        #---------------------------------------------------------
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
            except Exception as e: st.error(f"Error procesando resultados: {str(e)}")            
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
