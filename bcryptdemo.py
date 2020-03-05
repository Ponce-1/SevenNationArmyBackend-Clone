import bcrypt
password = "super secret password"

hashed = bcrypt.hashpw(password, bcrypt.gensalt(14))
print(hashed)
if bcrypt.checkpw(password, hashed):
 print("It Matches!")
else:
 print("It Does not Match :(")