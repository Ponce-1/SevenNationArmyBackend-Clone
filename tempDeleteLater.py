import json
import random
#
# with open('gameCache.json', 'r') as f:
#     data = json.load(f)
#
# json_data = json.dumps(data)
# item_dict = json.loads(json_data)
# #print(item_dict["Adriatic_Sea"]["adjacencyList"][])
# print(len(item_dict["Adriatic_Sea"]["adjacencyList"]))
# print(item_dict["Adriatic_Sea"]["adjacencyList"])
# for value in item_dict:
#     print(item_dict[value]["spaceType"])
#     break
# print('---------------------------------------------------')
# for value in item_dict:
#     for x in range(len(item_dict[value]["adjacencyList"])):
#         print(item_dict[value]["adjacencyList"][x])
#     break
#
#
# list = random.sample(range(0,7), 7)
# for value in list:
#     print(value)

with open('countries.json', 'r') as c:
    countries = json.load(c)
countries_data = json.dumps(countries)
countries_dict = json.loads(countries_data)
data =[]
for value in countries_dict["France"]["unitLocations"]:
    # print(value)
    # print(countries_dict["France"]["unitLocations"][value])
    data.append(value)

print(data[1])
