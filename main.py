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

def load_sgf(path: Path):
    with path.open("r") as f:
        lines = [l.strip("\n") for l in f.readlines()]

    # Skip header/footer lines
    for line in lines[11:-5]:

        if 'Pick W' in line:
            continue
        if 'Pickb' in line:
            continue
        elif 'Dropb' in line:
            match = re.search(r'Dropb (\S+) \S+ \S+ (\S+?)]', line)
            if not match:
                raise ValueError(f"Failed to parse drop: {line}")
            w_move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(w_move)
        elif 'Done' in line:
            continue
        elif 'Move B' in line:
            match = re.search(r'Move B (\S+) \S+ \S+ (\S+?)]', line)
            if not match:
                raise ValueError(f"Failed to parse move: {line}")
            b_move = {
                'piece_moved': match.group(1),
                'destination': match.group(2),
            }
            print(b_move)
        else:
            raise ValueError(f"Could parse line {line}")





def main():
    print(load_sgf(Path("./games/HV-pmitrano-WeakBot-2025-06-06-0308.sgf")))



if __name__ == "__main__":
    main()
