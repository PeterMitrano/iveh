from pathlib import Path
import re

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


def load_sgf(path: Path):
    with path.open("r") as f:
        lines = [l.strip("\n") for l in f.readlines()]

    # Skip header/footer lines
    for line in lines[11:-5]:

        if in_str('Pick W', line):
            continue
        if in_str('Pickb', line):
            continue
        elif in_str('Dropb', line):
            match = re.search(r'Dropb (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse drop: {line}")
            w_move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(w_move)
        elif in_str('done', line):
            continue
        elif in_str('Move B', line):
            match = re.search(r'Move B (\S+) \S+ \S+ (\S+?)]', line, flags=re.IGNORECASE)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            b_move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(b_move)
        else:
            raise ValueError(f"Could parse line {line}")


def get_sgf_paths(games_root = Path("games")):
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
