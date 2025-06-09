"""

"hec" to refers to hexagonal coordinates (a, r, c, z)
"uvz" refers to (u, v, z) where z is the height, used for pieces like beetles.
"xyz" refercs to (x, y, z) in 3D.
x = c and y = -r

"""
import re
import time
from pathlib import Path

import numpy as np
import rerun as rr
from pymongo import MongoClient

from notation import PlayerW

r32 = np.sqrt(3) / 2
hex_points = np.array([
    [0, 1],
    [r32, 0.5],
    [r32, -0.5],
    [0, -1],
    [-r32, -0.5],
    [-r32, 0.5],
    [0, 1],
])

# ref_piece = re.search(r'[wb][QAGBSLMP]\d*', dest_str).group()
PIECE_COLORS = {
    'Q': (168, 155, 50),
    'A': (50, 70, 168),
    'G': (43, 92, 21),
    'B': (49, 23, 84),
    'S': (120, 38, 19),
    'L': (222, 16, 43),
    'M': (150, 150, 150),
    'P': (66, 138, 105),
}
ASSETS_ROOT = Path("assets")


def log_tile(uvz, piece, color):
    m = re.search(r'([wb])(\w)(\d*)', piece)
    if m is None:
        raise ValueError(f"Failed to parse {piece=}")

    color_str = m.group(1)
    piece_type = m.group(2)
    piece_no_idx = f"{color_str}{piece_type}"
    try:
        piece_orientation_idx = int(m.group(3))
    except ValueError:
        piece_orientation_idx = 1

    piece_color = PIECE_COLORS[piece_type]

    u, v, z = uvz
    uv = uvz[:2]

    # 2D
    rr.log(piece, rr.LineStrips2D(uv[:2] + 1 / 2 * hex_points, labels=piece, colors=color, radii=0.04, draw_order=z))
    rr.log(f'{piece}/center', rr.Points2D(uv, colors=piece_color, radii=0.46, draw_order=z - 1))

    # 3D
    piece_path = ASSETS_ROOT / f"{piece_no_idx}.glb"
    # TODO: Z index???
    xy_scale = 0.09
    xyz = np.array([u * xy_scale, -v * xy_scale, z * 0.03])
    if piece_path.exists():
        piece_orientation = (1 - piece_orientation_idx) * np.deg2rad(60)
        rr.log(f"{piece}/mesh", rr.Transform3D(translation=xyz, rotation=rr.RotationAxisAngle(axis=np.array([0, 0, 1]),
                                                                                              angle=piece_orientation)))
        rr.log(f"{piece}/mesh", rr.Asset3D(path=piece_path))
        pass


def get_destination_coordinates(board_state, destination_str):
    pass


def resolve_move_hec(ref_hec, dest_str):
    a, r, c, z = ref_hec
    if re.fullmatch(r'/.*', dest_str):
        return 1 - a, r + a, c - (1 - a), z
    elif re.fullmatch(r'-.*', dest_str):
        return a, r, c - 1, z
    elif re.fullmatch(r'\\.*', dest_str):
        return 1 - a, r - (1 - a), c - (1 - a), z
    elif re.fullmatch(r'.*/', dest_str):
        return 1 - a, r - (1 - a), c + a, z
    elif re.fullmatch(r'.*-', dest_str):
        return a, r, c + 1, z
    elif re.fullmatch(r'.*\\', dest_str):
        return 1 - a, r + a, c + a, z
    elif re.fullmatch(r'[wb](\w\d*)', dest_str):
        # TODO: handle moving on top of other pieces (wht about mstacks of multiple pieces?)
        return a, r, c, z + 1
    else:
        raise ValueError(f"Failed to parse {dest_str}")


def hec_to_uvz(hec):
    a, r, c, z = hec
    return np.array([
        a / 2 + c,
        np.sqrt(3) * (a / 2 + r),
        z,
    ])


def main():
    client = MongoClient()
    db = client.get_database('iveh')
    coll = db.get_collection('games')

    # paths = [
    #     Path("./games/games-Oct-2-2008/HV-Dumbot-Loizz-2008-10-01-1716.sgf")
    # ]
    # for path in paths:
    #     doc = coll.find_one({'sgf_path': str(path)})
    for doc in coll.find():
        moves = doc['moves']
        # moves = [
        #     {
        #         'piece_moved': 'wG1',
        #         'destination': None,
        #         'player': PlayerW,
        #     },
        #     {
        #         'piece_moved': 'bG1',
        #         'destination': 'wG1-',
        #         'player': PlayerB,
        #     },
        #     {
        #         'piece_moved': 'wB1',
        #         'destination': '/wG1',
        #         'player': PlayerW,
        #     }
        # ]

        rr.RecordingStream('visualize_game', make_default=True)
        rr.connect_grpc()

        rr.log(f'axes_2d', rr.Arrows2D(origins=np.zeros((2, 2)), vectors=np.array([[1, 0], [0, 1]]),
                                       colors=[(255, 0, 0), (0, 255, 0)]))

        board_state = {
            # Keys are unique tile IDs (e.g. wB1)
            # Values are coordinates in HECS (https://en.wikipedia.org/wiki/Hexagonal_Efficient_Coordinate_System)
        }
        for move_idx, move in enumerate(moves):
            rr.set_time('move_idx', sequence=move_idx)
            # TODO: currently piece moved doesn't include color, but it needs to!
            piece = move['piece_moved']
            if piece is None or move['destination'] == 'pass':  # This is a 'pass'
                continue

            if 'b' not in piece and 'w' not in piece:
                piece = 'w' + piece

            if move_idx == 0:
                dest_hec = (0, 0, 0, 0)
            else:
                dest_str = move['destination']
                # find the piece we are reference and get its HECs
                ref_piece = re.search(r'[wb][QAGBSLMP]\d*', dest_str).group()
                ref_hec = board_state[ref_piece]
                dest_hec = resolve_move_hec(ref_hec, dest_str)

            dest_uvz = hec_to_uvz(dest_hec)

            color = (255, 255, 255) if move['player'] == PlayerW else (20, 20, 20)
            log_tile(dest_uvz, piece, color)
            board_state[piece] = dest_hec

            # time.sleep(4.0)


if __name__ == "__main__":
    main()
