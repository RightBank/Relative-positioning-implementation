# -*- coding: utf-8 -*-
# Copyright (C) 2017 Haiqi Xu and Ehsan Abdolmajidi
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
@author: Haiqi Xu and Ehsan Abdolmajidi
"""
import arcpy
import pythonaddins
import uuid
import os, rdflib
import sys

def relativeCoor(IndependentCoords): # Transform absolute coordinates to relative coordinates for line geometry.
    # Read planar coordinates for the first point in the line geometry.
    sp_X = IndependentCoords.getObject(0).X
    sp_Y = IndependentCoords.getObject(0).Y
    reCoords=[] # Save relative coordinates in the list
    for p in IndependentCoords:
        reCoords.append(((p.X-sp_X),(p.Y-sp_Y)))
    print reCoords
    return reCoords

def ReadGeometry(Backlayer): # Read coordinates of each ring in a selected polygon feature.
    Coords = []
    # Read geometries of selected feature.
    for row in arcpy.da.SearchCursor(Backlayer, ['OID@', 'SHAPE@']):  # feature
        for part in row[1]:  # part: row[1] = SHAPE@XY
            for pnt in part:  # ring
                if pnt:
                    Coords.append((pnt.X, pnt.Y))
                else:
                    Coords.append('Inf')
    # Detect point locates in exterior or interior ring.
    temp = [] # save coordinates of a ring.
    ind = 0 # save the index of rings.
    Ring = [] # save coordinates of all the rings.
    for i in range(len(Coords)):
        if Coords[i] != 'Inf':
            temp.append(Coords[i])
        else:
            Ring.insert(ind, temp)
            temp = []
            ind += 1
    Ring.insert(ind, temp)
    return Ring

def is_clockwise(vertices): # Detect a ring is clockwise or anticlockwise, requires coordinates of the ring.
    if len(vertices) < 3:
        return True
    area = 0.0
    ax, ay = vertices[0]
    for bx, by in vertices[1:]:
        area += ax * by - ay * bx
        ax, ay = bx, by
    bx, by = vertices[0]
    area += ax * by - ay * bx
    return area < 0.0

def delete_Point(Pointpath, PointCoords): # Delete a point feature on the map, requires the Point layer and coordinates
    edit = arcpy.da.Editor(Pointpath) # Start an edit session. Require the workspace.
    edit.startEditing(True) # Edit session is started without an undo/redo stack for versioned data.
    edit.startOperation() # Start an edit operation.
    with arcpy.da.UpdateCursor('Point', 'SHAPE@XY') as cursor:
        for row in cursor:
            if (abs(row[0][0] - PointCoords[0]) < 0.1) and (abs(row[0][1] - PointCoords[1]) < 0.1):
                cursor.deleteRow()
    del cursor
    edit.stopOperation() # Stop the edit operation.
    edit.stopEditing(True) # Stop the edit session and save the changes.
    arcpy.RefreshActiveView() # Refreshes the active view and table of contents of the current map document.

def delete_Line(Linepath, numFea, numSeg): # Delete a line feature on the map, requires the Line layer and deleteID(=numFea+numSeg).
    edit = arcpy.da.Editor(Linepath)
    edit.startEditing(True)
    edit.startOperation()
    with arcpy.da.UpdateCursor('Line', ['SHAPE@XY', 'DeleteID']) as cursor:
        for row in cursor:
            if row[1] == str(numFea) + str(numSeg):
                cursor.deleteRow()
    del cursor
    edit.stopOperation()
    edit.stopEditing(True)
    arcpy.RefreshActiveView()

class GenInfo: # Declare all the public variables.
    mxd = arcpy.mapping.MapDocument('current')
    list = []
    allLayersFeatures = []
    selectedFeature = None
    spatialReference = None

    for lyr in arcpy.mapping.ListLayers(mxd):  # load all the layers.
        list.append(lyr.name)

        if (lyr.visible) and lyr.name != 'Point' and lyr.name != 'Line' and lyr.name != 'Polygon':
            try:
                for sublyr in lyr:
                    if (sublyr.visible):
                        with arcpy.da.SearchCursor(sublyr, ["SHAPE@", ]) as lyrFeatures:
                            for feature in lyrFeatures:
                                allLayersFeatures.append(feature[0])
                        del lyrFeatures
            except:
                pass

    workpath = '' # save the working directory.
    selectLayer = '' # save the name of selected layer
    ClearSelection = ''
    # Component information
    n = 0  # Segment order
    SelDict = {'BaseURI': 'Inf', 'StartP': 'Inf', 'EndP': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}  # RDF dictionary for selected feature.
    LineDict = {'LineGeometry': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}  # RDF dictionary for created line.

    Feature = {'URI': 'Inf', 'Segments': []}  # Save each feature.
    AllFeature = []  # Save all the features.

    numFea = 0  # For deleting Line, is a part of value of the field-'DeleteID' in 'Line'.

    # Inner ring variable
    startRing = 0
    m = 0 # Inner ring order
    ExteriorSeg = 0
    NextRing = 0

class AllFeature(object): # Print all the created feature.
    """Implementation for Digitool_addin.Allfeature (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        print GenInfo.AllFeature #Print all the created features

class Anticlockwise(object): # Detect the vertices direction of thematic component.
    """Implementation for Digitool_addin.Anticlockwise (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        if arcpy.Describe(GenInfo.selectLayer).shapeType == 'Polygon':
            Ring = ReadGeometry(GenInfo.selectLayer)
            # Find which ring is closest to start point
            dis = []  # save distance from Point to Line
            for r in Ring:
                a = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in r]))
                dis.append(a.distanceTo(arcpy.Point(GenInfo.SelDict['StartP'][0], GenInfo.SelDict['StartP'][1])))
            loc = dis.index(min(dis))
            ## Detect vertices direction of the closest ring and Assign the value for Vertices Direction.
            if is_clockwise(Ring[loc]):
                GenInfo.SelDict['VDirection'] = 'Inverse'
            else:
                GenInfo.SelDict['VDirection'] = 'Same'

            # Assign the Segment order for the thematic component.
            GenInfo.SelDict['SegOrder'] = GenInfo.n
            GenInfo.n += 1

            print GenInfo.SelDict

            GenInfo.Feature['Segments'].append(GenInfo.SelDict)
            GenInfo.SelDict = {'BaseURI': 'Inf', 'StartP': 'Inf', 'EndP': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}

class Clockwise(object): # Detect the vertices direction of thematic component.
    """Implementation for Digitool_addin.Clockwise (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        if arcpy.Describe(GenInfo.selectLayer).shapeType == 'Polygon':
            Ring = ReadGeometry(GenInfo.selectLayer)
            dis = []  # save distance from Point to Line
            for r in Ring:
                a = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in r]))
                dis.append(a.distanceTo(arcpy.Point(GenInfo.SelDict['StartP'][0], GenInfo.SelDict['StartP'][1])))
            loc = dis.index(min(dis))

            # Detect vertices direction of the closest ring and Assign the value for Vertices Direction.
            if is_clockwise(Ring[loc]):
                GenInfo.SelDict['VDirection'] = 'Same'
            else:
                GenInfo.SelDict['VDirection'] = 'Inverse'

            # Assign the Segment order for the thematic component.
            GenInfo.SelDict['SegOrder'] = GenInfo.n
            GenInfo.n += 1

            print GenInfo.SelDict

            GenInfo.Feature['Segments'].append(GenInfo.SelDict)
            GenInfo.SelDict = {'BaseURI': 'Inf', 'StartP': 'Inf', 'EndP': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}

