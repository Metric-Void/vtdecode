import argparse
import asyncio
from .decoder.BytesDecoder import BytesDecoder
import json
import os
import sys
import re
from aiohttp_retry import RetryClient, ExponentialRetry
import geojson

pattern = re.compile("https://tiles.mapillary.com/maps/vtp/([^/]*)/2/(\\d+)/{x}/{y}.*")
fixed_pattern = re.compile("https://tiles.mapillary.com/maps/vtp/([^/]*)/2/(\\d+)/(\\d+)/(\\d+).*")

async def worker(url, client, output_dir, tile_name, json_indent, xtile, ytile, zoom, split_layers):
    print(f"Fetching tile {zoom}-{xtile}-{ytile}")
    async with client.get(url) as response:
        if(response.status == 429):
            asyncio.sleep(5)
        elif(response.status // 100 == 2):
            body = await response.read()
            decoder = BytesDecoder(xtile, ytile, zoom, body)
            result = decoder.decode()
            if(split_layers):
                for layer_name, layer_content in result.items():
                    output_filename = os.path.join(output_dir, f"{tile_name}-{zoom}-{xtile}-{ytile}-{layer_name}.json")
                    print("Writing layer {} to {}".format(layer_name, output_filename))
                    with open(output_filename, 'w') as f:
                        geojson.dump(layer_content, f, indent=json_indent if json_indent > 0 else None)
            else:
                output_filename = os.path.join(output_dir, f"{tile_name}-{zoom}-{xtile}-{ytile}.json")
                with open(output_filename, 'w') as f:
                    json.dump(result, f, indent=json_indent if json_indent > 0 else None)
                print(f"Writing all layers to {output_filename}")
        elif(response.status // 100 == 5):
            asyncio.sleep(10)

async def run(url: str, start_x: int, start_y: int, end_x: int, end_y: int, output_dir, json_indent, split_layers):
    os.makedirs(output_dir, exist_ok=True)

    match = re.match(pattern, url)
    if(match is None):
        print("URL does not match Mapillary tile request pattern.")
        return
    
    tile_name = match[1]
    zoom = int(match[2])
    async with RetryClient(raise_for_status=False, retry_options=ExponentialRetry(attempts=5, start_timeout=0.5, max_timeout=10)) as client:
        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                tile_url = url.replace('{x}', str(x)).replace('{y}', str(y))
                output_filename = os.path.join(output_dir, f"{tile_name}-{zoom}-{x}-{y}.json")
                await worker(tile_url, client, output_dir, tile_name, json_indent, x, y, zoom, split_layers)

async def run_fixed(url: str, output_dir: str, output_filename: str, json_indent, split_layers):
    match = re.match(fixed_pattern, url)
    if(match is None):
        print("URL does not match Mapillary tile request pattern.")
        return
    
    tile_name = match[1]
    zoom = int(match[2])
    xtile = int(match[3])
    ytile = int(match[4])

    async with RetryClient(raise_for_status=False, retry_options=ExponentialRetry(attempts=5, start_timeout=0.5, max_timeout=10)) as client:
        async with client.get(url) as response:
            if(response.status == 429):
                asyncio.sleep(5)
            elif(response.status // 100 == 2):
                body = await response.read()
                decoder = BytesDecoder(xtile, ytile, zoom, body)
                result = decoder.decode()
                if(split_layers):
                    for layer_name, layer_content in result.items():
                        if(output_filename is not None):
                            if(output_filename.endswith(".json")):
                                layer_filename = output_filename.replace(".json", f"-{layer_name}.json")
                            else:
                                layer_filename = output_filename + f"-{layer_name}.json"
                        else:
                            layer_filename = os.path.join(output_dir, f"{tile_name}-{zoom}-{xtile}-{ytile}-{layer_name}.json")

                        print("Writing layer {} to {}".format(layer_name, layer_filename))
                        with open(layer_filename, 'w') as f:
                            geojson.dump(layer_content, f, indent=json_indent if json_indent > 0 else None)
                else:
                    if(output_filename is None):
                        layers_filename = os.path.join(output_dir, f"{tile_name}-{zoom}-{xtile}-{ytile}.json")
                    else:
                        layers_filename = output_filename
                    with open(layers_filename, 'w') as f:
                        json.dump(result, f, indent=json_indent if json_indent > 0 else None)
                    print(f"Writing all layers to {layers_filename}")
            elif(response.status // 100 == 5):
                asyncio.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="Fetch multiple tiles from mapillary.com and convert to GeoJSON.")
    parser.add_argument("--url", dest = "url", help="URL template of tiles to fetch. {x} and {y} in the template will be replaced.", required=True)
    parser.add_argument("--start-x", dest = "start_x", help="X coordinate of first tile", required=False, type=int)
    parser.add_argument("--start-y", dest = "start_y", help="Y coordinate of first tile", required=False, type=int)
    parser.add_argument("--end-x", dest = "end_x", help="X coordinate of last tile (inclusive)", required=False, type=int)
    parser.add_argument("--end-y", dest = "end_y", help="Y coordinate of last tile (inclusive)", required=False, type=int)

    parser.add_argument("--json-indent", dest="json_indent", help="JSON file indentation. 0 or negative numbers generate dense JSON file.", default=0, type=int, required = False)
    parser.add_argument("--output-dir", dest = "output_dir", help="Output directory", required=False)
    parser.add_argument("--split-layers", dest = "split_layers", help="Split layers into separate GeoJSON files. Outputs Pure GeoJSON.", action="store_true", default=False)
    parser.add_argument("--output", dest = "output", help="Output file", required=False)

    args = parser.parse_args()

    if("win" in sys.platform.lower()):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except:
            pass

    if(args.output_dir is None and args.output is None):
        print("Must specify either --output or --output-dir")
        exit(1)
    
    if(args.output_dir is not None):
        os.makedirs(args.output_dir, exist_ok=True)
    
    if(args.start_x is None or args.start_y is None or args.end_x is None or args.end_y is None):
        asyncio.run(run_fixed(args.url, args.output_dir, args.output, args.json_indent, args.split_layers))
        exit(0)
    
    if(args.start_x > args.end_x):
        print("Start X coordinate must be smaller than end X coordinate.")
        exit(1)
    elif(args.start_y > args.end_y):
        print("Start Y coordinate must be smaller than end Y coordinate.")
        exit(1)
    else:
        asyncio.run(run(args.url, args.start_x, args.start_y, args.end_x, args.end_y, args.output_dir, args.json_indent, args.split_layers))

if __name__ == '__main__':
    main()