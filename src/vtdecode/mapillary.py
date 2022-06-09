import argparse
import asyncio
from .decoder.BytesDecoder import BytesDecoder
import json
import os
import re
from aiohttp_retry import RetryClient, ExponentialRetry

pattern = re.compile("https://tiles.mapillary.com/maps/vtp/([^/]*)/2/(\\d+)/{x}/{y}.*")

async def worker(url, client, output_file, json_indent, xtile, ytile, zoom):
    print("Fetching %s" % (url))
    async with client.get(url) as response:
        if(response.status == 429):
            asyncio.sleep(5)
        elif(response.status // 100 == 2):
            body = await response.read()
            decoder = BytesDecoder(xtile, ytile, zoom, body)
            result = decoder.decode()
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=json_indent if json_indent > 0 else None)
            print(f"Written to {output_file}")
        elif(response.status // 100 == 5):
            asyncio.sleep(10)

async def run(url: str, start_x: int, start_y: int, end_x: int, end_y: int, output_dir, json_indent):
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
                await worker(tile_url, client, output_filename, json_indent, x, y, zoom)

def main():
    parser = argparse.ArgumentParser(description="Fetch multiple tiles from mapillary.com and convert to GeoJSON.")
    parser.add_argument("--url", dest = "url", help="URL template of tiles to fetch. {x} and {y} in the template will be replaced.", required=True)
    parser.add_argument("--start-x", dest = "start_x", help="X coordinate of first tile", required=True, type=int)
    parser.add_argument("--start-y", dest = "start_y", help="Y coordinate of first tile", required=True, type=int)
    parser.add_argument("--end-x", dest = "end_x", help="X coordinate of last tile (inclusive)", required=True, type=int)
    parser.add_argument("--end-y", dest = "end_y", help="Y coordinate of last tile (inclusive)", required=True, type=int)

    parser.add_argument("--json-indent", dest="json_indent", help="JSON file indentation. 0 or negative numbers generate dense JSON file.", default=0, type=int, required = False)
    parser.add_argument("--output-dir", dest = "output_dir", help="Output directory", required=True)

    args = parser.parse_args()

    if(args.start_x > args.end_x):
        print("Start X coordinate must be smaller than end X coordinate.")
        exit(1)
    elif(args.start_y > args.end_y):
        print("Start Y coordinate must be smaller than end Y coordinate.")
        exit(1)
    else:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run(args.url, args.start_x, args.start_y, args.end_x, args.end_y, args.output_dir, args.json_indent))

if __name__ == '__main__':
    main()