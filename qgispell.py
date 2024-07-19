# -*- coding: utf-8 -*-
"""
/***************************************************************************
QGISpell
                                 A QGIS plugin
 A spelling plugin with basic functionality from Go2NextFeature and
 SpellTextEdit code
 
 Requires PyEnchant
                             -------------------
        begin                : 2024-07-14
        git sha              : $Format:%H$
        copyright            : (C) 2024 Walking-the-Talk
        email                : chris.york@walking-the-talk.co.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

"""
/***************************************************************************
 Modified from Go2NextFeature
                                 A QGIS plugin
 Allows jumping from a feature to another following an attribute order
                              -------------------
        begin                : 2016-12-27
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Alberto De Luca for Tabacco Editrice
        email                : info@tabaccoeditrice.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
# Initialize Qt resources from file resources.py
from . import resources

# Import the code for the DockWidget
from .qgispell_dockwidget import QGISpellDockWidget
import os.path


class QGISpell(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QGISpell_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.pluginIsActive = False
        self.dockwidget = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/QGISpell/icon.png"),
            QCoreApplication.translate('QGISpell', u"QGISpell"), self.iface.mainWindow())
        self.action.setEnabled(True)

        # connect to signals for button behavior
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.pluginToolBar().addAction(self.action)
        self.iface.pluginMenu().addAction(self.action)

    def onClosePlugin(self):

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        # self.dockwidget = None
        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.pluginMenu().removeAction(self.action)
        self.iface.pluginToolBar().removeAction(self.action)

    def run(self):

        """Run method that loads and starts the plugin"""
        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = QGISpellDockWidget(self.iface)
                # connect to provide cleanup on closing of dockwidget
                self.dockwidget.closingPlugin.connect(self.onClosePlugin)

                # show the dockwidget
                self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

        else:
            self.pluginIsActive = False
            self.dockwidget.hide()
