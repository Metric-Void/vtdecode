from pyparsing import line
import decode.vector_tile_pb2 as vt_proto
from geojson import Feature, Point, FeatureCollection, LineString, MultiLineString, MultiPolygon, Polygon, MultiPoint
from typing import Dict, Tuple, List
import math

def area_by_shoelace(points:  List[Tuple[float, float]]) -> float:
    "Assumes x,y points go around the polygon in one direction"
    x, y = zip(*points)
    return (sum(i * j for i, j in zip(x,             y[1:] + y[:1]))
           -sum(i * j for i, j in zip(x[1:] + x[:1], y            ))) / 2
               
def num2deg(xtile: int, ytile: int, zoom: int) -> Tuple[float, float]:
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)

def offset_to_latlon(xtile, ytile, zoom, xoffset, yoffset, extent):
    x_tiled_coord = xtile * extent + xoffset
    y_tiled_coord = ytile * extent + yoffset

    lon = x_tiled_coord * 360 / (extent * 2 ** zoom) - 180

    lat_noncoerce = 180 - y_tiled_coord * 360. / (extent * 2 ** zoom)
    lat = 360. / math.pi * math.atan(math.exp(lat_noncoerce * math.pi / 180)) - 90
    return (lon, lat)

def decode_file(filename: str, xtile, ytile, zoom) -> Dict[str, FeatureCollection]:
    tile = read_protobuf(filename)
    layers = tile.layers
    layers_dict = {}
    for layer in layers:
        layer_name, layer_content = extract_layer(layer, xtile, ytile, zoom)
        layers_dict[layer_name] = layer_content
    return layers_dict

def read_protobuf(filename: str) -> vt_proto.Tile:
    with open(filename, 'rb') as f:
        return vt_proto.Tile.FromString(f.read())

def unzigzag_coords(value: int) -> int:
    return (value >> 1) ^ (-(value & 1))

def expand_commands(cmds: List[int]) -> List[Tuple]:
    expanded_cmds = []
    cmds_pc = 0
    while(cmds_pc < len(cmds)):
        command_integer = cmds[cmds_pc]
        command_id = command_integer & 0x07
        command_count = command_integer >> 3
        if(command_id == 1 or command_id == 2):
            for i in range(command_count):
                cmds_pc += 1
                param1 = cmds[cmds_pc]
                cmds_pc += 1
                param2 = cmds[cmds_pc]
                expanded_cmds.append((command_id, param1, param2))
        elif(command_id == 7):
            expanded_cmds.extend([(command_id, -1, -1)]*command_count)
        else:
            print("ERROR: Unknown command encountered.")
        cmds_pc += 1
    return expanded_cmds

def parse_point(feature: vt_proto.Tile.Feature, keys, values, xtile, ytile, zoom, extent):
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
                acquired_points.append(offset_to_latlon(xtile, ytile, zoom, x, y, extent))
                cX = x
                cY = y
        else:
            print("ERROR: Unknown command encountered in Point feature.")
        geom_pc += 1
    
    tags = feature.tags
    tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
    properties = {keys[key]: values[value] for key, value in tag_pairs}

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

def parse_linestring(feature: vt_proto.Tile.Feature, keys, values, xtile, ytile, zoom, extent):
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
                line_coords.append(offset_to_latlon(xtile, ytile, zoom, x, y, extent))
                cX = x
                cY = y
            else:
                print("ERROR: ClosePath command found in LineString feature, unexpected.")
                line_coords.append(line_coords[0])
        acquired_lines.append(line_coords)
    
    tags = feature.tags
    tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
    properties = {keys[key]: values[value] for key, value in tag_pairs}

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

def parse_polygon(feature: vt_proto.Tile.Feature, keys, values, xtile, ytile, zoom, extent):
    geometry_cmds = feature.geometry

    acquired_polygons = []

    tags = feature.tags
    tag_pairs = [(tags[i*2], tags[i*2+1]) for i in range(len(tags)//2)]
    properties = {keys[key]: values[value] for key, value in tag_pairs}

    cX = 0
    cY = 0

    all_commands = expand_commands(geometry_cmds)

    split_commands = []
    for command in all_commands:
        if(command[0] == 1):
            split_commands.append([command])
        elif(command[0] == 2 or command[0] == 7):
            split_commands[-1].extend([command])
    
    for polygons in split_commands:
        poly_coords = []
        poly_raw_coords = []
        for command_id, x, y in polygons:
            if(command_id == 1 or command_id == 2):
                dX = unzigzag_coords(x)
                dY = unzigzag_coords(y)
                x = cX + dX
                y = cY + dY
                poly_coords.append(offset_to_latlon(xtile, ytile, zoom, x, y, extent))
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
                print("ERROR: Interior ring found before exterior ring.")
    
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
    
def extract_layer(layer: vt_proto.Tile.Layer, xtile, ytile, zoom) -> Tuple[str, FeatureCollection]:
    layer_content = []

    keys = layer.keys
    values = []
    for value in layer.values:
        if(value.HasField('string_value')):
            values.append(value.string_value)
        elif(value.HasField('double_value')):
            values.append(value.double_value)
        elif(value.HasField('float_value')):
            values.append(value.float_value)
        elif(value.HasField('int_value')):
            values.append(value.int_value)
        elif(value.HasField('uint_value')):
            values.append(value.uint_value)
        elif(value.HasField('sint_value')):
            values.append(value.sint_value)
        elif(value.HasField('bool_value')):
            values.append(value.bool_value)
    
    for feature in layer.features:
        geom_type = feature.type

        if(geom_type == vt_proto.Tile.GeomType.POINT):
            layer_content.append(Feature(geometry=parse_point(feature, keys, values, xtile, ytile, zoom, layer.extent)))
        elif(geom_type == vt_proto.Tile.GeomType.LINESTRING):
            layer_content.append(Feature(geometry=parse_linestring(feature, keys, values, xtile, ytile, zoom, layer.extent)))
        elif(geom_type == vt_proto.Tile.GeomType.POLYGON):
            layer_content.append(Feature(geometry=parse_polygon(feature, keys, values, xtile, ytile, zoom, layer.extent)))
    return layer.name, FeatureCollection(layer_content)
