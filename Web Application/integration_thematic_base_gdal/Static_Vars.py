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
"""This module stores static variables for the integration task.
Before running the web application, the variables should be checked here."""

scale_hierarchy = ['default', '10k', '50k', '100k', '250k']

scale_hierarchy_dict_lake = {
    '10k': (18, 17, 16, 15),
    '50k': (14,),
    '100k': (13,),
    '250k': (12, 11, 10, 9, 8, 7, 6, 5)
}
scale_hierarchy_dict_river = {
    '10k': (18, 17, 16,),
    '50k': (15, 14,),
    '100k': (13,),
    '250k': (12, 11, 10, 9, 8, 7, 6, 5)
}
scale_hierarchy_dict_road = {
    '10k': (18, 17, 16, ),
    '50k': (15,),
    '100k': (14,),
    '250k': (13, 12, 11, 10, 9, 8, 7, 6, 5)
}

scale_URI_hierarchy = ['geosparql:defaultGeometry', 'base_map:geometry_10k',
                       'base_map:geometry_50k', 'base_map:geometry_100k', 'base_map:geometry_250k']

CRS = ''

RDF_file_path_thematic = r"" # The path for RDF file of thematic data
RDF_file_path_base = r"" # The path for RDF file of base map


