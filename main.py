from pathlib import Path
import re

from tqdm import tqdm


# G1 = "G1"
# G2 = "G2"
# G3 = "G3"
#
# PIECES = [
#     G1, G2, G3,
#     B1, B2,
#     S1, S2
# ]

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
    return re.search('\[time', line)


def remove_extra_slashes(destination: str):
    return destination.replace("\\\\", "\\")


def load_sgf(path: Path):
    with path.open("r", encoding='latin-1') as f:
        lines = [l.strip("\n") for l in f.readlines()]

    # Skip header/footer lines
    for line in lines[11:-5]:
        if is_drop(line):
            if in_str('rack', line):
                # This means the tile was placed back in the rack, so that's not really a move
                continue
            match = re.search(r'Dropb (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse drop: {line}")
            w_move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(w_move)
        elif in_str('Move W', line):
            match = re.search(r'Move W (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(move)
        elif in_str('Move B', line):
            match = re.search(r'Move B (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            move = {
                'piece_moved': match.group(1),
                'destination': remove_extra_slashes(match.group(2)),
            }
            print(move)
        elif is_pass(line):
            move = {
                'piece_moved': None,
                'destination': None,
            }
        elif is_color_choice(line) or is_resign(line) or is_draw(line) or is_win_on_time(line) or is_pick(
                line) or in_str('rack', line) or in_str('done', line):
            continue
        elif line == ';' or is_time(line) or line == ')' or line == '(;':
            # These games seem to be split into multiple parts maybe? for now I'll just ignore them
            break
        else:
            raise ValueError(f"Could parse line {line}")


def get_sgf_paths(games_root=Path("games")):
    for path in games_root.iterdir():
        if path.is_dir():
            yield from get_sgf_paths(path)
        elif path.suffix == '.sgf':
            yield path
        else:
            print(f"Found {path.name} but it isn't .sgf so it will be ignored")


def main():
    for sgf_path in get_sgf_paths():
        print(load_sgf(sgf_path))


if __name__ == "__main__":
    main()
