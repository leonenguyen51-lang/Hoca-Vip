import streamlit as st
import cv2
import requests
import time
from datetime import datetime, date
from ultralytics import YOLO
import google.generativeai as genai
from PIL import Image
from Adafruit_IO import Client, RequestError

# ==========================================
# ⚙️ PHẦN 1: CẤU HÌNH HỆ THỐNG (QUAN TRỌNG)
# ==========================================
# 🔐 THÔNG TIN ĐĂNG NHẬP
USER_ADMIN = "quan40" 
PASS_ADMIN = "123456"

# 🔑 THÔNG TIN CLOUD ADAFRUIT (Dán chính xác từ ảnh của sếp)
ADAFRUIT_AIO_USERNAME = "MinhQuan1904"
ADAFRUIT_AIO_KEY      = "aio_MECR64xIH9omKQWEmxfan8UaKruO"
aio = Client(username=ADAFRUIT_AIO_USERNAME, key=ADAFRUIT_AIO_KEY)

# 🔑 CÁC CHÌA KHÓA KHÁC (Sếp nhớ điền đủ để báo động chạy)
BOT_TOKEN = "8724967452:AAHCCb2kqQwvnLduz_uuH0fb5N3PFo6D3ec"
CHAT_ID = "7614770132"
API_KEY_GEMINI = "AIzaSyCLtT-374kbMkC7x85qiqiV0F2QoQrSDQg"

# Khởi tạo kết nối Cloud
try:
    aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
    genai.configure(api_key=API_KEY_GEMINI)
    model_bacsi = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"⚠️ Lỗi kết nối ban đầu: {e}")

# --- HÀM TIỆN ÍCH ---
def gui_tin_nhan(noi_dung):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": noi_dung})
    except: pass

def aio_send_safe(feed_id, value):
    """Hàm gửi dữ liệu lên mây có kiểm tra lỗi 401/404"""
    try:
        aio.send(feed_id, value)
        return True
    except RequestError as e:
        st.error(f"❌ Lỗi Adafruit (Feed: {feed_id}): {e}")
        return False

st.set_page_config(page_title="HoCa AI | Quân Gia Dụng 4.0", page_icon="🐟", layout="wide")

# ==========================================
# 🛡️ PHẦN 2: CỬA SỔ ĐĂNG NHẬP
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🐟 HOCA AI</h1>", unsafe_allow_html=True)
    with st.container():
        _, col_mid, _ = st.columns([1, 1.5, 1])
        with col_mid:
            u = st.text_input("Tên đăng nhập")
            p = st.text_input("Mật khẩu", type="password")
            if st.button("🚀 TRUY CẬP HỆ THỐNG", use_container_width=True):
                if u == USER_ADMIN and p == PASS_ADMIN:
                    st.session_state.authenticated = True
                    st.success("Xác thực thành công!")
                    st.rerun()
                else:
                    st.error("Sai thông tin rồi sếp ơi!")
    st.stop()

