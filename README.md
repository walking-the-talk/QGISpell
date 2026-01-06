## This plugin is depreciated and no longer maintained. Please use QspellinGIS instead - https://github.com/walking-the-talk/qspellingis

# QGISpell
A spelling plug-in for QGIS allowing users to spell-check attribute data inline

This plugin uses a modified QPlainTextEdit widget (thanks to Stephan Sokolow) to provide inline spelling using the Enchant libraries. See https://github.com/qgis/QGIS/issues/49934 for context
It is a proof of concept - so may throw errors if you try too hard. The basic functionality works.
## Installation
An easy way to install the Enchant libraries is to use pyEnchant https://pyenchant.github.io/pyenchant/install.html
### NOTE: In Windows the QGIS python interpreter breaks the Enchant libraries: https://github.com/qgis/QGIS/issues/55124
I have managed to get a mock-version to work in Windows, but it doesn't actually highlight spelling errors

If you have space, consider installing WSL Ubuntu on your Windows PC, install QGIS and add libenchant2 or pyenchant to this python installation. It works! This is how I built this plug-in

## Next Steps
If it is possible to port the Enchant libraries and the class SpellTextEdit into C++ within QGIS this could be integrated into QGIS - anywhere that currently uses a QPlainTextEdit widget could then use a SpellTextEdit widget instead (so attribute forms with text fields that are multiline, for example). This is way beyond my competence...

Feel free to take the ideas and fly...
