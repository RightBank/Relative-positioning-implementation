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
from django.http import HttpResponse
from Web_App_Entrance import Get_Geojson_Generated_Feature
import datetime
from django.shortcuts import render
from Static_Vars import *
import rdflib


def web_map(request):

    dp1 = datetime.datetime.now()
    g = rdflib.Graph()
    g.parse(RDF_file_path_thematic, format='n3')
    g.parse(RDF_file_path_base, format='n3')

    try:
        if request.GET:
            print request.get_raw_uri()
            zoom_level = int(request.GET['zoom_level'])
            geojson = Get_Geojson_Generated_Feature(g, zoom_level, 4326)
            dp2 = datetime.datetime.now()
            elapsed_time = dp2 - dp1
            print str(elapsed_time.total_seconds())
            print geojson
            return HttpResponse(geojson)

    except:
        pass

    data = {'data': str('')}
    return render(request, r'integration_thematic_base_gdal/map.html', data)

