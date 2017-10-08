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

@author: Weiming Huang

This module includes all the key procedures of the regeneration of thematic feature, apart from
some small functions that are in 'Utilities' module.
"""


from Utilities import *

import geojson
from Static_Vars import *
from osgeo import osr
import Test_Utilities

_CRS = ''


def GetSegmentInfoCollection(endpoint, feature_name, username=None, password=None):
    """Given a thematic feature, return the collection of segments info which contains the segments'
    URI, hosting feature URI, starts/endsAt, segment order, vertices order, but not the geometry."""
    matched_components_query_body = """SELECT ?FeatureSegment ?hostFeature ?startingPointWKT ?endingPointWKT ?verticesOrder ?order ?feature_theme
                           ?innerRingNo
            WHERE
            {   <%s> thematic_map:hasComponent ?FeatureSegment.
                ?FeatureSegment rdf:type thematic_map:Matched_Component.
                ?FeatureSegment thematic_map:isPartOf ?hostFeature.
                ?hostFeature base_map:featureTheme ?feature_theme.
                ?FeatureSegment thematic_map:startsAt ?startingPoint.
                ?startingPoint  geosparql:asWKT ?startingPointWKT.
                ?FeatureSegment thematic_map:endsAt ?endingPoint.
                ?endingPoint    geosparql:asWKT ?endingPointWKT.
                ?FeatureSegment thematic_map:componentOrder ?order.
                OPTIONAL{
                        ?FeatureSegment thematic_map:verticesOrder ?verticesOrder.                        
            }
                OPTIONAL{                        
                        ?FeatureSegment thematic_map:innerRingNo ?innerRingNo.
            }
            }
            """ % feature_name
    matched_components = SparqlQueryToTripleStore(endpoint=endpoint,
                                                  query_body=matched_components_query_body,
                                                  username=username,
                                                  password=password)

    independent_components_query_body = """
            SELECT ?FeatureSegment ?ComponentWKT ?order  ?innerRingNo
            WHERE
            {   <%s> thematic_map:hasComponent ?FeatureSegment.
                ?FeatureSegment rdf:type thematic_map:Independent_Component.
                ?FeatureSegment geosparql:defaultGeometry ?ComponentGeometry.
                ?ComponentGeometry geosparql:asWKT ?ComponentWKT.
                ?FeatureSegment thematic_map:componentOrder ?order.
                OPTIONAL{                          
                          ?FeatureSegment thematic_map:innerRingNo ?innerRingNo.
            }
            }

        """ % feature_name
    independent_components = SparqlQueryToTripleStore(endpoint=endpoint,
                                                  query_body=independent_components_query_body,
                                                  username=username,
                                                  password=password)
    crs_query_body = """
                    SELECT ?CRS
                    WHERE
                    {   <%s> thematic_map:CRS ?CRS.
                    }

                """ % feature_name
    crs_query = SparqlQueryToTripleStore(endpoint=endpoint,
                                        query_body=crs_query_body,
                                        username=username,
                                        password=password)
    global _CRS
    _CRS = str(crs_query.bindings[0][rdflib.term.Variable(u'CRS')])

    # Here start to create the list of segment info, but the geometries will be added later on
    segment_collection = []

    for row in matched_components:

        starting_point = ogr.CreateGeometryFromWkt(RemoveCRS(str(row.startingPointWKT)))
        ending_point = ogr.CreateGeometryFromWkt(RemoveCRS(str(row.endingPointWKT)))
        segment_info = MatchedComponent(component_order=int(row.order), component_URI=str(row.FeatureSegment)
                                      ,hosting_feature_URI=str(row.hostFeature),
                                        hosting_feature_theme=row.feature_theme,
                                      starts_at=starting_point, ends_at=ending_point)
        if row.verticesOrder:
            segment_info.vertice_order = str(row.verticesOrder)
        if row.innerRingNo is not None:
            # segment_info.is_inner_ring_of = str(row.outerRing)
            segment_info.inner_ring_no = int(row.innerRingNo)
        segment_collection.append(segment_info)
    for row in independent_components:
        # print RemoveCRS(str(row.ComponentWKT))
        component_geom = ogr.CreateGeometryFromWkt(RemoveCRS(str(row.ComponentWKT)))
        segment_info = IndependentComponent(
            component_order=int(row.order), component_URI=str(row.FeatureSegment),
            geom=component_geom
        )
        if row.innerRingNo is not None:
            # segment_info.is_inner_ring_of = str(row.outerRing)
            segment_info.inner_ring_no = int(row.innerRingNo)
        segment_collection.append(segment_info)
    segment_collection.sort(key=lambda seg: seg.component_order)
    return segment_collection


def GetHostingFeatureGeom(endpoint, segment_collection, current_scale,
                          username=None, password=None):

    """This function gets the segment info's collection without the hosting features' geometries,
    and this function adds the geometries' info to the collection"""
    # scale_index_road = None
    # scale_index_water = None
    # for key, value in scale_hierarchy_dict_road.iteritems():
    #     if current_scale in value:
    #         scale_index_road = scale_hierarchy.index(key)
    #         break
    # for key, value in scale_hierarchy_dict_river.iteritems():
    #     if current_scale in value:
    #         scale_index_river = scale_hierarchy.index(key)
    #         break
    # for key, value in scale_hierarchy_dict_lake.iteritems():
    #     if current_scale in value:
    #         scale_index_lake = scale_hierarchy.index(key)
    #         break
    # # scale_index = scale_hierarchy.index(current_scale)

    for segment_info in segment_collection:
        if type(segment_info) == MatchedComponent:
            feature_geom = GeometryforBackgroundFeature(endpoint, segment_info.hosting_feature_URI,
                                    segment_info.vertice_order, current_scale, username, password)
            if feature_geom is None:
                # if the scale range has already exceeded the max value of the scales in base
                # map data, then retrieve the geometry in the closest scale range
                feature_geom = GeometryforClosestScaleRange(endpoint, segment_info.hosting_feature_URI,
                                                            segment_info.vertice_order, current_scale, username,
                                                            password)

            segment_info.hosting_feature_geometry = feature_geom

    return segment_collection


