# coding=utf-8
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import pygame
from PyQt5.QtCore import Qt

import easypie
import gui.editor
import gui.debug_console
import easypie.user_bindings as game

main_window = None
app = None


class CanvasWidget(QtWidgets.QFrame):
    def __init__(self, pygame_surface, parent=None):
        super(CanvasWidget, self).__init__(parent)
        self.buffer = pygame_surface
        self.screen = self.buffer
        self.border_size = 5
        self.w, self.h = 100-self.border_size, 100-self.border_size
        self.painter = QtGui.QPainter()
        self.setMinimumSize(self.w, self.h)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.enable_painting = False
        self.stop()

    def toggle_fullscreen(self,state=None):
        state = state if state else self.isWindow()
        if state:
            self.setWindowFlags(self.windowFlags() & ~Qt.Window)
            self.setFocus()
            self.show()
        else:
            self.setWindowFlags(Qt.Window)
            self.showFullScreen()

    def play(self):
        self.enable_painting = True
        self.setStyleSheet("background-color: rgb(0,0,0); border: 5px solid green;")

    def closeEvent(self, event):
        self.toggle_fullscreen()
        event.ignore()

    def stop(self):
        self.setStyleSheet("background-color: rgb(0,0,0); border: 5px solid red;")
        self.buffer.fill((0,0,0))
        self.enable_painting = False

    def qt_to_sdl_press(self, key_code):
        return key_code+32

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        modifiers = int(QtGui.QGuiApplication.keyboardModifiers())
        print("KeyPressEvent:", event.key(), event.text())
        if event.key() == Qt.Key_Escape:
            self.toggle_fullscreen(False)
            self.clearFocus()

        elif event.key() == Qt.Key_F10:
            self.toggle_fullscreen()

        else:
            key = self.qt_to_sdl_press(event.key())
            if event.isAutoRepeat():
                if key not in game.pressed_keys:
                    game.pressed_keys.append(key)
            else:
                method = easypie.KEYDOWN
                game.key_queue.append((method, key, modifiers))
                game.pressed_keys.append(key)

    def keyReleaseEvent(self, event):
            if self.qt_to_sdl_press(event.key()) in game.pressed_keys:
                game.pressed_keys.remove(self.qt_to_sdl_press(event.key()))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setCursor(QtCore.Qt.BlankCursor)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def paintEvent(self, event):
        if self.enable_painting:
            scaled_buffer = pygame.transform.scale(self.buffer.copy(), (self.w, self.h))
            image = QtGui.QImage(scaled_buffer.get_buffer().raw, self.w, self.h, QtGui.QImage.Format_RGB32)
            self.painter.begin(self)
            self.painter.drawImage(self.border_size, self.border_size, image)
            self.painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.w, self.h = self.width()-self.border_size*2, self.height()-self.border_size*2


class StageWidget(QtWidgets.QWidget):
    def __init__(self, pygame_canvas, parent=None):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout(self))
        self.layout().setSpacing(5)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.canvas = CanvasWidget(pygame_canvas)
        self.layout().addWidget(self.canvas, 50)

        self.console = gui.debug_console.QDbgConsole((100, 100))
        self.layout().addWidget(self.console, 50)

    def play(self, code):
        self.console.clear()
        self.console.write("Starting program.")
        self.canvas.play()
        game._execute(code)

    def stop(self):
        game._game_thread.stop()
        self.canvas.stop()

    def pause(self):
        game._game_thread.paused = not game._game_thread.paused


class MainWidget(QtWidgets.QWidget):
    def __init__(self, pygame_canvas, parent=None):
        super(MainWidget, self).__init__(parent)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.stage = StageWidget(pygame_canvas)
        self.editor = gui.editor.Editor()

        self.layout().addWidget(self.stage, 50)
        self.layout().addWidget(self.editor, 50)

    def play(self):
        self.stage.play(self.editor.toPlainText())

    def stop(self):
        self.stage.stop()

    def pause(self):
        self.stage.pause()


class PlaceHolderWidget(QtWidgets.QTextEdit):
    def __init__(self, size=None, parent=None):
        super().__init__(parent)
        if size:
            self.setMinimumSize(*size)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, pygame_canvas, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setCentralWidget(MainWidget(pygame_canvas))
        self.setMinimumSize(1024, 768)

        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(60, 60))
        toolbar.addAction(QtGui.QIcon('./res/play.jpeg'), "play", self.centralWidget().play)
        toolbar.addAction(QtGui.QIcon('./res/stop.png'), "stop", self.centralWidget().stop)
        toolbar.addAction(QtGui.QIcon('./res/pause.jpg'), "pause", self.centralWidget().pause)
        self.addToolBar(toolbar)
        self.toolBar = toolbar

        self.show()

    def loop(self):
        self.centralWidget().stage.canvas.update()

    def closeEvent(self, event):
        game._game_thread.stop()


def init(screen):
    global main_window, app
    app = QtWidgets.QApplication([])
    main_window = MainWindow(screen)


def loop():
    main_window.loop()