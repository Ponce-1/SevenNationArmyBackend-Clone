from __future__ import print_function

from flask import Flask, redirect, url_for, g
from flask import request, abort, jsonify
import pyrebase
from firebase.config import config
from requests.exceptions import HTTPError
import os
from flask_httpauth import HTTPBasicAuth
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth as firebase_admin_auth
from firebase_admin import db as AdminDB
from SessionManager import SessionManager
import bcrypt
from flask_cors import CORS, cross_origin
import json
import logging
import sys
#import gameCache
import json
import compareHelper
import random


app = Flask(__name__)
cors = CORS(app, allow_headers=[
    "Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True)
# app.config['CORS_HEADERS'] = 'Content-Type'

#DO NOT USE! It does not have token authentication and admin access.
#this is the client version of firebase. this is just for testing purposes. We are only using this as an easy way of logging in and
#registering because that has not been implemented on the client yet.
firebase = pyrebase.initialize_app(config)
# db = firebase.database()

#not sure if needed
app.config.from_object(__name__)
app.secret_key = os.urandom(12)


#require login on routes
auth = HTTPBasicAuth()


#USE THIS DB.
#Set credentials to use firebase-admin
#Also set the db url
cred = credentials.Certificate("./cecs475-firebase-admin-credentials.json")
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://cecs475-b8e5c.firebaseio.com'})


#Manage sessions with sessionManager
sessionManager = SessionManager(AdminDB)
sessionManager.start()
#sessionManager.startSessionsFromDatabase()



@app.after_request
def after_request(response):
  response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5000'
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
  response.headers.add('Access-Control-Allow-Credentials', 'true')
  return response


'''~~~~~~~~~REGISTER/LOGIN ROUTES (For testing purposes only)~~~~~~~~~'''

#Testing purposes. Easy way to register a new account.
@app.route('/register', methods=['POST', "GET"])
def register():
    result = ""
    try:
        email = request.form['email']
        password = request.form['password']
        try:
            result = firebase.auth().create_user_with_email_and_password(email,password)
        except HTTPError:
            return jsonify({'result': False})
    except KeyError:
        return jsonify({'result': "incorrect form"})
    return jsonify({'result': result})


#for now just checks if provided token is valid on a route with auth_login_required decorator.
#NOTE: This is called whenever @auth.login_required is used as a decorator on a route.
@auth.verify_password
def verify_password(username_or_token, password):
    try:
        user = firebase_admin_auth.verify_id_token(username_or_token)
        if not user:
            return False
        g.user = user
        return True
    except:
        return False


#Just for testing purposes to allow easy login.
@app.route('/api/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            user =firebase.auth().sign_in_with_email_and_password(email, password)
            user = firebase.auth().refresh(user['refreshToken'])

            user_id = user['idToken']
            return jsonify({'result': user_id})
        except HTTPError:
            return jsonify({'result': False})
    return jsonify({'result': True})


'''~~~~~~~~~SESSION ROUTES~~~~~~~~~'''

#Create a new session with the game master as the only player. Also take the provided password and hash it for storage.
@app.route('/api/createsession', methods=["POST"])
@auth.login_required
def createSession():
    try:
        title = request.form["title"]
        gameMasterUserID = g.user['user_id']
        passcode = (str(request.form["passcode"])).encode('utf-8')
        adjudicationPeriod = request.form["adjudicationPeriod"]
    except:
        return jsonify({'data': 'Invalid data'})

    displayName = "unnamedUser"
    if 'name' in g.user:
        displayName = g.user['name']
    sessionManager.addSession(title, gameMasterUserID, displayName, passcode, adjudicationPeriod)


    return jsonify({'data': 'session created'})


#add a user to game session
@app.route('/api/joinsession', methods=["POST"])
@auth.login_required
def joinSession():
    userID = g.user['user_id']
    passcode = ""
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    try:
        passcode = request.form["passcode"]
    except:
        return jsonify({'data': 'missing passcode'})

    try:
        passcode = (str(request.form["passcode"])).encode('utf-8')
    except:
        return jsonify({'data': 'invalid passcode'})

    sessionsRef = AdminDB.reference('root/sessions/' + sessionID)
    sessionSnapshot = sessionsRef.get()
    hashedPasscode = ""
    try:
        hashedPasscode = sessionSnapshot['hashedPasscode'].encode('utf-8')
    except:
        return jsonify({'data': 'Error: this server does not have a passcode.'})

    if bcrypt.checkpw(passcode, hashedPasscode):
        displayName = "unnamedUser"
        if 'name' in g.user:
            displayName = g.user['name']
        addUserIDToSession(sessionID, userID, displayName)
    else:
        return jsonify({'data': 'Incorrect passcode'})

    return jsonify({'data': 'User added'})


#leave a session if user is not a game master
@app.route('/api/leavesession', methods=["POST"])
@auth.login_required
def leaveSession():
    userID = g.user['user_id']
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})


    if AdminDB.reference('root/sessions/' + sessionID).get() is None:
        return jsonify({'data': 'Session does not exist'})


    #do not allow the game master to leave the game session. if they want to quit playing, they must delete the session because they are the owner."
    if not checkUserIDIsGameMaster(sessionID, userID):
        removeUserIDFromSession(sessionID, userID)
    else:
        return jsonify({'data': 'User is a game master and cannot abandon a game.'})
    return jsonify({'data': 'User removed'})


#delete a session if user is a game master
@app.route('/api/deletesession', methods=["POST"])
@auth.login_required
def deleteSession():
    userID = g.user['user_id']
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    if AdminDB.reference('root/sessions/' + sessionID).get() is None:
        return jsonify({'data': 'Session does not exist'})

    #able to delete if game master
    if checkUserIDIsGameMaster(sessionID, userID):
        sessionManager.deleteSession(sessionID)
        return jsonify({'data': 'Session deleted'})
    else:
        return jsonify({'data': 'User is not gamemaster and cannot delete this session.'})


#start a session if user is a game master
@app.route('/api/startsession', methods=["POST"])
@auth.login_required
def startSession():
    userID = g.user['user_id']
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})

    if AdminDB.reference('root/sessions/' + sessionID).get() is None:
        return jsonify({'data': 'Session does not exist'})

    #able to start game if game master
    if checkUserIDIsGameMaster(sessionID, userID):
        # able to start game if there are 7 players
        if len(AdminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').get()) == 1:
            sessionManager.startSession(sessionID)
            return jsonify({'data': 'Session started'})
        else:
            return jsonify({'data': 'Failed to start game session'})
    else:
        return jsonify({'data': 'User is not gamemaster and cannot start this session.'})


#helper functions
def addUserIDToSession(sessionID, userID, displayName):
    AdminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').child(userID).set(True)
    AdminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs/'+ userID).child('displayName').set(displayName)

def removeUserIDFromSession(sessionID, userID):
    AdminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').child(userID).delete()

def checkUserIDIsGameMaster(sessionID, userID):
    sessionSnapshot = AdminDB.reference('root/sessions/' + sessionID)
    return userID == sessionSnapshot.get()['gameMasterUserID']

'''~~~~~~~~~Action ROUTES~~~~~~~~~'''

@app.route('/api/postaction', methods=["POST", "GET"])
@auth.login_required
def postAction():
    #recieves info from python as a a joson
    content = request.get_json(force=True)
    #makes it easy parse as a json
    json_data = json.dumps(content)
    #turns it into a dictionary
    item_dict = json.loads(json_data)
    userID = g.user['user_id']
    sessionID = content['sessionID']
    userInfo = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs/'+userID+'/action')
    userInfo.delete()
    item_dict.pop('sessionID')
    #userInfo.set(item_dict)
    for value in item_dict:
        if value =="sessionID":
            continue
        AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs/'+userID+'/action/'+value).set({
            'unitOrigin': item_dict[value][0]['unitOrigin'],
            'unitDest': item_dict[value][1]['unitDest'],
            'secondaryUnit': item_dict[value][2]['secondaryUnit'],
            'actionType': item_dict[value][3]['actionType']
        })
    return jsonify({'data': 'Action Posted!'})