def GetArcsofRegeneratedFeature(segment_collection):

    # looking up the closest vertice for starting points and
    # add the vertical foots and sometimes the closest points to replaced arc
    # in the next for loop, looking up the closest points on the geometries to the starting and ending points
    for segment_info in segment_collection:
        Arc = []
        if type(segment_info) == MatchedComponent:
            hosting_feature = segment_info.hosting_feature_geometry
            starting_point = segment_info.starts_at
            ending_point = segment_info.ends_at
            if hosting_feature.GetGeometryName() == 'POLYGON':
                if hosting_feature.GetGeometryCount() == 1:
                    hosting_geom = hosting_feature.GetGeometryRef(0)
                    closest_point_info_starting = GetClosestPointofGeomtoPoint([starting_point.GetX(),
                                                starting_point.GetY()], hosting_geom)
                    closest_point_info_ending = GetClosestPointofGeomtoPoint([ending_point.GetX(),
                                                ending_point.GetY()], hosting_geom)
                else:
                    temp_lst = []
                    for i in xrange(0, hosting_feature.GetGeometryCount()):
                        closest_point_info_starting_temp = GetClosestPointofGeomtoPoint([starting_point.GetX(),
                                                                    starting_point.GetY()], hosting_geom)
                        temp_lst.append(closest_point_info_starting_temp.distance)
                    closest_geom_index = temp_lst.index(min(temp_lst))
                    hosting_geom = hosting_feature.GetGeometryRef(closest_geom_index)
                    closest_point_info_starting = GetClosestPointofGeomtoPoint([starting_point.GetX(),
                                                                                starting_point.GetY()], hosting_geom)
                    closest_point_info_ending = GetClosestPointofGeomtoPoint([ending_point.GetX(),
                                                                              ending_point.GetY()], hosting_geom)
                    #raise NotImplementedError("if the polygon is multi-part, then it hasn't been implemented")
            elif hosting_feature.GetGeometryName() == 'LINESTRING':
                hosting_geom = hosting_feature
                closest_point_info_starting = GetClosestPointofGeomtoPoint([starting_point.GetX(),
                                                            starting_point.GetY()], hosting_geom)
                closest_point_info_ending = GetClosestPointofGeomtoPoint([ending_point.GetX(),
                                                            ending_point.GetY()], hosting_geom)
                if closest_point_info_starting.index > closest_point_info_ending.index:
                    segment_info.vertice_order = 'Inverse'
                elif closest_point_info_starting.index < closest_point_info_ending.index:
                    segment_info.vertice_order = 'Same'
                else:
                    start_vector_dot = numpy.dot([starting_point.GetX() - closest_point_info_starting.X,
                                                  starting_point.GetY() - closest_point_info_starting.Y],
                                                 [hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1)[0] - closest_point_info_starting.X,
                                                  hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1)[1] - closest_point_info_starting.Y])
                    end_vector_dot = numpy.dot([ending_point.GetX() - closest_point_info_ending.X,
                                                ending_point.GetY() - closest_point_info_ending.Y],
                                               [hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1)[0] - closest_point_info_starting.X,
                                                hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1)[1] - closest_point_info_starting.Y])
                    if start_vector_dot > end_vector_dot:
                        segment_info.vertice_order = 'Inverse'
                    else:
                        segment_info.vertice_order = 'Same'

            else:

                raise NotImplementedError('if the hosting feature is of other types, then it needs'\
                                           'to be implemented')

            if closest_point_info_starting.index in xrange(1, hosting_geom.GetPointCount() - 1):

                (A1, B1, C1) = Coefficient(closest_point_info_starting.X, closest_point_info_starting.Y,
                                           *hosting_geom.GetPoint_2D(closest_point_info_starting.index-1))
                (A2, B2, C2) = Coefficient(closest_point_info_starting.X, closest_point_info_starting.Y,
                                           *hosting_geom.GetPoint_2D(closest_point_info_starting.index+1))
                (xp1, yp1) = FootOfPerpendicular(A1, B1, C1, starting_point.GetX(), starting_point.GetY())
                p1 = Point(xp1, yp1)
                (xp2, yp2) = FootOfPerpendicular(A2, B2, C2, starting_point.GetX(), starting_point.GetY())

                if PointOnLineSegment(p1, closest_point_info_starting.PointObject(),
                                      Point(*hosting_geom.GetPoint_2D(closest_point_info_starting.index - 1))):
                    if segment_info.vertice_order == 'Inverse':
                        Arc.append([xp1, yp1])
                    else:
                        Arc.append([xp1, yp1])
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_starting.index)))
                else:
                    if segment_info.vertice_order == 'Inverse':
                        Arc.append([xp2, yp2])
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_starting.index)))
                    else:
                        Arc.append([xp2, yp2])
            # handle the problems that raised by the situations when the closest points are the first points
            elif hosting_feature.GetGeometryName() == 'LINESTRING':
                if closest_point_info_starting.index == 0:
                    (A2, B2, C2) = Coefficient(closest_point_info_starting.X, closest_point_info_starting.Y,
                                               *hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1))
                    (xp2, yp2) = FootOfPerpendicular(A2, B2, C2, starting_point.GetX(), starting_point.GetY())
                    p2 = Point(xp2, yp2)

                    if PointOnLineSegment(p2, closest_point_info_starting.PointObject(),
                                            Point(*hosting_geom.GetPoint_2D(closest_point_info_starting.index + 1))):
                        Arc.append([xp2, yp2])
                    else:
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_starting.index)))
                elif closest_point_info_starting.index == hosting_geom.GetPointCount() - 1:
                    (A1, B1, C1) = Coefficient(closest_point_info_starting.X, closest_point_info_starting.Y,
                                               *hosting_geom.GetPoint_2D(closest_point_info_starting.index - 1))
                    (xp1, yp1) = FootOfPerpendicular(A1, B1, C1, starting_point.GetX(), starting_point.GetY())
                    p1 = Point(xp1, yp1)
                    if PointOnLineSegment(p1, closest_point_info_starting.PointObject(),
                                          Point(*hosting_geom.GetPoint_2D(closest_point_info_starting.index - 1))):
                        Arc.append([xp1, yp1])
                    else:
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_starting.index)))
            elif hosting_feature.GetGeometryName() == 'POLYGON':
                raise NotImplementedError("if the geometry is polygon, it hasn't been implemented.")

            # start to add the middle points
            if segment_info.vertice_order == 'Inverse':
                if closest_point_info_starting.index > closest_point_info_ending.index:
                    i = closest_point_info_starting.index - 1
                    while i > closest_point_info_ending.index:
                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i -= 1
                elif closest_point_info_starting.index < closest_point_info_ending.index:

                    i = closest_point_info_starting.index - 1
                    while i >= 0:
                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i -= 1
                    i = hosting_geom.GetPointCount() - 1
                    while i > closest_point_info_ending.index:
                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i -= 1

            else:
                # This "if" is for whether the last vertice is reached
                if closest_point_info_starting.index < closest_point_info_ending.index:
                    i = closest_point_info_starting.index + 1
                    while i < closest_point_info_ending.index:

                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i += 1
                elif closest_point_info_starting.index > closest_point_info_ending.index:
                    i = closest_point_info_starting.index + 1
                    while i < hosting_geom.GetPointCount():
                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i += 1
                    i = 0
                    while i < closest_point_info_ending.index:
                        Arc.append(list(hosting_geom.GetPoint_2D(i)))
                        i += 1
            # Adding the last vertices in each arc

            if closest_point_info_ending.index in xrange(1, hosting_geom.GetPointCount() - 1):
                (A1, B1, C1) = Coefficient(closest_point_info_ending.X, closest_point_info_ending.Y,
                                           *hosting_geom.GetPoint_2D(closest_point_info_ending.index - 1))
                (A2, B2, C2) = Coefficient(closest_point_info_ending.X, closest_point_info_ending.Y,
                                           *hosting_geom.GetPoint_2D(closest_point_info_ending.index + 1))
                (xp1, yp1) = FootOfPerpendicular(A1, B1, C1, ending_point.GetX(), ending_point.GetY())
                p1 = Point(xp1, yp1)
                (xp2, yp2) = FootOfPerpendicular(A2, B2, C2, ending_point.GetX(), ending_point.GetY())
                # Judging if the foot is located on which segment (the two comprise closest point)
                if PointOnLineSegment(p1, closest_point_info_ending.PointObject(),
                                      Point(*hosting_geom.GetPoint_2D(closest_point_info_ending.index - 1))):
                    if segment_info.vertice_order == 'Inverse':
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_ending.index)))
                        Arc.append([xp1, yp1])
                    else:
                        Arc.append([xp1, yp1])
                else:
                    if segment_info.vertice_order == 'Inverse':
                        Arc.append([xp2, yp2])
                    else:
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_ending.index)))
                        Arc.append([xp2, yp2])
            elif hosting_feature.GetGeometryName() == 'LINESTRING':
                if closest_point_info_ending.index == 0:
                    (A2, B2, C2) = Coefficient(closest_point_info_ending.X, closest_point_info_ending.Y,
                                               *hosting_geom.GetPoint_2D(closest_point_info_ending.index + 1))
                    (xp2, yp2) = FootOfPerpendicular(A2, B2, C2, ending_point.GetX(), ending_point.GetY())
                    p2 = Point(xp2, yp2)
                    if PointOnLineSegment(p2, closest_point_info_ending.PointObject(),
                                          Point(*hosting_geom.GetPoint_2D(closest_point_info_ending.index + 1))):
                        Arc.append([xp2, yp2])

                    else:
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_ending.index)))
                elif closest_point_info_ending.index == hosting_geom.GetPointCount() - 1:
                    (A1, B1, C1) = Coefficient(closest_point_info_ending.X, closest_point_info_ending.Y,
                                               *hosting_geom.GetPoint_2D(closest_point_info_ending.index - 1))
                    (xp1, yp1) = FootOfPerpendicular(A1, B1, C1, ending_point.GetX(), ending_point.GetY())
                    p1 = Point(xp1, yp1)
                    if PointOnLineSegment(p1, closest_point_info_ending.PointObject(),
                                          Point(*hosting_geom.GetPoint_2D(closest_point_info_ending.index - 1))):
                        Arc.append([xp1, yp1])
                    else:
                        Arc.append(list(hosting_geom.GetPoint_2D(closest_point_info_ending.index)))
            elif hosting_feature.GetGeometryName() == 'POLYGON':
                raise NotImplementedError("if the geometry is polygon, it hasn't been implemented.")
            segment_info.cut_hosting_geometry = Arc
        elif type(segment_info) == IndependentComponent:
            for linestring in segment_info.geom:
                for point in linestring.GetPoints():
                    Arc.append(list(point))
            segment_info.cut_hosting_geometry = Arc
    # for the affine transformation of relative coordinates of independent components
    for segment_info in segment_collection:
        if type(segment_info) == IndependentComponent:
            index = segment_collection.index(segment_info)
            if index != len(segment_collection) - 1:
                scaling_ratio_numerator_X = segment_collection[index+1].cut_hosting_geometry[0][0] - \
                                        segment_collection[index-1].cut_hosting_geometry[-1][0]
                scaling_ratio_numerator_Y = segment_collection[index+1].cut_hosting_geometry[0][1] - \
                                        segment_collection[index-1].cut_hosting_geometry[-1][1]
                scaling_ratio_denominator_X = segment_info.cut_hosting_geometry[-1][0]
                scaling_ratio_denominator_Y = segment_info.cut_hosting_geometry[-1][1]
                scaling_ratio_X = scaling_ratio_numerator_X / scaling_ratio_denominator_X
                scaling_ratio_Y = scaling_ratio_numerator_Y / scaling_ratio_denominator_Y

                print scaling_ratio_X, scaling_ratio_Y
            elif segment_info.inner_ring_no is None:
                scaling_ratio_numerator_X = segment_collection[0].cut_hosting_geometry[0][0] - \
                                            segment_collection[index - 1].cut_hosting_geometry[-1][0]
                scaling_ratio_numerator_Y = segment_collection[0].cut_hosting_geometry[0][1] - \
                                            segment_collection[index - 1].cut_hosting_geometry[-1][1]
                scaling_ratio_denominator_X = segment_info.cut_hosting_geometry[-1][0]
                scaling_ratio_denominator_Y = segment_info.cut_hosting_geometry[-1][1]
                scaling_ratio_X = scaling_ratio_numerator_X / scaling_ratio_denominator_X
                scaling_ratio_Y = scaling_ratio_numerator_Y / scaling_ratio_denominator_Y

                print scaling_ratio_X, scaling_ratio_Y
            elif segment_info.inner_ring_no is not None:
                scaling_ratio_numerator_X = segment_collection[index - 1].cut_hosting_geometry[0][0] - \
                                            segment_collection[index - 1].cut_hosting_geometry[-1][0]
                scaling_ratio_numerator_Y = segment_collection[index - 1].cut_hosting_geometry[0][1] - \
                                            segment_collection[index - 1].cut_hosting_geometry[-1][1]
                scaling_ratio_denominator_X = segment_info.cut_hosting_geometry[-1][0]
                scaling_ratio_denominator_Y = segment_info.cut_hosting_geometry[-1][1]
                scaling_ratio_X = scaling_ratio_numerator_X / scaling_ratio_denominator_X
                scaling_ratio_Y = scaling_ratio_numerator_Y / scaling_ratio_denominator_Y
                scaling_ratio_X = 1
                scaling_ratio_Y = 1
            for vertex in segment_info.cut_hosting_geometry:
                vertex[0] = (vertex[0] * scaling_ratio_X) + segment_collection[index-1].cut_hosting_geometry[-1][0]
                vertex[1] = (vertex[1] * scaling_ratio_Y) + segment_collection[index-1].cut_hosting_geometry[-1][1]



    return segment_collection