class DeleteSegment(object): # Delete the latest thematic component user created.
    """Implementation for Digitool_addin.DeleteSegment (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        if GenInfo.SelDict['BaseURI'] != 'Inf':  # delete current component during creating process.
            if GenInfo.SelDict['StartP'] != 'Inf':
                Pointpath = GenInfo.workpath + '\TestTD.gdb'
                PointCoords = GenInfo.SelDict['StartP']
                delete_Point(Pointpath, PointCoords)
            if GenInfo.SelDict['EndP'] != 'Inf':
                Pointpath = GenInfo.workpath + '\TestTD.gdb'
                PointCoords = GenInfo.SelDict['EndP']
                delete_Point(Pointpath, PointCoords)
            GenInfo.SelDict = {'BaseURI': 'Inf', 'StartP': 'Inf', 'EndP': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}
            if GenInfo.ClearSelection:
                arcpy.SelectLayerByAttribute_management(GenInfo.ClearSelection, "CLEAR_SELECTION")  # Clear selection
        else: # when the component is done.
            lastItem = GenInfo.Feature['Segments'][len(GenInfo.Feature['Segments']) - 1]
            if len(lastItem) == 5 or len(lastItem) == 6 or len(lastItem) == 7:  # delete when segment is done
                Pointpath = GenInfo.workpath + '\TestTD.gdb'
                PointCoords = lastItem['StartP']
                delete_Point(Pointpath, PointCoords)

                PointCoords1 = lastItem['EndP']
                delete_Point(Pointpath, PointCoords1)

                if GenInfo.ClearSelection:
                    arcpy.SelectLayerByAttribute_management(GenInfo.ClearSelection, "CLEAR_SELECTION")  # Clear selection

            if len(lastItem) == 3 or len(lastItem) == 4:  # delete line segment
                Linepath = GenInfo.workpath + '\TestTD.gdb'
                delete_Line(Linepath, GenInfo.numFea, GenInfo.n - 1)

            GenInfo.n -= 1
            del GenInfo.Feature['Segments'][len(GenInfo.Feature['Segments']) - 1]
            print GenInfo.Feature

class DeteleFeature(object): # Delete the latest feature user created.
    """Implementation for Digitool_addin.DeteleFeature (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        # Haven't finished the current feature,e.g.you are drawing the third component then found the first one is wrong.
        if GenInfo.Feature['Segments'] != []:
            for item in GenInfo.Feature['Segments']:
                if len(item) == 5 or len(item) == 6:
                    Pointpath = GenInfo.workpath + '\TestTD.gdb'
                    PointCoords = item['StartP']
                    delete_Point(Pointpath, PointCoords)
                    PointCoords1 = item['EndP']
                    delete_Point(Pointpath, PointCoords1)

                if len(item) == 3 or len(item) == 4:
                    Linepath = GenInfo.workpath + '\TestTD.gdb'
                    delete_Line(Linepath, GenInfo.numFea, item['SegOrder'])

            GenInfo.Feature = {'URI': 'Inf', 'Segments': []}
        # Finish the current feature.
        else:
            lastFeat = GenInfo.AllFeature[len(GenInfo.AllFeature) - 1]
            for item in lastFeat['Segments']:
                if len(item) == 5 or len(item) == 6 or len(item) == 7:
                    Pointpath = GenInfo.workpath + '\TestTD.gdb'
                    PointCoords = item['StartP']
                    delete_Point(Pointpath, PointCoords)
                    PointCoords1 = item['EndP']
                    delete_Point(Pointpath, PointCoords1)

                if len(item) == 3 or len(item) == 4:
                    Linepath = GenInfo.workpath + '\TestTD.gdb'
                    delete_Line(Linepath, GenInfo.numFea - 1, item['SegOrder'])

            GenInfo.numFea -= 1
            del GenInfo.AllFeature[len(GenInfo.AllFeature) - 1]
            print GenInfo.AllFeature

        if GenInfo.ClearSelection:
            arcpy.SelectLayerByAttribute_management(GenInfo.ClearSelection, "CLEAR_SELECTION")  # Clear selection

class EPoint(object): # Draw an end point, save the coordinates, and show it on the map.
    """Implementation for Digitool_addin.EPoint (Tool)"""
    def __init__(self):
        self.enabled = True
        self.cursor = 3
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDownMap(self, x, y, button, shift):
        epNew = None
        ep = arcpy.Point(x, y)
        numberOfSegments = len(GenInfo.Feature['Segments'])
        snappedToExistingFeature = False
        '''Perform the snap functionality & Save coordinates in RDF dictionary'''
        if numberOfSegments <> 0:
            for featureInfo in GenInfo.Feature['Segments']:
                try:
                    startPoint = arcpy.PointGeometry(arcpy.Point(featureInfo['StartP'][0], featureInfo['StartP'][1]))
                except:
                    startPoint = arcpy.PointGeometry(featureInfo['LineGeometry'].firstPoint)

                distanceEP = startPoint.distanceTo(ep)
                if 0 < distanceEP < 5:
                    epNew = startPoint.getPart(0)
                    snappedToExistingFeature = True

        if snappedToExistingFeature == False:
            if arcpy.Describe(GenInfo.selectLayer).shapeType == 'Polygon':
                ring = ReadGeometry(GenInfo.selectLayer)
                dis = []
                for r in ring:
                    a = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in r]))
                    dis.append(a.distanceTo(arcpy.Point(ep.X, ep.Y)))
                loc = dis.index(min(dis))
                polygonToPolyline = arcpy.Polyline(arcpy.Array([arcpy.Point(*coord) for coord in ring[loc]]))
                epNew = polygonToPolyline.snapToLine(ep).getPart()
            else:
                epNew = GenInfo.selectedFeature.snapToLine(ep).getPart()

        '''Visualize the point'''
        fc = 'Point'
        path = GenInfo.workpath + '\TestTD.gdb'
        # Start an edit session. Require the workspace
        edit = arcpy.da.Editor(path)
        # Edit session is started without an undo/redo stack for versioned data
        # (for second argument, use False for unversioned data)
        edit.startEditing(True)
        # Start an edit operation
        edit.startOperation()

        if epNew is not None:
            GenInfo.SelDict['EndP'] = (epNew.X, epNew.Y)
            rowValue = [(epNew.X, epNew.Y)]
        else:
            GenInfo.SelDict['EndP'] = (ep.X, ep.Y)
            rowValue = [(ep.X, ep.Y)]
        cursor = arcpy.da.InsertCursor(fc, 'SHAPE@XY')
        cursor.insertRow(rowValue)

        # Stop the edit operation.
        edit.stopOperation()
        # Stop the edit session and save the changes
        edit.stopEditing(True)
        arcpy.RefreshActiveView()

        if GenInfo.startRing == 1:
            GenInfo.SelDict['InnerRingNum'] = GenInfo.m

        '''Assign the component order for the matched thematic component when the selected feature is a polyline'''
        if arcpy.Describe(GenInfo.selectLayer).shapeType == 'Polyline':
            GenInfo.SelDict['SegOrder'] = GenInfo.n
            print GenInfo.SelDict
            GenInfo.n += 1
            GenInfo.Feature['Segments'].append(GenInfo.SelDict)
            GenInfo.SelDict = {'BaseURI': 'Inf', 'StartP': 'Inf', 'EndP': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}