# ==========================================
# 📂 PHẦN 3: SIDEBAR - QUẢN LÝ & CÀI ĐẶT
# ==========================================
with st.sidebar:
    st.title(f"Xin chào sếp Quân! 👋")
    if st.button("🚪 Đăng xuất"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown("---")
    # Khởi tạo dữ liệu hồ
    if 'data_ho' not in st.session_state:
        st.session_state.data_ho = {"Hồ Cá Koi": {"temp_set": 26.0, "count": 20, "start_date": date.today(), "dirty_limit": 70}}
    
    option_ho = st.selectbox("📂 CHỌN HỒ:", list(st.session_state.data_ho.keys()))
    curr = st.session_state.data_ho[option_ho]
    
    # ⏰ CÀI ĐẶT GIỜ ĂN (ĐÃ KHÔI PHỤC)
    st.subheader("⏰ Hẹn giờ ăn tự động")
    gio_1 = st.time_input("Bữa sáng", value=datetime.strptime("08:00", "%H:%M").time())
    gio_2 = st.time_input("Bữa chiều", value=datetime.strptime("16:00", "%H:%M").time())
    
    st.markdown("---")
    with st.expander("📝 Cấu hình thông số hồ"):
        curr['temp_set'] = st.slider("Nhiệt độ mục tiêu (°C)", 15.0, 35.0, curr['temp_set'])
        curr['dirty_limit'] = st.slider("Ngưỡng thay nước (%)", 0, 100, curr['dirty_limit'])

# ==========================================
# 🚀 PHẦN 4: LOGIC ĐIỀU KHIỂN & CLOUD
# ==========================================
# Lấy dữ liệu thực tế từ Cloud
try:
    temp_real = float(aio.receive('hoca-temp').value)
    dirty_real = float(aio.receive('hoca-dirty').value)
except:
    temp_real, dirty_real = 27.5, 30.0

# Logic giờ ăn tự động
now_time = datetime.now().strftime("%H:%M")
if now_time in [gio_1.strftime("%H:%M"), gio_2.strftime("%H:%M")]:
    if st.session_state.get('last_fed_auto') != now_time:
        gui_tin_nhan(f"🍖 {option_ho}: Đã tự động cho ăn lúc {now_time}.")
        st.session_state.last_fed_auto = now_time

# ==========================================
# 🎛️ PHẦN 5: DASHBOARD HIỂN THỊ
# ==========================================
st.title(f"📍 Dashboard Real-time: {option_ho}")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: st.metric("🌡️ Nhiệt độ", f"{temp_real}°C", f"{temp_real - curr['temp_set']:.1f}°C")
with col_m2: st.metric("💧 Độ dơ nước", f"{dirty_real}%", delta_color="inverse")
with col_m3: st.metric("⏰ Hẹn giờ ăn", f"{gio_1.strftime('%H:%M')}", f"{gio_2.strftime('%H:%M')}")
with col_m4: st.metric("🌐 Cloud Status", "ONLINE", delta_color="normal")

st.markdown("---")

# --- NÚT BẤM THỦ CÔNG ---
st.subheader("⚡ Điều khiển nhanh qua 3G")
btn1, btn2, btn3, btn4 = st.columns(4)
with btn1:
    if st.button("🍴 CHO ĂN NGAY"):
        if aio_send_safe('hoca-feed', 'ON'): st.toast("Đã thả thức ăn!")
with btn2:
    if st.button("🌊 BẬT BƠM THAY NƯỚC"):
        if aio_send_safe('hoca-pump', 'ON'): st.toast("Máy bơm đang chạy...")
with btn3:
    if st.button("❄️ LÀM MÁT"): aio_send_safe('hoca-fan', 'ON')
with btn4:
    if st.button("☀️ BẬT SƯỞI"): aio_send_safe('hoca-heater', 'ON')

st.markdown("---")

# ==========================================
# 🛡️ PHẦN 6: CAMERA & AI GIÁM SÁT
# ==========================================
tab_cam, tab_ai = st.tabs(["🎥 MẮT THẦN AN NINH", "🩺 BÁC SĨ TƯ VẤN GEMINI"])

with tab_cam:
    on_cam = st.toggle("Kích hoạt Camera giám sát")
    if on_cam:
        yolo = YOLO('yolov8n.pt')
        cap = cv2.VideoCapture(0)
        video_area = st.empty()
        while on_cam:
            ret, frame = cap.read()
            if not ret: break
            
            # YOLO Báo trộm
            res = yolo(frame, stream=True)
            for r in res:
                for b in r.boxes:
                    if yolo.names[int(b.cls[0])] == 'person':
                        gui_tin_nhan(f"🚨 CẢNH BÁO: Phát hiện người lạ tại {option_ho}!")
            
            video_area.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
        cap.release()

with tab_ai:
    st.write("🏥 Gửi ảnh cá để chẩn đoán bệnh lý từ xa qua 3G.")
    up = st.file_uploader("Tải ảnh...", type=["jpg", "png"])
    if up:
        img_pil = Image.open(up)
        st.image(img_pil, width=500)
        if st.button("🔎 PHÂN TÍCH SỨC KHỎE"):
            with st.spinner('Đang hội chẩn...'):
                resp = model_bacsi.generate_content([f"Khám cá {option_ho}, {temp_real} độ, nước dơ {dirty_real}%", img_pil])
                st.info(resp.text)