def EliminatingIntersections (segment_info_collection):
    """ The function for eliminating intersections between the primitive arcs that consist the
    rebulit polygon geometry.
    """
    polylines = []
    for segment_info in segment_info_collection:
        line = ogr.Geometry(ogr.wkbLineString)

        for vertice in segment_info.cut_hosting_geometry:
            line.AddPoint_2D(*vertice)
        polylines.append(line)

    for i in xrange(1, len(polylines)):
        # j = 0
        #print polylines[i].disjoint(polylines[i-1])
        while (not polylines[i].Disjoint(polylines[i-1])) and (polylines[i].GetPointCount() > 3):
            '''test block
            print polylines[i].WKT
            print polylines[i-1].WKT
            # del arcs[i][j]'''
            line_new = ogr.Geometry(ogr.wkbLineString)
            for pnt_index in xrange(1, polylines[i].GetPointCount()):
                line_new.AddPoint_2D(*list(polylines[i].GetPoint_2D(pnt_index)))
            polylines[i] = line_new
            #j += 1

    arcs_return = []
    for i in xrange(0, len(polylines)):
        arc_new = []
        arcs_return.append([])
        for pnt in polylines[i].GetPoints():
            arc_new.append(list(pnt))

        segment_info_collection[i].cut_hosting_geometry = arc_new
    return segment_info_collection


