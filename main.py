from pymongo import MongoClient
from pathlib import Path
import re

from tqdm import tqdm

from notation import PlayerB, PlayerW


def in_str(w: str, line: str):
    """ a case-insensitive 'in' """
    return w.lower() in line.lower()


def is_black_drop(line):
    if in_str('Drop B', line):
        return True
    if in_str('dropb', line):
        return True  # NOTE: this case not yet handled correctly in my regex
    return False


def is_pick(line):
    if any([
        in_str('Pick W', line),
        in_str('Pick B', line),
    ]):
        return True
    if any([
        in_str('pickw', line),
        in_str('pickb', line),
    ]):
        return True  # NOTE: regex
    return False


def is_resign(line):
    return in_str('resign', line)


def is_pass(line):
    return in_str('pass', line)


def is_draw(line):
    return in_str('draw', line)


def is_win_on_time(line):
    return in_str('WinOnTime', line)


def is_color_choice(line):
    return in_str("playwhite", line) or in_str("playblack", line)


def is_time(line):
    return '[time' in line


def remove_extra_slashes(destination: str):
    return destination.replace("\\\\", "\\")


def is_start(line):
    return in_str('start', line)


def skip_line(line):
    return any([
        is_start(line),
        is_color_choice(line),
        is_resign(line),
        is_draw(line),
        is_win_on_time(line),
        is_pick(line),
        in_str('rack', line),
        in_str('done', line),
        in_str('reset', line),
        in_str('edit', line),
        line == '; ',
        in_str('[id ', line),
        line == '',
    ])


def load_sgf(path: Path):
    with path.open("r", encoding='latin-1') as f:
        lines = [l.strip("\n") for l in f.readlines()]

    # Skip header/footer lines
    moves = []
    last_player = None
    start_found = False
    for line in lines[:-5]:
        if "Start" in line:
            start_found = True
            continue
        if not start_found:
            continue

        if is_black_drop(line):
            if in_str('rack', line):
                # This means the tile was placed back in the rack, so that's not really a move
                continue
            match = re.search(r'Dropb (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse drop: {line}")
            moves.append({
                'player': PlayerB,
                'piece_moved': f'b{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
            last_player = PlayerB
        elif in_str('Move W', line):
            match = re.search(r'Move W (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            moves.append({
                'player': PlayerW,
                'piece_moved': f'w{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
            last_player = PlayerW
        elif in_str('Move B', line):
            match = re.search(r'Move B (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            moves.append({
                'player': PlayerB,
                'piece_moved': f'b{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
            last_player = PlayerB
        elif is_pass(line):
            if last_player is None:
                raise ValueError(f"Who just passed? {last_player=}")
            next_player = PlayerW if last_player == PlayerB else PlayerB
            moves.append({
                'player': next_player,
                'piece_moved': None,
                'destination': 'pass',
            })
        elif skip_line(line):
            continue
        elif line == ';' or is_time(line) or line == ')' or line == '(;':
            # These games seem to be split into multiple parts maybe? for now I'll just ignore them
            break
        else:
            raise ValueError(f"Could parse line {line}")

    return moves


def get_sgf_paths(games_root=Path("games")):
    for path in games_root.iterdir():
        if path.is_dir():
            yield from get_sgf_paths(path)
        elif path.suffix == '.sgf':
            yield path
        else:
            print(f"Found {path.name} but it isn't .sgf so it will be ignored")

def mark_as_start_missing(coll):
    paths_start_not_found = []
    for sgf_path in tqdm(list(get_sgf_paths())):
        # Check whether all files contain the expected "Start" keyword
        with sgf_path.open("r", encoding='latin-1') as f:
            lines = [l.strip("\n") for l in f.readlines()]
        if len(lines) < 10:
            continue
        start_found = False
        for line in lines:
            if su_match := re.search(r"SU[(\w)]", line):
                su_value = su_match.group(1)
            if "Start" in line:
                start_found = True
                break
        if not start_found:
            paths_start_not_found.append(sgf_path)
    print(len(paths_start_not_found))
    for sgf_path in paths_start_not_found:
        coll.update_one({'sgf_path': str(sgf_path)},
                        {'$set': {'missing_start': True}})


def main():
    client = MongoClient()
    db = client.get_database('iveh')
    coll = db.get_collection('games')

    # sgf_path = Path("./games/games-Oct-2-2008/HV-Dumbot-Loizz-2008-10-01-1716.sgf")
    # moves = load_sgf(sgf_path)
    # ret = coll.update_one({'sgf_path': str(sgf_path)},
    #                 {'$set': {'moves': moves}})
    # print(ret)

    for sgf_path in tqdm(list(get_sgf_paths())):
        # Check if the game is already in our DB
        # if coll.count_documents({'sgf_path': str(sgf_path)}, limit=1) == 0:
        #     moves = load_sgf(sgf_path)
        #     coll.insert_one({
        #         'sgf_path': str(sgf_path),
        #         'moves': moves,
        #     })
        moves = load_sgf(sgf_path)
        coll.update_one({'sgf_path': str(sgf_path)},
                        {'$set': {'moves': moves}})



if __name__ == "__main__":
    main()
