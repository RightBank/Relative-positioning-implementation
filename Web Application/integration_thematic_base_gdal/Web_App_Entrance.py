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
Created on Nov 18, 2016

@author: Weiming.Huang
"""


from Key_Procedures import *


def Get_Geojson_Generated_Feature(g, scale, CRS):

    geomcol = ogr.Geometry(ogr.wkbGeometryCollection)

    thematic_features = LookingUpAllThematicFeature(g)

    for thematic_feature in thematic_features:

        segment_collection_without_hosting_geometry = GetSegmentInfoCollection(g, thematic_feature)

        segment_info_collection = GetHostingFeatureGeom(g, segment_collection_without_hosting_geometry, scale)

        segment_info_collection_with_arcs_for_regeneration = GetArcsOfGeneratedFeature(segment_info_collection)

        pruned_segments = EliminatingIntersections(segment_info_collection_with_arcs_for_regeneration)

        reprojected_geometry = AssemblyAndCRSTransformation(pruned_segments, CRS)

        geomcol.AddGeometry(reprojected_geometry)

    geojson = ExporttoJson(geomcol)

    return geojson