import argparse
from base64 import decode
import decode.vector_tile_pb2 as vt_proto
from decode.decode import decode_file
import geojson
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert Vector Tile Protobuf files to GeoJSON.")
    parser.add_argument("-i", "--input", required=True, dest='input_file', help="Input file")
    parser.add_argument("-o", "--output", required=True, dest='output_file',help="Output file")

    parser.add_argument("-x", dest = "tile_x", help="X coordinate of tile", required=False, type=int)
    parser.add_argument("-y", dest = "tile_y", help="Y coordinate of tile", required=False, type=int)
    parser.add_argument("-z", dest = "tile_z", help="Zoom level of tile", required=False, type=int)
    parser.add_argument("--json-indent", dest="json_indent", help="JSON file indentation. 0 or negative numbers generate dense JSON file.", default=0, type=int)
    parser.add_argument("--layer", dest = "layer", help="Only decode layer with given name. Outputs Pure GeoJSON.", required=False)
    args = parser.parse_args()

    if(not (args.tile_x is not None and args.tile_y is not None and args.tile_z is not None)):
        print("Please provide tile coordinates.")
        exit(1)
    elif(args.output_file is None):
        print("No output file specified.")
    else:
        decoded = decode_file(args.input_file, args.tile_x, args.tile_y, args.tile_z)
        if(args.layer is None):
            json.dump(decoded, open(args.output_file, 'w'), indent=args.json_indent if args.json_indent > 0 else None)
        else:
            if(args.layer in decoded):
                geojson.dump(decoded[args.layer], open(args.output_file, 'w'), indent=args.json_indent if args.json_indent > 0 else None)
            else:
                print("Layer %s not found in input file." % (args.layer))