@app.route('/api/getaction', methods=["Get"])
@auth.login_required
def getAction():
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    userID = request.form["userID"]
    actions = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs/'+userID).get()
    print(actions, file=sys.stderr)
    # content = boardState.get()
    # json_data = json.dumps(content)
    # item_dict = json.loads(json_data)
    return jsonify({'data': 'Action Posted!'})

# @app.route('/api/postgamestate', methods=["Post"])
# @auth.login_required
# def postGameState():
#     sessionID = request.form["sessionID"]
#     boardState = AdminDB.reference('root/sessions/'+sessionID+'/boardState')
#     boardState.delete()
#     with open('gameCache.json', 'r') as f:
#         data = json.load(f)
#     json_data = json.dumps(data)
#     item_dict = json.loads(json_data)
#     boardState.set(item_dict)
#     return jsonify({'data': 'Action Posted!'})

@app.route('/api/getgamestate', methods=["Get"])
@auth.login_required
def getGameState():
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    boardState = AdminDB.reference('root/sessions/'+sessionID+'/boardState')
    content = boardState.get()
    json_data = json.dumps(content)
    item_dict = json.loads(json_data)

    return json_data

#assigns a random country to every player
@app.route('/api/assigncountries', methods=["Post"])
@auth.login_required
def assignCountries():
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    players = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs').get()
    counrtyList = random.sample(range(0,7), 7)
    assign = {
        counrtyList[0]: "London",
        counrtyList[1]: "Germany",
        counrtyList[2]: "Russia",
        counrtyList[3]: "Turkey",
        counrtyList[4]: "Austria-Hungary",
        counrtyList[5]: "Italy",
        counrtyList[6]: "France"
    }
    iter = 0
    for key, value in players.iteritems():
        playerPath = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs'+'/'+key+'/country')
        playerPath.set(assign.get(iter))
        iter+=1
    return jsonify({'data': 'Action Posted!'})

