# vtdecode

This project centers around decoding Vector Tile formats (protobuf) files and converting them to JSON. It uses the same backend for decoding Vertex Tile files, and provides multiple entrypoints for fetching those files.

## Installation
This package is available on PyPI.
```
pip install vtdecode
```

It provides three commands: `vtdecode`, `vtdecode-mapbox` and `vtdecode-mapillary`

## Entrypoints

### vtdecode
Decodes a Vertex-Tile Protobuf on the local machine, and saves it to a JSON file containing GeoJSON.

```
usage: main.py [-h] -i INPUT_FILE -o OUTPUT_FILE [-x TILE_X] [-y TILE_Y] [-z TILE_Z] [--json-indent JSON_INDENT] [--layer LAYER] [--split-layers]

Convert Vector Tile Protobuf files to GeoJSON, and saves it to a *.json file.

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
  --split-layers        Split layers into separate GeoJSON files. Outputs Pure GeoJSON.
```

X, Y, and Zoom levels represent the tile coordinates as specified in https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames.
This information is necessary to calculate the actual latitude and longitude of point coordinates.

When not using the --layer or --split-layer options, the output file will contain multiple GeoJSON features, denoted by their keys.
When using the --layer LAYER_NAME option, only a single layer will be exported, and the output will be a single GeoJSON FeatureCollection.
When using the --split-layer option, multiple files will be generated (suffixed with the layer name), each containing a single layer in GeoJSON FeatureCollection.

Example usage: `vtdecode --input sample_14_8185_5449.pbf -x 8185 -y 5449 -z 14 --output-file sample_14_8185_5449.json`.

### vtdecode-mapillary, vtdecode-mapbox
Fetch data from Mapillary or Mapbox, convert them to GeoJSON, and put them into a folder.

**Fetching a range of tiles:** If all of `--start-x`, `--start-y`, `--end-x`, `--end-y` is provided, the URL will be treated as a template, replace `{x}` and `{y}`, and fetch all tiles within the specified range. 

When fetching a range of tiles, you must use `--output-dir` to specify an output directory. 

**Fetching a single tile:** If any of`--start-x`, `--start-y`, `--end-x`, `--end-y` is not provided, the URL will be treated as a pure URL and only a single file will be fetched. 

When fetching a single tile, you can either use `--output-dir` to specify a directory or `--output` to specify an output filename. When both is provided, `--output` is preferred.

```
usage: mapillary.py [-h] --url URL [--start-x START_X] [--start-y START_Y] [--end-x END_X] [--end-y END_Y] [--json-indent JSON_INDENT] [--output-dir OUTPUT_DIR] [--split-layers] [--output OUTPUT]

Fetch multiple tiles from mapillary.com and convert to GeoJSON.

optional arguments:
  -h, --help            show this help message and exit
  --url URL             URL template of tiles to fetch. {x} and {y} in the template will be replaced.
  --start-x START_X     X coordinate of first tile
  --start-y START_Y     Y coordinate of first tile
  --end-x END_X         X coordinate of last tile (inclusive)
  --end-y END_Y         Y coordinate of last tile (inclusive)
  --json-indent JSON_INDENT
                        JSON file indentation. 0 or negative numbers generate dense JSON file.
  --output-dir OUTPUT_DIR
                        Output directory
  --split-layers        Split layers into separate GeoJSON files. Outputs Pure GeoJSON.
  --output OUTPUT       Output file
```

Example usage: 

**Fetching a range of tiles:** `vtdecode-mapillary --url "https://tiles.mapillary.com/maps/vtp/mly_map_feature_traffic_sign/2/14/{x}/{y}?access_token=<YOUR_API_KEY>" --start-x 2744 --end-x 2748 --start-y 6520 --end-y 6524 --output-dir "./traffic-signs" --json-indent 4`

Note that the Mapillary URL must resemble `https://tiles.mapillary.com/maps/vtp/<feature-type>/2/<zoom-level>/{x}/{y}******`. The program will try to parse the string and find object type and tile coordinates. Zoom level should be fixed and directly encoded in the URL.

**Fetching a single tile:** `vtdecode-mapillary --url https://tiles.mapillary.com/maps/vtp/mly_map_feature_traffic_sign/2/14/2745/6520?access_token=<YOUR_API_KEY> --output-file traffic-signs-14-2745-6520.json`.

Here the URL is treated as fixed.

## Output Format
A Vertex Tile file may contain multiple layers, each layer containing a `FeatureCollection` GeoJSON object. However, there can only be one `FeatureCollection` in each GeoJSON file.

Therefore, when none of `--layer` or `--split-layers` is provided, all generated GeoJSON objects will be put into a single JSON file. The generated JSON object will contain keys that correspond to layer names, and values as the GeoJSON object.

For example, parsing a terrain file from mapbox generates a JSON file like this:
```
{
    "landcover": <A GeoJSON object>,
    "hillshade": <A GeoJSON object>,
    "contour": <A GeoJSON object>
}
```

This behavior can be avoided if you use the `--layer` or `--split-layers` switch. For example, if you used `--layer landcover`, the output JSON file will be a pure GeoJSON that contains only the `landcover` layer.
