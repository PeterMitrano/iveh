from pymongo import MongoClient


def remove_dot_destinations_after_first_move(collection):
    cursor = collection.aggregate(
        [
            {
                "$project": {
                    "moves_tail": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$moves"}, 1]},
                            "then": {"$slice": [
                                "$moves",
                                1,
                                {"$size": "$moves"}
                            ]
                            },
                            "else": [],
                        }
                    },
                    "original_doc": '$$ROOT'
                }
            },
            {
                "$match": {
                    'moves_tail.destination': {
                        "$regex": '\\.'
                    }
                }
            }
        ],
    )
    ids_to_delete = [doc['_id'] for doc in cursor]

    # Remove everything in the resulting collection
    collection.delete_many({'_id': {"$in": ids_to_delete}})


def main():
    client = MongoClient()
    db = client.get_database('iveh')
    coll = db.get_collection('games')
    remove_dot_destinations_after_first_move(coll)


if __name__ == '__main__':
    main()