class ExportToRdf(object): # Convert all the created features into RDF statements.
    """Implementation for Digitool_addin.Exportrdf (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        os.chdir(GenInfo.workpath)
        for row in arcpy.SearchCursor('Domain', fields='URIDomain'):
            domain = row.getValue('URIDomain')
        EPSG = '<***>' # Fill in the coordinate reference system.
        p = rdflib.Namespace('***') # Fill in the URI of the ontology of the thematic map
        geom = rdflib.Namespace('http://www.opengis.net/ont/geosparql#')
        g = rdflib.Graph()
        g.bind('', domain)
        g.bind('thematic_map', p)
        g.bind('geosparql', geom)
        rdf = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        g.bind('rdf', rdf)
        terms = rdflib.Namespace('http://purl.org/dc/terms/')
        g.bind('terms', terms)
        owl = rdflib.Namespace('http://www.w3.org/2002/07/owl#')
        g.bind('owl', owl)
        xml = rdflib.Namespace('http://www.w3.org/XML/1998/namespace')
        g.bind('xml', xml)
        base_map = rdflib.Namespace('***') # Fill in the URI of the ontology of the thematic map
        g.bind('base_map', base_map)
        xsd = rdflib.Namespace('http://www.w3.org/2001/XMLSchema#')
        g.bind('xsd', xsd)
        skos = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
        g.bind('skos', skos)
        rdfs = rdflib.Namespace('http://www.w3.org/2000/01/rdf-schema#')
        g.bind('rdfs', rdfs)
        dc = rdflib.Namespace('http://purl.org/dc/elements/1.1/')
        g.bind('dc', dc)
        sf = rdflib.Namespace('http://www.opengis.net/ont/sf#')
        g.bind('sf', sf)

        CRS = '' # Fill in the coordinate reference system.

        for feature in GenInfo.AllFeature:
            thematicFeature = rdflib.URIRef(feature['URI'])
            g.add((thematicFeature, rdflib.RDF.type, p.Thematic_Feature))
            g.add((thematicFeature, p.CRS, rdflib.Literal(CRS)))
            for seg in feature['Segments']:
                if len(seg) == 5 or len(seg) == 6 or len(seg) == 7:
                    segment = rdflib.URIRef(seg['URI'])
                    g.add((thematicFeature, p.hasComponent, segment))
                    g.add((segment, rdflib.RDF.type, p.Matched_Component))

                    startPoint = rdflib.URIRef(domain + str(uuid.uuid4()))
                    g.add((startPoint, rdflib.RDF.type, sf.Point))
                    g.add((segment, p.startsAt, startPoint))
                    startGeo = EPSG + '\n' + arcpy.PointGeometry(arcpy.Point(seg['StartP'][0], seg['StartP'][1])).WKT
                    g.add((startPoint, geom.asWKT, rdflib.Literal(startGeo, datatype=geom.wktLiteral)))

                    endPoint = rdflib.URIRef(domain + str(uuid.uuid4()))
                    g.add((endPoint, rdflib.RDF.type, sf.Point))
                    g.add((segment, p.endsAt, endPoint))
                    endGeo = EPSG + '\n' + arcpy.PointGeometry(arcpy.Point(seg['EndP'][0], seg['EndP'][1])).WKT
                    g.add((endPoint, geom.asWKT, rdflib.Literal(endGeo, datatype=geom.wktLiteral)))

                    BaseFeat = rdflib.URIRef(seg['BaseURI'])
                    g.add((segment, p.isPartOf, BaseFeat))

                    g.add((segment, p.componentOrder, rdflib.Literal(seg['SegOrder'])))

                    if seg.has_key('VDirection'):
                        g.add((segment, p.verticesOrder, rdflib.Literal(seg['VDirection'])))
                    if seg.has_key('InnerRingNum'):
                        g.add((segment, p.innerRingNo, rdflib.Literal(seg['InnerRingNum'], datatype=xsd.int)))

                if len(seg) == 3 or len(seg) == 4:
                    segment = rdflib.URIRef(seg['URI'])
                    g.add((thematicFeature, p.hasComponent, segment))
                    g.add((segment, rdflib.RDF.type, p.Independent_Component))

                    line = rdflib.URIRef(domain + str(uuid.uuid4()))
                    g.add((line, rdflib.RDF.type, sf.LineString))
                    g.add((segment, geom.defaultGeometry, line))
                    lineGeo = EPSG + '\n' + seg['LineGeometry'].WKT
                    g.add((line, geom.asWKT, rdflib.Literal(lineGeo, datatype=geom.wktLiteral)))

                    g.add((segment, p.componentOrder, rdflib.Literal(seg['SegOrder'])))

                    if seg.has_key('InnerRingNum'):
                        g.add((segment, p.innerRingNo, rdflib.Literal(seg['InnerRingNum'], datatype=xsd.int)))

        g.serialize('thematic_data.ttl', format="turtle")
        print 'The RDF file named thematic_data is saved in {}'.format(GenInfo.workpath)

class Line(object): # Draw a line feature, save the coordinates, and show it on the map.
    """Implementation for Digitool_addin.Line (Tool)"""
    def __init__(self):
        self.enabled = True
        self.cursor = 3
        self.shape = "Line" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onLine(self, line_geometry):
        fc = 'Line'
        deleteID = str(GenInfo.numFea) + str(GenInfo.n)
        path = GenInfo.workpath + '\TestTD.gdb'
        numberOfSegments = len(GenInfo.Feature['Segments'])

        lineCoordinates = line_geometry.getPart(0)
        sp = lineCoordinates[0]
        ep = lineCoordinates[len(lineCoordinates) - 1]

        # if numberOfSegments==0:
        '''Perform the snap functionality'''
        print [point for point in lineCoordinates]
        if (numberOfSegments <> 0 and GenInfo.startRing == 0) or (
                    numberOfSegments - GenInfo.ExteriorSeg > 0 and GenInfo.startRing == 1) or (
                GenInfo.NextRing == 0 and GenInfo.startRing == 1):
            try:
                lineCoordinates[0] = arcpy.Point(GenInfo.Feature['Segments'][numberOfSegments - 1]['EndP'][0],
                                                 GenInfo.Feature['Segments'][numberOfSegments - 1]['EndP'][1])
            except:
                try:
                    lineCoordinates[0] = GenInfo.Feature['Segments'][numberOfSegments - 1]['LineGeometry'].lastPoint
                except:
                    pass

            for featureInfo in GenInfo.Feature['Segments']:
                try:
                    startPoint = arcpy.PointGeometry(arcpy.Point(featureInfo['StartP'][0], featureInfo['StartP'][1]))
                except:
                    startPoint = arcpy.PointGeometry(featureInfo['LineGeometry'].firstPoint)

                distanceEP = startPoint.distanceTo(ep)
                if 0 < distanceEP < 5:
                    # del lineCoordinates[-1]
                    lineCoordinates.append(startPoint.getPart(0))

        if numberOfSegments == 0 or (numberOfSegments - GenInfo.ExteriorSeg == 0 and GenInfo.startRing == 1) or (
                GenInfo.NextRing == 1 and GenInfo.startRing == 1):
            minDistanceSP, closestFeatureSP = 5, None
            minDistanceEP, closestFeatureEP = 5, None
            spGeo = arcpy.PointGeometry(sp)
            epGeo = arcpy.PointGeometry(ep)
            for feature in GenInfo.allLayersFeatures:
                distanceSP = feature.distanceTo(sp)
                if 0 < distanceSP < 5:
                    print 'SP distance -->', distanceSP
                    try:
                        print 'we are in SP try'
                        if distanceSP < minDistanceSP:
                            minDistanceSP = distanceSP
                            closestFeatureSP = feature
                    except:
                        print 'we are in SP exception'
                        minDistanceSP = distanceSP
                        closestFeatureSP = featur

                distanceEP = feature.distanceTo(ep)
                if 0 < distanceEP < 5:
                    print 'EP distance -->', distanceEP
                    try:
                        print 'we are in EP try'
                        if distanceEP < minDistanceEP:
                            minDistanceEP = distanceEP
                            closestFeatureEP = feature
                    except:
                        print 'we are in EP exception'
                        minDistanceEP = distanceEP
                        closestFeatureEP = feature

            if closestFeatureSP is not None:
                spNew = closestFeatureSP.snapToLine(sp).getPart(0)
                lineCoordinates[0] = spNew

            if closestFeatureEP is not None:
                epNew = closestFeatureEP.snapToLine(ep).getPart(0)
                lineCoordinates.append(epNew)

        line_geometry = arcpy.Polyline(arcpy.Array([point for point in lineCoordinates]), GenInfo.spatialReference)

        '''Visualize the line'''
        edit = arcpy.da.Editor(path)
        edit.startEditing(True)
        edit.startOperation()

        cur = arcpy.da.InsertCursor(fc, ['SHAPE@', 'DeleteID'])
        cur.insertRow((line_geometry, deleteID))

        edit.stopOperation()
        edit.stopEditing(True)
        arcpy.RefreshActiveView()

        '''Transform the absolute coordinates to relative coordinates'''
        reCoords = relativeCoor(lineCoordinates)
        re_line_geometry = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in reCoords]))

        '''Save coordinates of line_geometry'''
        GenInfo.LineDict['LineGeometry'] = re_line_geometry
        GenInfo.LineDict['SegOrder'] = GenInfo.n

        for row in arcpy.SearchCursor('Domain', fields='URIDomain'):
            domain = row.getValue('URIDomain')
        GenInfo.LineDict['URI'] = domain + str(uuid.uuid4())

        if GenInfo.startRing == 1:
            GenInfo.LineDict['InnerRingNum'] = GenInfo.m

        GenInfo.n += 1
        print GenInfo.LineDict

        GenInfo.Feature['Segments'].append(GenInfo.LineDict)
        GenInfo.LineDict = {'LineGeometry': 'Inf', 'SegOrder': 'Inf', 'URI': 'Inf'}

class NextFeature(object): # Finishing creating the current feature and start to create next one.
    """Implementation for Digitool_addin.Nextfeature (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        # Assign a URI of the current feature.
        for row in arcpy.SearchCursor('Domain', fields='URIDomain'):
            domain = row.getValue('URIDomain')
        GenInfo.Feature['URI'] = domain  + str(uuid.uuid4())

        print GenInfo.Feature
        GenInfo.AllFeature.append(GenInfo.Feature)
        GenInfo.n = 0
        GenInfo.Feature = {'URI': 'Inf', 'Segments': []}

        GenInfo.numFea += 1

class NextRing(object): # Finish creating the current interior ring and move to next one.
    """Implementation for Digitool_addin.nextring (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GenInfo.m += 1
        GenInfo.NextRing = 1
        print 'Start creating next interior ring.'

class Polygon(object): # Draw a polygon and show it on the map.
    """Implementation for Digitool_addin.Polygon (Tool)"""
    def __init__(self):
        self.enabled = True
        self.cursor = 3
        self.shape = "Line"# Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onLine(self, line_geometry):
        array = arcpy.Array()
        part = line_geometry.getPart(0)
        for pt in part:
            array.add(pt)
        array.add(line_geometry.firstPoint)
        polygon = arcpy.Polygon(array)

        path = GenInfo.workpath + '\TestTD.gdb' + '\Polygon'
        # Process: Append Polygon to existing file.
        arcpy.Append_management(polygon, path, "Test", "", "")

class QuitRing(object): # Stop creating interior rings
    """Implementation for Digitool_addin.quitring (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GenInfo.startRing = 0
        GenInfo.m = 0
        print 'Stop creating interior ring.'

class SPoint(object): # Draw a start point, save the coordinates, and show it on the map.
    """Implementation for Digitool_addin.SPoint (Tool)"""
    def __init__(self):
        self.enabled = True
        self.cursor = 3
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDownMap(self, x, y, button, shift):
        numberOfSegments = len(GenInfo.Feature['Segments'])
        spNew = None
        sp = arcpy.Point(x, y)
        '''Perform the snap functionality & Save coordinates in RDF dictionary'''
        if (numberOfSegments <> 0 and GenInfo.startRing == 0) or (
                    numberOfSegments - GenInfo.ExteriorSeg > 0 and GenInfo.startRing == 1) or (
                GenInfo.NextRing == 0 and GenInfo.startRing == 1):
            try:
                spNew = arcpy.Point(GenInfo.Feature['Segments'][numberOfSegments - 1]['EndP'][0],
                                    GenInfo.Feature['Segments'][numberOfSegments - 1]['EndP'][1])
            except:
                try:
                    spNew = GenInfo.Feature['Segments'][numberOfSegments - 1]['LineGeometry'].lastPoint
                except:
                    pass
            GenInfo.SelDict['StartP'] = (spNew.X, spNew.Y)
        if numberOfSegments == 0 or (numberOfSegments - GenInfo.ExteriorSeg == 0 and GenInfo.startRing == 1) or (
                GenInfo.NextRing == 1 and GenInfo.startRing == 1):
            if arcpy.Describe(GenInfo.selectLayer).shapeType == 'Polygon':
                ring = ReadGeometry(GenInfo.selectLayer)
                dis = []
                for r in ring:
                    a = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in r]))
                    dis.append(a.distanceTo(arcpy.Point(sp.X, sp.Y)))
                loc = dis.index(min(dis))
                polygonToPolyline = arcpy.Polyline(arcpy.Array([arcpy.Point(*coord) for coord in ring[loc]]))
                spNew = polygonToPolyline.snapToLine(sp).getPart()
            else:
                spNew = GenInfo.selectedFeature.snapToLine(sp).getPart()
            GenInfo.SelDict['StartP'] = (spNew.X, spNew.Y)

        '''Visualize the point'''
        fc = 'Point'
        path = GenInfo.workpath + '\TestTD.gdb'
        # Start an edit session. Require the workspace
        edit = arcpy.da.Editor(path)
        # Edit session is started without an undo/redo stack for versioned data
        # (for second argument, use False for unversioned data)
        edit.startEditing(True)
        # Start an edit operation
        edit.startOperation()

        if spNew is not None:
            rowValue = [(spNew.X, spNew.Y)]
        else:
            GenInfo.SelDict['StartP'] = (sp.X, sp.Y)
            rowValue = [(sp.X, sp.Y)]

        cursor = arcpy.da.InsertCursor(fc, 'SHAPE@XY')
        cursor.insertRow(rowValue)

        # Stop the edit operation.
        edit.stopOperation()
        # Stop the edit session and save the changes
        edit.stopEditing(True)
        arcpy.RefreshActiveView()

