# -*- coding: utf-8 -*-
"""
/***************************************************************************
QGISpell
                                 A QGIS plugin
 A spelling plugin with basic functionality from Go2NextFeature and
 with inclusion of SpellTextEdit code
 
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

"""QPlainTextEdit With Inline Spell Check [Applies to class SpellTextEdit]
Original PyQt4 Version:
    https://nachtimwald.com/2009/08/22/qplaintextedit-with-in-line-spell-check/
Copyright 2009 John Schember
Copyright 2018 Stephan Sokolow
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from builtins import str
import os

from collections import OrderedDict
from .geo_utils import utils as geo_utils, vector_utils as vutils
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsMessageBar
from qgis.core import QgsProject, Qgis, QgsMapLayerProxyModel, QgsFieldProxyModel,edit
from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, Qt, QRect
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFrame, QFormLayout, QLabel, QLineEdit, QHBoxLayout, QTabWidget,\
    QScrollArea, QRadioButton, QButtonGroup, QCheckBox, QPushButton, QShortcut, QDockWidget, QSizePolicy, QSpacerItem, QGroupBox
from qgis.PyQt.QtGui import QKeySequence, QCursor

from . import buttons_utils
import operator

try:
    from qgis.core import QgsMapLayerType
except:
    pass

#start spell check imports
import sys
try: 
    import enchant
    from enchant import tokenize
    from enchant.errors import TokenizerNotFoundError
except ImportError:  
    pass

# pylint: disable=no-name-in-module
from PyQt5.Qt import Qt 
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import (QFocusEvent, QSyntaxHighlighter, QTextBlockUserData,
                         QTextCharFormat, QTextCursor)
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QMenu,
                             QPlainTextEdit)

try:
    # pylint: disable=ungrouped-imports
    from enchant.utils import trim_suggestions
except ImportError:  # Older versions of PyEnchant as on *buntu 14.04
    # pylint: disable=unused-argument
    def trim_suggestions(word, suggs, maxlen, calcdist=None):
        """API Polyfill for earlier versions of PyEnchant.
        TODO: Make this actually do some sorting
        """
        return suggs[:maxlen]

#end spell check imports
      
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgispell_dockwidget.ui'))


class QGISpellDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    plugin_name = 'QGISpell'

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(QGISpellDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.iface = iface

        self.feats_od = OrderedDict()
        self.ft_pos = -1
        self.sel_ft_pos = -1
        self.sel_ft_ids = None

        self.tool = None

        self.setup()

    def setup(self):
        self.setWindowTitle(QGISpellDockWidget.plugin_name)
        self.layer = self.iface.activeLayer() #get the active layer
        self.populateLayers()

        #Connect form actions to signals

        self.MapLayer.layerChanged.connect(self.update_textboxes)
        self.FieldOrderBy.fieldChanged.connect(self.cbo_attrib_activated) #Added
        self.chk_use_sel.toggled.connect(self.chk_use_sel_clicked)
        self.layerRefresh.pressed.connect(self.populateLayers)
        self.btn_first.pressed.connect(self.btn_first_pressed)
        self.btn_prev.pressed.connect(self.btn_prev_pressed)
        self.btn_next.pressed.connect(self.btn_next_pressed)
        self.btn_last.pressed.connect(self.btn_last_pressed)
        self.save_record.pressed.connect(self.save_record_pressed)
        self.cancel_record.pressed.connect(self.cancel_save)

        #QgsProject.instance().layerRemoved.connect(self.populateLayers)

        # Set controls

        self.chk_use_sel.setEnabled(False)
        self.FieldOrderBy.setEnabled(True) #added
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)


        # Shortcut
        shortcut = QShortcut(QKeySequence(Qt.Key_F8), self.iface.mainWindow())
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(self.btn_next_pressed)
        #self.update_textboxes()

    def populateLayers(self):
        try:
            self.map_layers = QgsProject.instance().mapLayers().values()
            self.allow_list = [lyr.id() for lyr in self.map_layers if lyr.type() == QgsMapLayerType.VectorLayer] #  and lyr.isEditable()]
            self.except_list = [l for l in self.map_layers if l.id() not in self.allow_list]
            self.MapLayer.setExceptedLayerList(self.except_list)
            #activelayer = QgsProject.instance().mapLayersByName(self.layer.name())[0]
            #self.MapLayer.setCurrentText(activelayer.name())
            #print(activelayer.name(),'current',self.layer.name(), 'combo',self.MapLayer)
            self.feats_od.clear()
            feats_d = {}
        except:
            return

    def update_textboxes(self):
    
        #on Spelling tab reset the layer fields - remove any existing from the previous layer
        for i in reversed(range(self.formLayout.count())): 
            widgetToRemove = self.formLayout.itemAt(i).widget()
            # remove it from the layout list
            self.formLayout.removeWidget(widgetToRemove)
            # remove it from the gui
            widgetToRemove.setParent(None)
        self.currentfeature = []
        layername = self.MapLayer.currentLayer()
        self.layer_label.setText('Layer: '+str(layername.name()))
        self.layer_label.setStyleSheet("background: DarkSeaGreen")
        self.FieldOrderBy.setLayer(layername)
        self.widgetBox = QWidget()
        #print("Loading layer: ", layername, self.FieldOrderBy.fields())  
        # get the list of selected layer's fields
        self.fields = [(field.name(), field.type()) for field in self.FieldOrderBy.fields()]
        # add QLabels and SpellTextEdit (text fields) / QLineEdits inside frame
        for row,(field_name, field_type) in enumerate(self.fields):
            # label as illustrative scope
            #print(field_name, field_type)
            fieldlabel = QLabel(field_name) 
            if field_type == 10:
                self.currentfeature.append(SpellTextEdit())
                #self.currentfeature[row].setEnabled(True)
            else:
                self.currentfeature.append(QLineEdit())
                #self.currentfeature[row].setEnabled(False)
            self.formLayout.addRow(fieldlabel,self.currentfeature[-1])
            fields = self.MapLayer.currentLayer().fields()
            #do not enable fields from joined layers
            if fields.fieldOrigin(row) == 2 or field_type != 10:
                self.currentfeature[row].setEnabled(False)            
            else:
                self.currentfeature[row].setEnabled(True) 
        #print(self.currentfeature)
        self.widgetBox.setLayout(self.formLayout)
        self.scrollArea.setWidget(self.widgetBox)
        self.scrollArea.setWidgetResizable(True)
        #resize to the available space
        widgetheight = self.fra_main.frameGeometry().height()
        widgetwidth = self.fra_main.frameGeometry().width()
        self.Tabs.resize(widgetwidth - 15,widgetheight - 20)
        self.scrollArea.resize(widgetwidth - 15,widgetheight - 75)
        self.ft_pos = -1
        self.cbo_attrib_activated()



    def save_record_pressed(self):

        fid = self.feats_od[self.ft_pos].id() # get the row number
        
        CurrentLayer = self.MapLayer.currentLayer()
        if CurrentLayer.isEditable() :
            for row,(field_name, field_type) in enumerate(self.fields):
                #update record in layer
                if field_type == 10:
                    CurrentLayer.changeAttributeValue(fid,row, self.currentfeature[row].toPlainText())
                    self.currentfeature[row].setStyleSheet("background: None") 
                else:
                    pass
        else:
            with edit(CurrentLayer):
                for row,(field_name, field_type) in enumerate(self.fields):
                    #update record in layer
                    if field_type == 10:
                        CurrentLayer.changeAttributeValue(fid,row, self.currentfeature[row].toPlainText())
                        self.currentfeature[row].setStyleSheet("background: None") 
                    else:
                        pass

        self.save_record.setStyleSheet("background: DarkSeaGreen")
        self.btn_next.setStyleSheet("background: None")
        self.btn_prev.setStyleSheet("background: None")
        self.cbo_attrib_activated()
             

    def cancel_save(self):
        #reset fields to their stored value
        for row,(field_name, field_type) in enumerate(self.fields):
            attrib_value = self.feats_od[self.ft_pos].attribute(field_name) 
            #print(attrib_value)
            if field_type == 10:
                self.currentfeature[row].setPlainText(str(attrib_value))
                self.currentfeature[row].setStyleSheet("background: None") 
            else:
                self.currentfeature[row].setText(str(attrib_value))
        self.btn_next.setStyleSheet("background: None")
        self.btn_prev.setStyleSheet("background: None") 

 
    def closeEvent(self, event):
