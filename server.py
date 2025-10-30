import matplotlib
matplotlib.use('Agg')  # ✅ используем безголовый режим, без Tkinter GUI

from flask import Flask, Response
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io

# ---------------- Flask Server ----------------
app = Flask(__name__)

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

# UDP сокет для приема данных от ESP32
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

partial_frame = []

def get_frame():
    """Получает UDP-кадры и рендерит тепловизор в PNG"""
    global partial_frame
    print("🟡 Waiting for UDP frames from ESP32...")

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            floats = list(map(float, data.decode().strip().split(",")))
            partial_frame.extend(floats)

            # Один кадр = 32 x 24 = 768 пикселей
            if len(partial_frame) >= 768:
                frame = np.array(partial_frame[:768], dtype=np.float32).reshape((24, 32))
                partial_frame = partial_frame[768:]

                # Настраиваем изображение
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.axis('off')
                im = ax.imshow(frame, cmap="inferno", interpolation="nearest")
                fig.tight_layout(pad=0)

                # Рендерим в буфер PNG
                buf = io.BytesIO()
                canvas = FigureCanvas(fig)
                canvas.print_png(buf)
                plt.close(fig)

                # Отправляем в MJPEG поток
                yield (b'--frame\r\n'
                       b'Content-Type: image/png\r\n\r\n' + buf.getvalue() + b'\r\n')

        except Exception as e:
            print("⚠️ Ошибка парсинга или потока:", e)


@app.route('/')
def index():
    """Главная страница"""
    return '''
    <html>
      <head><title>MLX90640 Thermal Stream</title></head>
      <body style="background:#000; color:#fff; text-align:center;">
        <h1>🔥 MLX90640 Thermal Camera</h1>
        <img src="/video" style="width:512px; image-rendering:pixelated; border:3px solid #444;">
        <p>Streaming live from Jetson Nano</p>
      </body>
    </html>
    '''


@app.route('/video')
def video():
    """Отдаёт MJPEG видеопоток"""
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    print("🟢 Flask server started at: http://192.168.1.97:5000/")
    print("📡 Waiting for UDP packets on port 12345...")
    app.run(host='0.0.0.0', port=5000, threaded=True)
