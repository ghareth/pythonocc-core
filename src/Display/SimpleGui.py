#!/usr/bin/env python

# Copyright 2009-2016 Thomas Paviot (tpaviot@gmail.com)
#
# This file is part of pythonOCC.
##
# pythonOCC is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
##
# pythonOCC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
##
# You should have received a copy of the GNU Lesser General Public License
# along with pythonOCC.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from pythonocc import VERSION
from pythonocc.Display.backend import load_backend, get_qt_modules
from pythonocc.Display.OCCViewer import OffscreenRenderer

from utils.logging_env import setup_logging, logging
log = logging.getLogger(__name__)
setup_logging(log)


def check_callable(_callable):
    if not callable(_callable):
        raise AssertionError("The function supplied is not callable")


def init_display(backend_str=None,
                 disp=None,
                 size=(600, 400),
                 display_triedron=True,
                 background_gradient_color1=[206, 215, 222],
                 background_gradient_color2=[128, 128, 128],
                 ):
    """ This function loads and initialize a GUI using either wx, pyq4, pyqt5
    or pyside.
    If ever the environment variable PYTHONOCC_OFFSCREEN_RENDERER, then the
    GUI is simply
    ignored and an offscreen renderer is returned.
    init_display returns 4 objects :
    * display : an instance of Viewer3d ;
    * start_display : a function (the GUI mainloop) ;
    * add_menu : a function that creates a menu in the GUI
    * add_function_to_menu : adds a menu option

    In case an offscreen renderer is returned, start_display and add_menu are
    ignored, i.e.an empty function is returned (named do_nothing).
    add_function_to_menu just execute the function taken as a paramter.

    Note : the offscreen renderer is used on the travis side.
    """
    if os.getenv("PYTHONOCC_OFFSCREEN_RENDERER") == "1":
        # create the offscreen renderer
        offscreen_renderer = OffscreenRenderer()

        def do_nothing(*kargs, **kwargs):
            """ A method that does nothing
            """
            pass

        def call_function(s, func):
            """ A function that calls another function.
            Helpfull to bypass add_function_to_menu. s should be a string
            """
            check_callable(func)
            log.debug("Execute %s :: %s menu fonction" % (s, func.__name__))
            func()

        # returns empty classes and functions
        return offscreen_renderer, do_nothing, do_nothing, call_function
    used_backend = load_backend(backend_str)
    log.debug("GUI backend set to: %s", used_backend)

    # wxPython based simple GUI
    if used_backend == 'wx':
        import wx
        from OCC.Display.wxDisplay import wxViewer3d

        class AppFrame(wx.Frame):

            def __init__(self, parent):
                wx.Frame.__init__(self, parent, -1,
                                  ("pythonOCC-%s 3d viewer ('wx' backend)"
                                   % VERSION),
                                  style=wx.DEFAULT_FRAME_STYLE, size=size)
                self.canva = wxViewer3d(self)
                self.menuBar = wx.MenuBar()
                self._menus = {}
                self._menu_methods = {}

            def add_menu(self, menu_name):
                _menu = wx.Menu()
                self.menuBar.Append(_menu, "&" + menu_name)
                self.SetMenuBar(self.menuBar)
                self._menus[menu_name] = _menu

            def add_function_to_menu(self, menu_name, _callable):
                # point on curve
                _id = wx.NewId()
                check_callable(_callable)
                call_name = _callable.__name__
                _call_name = call_name.replace('_', ' ').lower()
                try:
                    self._menus[menu_name].Append(_id,
                                                  _call_name)
                except KeyError:
                    raise ValueError('the menu item %s does not exist'
                                     % menu_name)
                self.Bind(wx.EVT_MENU, _callable, id=_id)

        app = wx.App(False)
        win = AppFrame(None)
        win.Show(True)
        wx.SafeYield()
        win.canva.InitDriver()
        app.SetTopWindow(win)
        display = win.canva._display

        def add_menu(*args, **kwargs):
            win.add_menu(*args, **kwargs)

        def add_function_to_menu(*args, **kwargs):
            win.add_function_to_menu(*args, **kwargs)

        def start_display():
            app.MainLoop()

    # Qt based simple GUI
    elif 'qt' in used_backend:
        from pythonocc.Display.qtDisplay import qtViewer3d

        QtCore, QtGui, QtWidgets, QtOpenGL = get_qt_modules()

        class MainWindow(QtWidgets.QMainWindow):

            def __init__(self, *args, **kwargs):
                QtWidgets.QMainWindow.__init__(self, *args)
                self.canva = qtViewer3d(self)
                self.setWindowTitle("pythonOCC-%s 3d viewer ('%s' backend)"
                                    % (VERSION, used_backend))
                self.setCentralWidget(self.canva)
                if sys.platform != 'darwin':
                    self.menu_bar = self.menuBar()
                else:
                    # create a parentless menubar
                    # see: http://stackoverflow.com/questions/11375176/
                    # qmenubar-and-qmenu-doesnt-show-in-mac-os-x?lq=1
                    #
                    # noticeable is that the menu ( alas ) is created in the
                    # topleft of the screen, just next to the apple icon
                    # still does ugly things like showing the "Python" menu in
                    # bold

                    # Original code ..
                    # self.menu_bar = QtWidgets.QMenuBar()
                    # Replaced by http://littlecaptain.net/2017/10/13/PyQt5-tutorial-Menus-and-toolbars/
                    self.menu_bar = self.menuBar()
                    self.menu_bar.setNativeMenuBar(False)
                self._menus = {}
                self._menu_methods = {}
                # place the window in the center of the screen, at half the
                # screen size
                self.centerOnScreen()

            def centerOnScreen(self):
                '''Centers the window on the screen.'''
                resolution = QtWidgets.QDesktopWidget().screenGeometry()
                log.debug(resolution)
                self.resize((resolution.width() / 1.1),
                            (resolution.height() / 1.1))

                self.move((resolution.width() / 2)
                          - (self.frameSize().width() / 2),
                          (resolution.height() / 2)
                          - (self.frameSize().height() / 2))

                # self.move((resolution.width() / 2)
                #           - (self.frameSize().width() / 2),
                #           (resolution.height() / 8) )

            def add_menu(self, menu_name):
                _menu = self.menu_bar.addMenu("&" + menu_name)
                self._menus[menu_name] = _menu

            def add_function_to_menu(self, menu_name, _callable):
                check_callable(_callable)
                try:
                    call_name = _callable.__name__.replace('_', ' ').lower()
                    _action = QtWidgets.QAction(call_name, self)
                    # if not, the "exit" action is now shown...
                    _action.setMenuRole(QtWidgets.QAction.NoRole)
                    _action.triggered.connect(_callable)

                    self._menus[menu_name].addAction(_action)
                except KeyError:
                    raise ValueError('the menu item %s does not exist'
                                     % menu_name)

            def add_function(self, _callable):
                check_callable(_callable)
                call_name = _callable.__name__
                _call_name = call_name.replace('_', ' ').lower()
                self.canva._actions[call_name] = QtWidgets.QAction(_call_name,
                                                                   self)
                self.canva._actions[call_name].triggered.connect(_callable)
                self.canva.addAction(self.canva._actions[call_name])

        # following couple of lines is a tweak to enable ipython --gui='qt'

        app = QtWidgets.QApplication.instance()  # checks if QApplication
        #                                        # already exists
        if not app:  # create QApplication if it doesnt exist
            app = QtWidgets.QApplication(sys.argv)
        win = MainWindow()
        win.show()

        # win.window().setScreen(app.screens()[0])
        # win.resize(size[0], size[1])

        win.canva.InitDriver(win.close)
        win.canva.qApp = app
        display = win.canva._display

        # background gradient
        if background_gradient_color1 and background_gradient_color2:
            display.set_bg_gradient_color(background_gradient_color1,
                                          background_gradient_color2)
        # display black triedron
        display.display_triedron()

        def add_menu(*args, **kwargs):
            win.add_menu(*args, **kwargs)

        def add_function_to_menu(*args, **kwargs):
            win.add_function_to_menu(*args, **kwargs)

        def start_display():
            win.raise_()  # make the application float to the top
            app.exec_()

        def add_function(*args, **kwargs):
            win.add_function(*args, **kwargs)

        add_menu('exit')
        add_function_to_menu('exit', win.close)

        disp['start'] = start_display
        disp['add_menu'] = add_menu
        disp['add_function_to_menu'] = add_function_to_menu
        disp['add_function'] = add_function
        disp['canva'] = win.canva
        disp['win'] = win

        disp['selected'] = win.canva.selected

    return display


if __name__ == '__main__':

    from OCC.Core.BRepPrimAPI import (BRepPrimAPI_MakeSphere,
                                      BRepPrimAPI_MakeBox)

    disp = {}
    display = init_display(disp=disp)

    def sphere(event=None):
        display.DisplayShape(BRepPrimAPI_MakeSphere(100).Shape(), update=True)

    def cube(event=None):
        display.DisplayShape(BRepPrimAPI_MakeBox(1, 1, 1).Shape(), update=True)

    def exit(event=None):
        sys.exit()

    disp['add_menu']('primitives')
    disp['add_function_to_menu']('primitives', sphere)
    disp['add_function_to_menu']('primitives', cube)
    disp['add_function_to_menu']('primitives', exit)

    disp['start']()