#        layer = nothing
        self.closingPlugin.emit()
        event.accept()

    def chk_use_sel_clicked(self):

        self.sel_ft_ids = self.MapLayer.currentLayer().selectedFeatureIds()
        if self.chk_use_sel.isChecked() and len(self.sel_ft_ids) < 1:
            self.iface.messageBar().pushMessage(
                QGISpellDockWidget.plugin_name,
                'Please select at least one feature.',
                Qgis.Warning)  # TODO: softcode
            return

        self.ft_pos = -1
        self.sel_ft_pos = -1

        # Reset buttons
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(True)


    def lay_selection_changed(self):
        self.chk_use_sel.setChecked(False)

    def cbo_attrib_activated(self):

        if self.MapLayer.currentLayer() is None:
            return

        #Added check whether orderBy is empty
        if self.FieldOrderBy.currentField() is None:
            return

        self.feats_od.clear()

        feats_d = {}
        for feat in self.MapLayer.currentLayer().getFeatures():
            feats_d[feat] = feat.attribute(self.FieldOrderBy.currentField())
            #print(feats_d[feat])
        # Order features by chosen attribute
        feats_d_s = [(k, feats_d[k]) for k in sorted(feats_d, key=feats_d.get, reverse=False)]
        #print(feats_d_s)
        pos = 0
        for k, v in feats_d_s:
            self.feats_od[pos] = k
            pos += 1

        if self.ft_pos >= 0:
            self.btn_prev.setEnabled(True)
            self.cancel_save() 
        else:
            self.ft_pos = -1
            self.btn_prev.setEnabled(False)
        self.chk_use_sel.setEnabled(True)
        self.FieldOrderBy.setEnabled(True) 
        self.btn_next.setEnabled(True)
        self.btn_next_pressed()  
   
    def btn_first_pressed(self):

        start_point = -(self.ft_pos)
        self.move_ft(start_point)
        self.save_record.setStyleSheet("background: None")
        self.CountFeatures.setText("%d of %d features" % (1, len(self.feats_od)))
        #print(self.feats_od[1])
        if self.ft_pos >= len(self.feats_od) - 1:
            self.btn_next.setEnabled(False)

        if len(self.feats_od) > 1 and self.ft_pos > 0:
            self.btn_prev.setEnabled(True)

   
    def btn_prev_pressed(self):

        self.move_ft(-1)
        self.save_record.setStyleSheet("background: None")
        self.CountFeatures.setText("%d of %d features" % ((self.ft_pos + 1), len(self.feats_od)))
        self.btn_next.setEnabled(True)
        if self.ft_pos <= 0:
            self.btn_prev.setEnabled(False)

    def btn_next_pressed(self):

        self.move_ft(1)
        self.save_record.setStyleSheet("background: None")
        self.CountFeatures.setText("%d of %d features" % ((self.ft_pos + 1), len(self.feats_od)))
        #print(self.feats_od[1])
        if self.ft_pos >= len(self.feats_od) - 1:
            self.btn_next.setEnabled(False)

        if len(self.feats_od) > 1 and self.ft_pos > 0:
            self.btn_prev.setEnabled(True)

    def btn_last_pressed(self):

        end_point = len(self.feats_od) - self.ft_pos
        self.move_ft(end_point)
        self.save_record.setStyleSheet("background: None")
        self.CountFeatures.setText("%d of %d features" % (len(self.feats_od), len(self.feats_od)))
        #print(self.feats_od[1])
        if self.ft_pos >= len(self.feats_od) - 1:
            self.btn_next.setEnabled(False)

        if len(self.feats_od) > 1 and self.ft_pos > 0:
            self.btn_prev.setEnabled(True)


    def move_ft(self, increment):

        if self.ft_pos > -1:
            #check if the feature has been changed in Text boxes
            for row,(field_name, field_type) in enumerate(self.fields):
                if field_type == 10:
                    prev_value = self.feats_od[self.ft_pos].attribute(field_name) 
                    if self.currentfeature[row].toPlainText() != str(prev_value):
                        self.currentfeature[row].setStyleSheet("background: red")
                        self.btn_next.setStyleSheet("background: red")
                        self.btn_prev.setStyleSheet("background: red")
                        return
        self.ft_pos += increment

        self.ft_pos = max(self.ft_pos, 0)
        self.sel_ft_pos = max(self.ft_pos, 0)
        self.ft_pos = min(self.ft_pos, len(self.feats_od) - 1)
        self.sel_ft_pos = min(self.ft_pos, len(self.feats_od) - 1)

        if self.chk_use_sel.isChecked():

            while not self.feats_od[self.ft_pos].id() in self.sel_ft_ids:
                self.ft_pos += increment
                if self.ft_pos >= len(self.feats_od) - 1 or self.ft_pos <= 0:
                    self.ft_pos -= increment
                    return

            self.sel_ft_pos += increment
            if self.sel_ft_pos == len(self.sel_ft_ids):
                self.btn_next.setEnabled(False)
            if self.sel_ft_pos == 0:
                self.btn_prev.setEnabled(False)


        if 0 <= self.ft_pos < len(self.feats_od):

            renderer = self.iface.mapCanvas().mapSettings()
            geom = self.feats_od[self.ft_pos].geometry()

            if geom is None:
                self.iface.messageBar().pushInfo(
                    QGISpellDockWidget.plugin_name,
                    'The geometry of the feature is null: can neither zoom nor pan to it.')  # TODO: softcode

            else:

                if self.rad_action_pan.isChecked():
                    self.iface.mapCanvas().setCenter(renderer.layerToMapCoordinates(
                        self.layer,
                        geom.centroid().asPoint()))

                elif self.rad_action_zoom.isChecked():
                    self.iface.mapCanvas().setExtent(renderer.layerToMapCoordinates(
                        self.layer,
                        geom.boundingBox()))
                    self.iface.mapCanvas().zoomByFactor(1.1)

            self.iface.mapCanvas().refresh()
            fields = [(field.name(), field.type()) for field in self.MapLayer.currentLayer().fields()]

            # update the values in each text box
            for row,(field_name, field_type) in enumerate(self.fields):
                attrib_value = self.feats_od[self.ft_pos].attribute(field_name) 
                #print(attrib_value)
                if field_type == 10:
                    self.currentfeature[row].setPlainText(str(attrib_value))
                    self.currentfeature[row].setStyleSheet("background: None") 
                else:
                    self.currentfeature[row].setText(str(attrib_value))

                



