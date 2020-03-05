from __future__ import print_function
import sys
import random
import app
import json
def compareActions(allMoves):
    print(allMoves["Adriatic_Sea"]["adjacencyList"], file=sys.stderr)
    return 0

def newGameState(players):
    with open('gameCache.json', 'r') as f:
        data = json.load(f)
    json_data = json.dumps(data)
    item_dict = json.loads(json_data)
    print(item_dict["Rome"]["isSupplyCenter"], file=sys.stderr)

    for value in players:
        #print(players[value]["country"], file=sys.stderr)
        if players[value]["country"] == "Italy":
            item_dict["Rome"]["player"] = players[value].get()
           # print(item_dict["Rome"]["player"], file=sys.stderr)
    return 0


def addPlayer(allMoves, userInfoCountry):
    # for value in len(allMoves):
    #     if allMoves[value]
    print("f")
