import matplotlib
matplotlib.use('Agg')  # Без GUI

from flask import Flask, Response
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io

app = Flask(__name__)

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

partial_frame = []

def get_frame():
    global partial_frame
    print("🟡 Waiting for UDP frames...")

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            floats = list(map(float, data.decode().strip().split(",")))
            partial_frame.extend(floats)

            if len(partial_frame) >= 768:
                frame = np.array(partial_frame[:768], dtype=np.float32).reshape((24, 32))
                partial_frame = partial_frame[768:]

                tmin = frame.min()
                tmax = frame.max()

                # Рисуем картинку
                fig, ax = plt.subplots(figsize=(5, 4))
                im = ax.imshow(frame, cmap="inferno", interpolation="nearest")
                ax.axis('off')

                # Подписи Tmin / Tmax
                label = f"Tmin = {tmin:.1f}°C, Tmax = {tmax:.1f}°C"
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


@app.route('/')
def index():
    return '''
    <html>
      <head><title>MLX90640 Thermal Stream</title></head>
      <body style="background:#000; color:#fff; text-align:center;">
        <h1>🔥 MLX90640 Thermal Camera</h1>
        <img src="/video" style="width:512px; image-rendering:pixelated; border:3px solid #444;">
        <p>Streaming live with temperature overlay</p>
      </body>
    </html>
    '''


@app.route('/video')
def video():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    print("🟢 Flask server started at: http://192.168.1.97:5000/")
    app.run(host='0.0.0.0', port=5000, threaded=True)
