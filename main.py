from pymongo import MongoClient
from pathlib import Path
import re

from tqdm import tqdm

from notation import PlayerB, PlayerW, PLAYERS


def in_str(w: str, line: str):
    """ a case-insensitive 'in' """
    return w.lower() in line.lower()


def is_drop(line):
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
        in_str('rack', line),
        in_str('done', line),
        in_str('reset', line),
        in_str('edit', line),
        line == '; ',
        in_str('[id ', line),
        line == '',
    ])


def other_player(player):
    return PlayerW if player == PlayerB else PlayerB


def load_sgf(path: Path):
    with path.open("r", encoding='latin-1') as f:
        lines = [l.strip("\n") for l in f.readlines()]

    # Skip header/footer lines
    player_id_to_player_color = [
        None,
        None
    ]
    moves = []
    start_found = False
    for line in lines[:-5]:
        if "Start" in line:
            start_found = True
            continue
        if not start_found:
            continue

        if is_drop(line):
            if in_str('rack', line):
                # This means the tile was placed back in the rack, so that's not really a move
                continue
            match = re.search(r'dropb (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse drop: {line}")
            m = re.search(r'; P(\d)', line)
            player_id = int(m.group(1))
            player = player_id_to_player_color[player_id]
            if player is None:
                raise RuntimeError("Player is none!")
            moves.append({
                'player': player,
                'piece_moved': f'{player}{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
        elif in_str('Move W', line):
            match = re.search(r'Move W (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            moves.append({
                'player': PlayerW,
                'piece_moved': f'w{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
        elif in_str('Move B', line):
            match = re.search(r'Move B (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            moves.append({
                'player': PlayerB,
                'piece_moved': f'b{match.group(1)}',
                'destination': remove_extra_slashes(match.group(2)),
            })
        elif is_pass(line):
            m = re.search(r'P(\d)', line)
            player_id = int(m.group(1))
            player = player_id_to_player_color[player_id]
            if player is None:
                raise RuntimeError("Player is none!")
            moves.append({
                'player': player,
                'piece_moved': None,
                'destination': 'pass',
            })
        elif is_pick(line):
            m = re.search(r'P(\d)\[\d+ pick(\S*) (\S+) \S+ (\S+)', line, flags=re.IGNORECASE)
            if m is None:
                raise ValueError(f"Failed to parse line: {line}")
            player_id = int(m.group(1))
            if player_id_to_player_color[player_id] is None:
                if m.group(2).lower() in PLAYERS:
                    inferred_player_color = m.group(2).lower()
                elif m.group(3).lower() in PLAYERS:
                    inferred_player_color = m.group(3).lower()
                elif m.group(4)[0].lower() in PLAYERS:
                    inferred_player_color = m.group(4)[0].lower()
                else:
                    raise ValueError(f"Failed to parse line: {line}")
                player_id_to_player_color[player_id] = inferred_player_color

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

    sgf_path = Path("games/games-Feb-23-2012/U!HV-guest-Dumbot-2012-02-22-1926.sgf")
    moves = load_sgf(sgf_path)
    ret = coll.update_one({'sgf_path': str(sgf_path)},
                    {'$set': {'moves': moves}})
    print(ret)
    return

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
