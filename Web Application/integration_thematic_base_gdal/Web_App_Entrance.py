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


from integration_thematic_base_gdal.Key_Steps import *
from Static_Vars import *


def Get_Geojson_Regenerated_Feature(scale, CRS):

    geomcol = ogr.Geometry(ogr.wkbGeometryCollection)

    thematic_features = LookingUpAllThematicFeature(endpoint_stardog, username_stardog, password_stardog)

    for thematic_feature in thematic_features:

        segment_collection_without_hosting_geometry = GetSegmentInfoCollection(endpoint_stardog, thematic_feature,
                                                                               username_stardog, password_stardog)

        segment_info_collection = GetHostingFeatureGeom(endpoint_stardog, segment_collection_without_hosting_geometry,
                                                        scale,
                                                        username_stardog, password_stardog)

        segment_info_collection_with_arcs_for_regeneration = GetArcsofRegeneratedFeature(segment_info_collection)

        pruned_segments = EliminatingIntersections(segment_info_collection_with_arcs_for_regeneration)

        reprojected_geometry = AssemblyAndCRSTransformation(pruned_segments, CRS)

        geomcol.AddGeometry(reprojected_geometry)
    geojson = ExporttoJson(geomcol)

    return geojson