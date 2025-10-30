import socket
import numpy as np

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("🟢 Listening...")

partial_frame = []
gradient = np.array(list(" .:-=+*#%@█"))

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

            # нормализуем и индексируем градиент
            norm = (frame - tmin) / (tmax - tmin + 1e-6)
            idx = (norm * (len(gradient) - 1)).astype(int)

            ascii_frame = ["".join(gradient[row]) for row in idx]
            print("\n".join(ascii_frame))
            print("-" * 40)

    except Exception as e:
        print("⚠️ Ошибка парсинга:", e)
