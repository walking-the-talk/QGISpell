from builtins import object
import configparser
from configparser import NoOptionError
from qgis.PyQt.QtGui import QColor

opt_layer_name = 'layer'
opt_attributes_name = 'attrib_names'
opt_values_name = 'values'
opt_label_name = 'label'
opt_text_color_name = 'text_color'
opt_bg_color_name = 'background_color'
opt_tooltip_name = 'tooltip'


def read_buttons_txt(txt_file_path):

    config = configparser.ConfigParser()
    config.read(txt_file_path)
    buttons = []
    for section in config.sections():

        layer_name = config.get(section, opt_layer_name)
        attrib_names = config.get(section, opt_attributes_name).split(',')
        values = config.get(section, opt_values_name).split(',')
        label = config.get(section, opt_label_name)

        text_color = None
        try:
            text_color_rgb = config.get(section, opt_text_color_name)
            if text_color_rgb != '':
                text_color_rgb = text_color_rgb.split(',')
                text_color = QColor(int(text_color_rgb[0]), int(text_color_rgb[1]), int(text_color_rgb[2]))
        except NoOptionError:
            text_color = None

        bg_color = None
        try:
            bg_color_rgb = config.get(section, opt_bg_color_name)
            if bg_color_rgb != '':
                bg_color_rgb = bg_color_rgb.split(',')
                bg_color = QColor(int(bg_color_rgb[0]), int(bg_color_rgb[1]), int(bg_color_rgb[2]))
        except NoOptionError:
            bg_color = None

        try:
            tooltip = config.get(section, opt_tooltip_name)
        except NoOptionError:
            tooltip = None

        button = TButton(layer_name, attrib_names, values, label, text_color, bg_color, tooltip)
        buttons.append(button)

    return buttons


class TButton(object):

    def __init__(self, layer_name, attrib_names, values, label, text_color=None, background_color=None, tooltip=None):
        self.layer_name = layer_name
        self.attrib_names = attrib_names
        self.values = values
        self.label = label
        self.text_color = text_color
        self.background_color = background_color
        self.tooltip = tooltip
