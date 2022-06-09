# vtdecode

Decodes Vertex-Tile Protobuf files into GeoJSON.

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