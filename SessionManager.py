import schedule
import time
import threading
import bcrypt
# from territories import territories
import random
import datetime
import json

class SessionManager:
    def __init__(self, adminDB):
        self.adminDB = adminDB


    #add a session entry to database. It will just sit in the database, not running.
    def addSession(self, title, gameMasterUserID, displayName, passcode, adjudicationPeriod):
        hashedPasscode = bcrypt.hashpw(passcode, bcrypt.gensalt(14)).decode("utf-8")
        sessionsRef = self.adminDB.reference('root/sessions')
        sessionID = sessionsRef.push({
            'title': title,
            'gameMasterUserID': gameMasterUserID,
            'hashedPasscode': hashedPasscode,
            'adjudicationPeriod': adjudicationPeriod,
            'running': False
        }).key
        self.adminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').child(gameMasterUserID).set(True)
        self.adminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs/' + gameMasterUserID).child('displayName').set(
            displayName)


        return True

    #delete a session from the database. If the session is currently running, end it.
    def deleteSession(self, sessionID):
        self.endSession(sessionID)
        self.adminDB.reference('root/sessions/' + sessionID).delete()
        return True

    #start a session by adding it to the scheduler and initializing the session with gameboard featuring territories and units.
    def startSession(self, sessionID):
        sessionSnapshot = self.adminDB.reference('root/sessions/' + sessionID)
        adjudicationPeriod = sessionSnapshot.get()['adjudicationPeriod']

        self.adminDB.reference('root/sessions/' + sessionID).child('running').set(True)
        #testing use seconds
        # schedule.every(int(adjudicationPeriod)).seconds.do(self.adjudicate, sessionID=sessionID).tag(sessionID)
        #for deployment use minutes
        schedule.every(int(adjudicationPeriod)).minutes.do(self.adjudicate, sessionID=sessionID).tag(sessionID)

        #add map/GameBoard to session
        players = self.adminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').get()
        countryList = random.sample(range(0, 7), 7)
        assign = {
            countryList[0]: "London",
            countryList[1]: "Germany",
            countryList[2]: "Russia",
            countryList[3]: "Turkey",
            countryList[4]: "Austria-Hungary",
            countryList[5]: "Italy",
            countryList[6]: "France"
        }
        iter = 0
        for key, value in players.items():
            playerPath = self.adminDB.reference(
                'root/sessions/' + sessionID + '/participatingUserIDs' + '/' + key + '/country')
            playerPath.set(assign.get(iter))
            iter += 1

        boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState')
        boardState = self.adminDB.reference('root/sessions/' + sessionID + '/boardState').get()

        players = self.adminDB.reference('root/sessions/' + sessionID + '/participatingUserIDs').get()
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
        # for updateJsonPlayer in boardState:
        for key, value in players.items():
            playerCountry = self.adminDB.reference(
                'root/sessions/' + sessionID + '/participatingUserIDs' + '/' + key + '/country').get()
            if playerCountry == "France":
                for value in countries_dict["France"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["France"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "Germany":
                for value in countries_dict["Germany"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["Germany"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "Russia":
                for value in countries_dict["Russia"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["Russia"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "England":
                for value in countries_dict["England"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["England"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "Turkey":
                for value in countries_dict["Turkey"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["Turkey"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "Austria-Hungary":
                for value in countries_dict["Austria"]["unitLocations"]:
                    boardStatePath = self.self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["Austria"]["unitLocations"][value],
                        "unitPower": 1
                    })
            if playerCountry == "Italy":
                for value in countries_dict["Italy"]["unitLocations"]:
                    boardStatePath = self.adminDB.reference('root/sessions/' + sessionID + '/boardState/' + value)
                    boardStatePath.update({
                        "country": playerCountry,
                        "player": key,
                        "unit": countries_dict["Italy"]["unitLocations"][value],
                        "unitPower": 1
                    })

        #declare next adjudication time.
        self.declareNextAdjudicationTime(sessionID)

        sessionSnapshot.child("phase").set("spring order")







    #remove the session from the scheduler so it doesn't keep adjudicating.
    def endSession(self, sessionID):
        self.adminDB.reference('root/sessions/' + sessionID).child('running').set(False)
        schedule.clear(sessionID)

    #sets the next time the session will adjudicate so users can know when is the next adjudication period.
    def declareNextAdjudicationTime(self, sessionID):
        sessionSnapshot = self.adminDB.reference('root/sessions/' + sessionID)

        #Add the adjudication period to the current time to get the next time the Session will adjudicate
        nextAdjudicationTime = datetime.datetime.now() + datetime.timedelta(minutes=int(sessionSnapshot.get()['adjudicationPeriod']))
        timeString = '%s/%s/%s/ %s:%s:%s' % (nextAdjudicationTime.month, nextAdjudicationTime.day, nextAdjudicationTime.year, nextAdjudicationTime.hour, nextAdjudicationTime.minute, nextAdjudicationTime.second)
        sessionSnapshot.child('nextAdjudicationTime').set(timeString)

    #add all session entries with the running flag set to true to the scheduler
    def startSessionsFromDatabase(self):
        sessionsRef = self.adminDB.reference('root/sessions/')
        sessions = sessionsRef.get()
        for sessionID in sessions:
            session = sessions[sessionID]
            adjudicationPeriod = ""
            runningFlag = False

            if "running" in session:
                runningFlag = session["running"]
            else:
                continue

            if "adjudicationPeriod" in session:
                adjudicationPeriod = session["adjudicationPeriod"]
            else:
                continue

            if session["running"] == True:
                schedule.every(int(adjudicationPeriod)).seconds.do(self.adjudicate, sessionID=sessionID).tag(sessionID)
                self.declareNextAdjudicationTime(sessionID)



    def adjudicator_ThreadFunction(self, name):
        while True:
            schedule.run_pending()
            time.sleep(1)

    #Process actions, switch to next season, update map accordingly.
    def adjudicate(self, sessionID):
        print("Adjudicating on session:" + sessionID)
        #TODO: Process actions in the session and move units accordingly.

        #TODO: Switch to next season

        #declare next adjudication phase.

        self.declareNextAdjudicationTime(sessionID)


    def getNextPhase(self, phase):
        phases = ["spring order", "spring retreat", "fall order","fall retreat", "winter"]

        for i in range(0, len(phases)):
            if phases[i] == phase:
                if i+1 > len(phases)-1:
                    return phases[i+1]
                else:
                    return phases[0]
        return 'Error phase'



    def start(self):
        adjudicatorThread = threading.Thread(target=self.adjudicator_ThreadFunction, args=(1,))
        adjudicatorThread.daemon = True
        adjudicatorThread.start()

