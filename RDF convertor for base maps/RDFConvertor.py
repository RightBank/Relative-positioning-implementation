# Copyright (C) 2017 Weiming Huang
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
Created on May 1, 2017

@author: Weiming.Huang
"""
from osgeo import ogr
import os
from rdflib import Namespace, Graph, Literal, URIRef, RDF

# handle cadastral data first

cadastral_data_path = '' # path of cadastral data

driver = ogr.GetDriverByName("ESRI Shapefile")
cadastral_dataSource = driver.Open(cadastral_data_path, 0)
cadastral_layer = cadastral_dataSource.GetLayer()

CRS = u'<http://www.opengis.net/def/crs/EPSG/0/3006>'

# create a new linked data graph
g = Graph()

geo = Namespace(u'http://www.opengis.net/ont/geosparql#')
g.bind('geosparql', geo)
geo_sf = Namespace(u'http://www.opengis.net/ont/sf#')
g.bind('geo_sf', geo_sf)
base_map_ontology = Namespace(u'http://www.semanticweb.org/weiming.huang/ontologies/2016/11/base_map#')
g.bind('base_map_ontology', base_map_ontology)
base_namespace = Namespace(u'http://semanticweb.org/weiming.huang/ontologies/2016/11/base_map_data#')
g.bind('', base_namespace)
for feature in cadastral_layer:
    if feature.GetField("URI") is not None:
        g.add((URIRef(feature.GetField("URI")), RDF.type, base_map_ontology.Background_Feature))
        g.add((URIRef(feature.GetField("URI")), base_map_ontology.featureTheme, Literal('cadastre')))
        geometry_of_this_feature = URIRef(feature.GetField("URI") + '_geom')
        g.add((geometry_of_this_feature, RDF.type, geo_sf.LineString))
        g.add((URIRef(feature.GetField("URI")), geo.defaultGeometry, geometry_of_this_feature))
        g.add((geometry_of_this_feature, geo.asWKT, Literal(CRS + '\n' +
                                                            feature.GetGeometryRef().ExportToWkt(),
                                                            datatype=geo.wktLiteral)))

# looking up all the MRDB data apart from cadastral data

MRDB = dict()
MRDB['10k'] = []; MRDB['50k'] = []; MRDB['100k'] = []; MRDB['250k'] = []

for root, dirs, files in os.walk(r""): # Here walk in the repository of shapefiles

    for file in files:
        if (file.endswith('.shp')) and (file != 'al_get.shp'):
            shapeFilePath = os.path.join(root, file)
            dataSource = ogr.Open(shapeFilePath)
            daLayer = dataSource.GetLayer(0)
            layerDefinition = daLayer.GetLayerDefn()
            for i in range(layerDefinition.GetFieldCount()):
                if layerDefinition.GetFieldDefn(i).GetName() == 'URI':

                    MRDB[root.split('\\')[7]].append(shapeFilePath)
print MRDB

# for each scale
for key, value in MRDB.iteritems():

    # another dir where keys are URIs and values are lists of geometries
    URI_geometry = {}
    for layer in value:
        driver = ogr.GetDriverByName("ESRI Shapefile")
        topographic_dataset = driver.Open(layer, 0)
        topographic_layer = topographic_dataset.GetLayer()

        geometry_peoperty = 'geometry_' + key

        for feature in topographic_layer:
            URI = feature.GetField('URI')
            if URI is not None:

                if URI not in URI_geometry.keys():
                    URI_geometry[URI] = [feature]
                else:
                    URI_geometry[URI].append(feature)

    # for each feature (with the same URI) in one single scale
    for key1, value1 in URI_geometry.iteritems():
        geometry_of_topographic_feature = URIRef(key1 + '_geom' + key)
       
        g.add((URIRef(key1), RDF.type, base_map_ontology.Background_Feature))
        g.add((URIRef(key1), URIRef(str(base_map_ontology) + geometry_peoperty),
               geometry_of_topographic_feature))

        if len(value1) == 1:
            if value1[0].GetGeometryRef().GetGeometryName() == 'POLYGON':
                g.add((geometry_of_topographic_feature, RDF.type, geo_sf.Polygon))
            elif value1[0].GetGeometryRef().GetGeometryName() == 'LINESTRING':
                g.add((geometry_of_topographic_feature, RDF.type, geo_sf.LineString))
            g.add((geometry_of_topographic_feature, geo.asWKT, Literal(CRS + '\n' +
                                                                value1[0].GetGeometryRef().ExportToWkt(),
                                                                datatype=geo.wktLiteral)))
        else:
            geomcol = ogr.Geometry(ogr.wkbGeometryCollection)
            # value1 = sorted(value1, key=lambda sub_fea: sub_fea.GetField('SegOrd'))
            value1.sort(key=lambda sub_fea: sub_fea.GetField('SegOrd'))
            for sub_feature in value1:
                print sub_feature.GetField('SegOrd')
                geomcol.AddGeometry(sub_feature.GetGeometryRef())

            g.add((geometry_of_topographic_feature, RDF.type, geo_sf.GeometryCollection))
            g.add((geometry_of_topographic_feature, geo.asWKT, Literal(CRS + '\n' +
                                                                       geomcol.ExportToWkt(),
                                                                       datatype=geo.wktLiteral)))


# Export RDF to Turtle file
for s, p, o in g:
    print s, p, o
g.serialize(r'',
            format='turtle',
            base=base_namespace) #Here is the path of storing the generated RDF
