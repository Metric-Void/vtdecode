import math
from typing import Dict, Tuple, List

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