from pyparsing import line
from decode.LayerDecoder import LayerDecoder
import decode.vector_tile_pb2 as vt_proto
from geojson import Feature, Point, FeatureCollection, LineString, MultiLineString, MultiPolygon, Polygon, MultiPoint
from typing import Dict, Tuple, List
from decode.LayerDecoder import LayerDecoder
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

class FileDecoder:
    def __init__(self, xtile: int, ytile: int, zoom: int, filename: str):
        "Load the file decoder with a file. Decoding has not started."
        self.xtile = xtile
        self.ytile = ytile
        self.zoom = zoom
        self.filename = filename
        self.decoded = None
    
    def read_protobuf(self) -> vt_proto.Tile:
        with open(self.filename, 'rb') as f:
            return vt_proto.Tile.FromString(f.read())
    
    def decode_layer(self, layer: vt_proto.Tile.Layer) -> Tuple[str, FeatureCollection]:
        layer_decoder = LayerDecoder(self, layer)
        layer_name, layer_content = layer_decoder.decode()
        return (layer_name, layer_content)
    
    def decode(self):
        "Perform the decoding of the file. Multiple calls will not re-decode."
        if(self.decoded is None):
            tile = self.read_protobuf()
            layers = tile.layers
            self.decoded = dict()

            with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
                decoded_layers = executor.map(self.decode_layer, layers)
                executor.shutdown(wait=True)
                for layer_name, layer_content in decoded_layers:
                    self.decoded[layer_name] = layer_content

        return self.decoded