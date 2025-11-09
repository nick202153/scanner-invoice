import streamlit as st
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import io
import re

# --- OCR Model Loading ---
@st.cache_resource
def load_ocr_model():
    return PaddleOCR(use_angle_cls=True, lang='ch')

ocr = load_ocr_model()

# --- Invoice Processing Function ---
def process_invoice_image(image_bytes):
    """
    Takes image bytes, performs OCR, and displays results in columns.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img_array = np.array(image)

        # 建立左右欄位
        col1, col2 = st.columns(2)

        with col1:
            st.image(image, caption='輸入的圖片', use_container_width=True)

        with col2:
            with st.spinner('正在辨識中...'):
                result = ocr.ocr(img_array, cls=True)

            st.subheader("辨識結果")
            
            if not result or not result[0]:
                st.warning("未偵測到任何文字。")
                return

            invoice_pattern = re.compile(r'^[A-Z]{2}-?\d{8}$')
            matched_texts = []
            found = False

            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                normalized = re.sub(r"[\s-]+", "", text).upper()

                if invoice_pattern.match(normalized):
                    found = True
                    normalized_number = normalized
                    if '-' not in normalized_number:
                         normalized_number = normalized_number[:2] + '-' + normalized_number[2:]

                    if confidence > 0.98:
                        st.success(f"發票號碼: {normalized_number} (信心: {confidence:.4f})")
                        matched_texts.append(normalized_number)
                    else:
                        st.warning(f"號碼: {normalized_number} (信心: {confidence:.4f} | 偏低，請確認)")
                        matched_texts.append(normalized_number)

            if not found:
                st.warning("未找到符合格式的發票號碼。")

    except Exception as e:
        st.error(f"處理圖片時發生錯誤: {e}")

# --- Streamlit UI (Single Interface with Button Toggle) ---
st.title('Streamlit + PaddleOCR 發票掃描')

# 初始化 session_state
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False

def activate_camera():
    st.session_state.camera_active = True

st.header("上傳圖片檔案")
uploaded_file = st.file_uploader("請選擇發票圖片", type=["jpg", "png", "jpeg"], key="uploader")

st.header("或 使用相機拍照")
st.button("開啟相機", on_click=activate_camera)

image_data = None
camera_file = None

# 僅在 state 為 active 時才渲染 camera_input
if st.session_state.camera_active:
    camera_file = st.camera_input("請拍攝發票", key="camera")

    if camera_file is not None:
        # 拍照後，立即處理並重設狀態
        image_data = camera_file.getvalue()
        st.session_state.camera_active = False # 釋放相機
        # 清除 file_uploader 的狀態，避免衝突
        st.session_state.uploader = None 

# 如果相機未處理 (未開啟或未拍照)，且檔案上傳有資料
if image_data is None and uploaded_file is not None:
    image_data = uploaded_file.getvalue()

# 最終處理
if image_data:
    process_invoice_image(image_data)