# vtdecode

This project centers around decoding Vector Tile formats (protobuf) files and converting them to JSON. It uses the same backend for decoding Vertex Tile files, and provides multiple entrypoints for fetching those files.

## Entrypoints

### main.py
Decodes a Vertex-Tile Protobuf on the computer, and saves it to a JSON file containing GeoJSON.

```
usage: main.py [-h] -i INPUT_FILE -o OUTPUT_FILE [-x TILE_X] [-y TILE_Y] [-z TILE_Z] [--json-indent JSON_INDENT] [--layer LAYER]

Convert Vector Tile Protobuf files to GeoJSON.

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input INPUT_FILE
                        Input file
  -o OUTPUT_FILE, --output OUTPUT_FILE
                        Output file
  -x TILE_X             X coordinate of tile
  -y TILE_Y             Y coordinate of tile
  -z TILE_Z             Zoom level of tile
  --json-indent JSON_INDENT
                        JSON file indentation. 0 or negative numbers generate dense JSON file.
  --layer LAYER         Only decode layer with given name. Outputs Pure GeoJSON.
```

Example usage: `python main.py --input sample_14_8185_5449.pbf -x 8185 -y 5449 -z 14 --output-file sample_14_8185_5449.json`.

### mapillary.py
Fetch a bunch of data from Mapillary, convert them to GeoJSON, and put them into a folder.

```
usage: mapillary.py [-h] --url URL --start-x START_X --start-y START_Y --end-x END_X --end-y END_Y [--json-indent JSON_INDENT] --output-dir OUTPUT_DIR

Fetch tiles from mapillary.com and convert to GeoJSON.

optional arguments:
  -h, --help            show this help message and exit
  --url URL             URL template of tiles to fetch
  --start-x START_X     X coordinate of first tile
  --start-y START_Y     Y coordinate of first tile
  --end-x END_X         X coordinate of last tile (inclusive)
  --end-y END_Y         Y coordinate of last tile (inclusive)
  --json-indent JSON_INDENT
                        JSON file indentation. 0 or negative numbers generate dense JSON file.
  --output-dir OUTPUT_DIR
                        Output directory
```

Example usage: `python .\mapillary.py --url "https://tiles.mapillary.com/maps/vtp/mly_map_feature_traffic_sign/2/14/{x}/{y}?access_token=<YOUR_API_KEY>" --start-x 2744 --end-x 2748 --start-y 6520 --end-y 6524 --output-dir "./traffic-signs" --json-indent 4`

The command above will generate file and folder structure as follows, where each `json` file is a dictionary of GeoJSON files as shown in the [Output Format] section below.
```
└── traffic-signs
    ├── mly_map_feature_traffic_sign-14-2744-6520.json
    ├── mly_map_feature_traffic_sign-14-2744-6521.json
    ├── mly_map_feature_traffic_sign-14-2744-6522.json
    ├── mly_map_feature_traffic_sign-14-2744-6523.json
    ├── mly_map_feature_traffic_sign-14-2744-6524.json
    ├── mly_map_feature_traffic_sign-14-2745-6520.json
    ├── mly_map_feature_traffic_sign-14-2745-6521.json
    ├── mly_map_feature_traffic_sign-14-2745-6522.json
    ├── mly_map_feature_traffic_sign-14-2745-6523.json
    ├── mly_map_feature_traffic_sign-14-2745-6524.json
    ├── mly_map_feature_traffic_sign-14-2746-6520.json
    ├── mly_map_feature_traffic_sign-14-2746-6521.json
    ├── mly_map_feature_traffic_sign-14-2746-6522.json
    ├── mly_map_feature_traffic_sign-14-2746-6523.json
    ├── mly_map_feature_traffic_sign-14-2746-6524.json
    ├── mly_map_feature_traffic_sign-14-2747-6520.json
    ├── mly_map_feature_traffic_sign-14-2747-6521.json
    ├── mly_map_feature_traffic_sign-14-2747-6522.json
    ├── mly_map_feature_traffic_sign-14-2747-6523.json
    ├── mly_map_feature_traffic_sign-14-2747-6524.json
    ├── mly_map_feature_traffic_sign-14-2748-6520.json
    ├── mly_map_feature_traffic_sign-14-2748-6521.json
    ├── mly_map_feature_traffic_sign-14-2748-6522.json
    ├── mly_map_feature_traffic_sign-14-2748-6523.json
    └── mly_map_feature_traffic_sign-14-2748-6524.json
```

Note that the Mapillary URL must resemble `https://tiles.mapillary.com/maps/vtp/****/2/**/{x}/{y}******`. The program will try to parse the string and find object type and tile coordinates.

## Output Format
Each layer in the input file will be converted into one `FeatureCollection`, therefore one GeoJSON object. Therefore, the output file will NOT be a pure GeoJSON file (unless you specified the `--layer` option). Instead, it will contain multiple GeoJSON objects indexed by their layer names.

For example, parsing a terrain file from mapbox generates a JSON file like this:
```
{
    "landcover": <A GeoJSON object>,
    "hillshade": <A GeoJSON object>,
    "contour": <A GeoJSON object>
}
```

This behavior can be avoided if you use the `--layer` switch. For example, if you used `--layer landcover`, the output JSON file will be a pure GeoJSON that contains only the `landcover` layer.