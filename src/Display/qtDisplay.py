#!/usr/bin/env python

# Copyright 2009-2019 Thomas Paviot (tpaviot@gmail.com)
#
# This file is part of pythonOCC.
#
# pythonOCC is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pythonOCC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pythonOCC.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import sys

from pythonocc.Display import OCCViewer
from pythonocc.Display.backend import get_qt_modules
# from pythonocc.Display.backend import load_backend  # removed in 7.4

from utils.logging_env import setup_logging, logging
log = logging.getLogger(__name__)
setup_logging(log)

# used_backend = load_backend() # removed in 7.4
QtCore, QtGui, QtWidgets, QtOpenGL = get_qt_modules()

# check if signal available, not available
# on PySide
HAVE_PYQT_SIGNAL = hasattr(QtCore, 'pyqtSignal')

class point(object):

    def __init__(self, obj=None):
        self.x = 0
        self.y = 0
        if obj is not None:
            self.set(obj)

    def set(self, obj):
        self.x = obj.x()
        self.y = obj.y()


class qtBaseViewer(QtOpenGL.QGLWidget):
    ''' The base Qt Widget for an OCC viewer
    '''
    def __init__(self, parent=None):
        super(qtBaseViewer, self).__init__(parent)
        self._display = None
        self._inited = False

        # enable Mouse Tracking
        self.setMouseTracking(True)

        # Strong focus
        self.setFocusPolicy(QtCore.Qt.WheelFocus)

        # required for overpainting the widget
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.setAutoFillBackground(False)

        X = self.size().width() // 2
        Y = self.size().height() // 2
        self.centrerect = (X - 10, Y - 10, X + 10, Y + 10)
        self.centrepoint = (X, Y)

    def GetHandle(self):
        ''' returns an the identifier of the GUI widget.
        It must be an integer
        '''
        win_id = self.winId()  # this returns either an int or voitptr
        if "%s" % type(win_id) == "<type 'PyCObject'>":  # PySide
            # ## with PySide, self.winId() does not return an integer
            if sys.platform == "win32":
                # # Be careful, this hack is py27 specific
                # # does not work with python31 or higher
                # # since the PyCObject api was changed
                import ctypes
                ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
                ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [
                    ctypes.py_object]
                win_id = ctypes.pythonapi.PyCObject_AsVoidPtr(win_id)
        elif not isinstance(win_id, int):  # PyQt4 or 5
            # # below integer cast may be required because self.winId() can
            # # returns a sip.voitptr according to the PyQt version used
            # # as well as the python version
            win_id = int(win_id)
        return win_id

    def resizeEvent(self, event):
        if self._inited:
            super(qtBaseViewer, self).resizeEvent(event)
            self._display.OnResize()
            X = self.size().width() // 2
            Y = self.size().height() // 2
            self.centrerect = (X - 10, Y - 10, X + 10, Y + 10)
            self.centrepoint = (X, Y)


