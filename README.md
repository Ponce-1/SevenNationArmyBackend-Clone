# SevenNationArmyBackend
Flask-firebase backend for diplomacy game

### Authenticating Routes
Most routes cannot be accessed without a token. 

To get a token with this API (with Postman):
NOTE: this will be done on the client when it is implemented.
1. Open a POST /api/login tab. If you do not have an account on Firebase, use /api/register for a new account.
2. Go to body -> form data and fill in two fields for email and password
3. execute the request and you should get back a token.

To use a token, copy and paste it under Authorization -> basic auth -> username. Password can be left blank.
Currently, the token expires after 1 hour. 

### Routes
Like mentioned above, the routes use body -> form data to pass argument data to the routes. The only data you do not need to pass in
is the User ID because that is already in the token. All routes   

#### POST /api/createsession

Form data:
1. title
2. passcode
3. adjudicationPeriod


#### POST /api/joinsession

Form data:
1. sessionID
2. passcode

#### POST /api/startsession

1. Form data:
2. sessionID

#### POST /api/deletesession

Form data:
1. sessionID

#### POST /api/leavesession

Form data:
1. sessionID

