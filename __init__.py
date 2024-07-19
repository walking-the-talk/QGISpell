# -*- coding: utf-8 -*-
"""
/***************************************************************************
qgispell
                                 A QGIS plugin
 A spelling plugin with basic functionality from Go2NextFeature and
 SpellTextEdit code
 
 Requires PyEnchant
                             -------------------
        begin                : 2024-07-14
        git sha              : $Format:%H$
        copyright            : (C) 2024 Walking-the-Talk
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

"""
/***************************************************************************
 Modified from Go2NextFeature
                                 A QGIS plugin
 Allows jumping from a feature to another following an attribute order
                             -------------------
        begin                : 2016-12-27
        copyright            : (C) 2016 by Alberto De Luca for Tabacco Editrice
        email                : info@tabaccoeditrice.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load qgispell class from file qgispell.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .qgispell import QGISpell
    return QGISpell(iface)
