"""
Utils
~~~~~

Utilities used throughout the bot, defined separately for ease of access.
"""

from datetime import datetime

class Log:

    # This class allows for us to output things to the console in a better format, including
    # the timestamp and where the log came from.


    def __init__(self, className:str) -> None:
        self.className = className


    def getTimestamp(self) -> str:
        # Return the current timestamp in a readable format, [hour:minute:second]
        return "[" + str(datetime.now().strftime("%H:%M:%S")) + "]"


    def print(self, string) -> None:
        # [hour:minute:second] className: output
        print(f"{self.getTimestamp()} {self.className}: {string}")


class EmbedColours:

    # Used for Discord Embeds, these are pre-defined colours for ease-of-access.

    positive = 0x57c782 # Green
    neutral = 0xFFFF55 # Yellow 
    negative = 0xFF5555 # Red
    info = 0x5555FF # Blurple
    error = 0xAA0000 # Dark Red