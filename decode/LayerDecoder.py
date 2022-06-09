from time import sleep
from pyparsing import line
import decode.vector_tile_pb2 as vt_proto
from geojson import Feature, Point, FeatureCollection, LineString, MultiLineString, MultiPolygon, Polygon, MultiPoint
from typing import Dict, Tuple, List
import math
from decode.utils import unzigzag_coords, expand_commands, area_by_shoelace
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

class LayerDecoder:
    def __init__(self, filedecoder, layer: vt_proto.Tile.Layer):
        "Initialize a Layer decoder from a file decoder."
        self.extent = layer.extent
        self.layer = layer
        self.decoded = None

        self.xtile = filedecoder.xtile
        self.ytile = filedecoder.ytile
        self.zoom = filedecoder.zoom

        self.keys = []
        self.values = []

    # Utility Functions.
    def offset_to_latlon(self, xoffset, yoffset) -> Tuple[float, float]:
        x_tiled_coord = self.xtile * self.extent + xoffset
        y_tiled_coord = self.ytile * self.extent + yoffset

        lon = x_tiled_coord * 360 / (self.extent * 2 ** self.zoom) - 180

        lat_noncoerce = 180 - y_tiled_coord * 360. / (self.extent * 2 ** self.zoom)
        lat = 360. / math.pi * math.atan(math.exp(lat_noncoerce * math.pi / 180)) - 90
        return (lon, lat)
    
    def extract_properties(self) -> None:
        self.keys = self.layer.keys
        for value in self.layer.values:
            if(value.HasField('string_value')):
                self.values.append(value.string_value)
            elif(value.HasField('double_value')):
                self.values.append(value.double_value)
            elif(value.HasField('float_value')):
                self.values.append(value.float_value)
            elif(value.HasField('int_value')):
                self.values.append(value.int_value)
            elif(value.HasField('uint_value')):
                self.values.append(value.uint_value)
            elif(value.HasField('sint_value')):
                self.values.append(value.sint_value)
            elif(value.HasField('bool_value')):
                self.values.append(value.bool_value)
    
    # Parser functions.
    def parse_point(self, feature: vt_proto.Tile.Feature):
        geometry_cmds = feature.geometry
        geom_pc = 0

        acquired_points = []

        cX = 0
        cY = 0

        while(geom_pc < len(geometry_cmds)):
            command_integer = geometry_cmds[geom_pc]
            command_id = command_integer & 0x07
            command_count = command_integer >> 3
            
            if(command_id == 1):
                for i in range(command_count):
                    geom_pc += 1
                    dX = unzigzag_coords(geometry_cmds[geom_pc])
                    geom_pc += 1
                    dY = unzigzag_coords(geometry_cmds[geom_pc])
                    x = cX + dX
                    y = cY + dY
                    acquired_points.append(self.offset_to_latlon(x, y))
                    cX = x
                    cY = y
            else:
                print("ERROR: Unexpected command encountered in Point feature. Ignored.")
            geom_pc += 1
        
        tags = feature.tags
        tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
        properties = {self.keys[key]: self.values[value] for key, value in tag_pairs}

        if(len(acquired_points) == 1):
            return Point(
                coordinates = acquired_points[0],
                properties = properties
            )
        else:
            return MultiPoint(
                coordinates=acquired_points,
                properties=properties
            )
    
    def parse_linestring(self, feature: vt_proto.Tile.Feature):
        geometry_cmds = feature.geometry
        acquired_lines = []

        cX = 0
        cY = 0

        all_commands = expand_commands(geometry_cmds)
        split_commands = []
        for command in all_commands:
            if(command[0] == 1):
                split_commands.append([command])
            elif(command[0] == 2):
                split_commands[-1].extend([command])
        
        for lines in split_commands:
            line_coords = []
            for command_id, x, y in lines:
                if(command_id == 1 or command_id == 2):
                    dX = unzigzag_coords(x)
                    dY = unzigzag_coords(y)
                    x = cX + dX
                    y = cY + dY
                    line_coords.append(self.offset_to_latlon(x, y))
                    cX = x
                    cY = y
                else:
                    print("ERROR: ClosePath command found in LineString feature. This is likely an error, closing the linestring feature as a best-effort guess.")
                    line_coords.append(line_coords[0])
            acquired_lines.append(line_coords)
        
        tags = feature.tags
        tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
        properties = {self.keys[key]: self.values[value] for key, value in tag_pairs}

        if(len(acquired_lines) > 1):
            return MultiLineString(
                coordinates=acquired_lines,
                properties=properties
            )
        else:
            return LineString(
                coordinates=acquired_lines[0],
                properties=properties
            )

    def parse_polygon(self, feature: vt_proto.Tile.Feature):
        geometry_cmds = feature.geometry

        acquired_polygons = []

        tags = feature.tags
        tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
        properties = {self.keys[key]: self.values[value] for key, value in tag_pairs}

        cX = 0
        cY = 0

        all_commands = expand_commands(geometry_cmds)

        split_commands = []
        for command in all_commands:
            if(command[0] == 1):
                split_commands.append([command])
            elif(command[0] == 2 or command[0] == 7):
                split_commands[-1].extend([command])
        
        # Sanity check: All polygons should have a start command MoveTo and an end command ClosePath.
        for command in split_commands:
            if(command[0][0] != 1):
                print("WARN: Polygon command does not start with MoveTo. There might be unknown consequences.")
            if(command[-1][0] != 7):
                print("WARN: Polygon command does not end with ClosePath. There might be unknown consequences.")
        
        for polygons in split_commands:
            poly_coords = []
            poly_raw_coords = []
            for command_id, x, y in polygons:
                if(command_id == 1 or command_id == 2):
                    dX = unzigzag_coords(x)
                    dY = unzigzag_coords(y)
                    x = cX + dX
                    y = cY + dY
                    poly_coords.append(self.offset_to_latlon(x, y))
                    poly_raw_coords.append((x, y))
                    cX = x
                    cY = y
                else:
                    poly_coords.append(poly_coords[0])
                    poly_raw_coords.append(poly_raw_coords[0])
            
            area = 0
            if(poly_raw_coords[0] == poly_raw_coords[-1]):
                area = area_by_shoelace(poly_raw_coords[:-1])
            else:
                area = area_by_shoelace(poly_raw_coords)
            
            if (area >= 0):
                acquired_polygons.append((1, poly_coords))
            else:
                acquired_polygons.append((-1, poly_coords))

        # Divide into sequences of exterior and interior rings
        polygon_items = []
        for polygon in acquired_polygons:
            if(polygon[0] > 0):
                # Exterior ring
                polygon_items.append([polygon[1]])
            else:
                # Interior ring
                if(len(polygon_items) >= 1):
                    polygon_items[-1].extend([polygon[1]])
                else:
                    print("ERROR: Interior ring found before exterior ring. The interior ring will be ignored.")
        
        if(len(polygon_items) > 1):
            return MultiPolygon(
                coordinates=polygon_items,
                properties=properties
            )
        else:
            return Polygon(
                coordinates=polygon_items[0],
                properties=properties
            )
    
    def parse_feature(self, feature: vt_proto.Tile.Feature) -> Feature:
        geom_type = feature.type
        if(geom_type == vt_proto.Tile.GeomType.POINT):
            return Feature(geometry=self.parse_point(feature))
        elif(geom_type == vt_proto.Tile.GeomType.LINESTRING):
            return Feature(geometry=self.parse_linestring(feature))
        elif(geom_type == vt_proto.Tile.GeomType.POLYGON):
            return Feature(geometry=self.parse_polygon(feature))

    def decode(self) -> Tuple[str, FeatureCollection]:
        if(self.decoded is None):
            self.extract_properties()

            layer_content = []

            num_cpus = multiprocessing.cpu_count()
            if(num_cpus == None):
                num_cpus = 4

            features_list = list(self.layer.features)

            with ThreadPoolExecutor(max_workers=num_cpus) as executor:
                layer_content = list(executor.map(self.parse_feature, features_list))
                executor.shutdown(wait=True)
            
            self.decoded = self.layer.name, FeatureCollection(layer_content)
        
        return self.decoded