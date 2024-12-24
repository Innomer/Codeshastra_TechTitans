import sys
import threading
import numpy as np
from collections import deque
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PyQt5.QtCore import QTimer
from OpenGL.GL import *
from noise import pnoise2
import pyaudio
from math import cos, sin, radians


class Particle:
    def __init__(self):
        self.angle = np.random.uniform(0, 360)  # Initial angle
        self.radius = np.random.uniform(0.3, 0.8)  # Initial radius
        self.speed = np.random.uniform(0.1, 1.0)  # Initial angular speed
        self.history = deque(maxlen=10)  # Store positions for trails

        # Perlin noise offsets for organic motion
        self.x_offset = np.random.uniform(0, 0.5)
        self.y_offset = np.random.uniform(0, 0.5)

    def update(self, loudness):
        # Update radius and speed based on loudness
        self.radius = 0.1 + loudness / 2500.0
        self.speed = 0.1 + loudness / 25000.0

        # Update angle
        self.angle += self.speed
        if self.angle >= 360:
            self.angle -= 360

        # Calculate new position
        angle_rad = radians(self.angle)
        x = self.radius * cos(angle_rad) + pnoise2(self.x_offset, self.y_offset)
        y = self.radius * sin(angle_rad) + pnoise2(self.x_offset + 0.5, self.y_offset + 0.5)

        # Update Perlin noise offsets for smooth movement
        self.x_offset += 0.01
        self.y_offset += 0.01

        # Add the current position to history
        self.history.append((x, y))

    def draw(self):
        # Draw trails
        glBegin(GL_LINE_STRIP)
        for i, (x, y) in enumerate(self.history):
            alpha = (i + 1) / len(self.history)  # Gradual fade
            glColor4f(0.5, 0.8, 1.0, alpha)  # Particle trail color
            glVertex2f(x, y)
        glEnd()

        # Draw the particle
        glColor3f(0.0, 0.8, 1.0)
        glBegin(GL_POINTS)
        x, y = self.history[-1]
        glVertex2f(x, y)
        glEnd()


class OpenGLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.particles = [Particle() for _ in range(100)]  # Create 100 particles
        self.loudness = 0.0

        # Set up a timer for animation updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)  # Call update every frame
        self.timer.start(16)  # Approximately 60 FPS

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.2, 1.0)  # Background color

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw particles
        for particle in self.particles:
            particle.update(self.loudness)
            particle.draw()

    def update_loudness(self, loudness):
        self.loudness = loudness


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A.I.V.A")
        self.setGeometry(100, 100, 800, 600)

        # OpenGL Widget
        self.opengl_widget = OpenGLWidget()
        self.setCentralWidget(self.opengl_widget)

        # Start real-time loudness calculation in a separate thread
        self.audio_thread = threading.Thread(target=self.stream_audio, daemon=True)
        self.audio_thread.start()

    def stream_audio(self):
        """Capture audio in real-time and calculate loudness."""
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=44100,
                        input=True,
                        frames_per_buffer=1024)

        print("Real-time audio stream is active.")

        while True:
            try:
                # Read audio data from the stream
                data = stream.read(1024, exception_on_overflow=False)

                # Convert audio data to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)

                # Calculate RMS loudness
                # rms = np.sqrt(np.mean(audio_data**2))
                rms=np.abs(audio_data).mean()
                print(rms)
                self.opengl_widget.update_loudness(rms)

            except Exception as e:
                print(f"Audio streaming error: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
