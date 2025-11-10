import streamlit as st
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import io
import re

# 1. 匯入 pyzbar 和 option_menu
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:
    st.error("缺少 pyzbar 函式庫，請執行： pip install pyzbar")
    st.stop()

try:
    from streamlit_option_menu import option_menu
except ImportError:
    st.error("缺少 streamlit_option_menu 函式庫，請執行： pip install streamlit-option-menu")
    st.stop()


# --- OCR Model Loading ---
@st.cache_resource
def load_ocr_model():
    return PaddleOCR(use_angle_cls=True, lang='ch')

ocr = load_ocr_model()

# --- Image Processing Function ---
def process_invoice_image(image_bytes):
    """
    Takes image bytes, performs QR scan AND OCR, displays results.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img_array = np.array(image)

        # 建立左右欄位
        col1, col2 = st.columns(2)

        display_final_invoice_text = ""
        found_invoice_number = ""
        is_invoice_found = False
        display_final_order_text = ""
        is_order_found = False
        found_order_number = ""

        with col1:
            # 修正：st.image 應使用 use_container_width
            st.image(image, caption='輸入的圖片', use_container_width=True)

        with col2:
            
            # --- QR Code 掃描 ---
            # st.subheader("QR Code 辨識 (銷貨單號)")
            qr_results = pyzbar_decode(image)
            sa_pattern = re.compile(r'^SA\d{10}$')
            qr_found = False
            
            if qr_results:
                for qr in qr_results:
                    try:
                        qr_data = qr.data.decode('utf-8')
                    except UnicodeDecodeError:
                        qr_data = qr.data.decode('latin-1') 

                    if sa_pattern.match(qr_data):
                        display_final_order_text += f"銷貨單號: {qr_data}"
                        found_order_number = qr_data
                        # st.success(f"銷貨單號: {qr_data} (來自 QR Code)")
                        qr_found = True
                        is_order_found = True
                    # else:
                        # st.text(f"掃到其他 QR Code: {qr_data[:30]}...")
                        # display_final_text += f"規格不符合的銷貨單QRCODE"
            
            if not qr_found and qr_results:
                #  st.warning("掃到 QR Code，但未找到 SA 格式的銷貨單號。")
                display_final_order_text += f"規格不符合的銷貨單QRCODE"
                is_order_found = False
            elif not qr_results:
                #  st.info("未偵測到 QR Code。")
                display_final_order_text += f"未偵測到 QR Code。"
                is_order_found = False

            # --- OCR 文字辨識 ---
            # st.subheader("OCR 辨識 (發票號碼)")
            with st.spinner('正在辨識文字...'):
                # 修正：cls 參數已在初始化時 (use_angle_cls) 設定
                result = ocr.ocr(img_array) 
            
            if not result or not result[0]:
                st.warning("OCR 未偵測到任何文字。")
            else:
                invoice_pattern = re.compile(r'^[A-Z]{2}-?\d{8}$')
                ocr_found = False

                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    normalized = re.sub(r"[\s-]+", "", text).upper()

                    if invoice_pattern.match(normalized):
                        ocr_found = True
                        normalized_number = normalized
                        if '-' not in normalized_number:
                             normalized_number = normalized_number[:2] + '-' + normalized_number[2:]

                        if confidence > 0.98:
                            display_final_invoice_text += f"發票號碼: {normalized_number} (信心: {confidence:.4f})"
                            # st.success(f"發票號碼: {normalized_number} (信心: {confidence:.4f})")
                            is_invoice_found = True
                            found_invoice_number = normalized_number
                        else:
                            display_final_invoice_text += f"發票號碼: {normalized_number} (信心: {confidence:.4f} | 偏低)"
                            # st.warning(f"號碼: {normalized_number} (信心: {confidence:.4f} | 偏低)")
                            is_invoice_found = False
                            found_invoice_number = normalized_number

                if not ocr_found:
                    # st.warning("OCR 未找到符合格式的發票號碼。")
                    display_final_invoice_text += f"OCR 未找到符合格式的發票號碼。"
                    is_invoice_found = False
        
            if is_order_found:
                st.success(display_final_order_text)
            else:
                st.warning(display_final_order_text)
                
            if is_invoice_found:
                st.success(display_final_invoice_text)
            else:
                st.warning(display_final_invoice_text)

        if is_order_found and is_invoice_found:
            st.button(
                label="登錄",
                on_click=add_order_and_invoice,
                args=(found_order_number, found_invoice_number),
                use_container_width=True,
                type="primary"
            )

    except Exception as e:
        st.error(f"處理圖片時發生錯誤: {e}")
        import traceback
        st.code(traceback.format_exc())

def add_order_and_invoice(order_number, invoice_number):
    st.toast(f"登錄成功，銷貨單號碼: {order_number}，發票號碼: {invoice_number}")
    # st.success(f"登錄成功，銷貨單號碼: {order_number}，發票號碼: {invoice_number}")


# --- Streamlit UI (Sidebar Menu with streamlit-option-menu) ---
st.title('發票-銷貨單登錄系統')

# 1. 建立 Sidebar 選單 (使用 streamlit-option-menu)
with st.sidebar:
    st.title("功能選單")
    page = option_menu(
        menu_title=None,  # Hides the default menu title
        options=["拍照上傳", "上傳圖片"],
        # 圖示來自 bootstrap icons: https://icons.getbootstrap.com/
        icons=["camera-fill", "file-arrow-up-fill"], 
        menu_icon="cast", # Optional
        default_index=0,
    )

# 2. 根據選單顯示不同頁面
if page == "拍照上傳":
    st.badge(label="拍照上傳，注意發票與銷貨單QRCODE盡量同框，且不要裁切到QRCODE", color="red")
    
    # 僅在此頁面渲染 camera_input
    camera_file = st.camera_input(label="按下Take photo拍照", key="camera_page_input")
    
    if camera_file is not None:
        image_data = camera_file.getvalue()
        process_invoice_image(image_data)

elif page == "上傳圖片":
    st.badge(label="拍照上傳，注意發票與銷貨單QRCODE盡量同框，且不要裁切到QRCODE", color="red")
    
    # 僅在此頁面渲染 file_uploader
    uploaded_file = st.file_uploader(
        "請選擇圖片",
        type=["jpg", "png", "jpeg"],
        key="uploader_page_input"
    )
    
    if uploaded_file is not None:
        image_data = uploaded_file.getvalue()
        process_invoice_image(image_data)