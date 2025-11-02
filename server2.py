import matplotlib
matplotlib.use('Agg')  # Без GUI

from flask import Flask, Response, jsonify, render_template
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import cv2
import io
import time
import requests

app = Flask(__name__, static_folder='static', template_folder='templates')

# ==== ПРИЁМ данных от ESP32 ====
UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

partial_frame = []
latest_tmin = 0
latest_tmax = 0

# ==== Вебкамера ====
cam = cv2.VideoCapture(0)
alpha = 0.5  # Прозрачность

# ==== PNG MJPEG-поток thermal ====
def thermal_stream_generator():
    import requests
    stream = requests.get("http://localhost:5000/video", stream=True)
    byte_data = b""

    for chunk in stream.iter_content(chunk_size=1024):
        byte_data += chunk
        a = byte_data.find(b'\x89PNG')
        b = byte_data.find(b'IEND')  # конец PNG

        if a != -1 and b != -1:
            b += 8  # конец IEND + CRC
            png = byte_data[a:b]
            byte_data = byte_data[b:]

            np_arr = np.frombuffer(png, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame

# ==== ТЕПЛОВИЗОРНЫЙ ПОТОК ====
def get_frame():
    global partial_frame, latest_tmin, latest_tmax
    print("🟡 Waiting for UDP frames...")

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            decoded = data.decode().strip()

            if decoded.startswith("S|"):
                partial_frame = []
                decoded = decoded[2:]

            floats = list(map(float, decoded.split(",")))
            partial_frame.extend(floats)

            if len(partial_frame) >= 768:
                frame = np.array(partial_frame[:768], dtype=np.float32).reshape((24, 32))
                partial_frame = partial_frame[768:]

                latest_tmin = float(frame.min())
                latest_tmax = float(frame.max())

                fig, ax = plt.subplots(figsize=(5, 4))
                im = ax.imshow(frame, cmap="inferno", interpolation="nearest")
                ax.axis('off')

                label = f"Tmin = {latest_tmin:.1f}°C, Tmax = {latest_tmax:.1f}°C"
                ax.text(0.5, 0.0, label, transform=ax.transAxes,
                        fontsize=10, ha='center', va='top', color='white',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.6))

                fig.tight_layout(pad=0)
                canvas = FigureCanvas(fig)
                buf = io.BytesIO()
                canvas.print_png(buf)
                plt.close(fig)

                yield (b'--frame\r\n'
                       b'Content-Type: image/png\r\n\r\n' + buf.getvalue() + b'\r\n')
        except Exception as e:
            print("⚠️ Ошибка парсинга:", e)

# ==== OVERLAY ПОТОК ====
def get_overlay_frame():
    print("🟣 Starting overlay stream...")
    thermal_frames = thermal_stream_generator()

    while True:
        ret_cam, frame_cam = cam.read()
        if not ret_cam:
            print("❌ Не удалось получить кадр с вебкамеры")
            continue

        try:
            frame_thermal = next(thermal_frames)
        except Exception as e:
            print("❌ Ошибка чтения thermal потока:", e)
            continue

        # Зеркалим только ВЕБКАМЕРУ
        frame_cam = cv2.flip(frame_cam, 1)

        # Приводим к одному размеру
        frame_thermal = cv2.resize(frame_thermal, (frame_cam.shape[1], frame_cam.shape[0]))

        # Наложение
        overlaid = cv2.addWeighted(frame_cam, 1 - alpha, frame_thermal, alpha, 0)

        # Добавим текст Tmin/Tmax
        label = f"Tmin={latest_tmin:.1f}C, Tmax={latest_tmax:.1f}C"
        cv2.putText(overlaid, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 255), 2, cv2.LINE_AA)

        # JPEG encode
        ret, jpeg = cv2.imencode('.jpg', overlaid)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

        time.sleep(0.03)  # ~30 FPS


# ==== МАРШРУТЫ ====
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video')
def video():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/overlay')
def overlay():
    return Response(get_overlay_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    return jsonify({"tmin": latest_tmin, "tmax": latest_tmax})


# ==== ЗАПУСК ====
if __name__ == '__main__':
    print("🟢 Flask server started at: http://192.168.1.97:5000/")
    app.run(host='0.0.0.0', port=5000, threaded=True)
