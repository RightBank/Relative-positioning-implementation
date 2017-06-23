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
class Point(object):
    """A simple class for store the X and Y coordinates for a 2D point"""
    def __init__(self, X, Y):
        self.__X = X
        self.__Y = Y

    @property
    def X (self):
        return self.__X

    @property
    def Y (self):
        return self.__Y

    @X.setter
    def X (self, value):
        self.__X = value

    @Y.setter
    def Y(self, value):
        self.__Y = value

    def __getitem__(self, item):
        if item == 0:
            return self.__X
        elif item == 1:
            return self.__Y

class ClosestPoint(object):
    """Class for closest points."""
    def __init__(self, point=[], pointIndex='', nearestDistance='', originalPoint = []):
        self. __point = point
        self. __index = pointIndex
        self. __distance = nearestDistance
        self. __originPoint = originalPoint

    @property
    def X(self):
        if self.__point is not []:
            return self.__point[0]
        else:
            raise NotImplementedError

    @property
    def Y(self):
        if self.__point is not []:
            return self.__point[1]
        else:
            raise NotImplementedError

    @property
    def index(self):
        return self.__index

    @property
    def distance(self):
        return self. __distance

    @property
    def originalPoint (self):
        try:
            return self.__originPoint
        except:
            raise NotImplementedError

    @X.setter
    def X(self, value):
        self.__point[0] = value

    @Y.setter
    def Y(self, value):
        self.__point[1] = value

    @index.setter
    def index(self, value):
        self.__index = value

    @distance.setter
    def distance(self,value):
        self.__distance=value

    @originalPoint.setter
    def originalPoint(self,value):
        self.__originPoint = value

    def PointObject(self): return Point(self.X, self.Y)

    def PointinLst(self): return [self.X, self.Y]


class IndependentComponent(object):
    """for the instances of independent components"""
    def __init__(self, component_order='', component_URI='', geom='',
                 inner_ring_no=None):
        self.component_order = component_order
        self.component_URI = component_URI
        self.geom = geom
        self.inner_ring_no = inner_ring_no

    def __str__(self):
        return 'info about segment %s' % self.segment_order


class MatchedComponent(object):
    """for the instances of matched components"""
    def __init__(self, component_order='', component_URI='', hosting_feature_URI='',
                 hosting_feature_theme='', hosting_feature_geometry='',
                 vertex_order=None, starts_at='', ends_at='',
                 inner_ring_no=None):
        self.component_order = component_order
        self.component_URI = component_URI
        self.hosting_feature_URI = hosting_feature_URI
        self.hosting_feature_theme = hosting_feature_theme
        self.hosting_feature_geometry = hosting_feature_geometry
        self.vertex_order = vertex_order
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.cut_hosting_geometry = []
        self.inner_ring_no = inner_ring_no

    def __str__(self):
        return 'info about segment %s' % self.segment_order


