from qgis.core import QgsVectorLayer, QgsVectorFileWriter, Qgis, QgsSingleSymbolRenderer, QgsSymbol, \
    QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer, QgsRendererCategory, QgsCategorizedSymbolRenderer, \
    QgsLineSymbol, QgsRectangle, QgsFeatureRequest, QgsPoint, QgsGeometry

__author__ = 'deluca'


def load_shp_to_layer(shp_path, layer_name='xxx'):

    vlayer = QgsVectorLayer(shp_path, layer_name, "ogr")

    if not vlayer.isValid():
        raise NameError("Error opening Shapefile: ", shp_path)

    return vlayer


def save_layer2shapefile(vlayer, shp_path):
    """
    :type vlayer: QgsVectorLayer
    :type shp_path: String
    :type wkb_type: QGis.WkbType
    :return:
    """

    error = QgsVectorFileWriter.writeAsVectorFormat(vlayer, shp_path, "CP1250", vlayer.crs(), "ESRI Shapefile")
    return error


def find_closest_feature(vlayer, map_coord, tolerance_units):

    search_rect = QgsRectangle(map_coord.x() - tolerance_units,
                               map_coord.y() - tolerance_units,
                               map_coord.x() + tolerance_units,
                               map_coord.y() + tolerance_units)
    request = QgsFeatureRequest()
    request.setFilterRect(search_rect)
    request.setFlags(QgsFeatureRequest.ExactIntersect)
    for feature in vlayer.getFeatures(request):
        return feature


def find_closest_vertex_on_geometry(coord, geom):
    """
    :param coord:
    :type coord: QgsPoint
    :param geom:
    :type geom: QgsGeometry
    :return:
    """

    return geom.closestSegmentWithContext(coord)[1]


def get_feats_by_id(vlay, ft_id):
    request = QgsFeatureRequest().setFilterFid(ft_id)
    feats = list(vlay.getFeatures(request))
    return feats
