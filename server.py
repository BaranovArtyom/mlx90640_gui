import matplotlib
matplotlib.use('Agg')  # Без GUI

from flask import Flask, Response, jsonify, render_template
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io

app = Flask(__name__, static_folder='static', template_folder='templates')

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

partial_frame = []
latest_tmin = 0
latest_tmax = 0

def get_frame():
    global partial_frame, latest_tmin, latest_tmax
    print("🟡 Waiting for UDP frames...")

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            decoded = data.decode().strip()

            # Если начинается с "S|", то сбрасываем буфер
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video')
def video():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    return jsonify({"tmin": latest_tmin, "tmax": latest_tmax})


if __name__ == '__main__':
    print("🟢 Flask server started at: http://192.168.1.97:5000/")
    app.run(host='0.0.0.0', port=5000, threaded=True)
