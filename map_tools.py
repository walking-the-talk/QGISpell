# -*- coding: utf-8 -*-

from builtins import range
from builtins import object
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsFeatureRequest, QgsGeometry, QgsFeature, QgsSnapper, QgsProject, QgsTolerance, QgsVectorLayer, QgsRectangle
from qgis.gui import *
import operator
from ..params import Params
from ..geo_utils import vector_utils as vutils

tolerance = 0.01


class SetAttributesTool(QgsMapTool):

    def __init__(self, data_dock, params, layer, attributes_values_d):
        QgsMapTool.__init__(self, data_dock.iface.mapCanvas())

        self.iface = data_dock.iface
        """:type : QgisInterface"""
        self.data_dock = data_dock
        """:type : DataDock"""
        self.params = params
        self.layer = layer
        self.attributes_values_d = attributes_values_d

        self.mouse_pt = None
        self.mouse_clicked = False

    def canvasPressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouse_clicked = False

        if event.button() == Qt.LeftButton:
            self.mouse_clicked = True

    def canvasMoveEvent(self, event):

        self.mouse_pt = self.toMapCoordinates(event.pos())

    def canvasReleaseEvent(self, event):

        if not self.mouse_clicked:
            return

        if event.button() == Qt.LeftButton:

            self.mouse_clicked = False
            self.mouse_pt = self.toLayerCoordinates(self.layer, event.pos())

            closest_fts = MapToolsUtils.find_clicked_feats(self.iface, self.mouse_pt, self.layer)
            if closest_fts is None:
                return
            closest_ft = closest_fts[0]

            self.layer.beginEditCommand('Set attributes')

            for attribute, value in self.attributes_values_d.items():

                old_val = closest_ft.attribute(attribute)
                closest_ft.setAttribute(attribute, None)
                self.layer.changeAttributeValue(
                    closest_ft.id(),
                    closest_ft.fieldNameIndex(attribute),
                    value,
                    old_val)

            self.layer.endEditCommand()

            self.iface.mapCanvas().refresh()

    def activate(self):
        pass

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def reset_marker(self):
        self.outlet_marker.hide()
        self.canvas().scene().removeItem(self.outlet_marker)


class SmoothFeatureTool(QgsMapTool):

    def __init__(self, data_dock, iters, offset, enforce_topol):
        QgsMapTool.__init__(self, data_dock.iface.mapCanvas())

        self.data_dock = data_dock
        self.iface = data_dock.iface

        self.mouse_pt = None
        self.mouse_clicked = False

        self.iters = iters
        self.offset = offset
        self.enforce_topol = enforce_topol

    def canvasPressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouse_clicked = False

        if event.button() == Qt.LeftButton:
            self.mouse_clicked = True

    def canvasMoveEvent(self, event):
        self.mouse_pt = self.toMapCoordinates(event.pos())

    def canvasReleaseEvent(self, event):
        if not self.mouse_clicked:
            return

        if event.button() == Qt.LeftButton:

            self.mouse_clicked = False

            layer = self.iface.activeLayer()
            if layer is None:
                self.iface.messageBar().pushWarning(
                    Params.plugin_name,
                    'No layer selected.')  # TODO: softcode
                return

            if not layer.isEditable():
                self.iface.messageBar().pushInfo(
                    Params.plugin_name,
                    'The selected layer is not editable.')  # TODO: softcode
                return

            self.mouse_pt = self.toLayerCoordinates(layer, event.pos())
            closest_fts = MapToolsUtils.find_clicked_feats(self.iface, self.mouse_pt, layer)
            if closest_fts is None:
                return
            closest_ft = closest_fts[0]

            old_geom = closest_ft.geometry()

            layer.beginEditCommand('Smooth line')

            old_pts = old_geom.asPolyline()

            # Find intersecting lines
            inters_lines = {}
            cand_fts = layer.getFeatures(QgsFeatureRequest().setFilterRect(old_geom.boundingBox()))
            for cand_ft in cand_fts:
                if cand_ft.id() == closest_ft.id():
                    continue
                if old_geom.intersects(cand_ft.geometry()):
                    cand_pts = cand_ft.geometry().asPolyline()
                    # Find points overlapping points
                    for cpt in range(len(cand_pts)):
                        for old_pt in old_pts:
                            if cand_pts[cpt].compare(old_pt, tolerance):
                                if cand_ft.id() in inters_lines:
                                    inters_lines[cand_ft.id()].append(cpt)
                                else:
                                    inters_lines[cand_ft.id()] = [cpt]

            # Smooth line
            new_line_pts = old_geom.smoothLine(old_geom.asPolyline(), self.iters, self.offset)
            # new_line_geom = QgsGeometry.fromPolyline(new_line_pts)

            # Modify intersecting lines
            if self.enforce_topol:
                for ints_line_ft_id, vertex_idxs in inters_lines.items():
                    ints_line_ft = vutils.get_feats_by_id(layer, ints_line_ft_id)[0]
                    old_ints_geom = ints_line_ft.geometry()
                    old_ints_pts = old_ints_geom.asPolyline()
                    for vertex_idx in vertex_idxs:
                        new_line_geom = QgsGeometry.fromPolyline(new_line_pts)
                        new_vx_pos = new_line_geom.nearestPoint(QgsGeometry.fromPoint(old_ints_pts[vertex_idx])).asPoint()
                        # Check if on the new line geometry a vertex exists closed enough to new vertex position
                        v_found = False
                        for new_line_pt in new_line_pts:
                            if new_line_pt.compare(new_vx_pos, tolerance):
                                old_ints_pts[vertex_idx] = new_line_pt
                                v_found = True
                                break
                        if not v_found:
                            # Add a point in new line geom and move point of intersecting l ine
                            pt, side, aft = new_line_geom.closestSegmentWithContext(new_vx_pos)
                            new_line_pts.insert(aft, new_vx_pos)
                            old_ints_pts[vertex_idx] = new_vx_pos

                    layer.changeGeometry(ints_line_ft.id(), QgsGeometry.fromPolyline(old_ints_pts))

            new_line_geom = QgsGeometry.fromPolyline(new_line_pts)
            layer.changeGeometry(closest_ft.id(), new_line_geom)
            layer.endEditCommand()

            self.iface.mapCanvas().refresh()

    def activate(self):
        pass

    def deactivate(self):
        self.data_dock.btn_ssl_smooth.setChecked(False)

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def reset_marker(self):
        self.outlet_marker.hide()
        self.canvas().scene().removeItem(self.outlet_marker)


