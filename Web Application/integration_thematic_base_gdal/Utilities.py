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
Created on Sep 22, 2016

@author: Weiming Huang

This module includes some necessary functionality for the sub - topic 1 implementation's work
"""

import numpy
from osgeo import ogr
import os
import rdflib
from Static_Vars import *
from Geometry_Classes import *


def Coefficient(x1, y1, x2, y2):
    """Returning the coefficients of the line that goes through two specific points"""
    k = (y2-y1)/(x2-x1)
    b = ((x2*y1)-(x1*y2))/(x2-x1)
    return k, -1, b


def FootOfPerpendicular(A, B, C, x0, y0):
    """Returning the foot of perpendicular from (x0,y0) to AX+BY+C=0"""
    x = (B*B*x0-A*B*y0-A*C)/(A*A+B*B)
    y = (-1*A*B*x0+A*A*y0-B*C)/(A*A+B*B)
    return x, y


def VerticalDistance(A,B,C,x0,y0):
    """Retruning the vertical distance from (x0,y0) to AX+BY+C=0"""
    D=numpy.abs((A*x0+B*y0+C)/numpy.sqrt(numpy.square(A)+numpy.square(B)))
    return D


def DistanceBetweenPoints(x1,y1,x2,y2):
    """Returning the distance between two points"""
    return numpy.sqrt(numpy.square(x1-x2)+numpy.square(y1-y2))


def RemoveCRS (WKT_string):
    """A small function that retrieves the WKT from 'asWKT'
    relationship which includes both CRS and coordinates"""
    return str(WKT_string).split('\n')[1]


def PointOnLineSegment (point, vertex1, vertex2):
    """The function judges if the foot of perpendicular is situated on a line segment, for general purpose, it could
    return if a point is located on a line segment"""
    xp = point.X
    yp = point.Y
    xv1 = vertex1.X
    yv1 = vertex1.Y
    xv2 = vertex2.X
    yv2 = vertex2.Y

    return (xp <= max([xv1, xv2])) and (xp >= min([xv1, xv2])) and \
           (yp >= min([yv1, yv2])) and (yp <= max([yv1, yv2]))


def RemovePrefixofURI(URI):
    """Get the id in the URI without prefix"""
    return URI.split('#')[1]


def GetGeomLonelyPart(graph, lonely_part_URI):
    """Get the geometry of a part which doesn't have any counterpart on the base maps."""
    geom = graph.query('''
            SELECT ?wkt
                WHERE
                { <%s> geosparql:defaultGeometry ?geom.
                 ?geom geosparql:asWKT ?wkt
                }
        ''' % lonely_part_URI
                       )
    for row in geom:
        lonely_part_wkt = str(row.wkt)
    return ogr.CreateGeometryFromWkt(lonely_part_wkt)


def GeometryforBackgroundFeature (graph, background_feature_uri, vertex_order, scale_URI):
    """This function returns, in a graph, the geometry of the feature which hosts a certain part of the geometry
        NOTE! the scale argument here should be in the format of predict in SPARQL query language"""

    geom = graph.query('''
        SELECT ?wkt
            WHERE
            { <%s> %s ?geom.
             ?geom geosparql:asWKT ?wkt
            }
    ''' % (background_feature_uri, scale_URI)
    )
    try:
        backg_geom = ogr.CreateGeometryFromWkt(RemoveCRS(str(geom.bindings[0]['wkt'])))
    except IndexError:
        return None
    geom_type = backg_geom.GetGeometryName()
    # If the feature in this scale is multi-parts
    if geom_type == 'GEOMETRYCOLLECTION':
        geom_lst = []
        for row in backg_geom:

            geom_lst.append(row)

        return CombineSegmentsforABackgFeature(geom_lst, vertex_order)
    # If this feature in this scale only has one part
    else:
        try:
            return ogr.CreateGeometryFromWkt(RemoveCRS(str(geom.bindings[0]['wkt'])))
        except:
            raise ValueError('invalid WKT')


def GetClosestPointofGeomtoPoint (point, geometry):
    """The function returns a 'closest point' object that contains the info about the point on a polygon/line which is
    the nearest to a specific point"""
    dis = 0
    index = 0
    temp_i = 0
    for pnt in geometry.GetPoints():
        if temp_i == 0:
            dis = DistanceBetweenPoints(pnt[0], pnt[1], point[0], point[1])
            temp_point = Point(pnt[0], pnt[1])
        else:
            temp_dis = DistanceBetweenPoints(pnt[0], pnt[1], point[0], point[1])
            if temp_dis < dis:
                dis = temp_dis
                index = temp_i
                temp_point = Point(pnt[0], pnt[1])
        temp_i += 1
    closest_point = ClosestPoint(temp_point, index, dis, point)
    return closest_point


def CombineSegmentsforABackgFeature(part_geometry, vertex_order):
    """The function for combining several sub-segments into one polyline feature"""
    combined_line = ogr.Geometry(ogr.wkbLineString)
    for i in xrange(0, len(part_geometry)):
        if part_geometry[i].GetGeometryName() == 'LINESTRING':
            for pnt in part_geometry[i].GetPoints():
                combined_line. AddPoint_2D(*pnt)
        if part_geometry[i].GetGeometryName() == 'POLYGON':
            if (i > 0) & (i < len(part_geometry)-1):

                for j in xrange(0, part_geometry[i].GetGeometryCount()):
                    # Note! If it's the interior rings composing
                    # parts of background feature, then it hasn't been supported

                    # last means the last point of previous line, fiest means the first point of next line
                    lastX = part_geometry[i - 1].GetPoint_2D(part_geometry[i - 1].GetPointCount() - 1)[0]
                    lastY = part_geometry[i - 1].GetPoint_2D(part_geometry[i - 1].GetPointCount() - 1)[1]
                    firstX = part_geometry[i + 1].GetPoint_2D(0)[0]
                    firstY = part_geometry[i + 1].GetPoint_2D(0)[1]

                    ring_geom = part_geometry[i].GetGeometryRef(j)
                    # Get the closest points to the two lines
                    closest_pre = GetClosestPointofGeomtoPoint([lastX, lastY], ring_geom)
                    closest_aft = GetClosestPointofGeomtoPoint([firstX, firstY], ring_geom)
                    # assemble the geometry according to the closest points
                    if vertex_order == 'Inverse':

                        if closest_pre.index < closest_aft.index:
                            for k in xrange(closest_pre.index, closest_aft.index + 1):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))
                        else:
                            for k in xrange(closest_pre.index, ring_geom.GetPointCount()):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))
                            for k in xrange(0, closest_aft.index + 1):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))
                    else:
                        if closest_pre.index < closest_aft.index:
                            for k in xrange(closest_pre.index, -1, -1):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))
                            for k in xrange(ring_geom.GetPointCount() - 1, closest_aft.index - 1, -1):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))
                        else:
                            for k in xrange(closest_pre.index, closest_aft.index - 1, -1):
                                combined_line. AddPoint_2D(*ring_geom.GetPoint_2D(k))

            else:
                # If the first or last component of the multi-part
                # background feature is polygon, then it hasn't been supported.
                pass

    return combined_line
