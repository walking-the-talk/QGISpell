from builtins import object
import os.path
import subprocess

from qgis.core import QgsProject

__author__ = 'deluca'


class Utils(object):

    def __init__(self):
        pass

    @staticmethod
    def launch_without_console(command, args):
        """Launches 'command' windowless and waits until finished"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen([command] + args, startupinfo=startupinfo).wait()


class FileUtils(object):

    def __init__(self):
        pass

    @staticmethod
    def paths_are_equal(path1, path2):
        return os.path.normpath(os.path.normcase(path1)) == os.path.normpath(os.path.normcase(path2))


class LayerUtils(object):

    def __init__(self):
        pass

    @staticmethod
    def get_lay_id(layer_name):
        layers = QgsProject .instance().mapLayers()
        for name, layer in layers.items():
            if layer_name in layer.name() and layer.name().startswith(layer_name):
                return layer.id()

    @staticmethod
    def get_lay_from_id(lay_id):
        return QgsProject .instance().mapLayer(lay_id)

    @staticmethod
    def remove_layer(layer_name):
        layers = QgsProject .instance().mapLayers()
        for name, layer in layers.items():
            if layer_name in name:
                try:
                    QgsProject.instance().removeMapLayers([name])
                except Exception:
                    raise NameError('Cannot remove ' + layer_name + ' layer.')