#Post a clean game state for the start of a new game
@app.route('/api/newgamestate', methods=["Post"])
@auth.login_required
def newGameState():
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    boardStatePath = AdminDB.reference('root/sessions/'+sessionID+'/boardState')
    boardState = AdminDB.reference('root/sessions/'+sessionID+'/boardState').get()

    players = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs').get()
    boardStatePath.delete()
    with open('gameCache.json', 'r') as f:
        data = json.load(f)
    json_data = json.dumps(data)
    item_dict = json.loads(json_data)
    with open('countries.json', 'r') as c:
        countries = json.load(c)
    countries_data = json.dumps(countries)
    countries_dict = json.loads(countries_data)
    boardStatePath.set(item_dict)
    #for updateJsonPlayer in boardState:
    for key, value in players.iteritems():
        playerCountry = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs'+'/'+key+'/country').get()
        if playerCountry == "France":
            for value in countries_dict["France"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["France"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "Germany":
            for value in countries_dict["Germany"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["Germany"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "Russia":
            for value in countries_dict["Russia"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["Russia"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "England":
            for value in countries_dict["England"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["England"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "Turkey":
           for value in countries_dict["Turkey"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["Turkey"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "Austria-Hungary":
            for value in countries_dict["Austria"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["Austria"]["unitLocations"][value],
                    "unitPower" : 1
                })
        if playerCountry == "Italy":
            for value in countries_dict["Italy"]["unitLocations"]:
                boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+value)
                boardStatePath.update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": countries_dict["Italy"]["unitLocations"][value],
                    "unitPower" : 1
                })
    return jsonify({'data': 'Action Posted!'})

# #FOR ADJUDECATION adjusts game state based on transactions
# @app.route('/api/adjustgamestateplayers', methods=["Post"])
# @auth.login_required
# def adjustGameStatePlayers():
#     try:
#         sessionID = request.form["sessionID"]
#     except:
#         return jsonify({'data': 'Missing sessionID'})
#     userID = g.user['user_id']
#     players = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs').get()
#     userInfoActions = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs').child(userID+'/action').get()
#     #userInfo.push()
#     item_dict =getGameState()
#     compareHelper.addPlayer(item_dict,userInfoCountry )
#     print(userInfoActions['actionList1'], file=sys.stderr)
#     return jsonify({'data': 'Action Posted!'})


@app.route('/api/compareactions', methods=["Post"])
@auth.login_required
def compareActions():
    try:
        sessionID = request.form["sessionID"]
    except:
        return jsonify({'data': 'Missing sessionID'})
    boardState =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/').get()
    # for value in boardState:
    #     print(value, file=sys.stderr)
    #boardState = AdminDB.reference('root/sessions/'+sessionID+'/boardState')
    # content = boardState.get()
    # json_data = json.dumps(content)
    # item_dict = json.loads(json_data)
    # compareHelper.compareActions(item_dict)
    #boardState.set(item_dict)
    players = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs').get()
    round = 0
    for key, value in players.items():
        playerCountry = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs'+'/'+key+'/country').get()
        #print(key, file=sys.stderr)
        userInfoActions = AdminDB.reference('root/sessions/'+sessionID+'/participatingUserIDs/'+key+'/action').get()
        for currentCountry in userInfoActions:
            #print(userInfoActions[value]["unitDest"], file=sys.stderr)
            if (userInfoActions[currentCountry]["actionType"]==0):
                filter
                #print(userInfoActions[value]["unitDest"], file=sys.stderr)
            if (userInfoActions[currentCountry]["actionType"]==1):
                for key2, value2 in players.items():
                    checkUserInfoActions = AdminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs/' + key2 + '/action').get()
                    for checkAction in checkUserInfoActions:
                        #Enter to compare your current user's actions to another if they are going to the same location
                        if(userInfoActions[currentCountry]["unitDest"] == checkUserInfoActions[checkAction]["unitDest"]) and (userInfoActions[currentCountry]["unitOrigin"] != checkUserInfoActions[checkAction]["unitOrigin"]):
                            #print(boardState[userInfoActions[currentCountry]["unitOrigin"]]["unitPower"], file=sys.stderr)
                            if(boardState[userInfoActions[currentCountry]["unitOrigin"]]["unitPower"] > boardState[checkUserInfoActions[checkAction]["unitOrigin"]]["unitPower"]):
                                 # AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+currentCountry).update({
                                 #     "country": playerCountry,
                                 #     "player": key,
                                 #     "unit" : "f",
                                 #    "unitpower": "f"
                                 # })
                                 #continue
                                 print('f')
                            elif(boardState[userInfoActions[currentCountry]["unitOrigin"]]["unitPower"] == boardState[checkUserInfoActions[checkAction]["unitOrigin"]]["unitPower"]):
                                # AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+currentCountry).update({
                                #     "country": playerCountry,
                                #     "player" : key,
                                #     "unit": countries_dict["Italy"]["unitLocations"][value],
                                #     "unitPower" : 1
                                # })
                                print("draw", file =sys.stderr)
                        #enter here to check if the current unit is going to a tile where another unit they own is located
                        if(userInfoActions[currentCountry]["unitDest"] == checkUserInfoActions[checkAction]["unitOrigin"] and checkUserInfoActions[checkAction]["actionType"]!=1):
                            print("unit already there!")
                        #enter here if there are no obstacles and user can make a successful move
                #print(userInfoActions[currentCountry]["unitOrigin"], file=sys.stderr)
                AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+userInfoActions[currentCountry]["unitDest"]).update({
                    "country": playerCountry,
                    "player" : key,
                    "unit": boardState[userInfoActions[currentCountry]["unitOrigin"]]["unit"],
                    "unitPower" : 1
                })
                AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+userInfoActions[currentCountry]["unitOrigin"]).update({
                    "country": "",
                    "player" : "",
                    "unit": "",
                    "unitPower" : 0
                })
            if userInfoActions[currentCountry]["actionType"]==2:
                print("2", file =sys.stderr)

                #print(userInfoActions[value]["unitDest"], file=sys.stderr)
            if (userInfoActions[currentCountry]["actionType"]==3):
                print("3", file =sys.stderr)

                #print(userInfoActions[value]["unitDest"], file=sys.stderr)
            # for country in boardState:
            #     if userInfoActions[value]["unitDest"] == country:
            #         #0 = hold, 1 = move, 2 = support, 3 = convoy
            #         if userInfoActions[value]["unitDest"]
            #         addToPower = boardState[country]["unitPower"] +1
            #         boardState[country]["unitPower"] = addToPower
            #         print(boardState[country]["unitPower"], file=sys.stderr)

                    # boardStatePath =  AdminDB.reference('root/sessions/'+sessionID+'/boardState/'+country)
                    # #ddToPower = boardStatePath["unitPower"] +1
                    # boardStatePath.update({
                    #     "unitPower": 0
                    # })
                    # print(boardState[country]["unitPower"], file=sys.stderr)
    finalUpdate = AdminDB.reference('root/sessions/'+sessionID+'/boardState')
    # finalUpdate.delete()
    # finalUpdate.push(boardState)
    return jsonify({'data': 'Action Posted!'})

if __name__=='__main___':
    app.run(debug=True)
