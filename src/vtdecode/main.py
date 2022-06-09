import argparse
from .decoder.FileDecoder import FileDecoder
import geojson
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Convert Vector Tile Protobuf files to GeoJSON, and saves it to a *.json file.")
    parser.add_argument("-i", "--input", required=True, dest='input_file', help="Input file")
    parser.add_argument("-o", "--output", required=True, dest='output_file',help="Output file")

    parser.add_argument("-x", dest = "tile_x", help="X coordinate of tile", required=False, type=int)
    parser.add_argument("-y", dest = "tile_y", help="Y coordinate of tile", required=False, type=int)
    parser.add_argument("-z", dest = "tile_z", help="Zoom level of tile", required=False, type=int)
    parser.add_argument("--json-indent", dest="json_indent", help="JSON file indentation. 0 or negative numbers generate dense JSON file.", default=0, type=int)
    parser.add_argument("--layer", dest = "layer", help="Only decode layer with given name. Outputs Pure GeoJSON.", required=False)
    parser.add_argument("--split-layers", dest = "split_layers", help="Split layers into separate GeoJSON files. Outputs Pure GeoJSON.", action="store_true", default=False)
    args = parser.parse_args()

    if(not (args.tile_x is not None and args.tile_y is not None and args.tile_z is not None)):
        print("Please provide tile coordinates.")
        exit(1)
    elif(args.output_file is None):
        print("No output file specified.")
    else:
        decoder = FileDecoder(args.tile_x, args.tile_y, args.tile_z, args.input_file)
        decoded = decoder.decode()
        if(args.layer is not None):
            if(args.layer in decoded):
                geojson.dump(decoded[args.layer], open(args.output_file, 'w'), indent=args.json_indent if args.json_indent > 0 else None)
                print("Writing layer {} to {}".format(args.layer, args.output_file))
            else:
                print("Layer %s not found in input file." % (args.layer))
        elif(args.split_layers):
            if(args.output_file.endswith(".json")):
                output_file_basename = args.output_file[:-5]
            else:
                output_file_basename = args.output_file
            
            for layer_name, layer_content in decoded.items():
                print("Writing layer {} to file {}.json".format(layer_name, output_file_basename + "-" + layer_name))
                json.dump(layer_content, open(output_file_basename + "-" + layer_name + ".json", 'w'), indent=args.json_indent if args.json_indent > 0 else None)
        else:
            json.dump(decoded, open(args.output_file, 'w'), indent=args.json_indent if args.json_indent > 0 else None)
            print("Wrote JSON to file {}".format(args.output_file))

if __name__ == '__main__':
    main()