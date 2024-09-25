"""
Role Provider
~~~~~~~~~~~~~

This bot is designed to provide users roles to choose from in a selection list for each guild, configured by guild admins.\n
This a trial application for the Toontown: Event Horizon Bot Developer position.\n
Programmed by Samuel T. (discord: samuelt24), September 2024.\n
We create a Client instance here, as this is the main program file.
"""

import BotGlobals as config
import Utils

import interactions

import os
import traceback


class RPBotClient(interactions.Client):

    # Our main client instance, this is where we set things up.


    log = Utils.Log("RPBotClient") # Initialising our Log instance, just to make the console more readable.


    def __init__(self, command_prefix=None, intents=None) -> None:

        # Not much yet, just log that we're starting up, and pass the arguments to our super class.

        self.log.print("Starting...")
        super().__init__(command_prefix=command_prefix, intents=intents, application_id=config.userId)


    @interactions.listen()
    async def on_startup(self) -> None:

        # This function is only called once, we do all of our startup procedures here, including
        # changing our Activity and loading Extensions.

        self.log.print("Bot is ready to start setting up.")
        # We're setting up still, so we'll let users know in our Activity that we're unavailable.
        await self.change_presence(activity=interactions.Activity(name="Starting"), status=interactions.Status.DND)
        
        if not config.useMongoDb:
            self.log.print("WARNING: It's highly recommended to use MongoDB over YAML in a production environment.")
        
        self.log.print("Loading Extensions.")
        # Now, we load our Extensions, this checks the extentions folder and loads any python files as extensions.
        # This bot isn't multi-purpose, so there's only the RoleSelection and Management extensions, but this would
        # add anything you put into the folder, so the bot is easily expandable.
        for file in os.listdir(f"./extensions"):
            if file.endswith(".py"):
                try:
                    self.load_extension(f"extensions.{file[:-3]}")
                except interactions.client.errors.ExtensionLoadException:
                    # We'll just silently fail here for this specific Extension, and output the traceback to the console.
                    self.log.print(f"ERROR: Extension {file[:-3]} could not be loaded.")
                    print(traceback.format_exc())

        self.log.print("Finished loading Extensions.")


    @interactions.listen()
    async def on_ready(self) -> None:

        # Called whenever the bot is ready, either on startup OR after a reconnection, so this can
        # be called multiple times. We don't do much here, other than change our Activity to let
        # users know that the bot is available, and provide a log for the console.

        self.log.print("Bot has initialised.")
        await self.change_presence(activity=interactions.Activity(name=config.version), status=interactions.Status.ONLINE)


if __name__ == "__main__":
    # Check if this file is being run directly (not imported), then create our Client instance!
    roleSelectionBot = RPBotClient(command_prefix=config.commandPrefix, intents=interactions.Intents.DEFAULT)
    try:
        roleSelectionBot.start(config.token)
    except interactions.client.errors.LoginError:
        # Usually this should only happen if the bot hasn't been configured yet.
        print(f"There was an issue when using the configured token to log in. Please ensure the bot is properly configured.\n\nAttempted token: {config.token}")