class qtViewer3d(qtBaseViewer):

    # emit signal when selection is changed
    # is a list of TopoDS_*
    if HAVE_PYQT_SIGNAL:
        sig_topods_selected = QtCore.pyqtSignal(list)

    def __init__(self, *kargs):
        qtBaseViewer.__init__(self, *kargs)

        self.setObjectName("qt_viewer_3d")

        self._drawbox = False
        self._zoom_area = False
        self._select_area = False
        self._inited = False
        self._leftisdown = False
        self._middleisdown = False
        self._rightisdown = False
        self._selection = None
        self._drawtext = True
        # self._qApp = QtWidgets.QApplication.instance() # GXB
        self._qApp = None  # GXB
        self._key_map = {}
        self._current_cursor = "arrow"
        self._available_cursors = {}

        self.selected = []  # GXB
        self.sig_topods_selected.connect(self.selected.extend)  # GXB

        # ############################# GXB code - dormant

        # self.add_funcky()
        
        # self._actions = {}
        # # define dummy function to handle events if no added function

        # def funcky(*args, **kargs):
        #     print("")
        #     pass

        # self._actions['view1'] = QtWidgets.QAction('view1', self)
        # self._actions['view1'].triggered.connect(funcky)
        # self._actions['perform'] = QtWidgets.QAction('view1', self)
        # self._actions['perform'].triggered.connect(funcky)

        # self.action_list = []
        # self.action_no = 0
        # ###################################

    @property
    def qApp(self):
        # reference to QApplication instance
        return self._qApp

    @qApp.setter
    def qApp(self, value):
        self._qApp = value

    def InitDriver(self, close_function):
        self.close_window = close_function

        self._display = OCCViewer.Viewer3d(window_handle=self.GetHandle(),
                                           parent=self)
        # GXB amended code to remove parent for some reason - reinstating
        # self._display = OCCViewer.Viewer3d(self.GetHandle()) # GXB

        self._display.Create()

        # background gradient
        # self._display.set_bg_gradient_color(206, 215, 222, 128, 128, 128)

        self._display.SetModeShaded()
        self._display.display_triedron()  # GXB preference
        self._inited = True
        # dict mapping keys to functions
        self._SetupKeyMap()
        self.createCursors()

        X = self.size().width() // 2  # GXB
        Y = self.size().height() // 2  # GXB
        self.centrerect = (X - 10, Y - 10, X + 10, Y + 10)  # GXB
        self.centrepoint = (X, Y)  # GXB

    def _SetupKeyMap(self):
        self._key_map = {ord('W'): self._display.SetModeWireFrame,
                         ord('S'): self._display.SetModeShaded,
                         ord('A'): self._display.EnableAntiAliasing,
                         ord('B'): self._display.DisableAntiAliasing,
                         ord('H'): self._display.SetModeHLR,
                         ord('F'): self._display.FitAll,
                         ord('G'): self._display.SetSelectionMode,
                         ord('Q'): self.close_window,
                         ord('1'): self._display.View_Iso,
                         # ord('2'): self._actions['perform'].trigger,
                         ord('2'): self._display.View_Above,
                         ord('6'): self._display.Up,
                         ord('3'): self._display.PrintCamera,
                         ord('4'): self._display.SetCamera,
                         # ord('9'): self._actions['view1'].trigger,
                         # ord('8'): self.timer,
                         # ord('7'): self.next_action
                         }

    def createCursors(self):
        module_pth = os.path.abspath(os.path.dirname(__file__))
        icon_pth = os.path.join(module_pth, "icons")

        _CURSOR_PIX_ROT = QtGui.QPixmap(os.path.join(icon_pth,
                                                     "cursor-rotate.png"))
        _CURSOR_PIX_PAN = QtGui.QPixmap(os.path.join(icon_pth,
                                                     "cursor-pan.png"))
        _CURSOR_PIX_ZOOM = QtGui.QPixmap(os.path.join(icon_pth,
                                                      "cursor-magnify.png"))
        _CURSOR_PIX_ZOOM_AREA = QtGui.QPixmap(os.path.join(icon_pth,
                                                           "cursor-magnify"
                                                           "-area.png"))

        self._available_cursors = {
            "arrow": QtGui.QCursor(QtCore.Qt.ArrowCursor),  # default
            "pan": QtGui.QCursor(_CURSOR_PIX_PAN),
            "rotate": QtGui.QCursor(_CURSOR_PIX_ROT),
            "zoom": QtGui.QCursor(_CURSOR_PIX_ZOOM),
            "zoom-area": QtGui.QCursor(_CURSOR_PIX_ZOOM_AREA),
        }

        self._current_cursor = "arrow"

    def keyPressEvent(self, event):
        code = event.key()
        if code in self._key_map:
            self._key_map[code]()
        elif code in range(256):
            log.info('key: "%s"(code %i) not mapped to any function' %
                     (chr(code), code))
        else:
            log.info('key: code %i not mapped to any function' % code)

    # ############################# GXB code - dormant
    # def actionEvent(self, event):
    #     self._SetupKeyMap()

    # def print_actions(self):
    #     print(self._actions)
    #     for each in self._actions.keys():
    #         pass

    # def next_action(self):
    #     self._actions.get(self.action_list[self.action_no],
    #                       self.funcky).trigger()
    #     self.action_no += 1
    #     if self.action_no >= len(self.action_list):
    #         self.action_no = 0

    # def timer(self):
    #     _timer = QtCore.QTimer(self)
    #     _timer.setSingleShot = True
    #     _timer.singleShot(3000, self.next_action)
    #     # _timer.start(1000)
    # ############################# GXB code - dormant


    def focusInEvent(self, event):
        if self._inited:
            self._display.Repaint()

    def focusOutEvent(self, event):
        if self._inited:
            self._display.Repaint()

    def paintEvent(self, event):
        if self._drawbox:
            self._display.Repaint()
            self._display.Repaint()
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2))
            rect = QtCore.QRect(*self._drawbox)
            painter.drawRect(rect)

    def wheelEvent(self, event):
        try:  # PyQt4/PySide
            delta = event.delta()
        except:  # PyQt5
            delta = event.angleDelta().y()
        if delta > 0:
            zoom_factor = 2.
        else:
            zoom_factor = 0.5
        self._display.Repaint()  # GXB
        self._display.ZoomFactor(zoom_factor)

    @property
    def cursor(self):
        return self._current_cursor

    @cursor.setter
    def cursor(self, value):
        if not self._current_cursor == value:

            self._current_cursor = value
            cursor = self._available_cursors.get(value)

            if cursor:
                self.qApp.setOverrideCursor(cursor)
            else:
                self.qApp.restoreOverrideCursor()

    def mousePressEvent(self, event):
        self.setFocus()
        ev = event.pos()
        self.dragStartPosX = ev.x()
        self.dragStartPosY = ev.y()
        self._display.StartRotation(self.dragStartPosX, self.dragStartPosY)

    def mouseReleaseEvent(self, event):
        pt = event.pos()
        modifiers = event.modifiers()

        if event.button() == QtCore.Qt.LeftButton:
            if self._select_area:
                [Xmin, Ymin, dx, dy] = self._drawbox
                self._display.SelectArea(Xmin, Ymin, Xmin + dx, Ymin + dy)
                self._select_area = False
            else:
                # multiple select if shift is pressed
                if modifiers == QtCore.Qt.ShiftModifier:
                    self._display.ShiftSelect(pt.x(), pt.y())
                else:
                    # single select otherwise
                    self._display.Select(pt.x(), pt.y())

                    case1 = (self._display.selected_shapes is not None)
                    shapes_to_emit = self._display.selected_shapes
                    if case1 and HAVE_PYQT_SIGNAL:
                        self.sig_topods_selected.emit(shapes_to_emit)
                        # self.sig_topods_selected1.emit(shapes_to_emit)

        elif event.button() == QtCore.Qt.RightButton:
            if self._zoom_area:
                [Xmin, Ymin, dx, dy] = self._drawbox
                self._display.ZoomArea(Xmin, Ymin, Xmin + dx, Ymin + dy)
                self._zoom_area = False

        self.cursor = "arrow"

    def DrawBox(self, event):
        tolerance = 2
        pt = event.pos()
        dx = pt.x() - self.dragStartPosX
        dy = pt.y() - self.dragStartPosY
        if abs(dx) <= tolerance and abs(dy) <= tolerance:
            return
        self._drawbox = [self.dragStartPosX, self.dragStartPosY, dx, dy]

    def mouseMoveEvent(self, evt):
        pt = evt.pos()
        buttons = int(evt.buttons())
        modifiers = evt.modifiers()
        # ROTATE
        if (buttons == QtCore.Qt.LeftButton
                and not modifiers == QtCore.Qt.ShiftModifier):
            self.cursor = "rotate"
            self._display.Rotation(pt.x(), pt.y())
            self._drawbox = False
        # DYNAMIC ZOOM
        elif (buttons == QtCore.Qt.RightButton
              and not modifiers == QtCore.Qt.ShiftModifier):
            self.cursor = "zoom"
            self._display.Repaint()
            self._display.DynamicZoom(abs(self.dragStartPosX),
                                      abs(self.dragStartPosY), abs(pt.x()),
                                      abs(pt.y()))
            self.dragStartPosX = pt.x()
            self.dragStartPosY = pt.y()
            self._drawbox = False
        # PAN
        elif buttons == QtCore.Qt.MidButton:
            dx = pt.x() - self.dragStartPosX
            dy = pt.y() - self.dragStartPosY
            self.dragStartPosX = pt.x()
            self.dragStartPosY = pt.y()
            self.cursor = "pan"
            self._display.Pan(dx, -dy)
            self._drawbox = False
        # DRAW BOX
        # ZOOM WINDOW
        elif (buttons == QtCore.Qt.RightButton
              and modifiers == QtCore.Qt.ShiftModifier):
            self._zoom_area = True
            self.cursor = "zoom-area"
            self.DrawBox(evt)
            self.update()
        # SELECT AREA
        elif (buttons == QtCore.Qt.LeftButton
              and modifiers == QtCore.Qt.ShiftModifier):
            self._select_area = True
            self.DrawBox(evt)
            self.update()
        else:
            self._drawbox = False
            self._display.MoveTo(pt.x(), pt.y())
            self.cursor = "arrow"

    # ######################################## GXB ADDED

    def select_all_visible(self):

        self._display.SelectArea(0, 0,
                                 self.size().width(),
                                 self.size().height())

        if (self._display.selected_shapes is not None) and HAVE_PYQT_SIGNAL:

            sys.stdout.flush()
            self.sig_topods_selected.emit(self._display.selected_shapes)

        return self._display.selected_shapes

    def select_centrepoint(self):

        self._display.Select5(*self.centrepoint)
        if (self._display.selected_shapes is not None) and HAVE_PYQT_SIGNAL:
            self.sig_topods_selected.emit(self._display.selected_shapes)
        return self._display.selected_shapes

    # ######################################## GXB ADDED

    # ######################################## GXB ADDED - not sure why

    # def funcky(self):
    #     pass

    # def add_funcky(self):
    #     self._actions["funcky"] = QtWidgets.QAction("funcky", self)
    #     self._actions["funcky"].triggered.connect(self.funcky)
    #     self.addAction(self._actions["funcky"])

    # def added_function(self, func):
    #     def funcky(*args, **kargs):
    #         pass
    #     if callable(func):
    #         self.func = func
    #     else:
    #         self.func = funcky

    # ######################################## GXB ADDED - not sure why