class SelectBackgroundFeature(object): # Select a feature from the selected layer
    """Implementation for Digitool_addin.BackFeature (Tool)"""
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDownMap(self, x, y, button, shift):
        # Respond to the mouse click, and then 'Select by location'
        mxd = arcpy.mapping.MapDocument('current')
        lay = []
        for layr in arcpy.mapping.ListLayers(mxd):  # load all the layers
            lay.append(layr.name)
        m = lay.index(GenInfo.selectLayer)
        lyr = arcpy.mapping.ListLayers(mxd)[m] # Convert the 'selectlayer' into a layer to perform the 'SelectLayerByLocation'
        pointGeom = arcpy.PointGeometry(arcpy.Point(x, y))
        arcpy.SelectLayerByLocation_management(lyr, 'WITHIN_A_DISTANCE', pointGeom, '25 meter', 'NEW_SELECTION')
        with arcpy.da.SearchCursor(lyr, ["SHAPE@", ]) as selectedFeatures:
            for feature in selectedFeatures:
                GenInfo.selectedFeature = feature[0]
                break

        GenInfo.ClearSelection = lyr

        # Read URI of the selected feature
        for row in arcpy.SearchCursor(GenInfo.selectLayer, fields='URI'):
            GenInfo.SelDict['BaseURI'] = row.getValue('URI')

        # Assign URI for the created feature
        for row in arcpy.SearchCursor('Domain', fields='URIDomain'):
            domain = row.getValue('URIDomain')
        GenInfo.SelDict['URI'] = domain + str(uuid.uuid4())