class CreateFeatureTool(QgsMapTool):
    def __init__(self, data_dock, params, layer, attributes_values_d):
        QgsMapTool.__init__(self, data_dock.iface.mapCanvas())

        self.layer = layer
        self.attributes_values_d = attributes_values_d

        self.map_canvas = data_dock.iface.mapCanvas()

        self.rubber_band = QgsRubberBand(self.map_canvas, False)
        self.rubber_band.setColor(QColor(255, 128, 128))
        self.rubber_band.setWidth(1)
        self.rubber_band.setBrushStyle(Qt.Dense4Pattern)
        self.rubber_band.reset()

        self.vertex_marker = QgsVertexMarker(self.canvas())
        self.vertex_marker.setColor(QColor(255, 0, 255))
        self.vertex_marker.setIconSize(10)
        self.vertex_marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.vertex_marker.setPenWidth(3)

        self.mouse_clicked = False
        self.first_click = False
        self.snapper = None
        self.mouse_pt = None
        self.snapped_vertex = None
        self.snapped_feat_id = None
        self.after_vx_idx = None
        self.feats_vx_idx_d = {}
        self.snapped_vx_nr = -1

    def canvasPressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.mouse_clicked = False

        if event.button() == Qt.LeftButton:
            self.mouse_clicked = True

    def canvasMoveEvent(self, event):
        self.mouse_pt = self.toMapCoordinates(event.pos())

        # Mouse not clicked: snapping to closest vertex
        (retval, result) = self.snapper.snapMapPoint(self.mouse_pt)

        if len(result) > 0:
            self.snapped_feat_id = result[0].snappedAtGeometry

            self.snapped_vertex = result[0].snappedVertex

            self.after_vx_idx = result[0].afterVertexNr

            self.snapped_vx_nr = result[0].snappedVertexNr

            # self.snapped_vertex = QgsPoint(snapped_vertex.x(), snapped_vertex.y())
            self.vertex_marker.setCenter(self.snapped_vertex)
            self.vertex_marker.show()

        else:
            self.snapped_vertex = None
            self.after_vx_idx = None
            self.snapped_feat_id = None
            self.vertex_marker.hide()

        last_ix = self.rubber_band.numberOfVertices()

        self.rubber_band.movePoint(last_ix - 1,
                                   (self.snapped_vertex if self.snapped_vertex is not None else self.mouse_pt))

    def canvasReleaseEvent(self, event):

        # if not self.mouse_clicked:
        #     return
        if event.button() == Qt.LeftButton:

            # Update rubber bands
            self.rubber_band.addPoint((self.snapped_vertex if self.snapped_vertex is not None else self.mouse_pt), True)
            if self.first_click:
                self.rubber_band.addPoint((self.snapped_vertex if self.snapped_vertex is not None else self.mouse_pt), True)

            self.first_click = not self.first_click

            if self.snapped_vx_nr == -1 and self.snapped_feat_id is not None:
                snapped_feat = vutils.get_feats_by_id(self.layer, self.snapped_feat_id)
                if self.snapped_feat_id in self.feats_vx_idx_d:
                    self.feats_vx_idx_d[self.snapped_feat_id].append(self.snapped_vertex)
                else:
                    self.feats_vx_idx_d[self.snapped_feat_id] = [self.snapped_vertex]

        elif event.button() == Qt.RightButton:

            pipe_band_geom = self.rubber_band.asGeometry()
            rubberband_pts = pipe_band_geom.asPolyline()[:-1]
            rubberband_pts = self.remove_duplicated_point(rubberband_pts)

            if len(rubberband_pts) < 2:
                self.rubber_band.reset()
                return

            geom = QgsGeometry.fromPolyline(rubberband_pts)

            self.layer.beginEditCommand('Create new feature')

            # try:
            new_feat = QgsFeature(self.layer.fields())

            new_feat.setAttribute('gid', "nextval('trasporti.wk_strade_sentieri_gid_seq'::regclass)")

            new_feat.setAttribute('priorita', 'f')
            new_feat.setAttribute('galleria', 'f')
            new_feat.setAttribute('ponte', 'f')
            new_feat.setAttribute('costruzione', 'f')
            new_feat.setAttribute('ciclabile', 'f')

            for attribute, value in self.attributes_values_d.items():
                new_feat.setAttribute(attribute, value)

            new_feat.setGeometry(geom)

            sel_feats = self.layer.selectedFeatures()

            self.layer.addFeatures([new_feat])

            # Add vertices to snapped features
            if self.feats_vx_idx_d:
                for feat_id, vertices in self.feats_vx_idx_d.items():

                    feat = vutils.get_feats_by_id(self.layer, feat_id)[0]
                    new_line_geom = feat.geometry()
                    new_line_pts = feat.geometry().asPolyline()

                    for vertex in vertices:

                        # Add a point in new line geom and move point of intersecting line
                        pt, side, aft = new_line_geom.closestSegmentWithContext(vertex)
                        new_line_pts.insert(aft, vertex)
                        new_line_geom = QgsGeometry.fromPolyline(new_line_pts)

                    self.layer.changeGeometry(feat.id(), QgsGeometry.fromPolyline(new_line_pts))

            self.layer.endEditCommand()

            # Restore previously selected feature
            sel_feats_ids = []
            for sel_feat in sel_feats:
                sel_feats_ids.append(sel_feat.id())

            self.layer.setSelectedFeatures(sel_feats_ids)

            self.rubber_band.reset()

            self.feats_vx_idx_d.clear()

            # except Exception as e:
            #     self.rubber_band.reset()
            #     self.layer.destroyEditCommand()
            #     self.feats_vx_idx_d.clear()
            #     raise e

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.rubber_band.reset()

    def activate(self):

        # QgsProject.instance().setSnapSettingsForLayer(self.layer.id(),
        #                                               True,
        #                                               QgsSnapper.SnapToVertexAndSegment,
        #                                               QgsTolerance.Pixels,
        #                                               10,
        #                                               True)

        self.snapper = QgsSnapper(self.map_canvas.mapSettings())

        snap_layer = QgsSnapper.SnapLayer()
        snap_layer.mLayer = self.layer
        snap_layer.mSnapTo = QgsSnapper.SnapToVertexAndSegment
        snap_layer.mUnitTupe = QgsTolerance.Pixels

        (a, b, c, d, tolerance, f) = QgsProject.instance().snapSettingsForLayer(self.layer.id())
        snap_layer.mTolerance = tolerance

        self.snapper.setSnapLayers([snap_layer])
        self.snapper.setSnapMode(QgsSnapper.SnapWithOneResult)

    def remove_duplicated_point(self, pts):

        # This is needed because the rubber band sometimes returns duplicated points

        purged_pts = [pts[0]]
        for p in enumerate(list(range(len(pts) - 1)), 1):
            if pts[p[0]] == pts[p[0]-1]:
                continue
            else:
                purged_pts.append(pts[p[0]])

        return purged_pts


class MapToolsUtils(object):
    def __init__(self):
        pass

    @staticmethod
    def find_clicked_feats(iface, mouse_pt, layer, feats_count=1):

        if type(layer) is not QgsVectorLayer:
            return

        width = iface.mapCanvas().mapUnitsPerPixel() * 4
        rect = QgsRectangle(mouse_pt.x() - width,
                            mouse_pt.y() - width,
                            mouse_pt.x() + width,
                            mouse_pt.y() + width)

        request = QgsFeatureRequest(rect)
        feats = layer.getFeatures(request)

        dists_d = {}
        for feat in feats:
             dists_d[feat] = feat.geometry().distance(QgsGeometry.fromPoint(mouse_pt))
             dist = feat.geometry().distance(QgsGeometry.fromPoint(mouse_pt))
             if dist > width / 2:
                 continue
             dists_d[feat] = dist

        sorted_dists = sorted(list(dists_d.items()), key=operator.itemgetter(1))
        closest_ft = sorted_dists[0][0:feats_count]
        return closest_ft
