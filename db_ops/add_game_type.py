from pymongo import MongoClient


def add_game_type(collection):
    special_pieces = {
        "ladybug": "L",
        "mosquito": "M",
        "pillbug": "P"
    }

    # Build the $set stage dynamically
    set_stage = {}
    for field, letter in special_pieces.items():
        set_stage[field] = {
            "$gt": [
                {
                    "$size": {
                        "$filter": {
                            "input": "$moves",
                            "as": "move",
                            "cond": {
                                "$regexMatch": {
                                    "input": "$$move.piece_moved",
                                    "regex": letter
                                }
                            }
                        }
                    }
                },
                0
            ]
        }

    # Execute the aggregation update
    collection.update_many(
        {},
        [
            {"$set": set_stage}
        ]
    )


def main():
    client = MongoClient()
    db = client.get_database('iveh')
    coll = db.get_collection('games')
    add_game_type(coll)


if __name__ == '__main__':
    main()
