"""
Bot Globals
~~~~~~~~~~~

We load our bot configuration file here.
"""

import json
import sys
import os


# We store our config values in a json file. If this file is missing, we generate a fresh one with default values.

if os.path.exists("Config.json"):
    with open("Config.json", "r") as configFile:
        config = json.load(configFile)
else:
    print("ERROR: Config file is missing. A new one will be generated for you. Please re-configure the bot then try again.")
    
    defaultConfig = {"userId": 0,
                     "token": "SETME",
                     "mongoServerString": "SETME",
                     "version": "v1.0.0",
                     "commandPrefix": "~",
                     "useMongoDb": True}
    
    # Default values, which will need to be changed before running the bot again.
    
    with open("Config.json", "w") as configFile:
        json.dump(defaultConfig, configFile, indent=4)

    sys.exit(1)


globals().update(config) # This stores all of our config values as variables.