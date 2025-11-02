import matplotlib
matplotlib.use('Agg')  # Без GUI

from flask import Flask, Response, jsonify, render_template
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import cv2

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

                # Normalize 0–255
                norm = np.clip((frame - latest_tmin) / (latest_tmax - latest_tmin), 0, 1)
                norm_uint8 = np.uint8(norm * 255)

                # Resize and apply colormap
                upscaled = cv2.resize(norm_uint8, (640, 480), interpolation=cv2.INTER_CUBIC)
                colored = cv2.applyColorMap(upscaled, cv2.COLORMAP_INFERNO)

                # Optional: add text
                label = f"Tmin={latest_tmin:.1f}C, Tmax={latest_tmax:.1f}C"
                cv2.putText(colored, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (255, 255, 255), 2)

                # Encode as JPEG
                ret, jpeg = cv2.imencode('.jpg', colored)
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

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