class SelectLayer(object): # Select a layer from the combo box.
    """Implementation for Digitool_addin.SelectLayer (ComboBox)"""
    def __init__(self):
        self.items = GenInfo.list # Load all the layers in combo box.
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'XXXXXXXXXXXXXXXXXX'
        self.width = 'XXXXXXXXXXXXXXXX'
    def onSelChange(self, selection):
        GenInfo.selectLayer = selection # Read the selected layer.
        if GenInfo.ClearSelection:
            arcpy.SelectLayerByAttribute_management(GenInfo.ClearSelection, "CLEAR_SELECTION")  # Clear selection
    def onFocus(self, focused):
        # When the combo box has focus, update the combo box with the list of layer names.
        if focused:
            self.mxd = arcpy.mapping.MapDocument('current')
            layers = arcpy.mapping.ListLayers(self.mxd)
            self.items = []
            for layer in layers:
                if (layer.visible) and layer.name != 'Point' and layer.name != 'Line' and layer.name != 'Polygon':
                    self.items.append(layer.name)

class StartRing(object): # Start creating interior rings
    """Implementation for Digitool_addin.startring (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GenInfo.startRing = 1
        GenInfo.ExteriorSeg = GenInfo.n
        print 'Start to create interior ring.'

class Workpath(object): # Set the working directory, and create geodatabases, feature classes and table
    """Implementation for Digitool_addin.workpath (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        GenInfo.workpath = pythonaddins.OpenDialog('Select a folder')
        print GenInfo.workpath
        arcpy.env.workspace = GenInfo.workpath
        # Create a file geodatabase
        TD = 'TestTD.gdb'
        if not arcpy.Exists(TD):
            arcpy.CreateFileGDB_management(GenInfo.workpath, TD)
        # Create point and line feature classes
        self.spatial_reference = arcpy.Describe(GenInfo.list[1]).spatialReference
        GenInfo.sptialReferernce = self.spatial_reference
        if not arcpy.Exists('Point'):
            arcpy.CreateFeatureclass_management(TD, 'Point', 'POINT', "#", "#", "#", self.spatial_reference)
        if not arcpy.Exists('Line'):
            arcpy.CreateFeatureclass_management(TD, 'Line', 'POLYLINE', "#", "#", "#", self.spatial_reference)
            arcpy.AddField_management('Line', 'DeleteID', 'TEXT', '', '', '10')
        if not arcpy.Exists('Polygon'):
            arcpy.CreateFeatureclass_management(TD, 'Polygon', 'POLYGON', "#", "#", "#", self.spatial_reference)
        if not arcpy.Exists('Domain'):
            try:
                arcpy.CreateTable_management(TD, 'Domain')
                arcpy.AddField_management('Domain', 'URIDomain', 'TEXT', '', '', '200')
            except:
                print "domain has not been created"