def GetAttributes(graph, feature_name):
    """this function retrieves the attributes from the RDF"""
    att = graph.query(
        """SELECT ?attribute_name ?value
            WHERE
            {  :%s ?p ?value.
            ?p rdfs:subPropertyOf base_map:attribute.
            ?p skos:prefLabel ?attribute_name
            }
            """ % feature_name)
    att_dict = {}

    for row in att:
        att_dict[str(row.attribute_name)] = str(row.value)

    return att_dict


def AssemblyAndCRSTransformation(segment_info_collection, target_CRS):
    """Assembling in the features Converting the CRS (3006 to 4326 in this case), note that\
    for now it only supports polygon with no more than one inner ring."""
    has_inner_ring = False
    for segment_info in segment_info_collection:
        if segment_info.inner_ring_no is not None:
            has_inner_ring = True
            break
    ring = ogr.Geometry(ogr.wkbLinearRing)
    poly = ogr.Geometry(ogr.wkbPolygon)
    if has_inner_ring:
        ring_inner = ogr.Geometry(ogr.wkbLinearRing)
    for segment_info in segment_info_collection:
        if segment_info.inner_ring_no is None:
            for pnt in segment_info.cut_hosting_geometry:
                ring.AddPoint_2D(*pnt)

        else:

            for pnt in segment_info.cut_hosting_geometry:
                ring_inner.AddPoint_2D(*pnt)
            # ring_inner.AddPoint_2D(*ring_inner.GetPoint_2D(0))
    ring.AddPoint_2D(*ring.GetPoint_2D(0))
    poly.AddGeometry(ring)
    if has_inner_ring:
        ring_inner_reverse = ogr.Geometry(ogr.wkbLinearRing)
        i = ring_inner.GetPointCount() - 1
        while i >= 0:
            ring_inner_reverse.AddPoint_2D(*ring_inner.GetPoint_2D(i))
            i -= 1
        ring_inner_reverse.AddPoint_2D(*ring_inner_reverse.GetPoint_2D(0))
        poly.AddGeometry(ring_inner_reverse)
    global _CRS
    if target_CRS != int(_CRS[-4:]):

        source = osr.SpatialReference()

        source.ImportFromEPSG(int(_CRS[-4:]))
        target = osr.SpatialReference()
        target.ImportFromEPSG(target_CRS)

        transform = osr.CoordinateTransformation(source, target)
        poly.Transform(transform)

        return poly
    else:
        return poly


def ExporttoJson(geometry_collection):

    feature_lst = []

    for geometry in geometry_collection:

        json_geom = geojson.loads(geometry.ExportToJson())

        feature = geojson.Feature(geometry=json_geom)

        feature_lst.append(feature)
    feature_coll = geojson.FeatureCollection(feature_lst)

    validation = geojson.is_valid(feature_coll)

    if validation['valid'] is 'yes':
        # pprint(geojson.dumps(feature_json, sort_keys=False))
        return geojson.dumps(feature_coll, sort_keys=True)
    else:
        raise TypeError('This is not a valid geojson string.')


def LookingUpAllThematicFeature (endpoint, username = None, password = None):
    """given the RDF of thematic data, looking up all the thematic features contained in it"""
    query_body = """
            SELECT ?thematic_feature
                WHERE { ?thematic_feature rdf:type thematic_map:Thematic_Feature }
        """
    thematic_feature_query = SparqlQueryToTripleStore(query_body=query_body,
                             endpoint=endpoint, username=username,
                             password=password)

    thematic_features = []

    for row in thematic_feature_query:
        thematic_features.append(str(row.thematic_feature))
    return thematic_features

