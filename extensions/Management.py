"""
Management
~~~~~~~~~~

This Extension can be used for administrative commands, but for now just contains the \"ping\" command.
"""

import Utils

import interactions

class Management(interactions.Extension):


    log = Utils.Log("Management") # Initialising our Log instance, just to make the console more readable.


    def __init__(self, client:interactions.Client) -> None:
        # We have nothing to do here, so just output that we're ready.
        self.log.print("Ready!")


    def drop(self) -> None:
        # This is called when the Extension is being dropped (unloaded).
        # If we need to do anything before unloading, we can do it here.

        # There's nothing we need to do for now, so we'll just log that we're unloading.
        self.log.print("Unloading.")
        super().drop()


    @interactions.slash_command(name="ping", description="Check latency.", default_member_permissions=interactions.Permissions.MANAGE_WEBHOOKS)
    async def ping(self, ctx: interactions.SlashContext) -> None:

        # This command is for server staff members to check the client latency.

        # We convert to ms for readability.
        latency = int(self.client.latency*1000)
        
        self.log.print(f"Server staff member requsted bot latecy. Latency: {latency} ms.")
        await ctx.send(f"Pong! Client latency: {latency} ms", ephemeral=True)