# This is the heavy lifting of Spell Checking

class SpellTextEdit(QPlainTextEdit):
    """QPlainTextEdit subclass which does spell-checking using PyEnchant"""

    # Clamping value for words like "regex" which suggest so many things that
    # the menu runs from the top to the bottom of the screen and spills over
    # into a second column.
    max_suggestions = 20

    def __init__(self, *args):
        QPlainTextEdit.__init__(self, *args)

        # Start with a default dictionary based on the current locale.
        try:
            self.highlighter = EnchantHighlighter(self.document())
            self.highlighter.setDict(enchant.Dict())

        except:
            pass


    def contextMenuEvent(self, event):
        """Custom context menu handler to add a spelling suggestions submenu"""
        popup_menu = self.createSpellcheckContextMenu(event.pos())
        popup_menu.exec_(event.globalPos())

        # Fix bug observed in Qt 5.2.1 on *buntu 14.04 LTS where:
        # 1. The cursor remains invisible after closing the context menu
        # 2. Keyboard input causes it to appear, but it doesn't blink
        # 3. Switching focus away from and back to the window fixes it
        self.focusInEvent(QFocusEvent(QEvent.FocusIn))

    def createSpellcheckContextMenu(self, pos):
        """Create and return an augmented default context menu.
        This may be used as an alternative to the QPoint-taking form of
        ``createStandardContextMenu`` and will work on pre-5.5 Qt.
        """
        try:  # Recommended for Qt 5.5+ (Allows contextual Qt-provided entries)
            menu = self.createStandardContextMenu(pos)
        except TypeError:  # Before Qt 5.5
            menu = self.createStandardContextMenu()

        # Add a submenu for setting the spell-check language
        menu.addSeparator()
        try: #[error capture QGIS on Windows]
            menu.addMenu(self.createLanguagesMenu(menu))
            menu.addMenu(self.createFormatsMenu(menu))
        except:
            menu.addMenu(self.not_enchanted(menu))

        # Try to retrieve a menu of corrections for the right-clicked word
        spell_menu = self.createCorrectionsMenu(
            self.cursorForMisspelling(pos), menu)

        if spell_menu:
            menu.insertSeparator(menu.actions()[0])
            menu.insertMenu(menu.actions()[0], spell_menu)

        return menu

    def createCorrectionsMenu(self, cursor, parent=None):
        """Create and return a menu for correcting the selected word."""
        if not cursor:
            return None

        text = cursor.selectedText()
        suggests = trim_suggestions(text,
                                    self.highlighter.dict().suggest(text),
                                    self.max_suggestions)

        spell_menu = QMenu('Spelling Suggestions', parent)
        for word in suggests:
            action = QAction(word, spell_menu)
            action.setData((cursor, word))
            spell_menu.addAction(action)

        # Only return the menu if it's non-empty
        if spell_menu.actions():
            spell_menu.triggered.connect(self.cb_correct_word)
            return spell_menu

        return None

    def not_enchanted(self, parent=None): #[added to create a mock spell menu even if Enchant is not installed / functioning :-)]
        """Create and return a menu for selecting the spell-check language."""
        nospell_menu = QMenu('Spelling Suggestions', parent)
        nospell_actions = QActionGroup(nospell_menu)

        actions = ['You wish!', 'You need to install ENCHANT packages for your Operating System', 'and Python environment for this plugin to work correctly', 'Not currently working in Windows', 'but WSL Ubuntu works! If you have disc space and head space.']
        for action in  actions:
            nospell_menu.addAction(action)
        return nospell_menu

    def createLanguagesMenu(self, parent=None):
        """Create and return a menu for selecting the spell-check language."""
        curr_lang = self.highlighter.dict().tag
        lang_menu = QMenu("Language", parent)
        lang_actions = QActionGroup(lang_menu)

        for lang in enchant.list_languages():
            action = lang_actions.addAction(lang)
            action.setCheckable(True)
            action.setChecked(lang == curr_lang)
            action.setData(lang)
            lang_menu.addAction(action)

        lang_menu.triggered.connect(self.cb_set_language)
        return lang_menu

    def createFormatsMenu(self, parent=None):
        """Create and return a menu for selecting the spell-check language."""
        fmt_menu = QMenu("Format", parent)
        fmt_actions = QActionGroup(fmt_menu)

        curr_format = self.highlighter.chunkers()
        for name, chunkers in (('Text', []), ('HTML', [tokenize.HTMLChunker])):
            action = fmt_actions.addAction(name)
            action.setCheckable(True)
            action.setChecked(chunkers == curr_format)
            action.setData(chunkers)
            fmt_menu.addAction(action)

        fmt_menu.triggered.connect(self.cb_set_format)
        return fmt_menu

    def cursorForMisspelling(self, pos):
        """Return a cursor selecting the misspelled word at ``pos`` or ``None``
        This leverages the fact that QPlainTextEdit already has a system for
        processing its contents in limited-size blocks to keep things fast.
        """
        cursor = self.cursorForPosition(pos)
        misspelled_words = getattr(cursor.block().userData(), 'misspelled', [])

        # If the cursor is within a misspelling, select the word
        for (start, end) in misspelled_words:
            if start <= cursor.positionInBlock() <= end:
                block_pos = cursor.block().position()

                cursor.setPosition(block_pos + start, QTextCursor.MoveAnchor)
                cursor.setPosition(block_pos + end, QTextCursor.KeepAnchor)
                break

        if cursor.hasSelection():
            return cursor
        else:
            return None

    def cb_correct_word(self, action):  # pylint: disable=no-self-use
        """Event handler for 'Spelling Suggestions' entries."""
        cursor, word = action.data()

        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(word)
        cursor.endEditBlock()

    def cb_set_language(self, action):
        """Event handler for 'Language' menu entries."""
        lang = action.data()
        self.highlighter.setDict(enchant.Dict(lang))

    def cb_set_format(self, action):
        """Event handler for 'Language' menu entries."""
        chunkers = action.data()
        self.highlighter.setChunkers(chunkers)
        # TODO: Emit an event so this menu can trigger other things

class EnchantHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter subclass which consults a PyEnchant dictionary"""
    tokenizer = None
    token_filters = (tokenize.EmailFilter, tokenize.URLFilter)

    # Define the spellcheck style once and just assign it as necessary
    # XXX: Does QSyntaxHighlighter.setFormat handle keeping this from
    #      clobbering styles set in the data itself?
    err_format = QTextCharFormat()
    err_format.setUnderlineColor(Qt.red)
    err_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)

    def __init__(self, *args):
        QSyntaxHighlighter.__init__(self, *args)

        # Initialize private members
        self._sp_dict = None
        self._chunkers = []

    def chunkers(self):
        """Gets the chunkers in use"""
        return self._chunkers

    def dict(self):
        """Gets the spelling dictionary in use"""
        return self._sp_dict

    def setChunkers(self, chunkers):
        """Sets the list of chunkers to be used"""
        self._chunkers = chunkers
        self.setDict(self.dict())
        # FIXME: Revert self._chunkers on failure to ensure consistent state

    def setDict(self, sp_dict):
        """Sets the spelling dictionary to be used"""
        try:
            self.tokenizer = tokenize.get_tokenizer(sp_dict.tag,
                chunkers=self._chunkers, filters=self.token_filters)
        except TokenizerNotFoundError:
            # Fall back to the "good for most euro languages" English tokenizer
            self.tokenizer = tokenize.get_tokenizer(
                chunkers=self._chunkers, filters=self.token_filters)
        self._sp_dict = sp_dict

        self.rehighlight()

    def highlightBlock(self, text):
        """Overridden QSyntaxHighlighter method to apply the highlight"""
        if not self._sp_dict:
            return

        # Build a list of all misspelled words and highlight them
        misspellings = []
        for (word, pos) in self.tokenizer(text):
            if not self._sp_dict.check(word):
                self.setFormat(pos, len(word), self.err_format)
                misspellings.append((pos, pos + len(word)))

        # Store the list so the context menu can reuse this tokenization pass
        # (Block-relative values so editing other blocks won't invalidate them)
        data = QTextBlockUserData()
        data.misspelled = misspellings
        self.setCurrentBlockUserData(data)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    spellEdit = SpellTextEdit()
    spellEdit.show()

    sys.exit(app.exec_())