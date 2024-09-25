"""
Role Selection
~~~~~~~~~~~~~~

This Extension entirely handles role selection for users, and administrative commands to manage it.
"""

import BotGlobals as config
import Utils

import interactions

if config.useMongoDb:
    import pymongo
else:
    import yaml

import os
import traceback


class RoleButton(interactions.Button):

    # This button has a set style and label, so we only ask for a customId, which we generate in our RoleSelection class.

    # In our callback (see RoleSelection:handleInteraction), we generate customised RoleList instances for users to select a role.
    
    
    def __init__(self, customId:str) -> None:
        super().__init__(style=interactions.ButtonStyle.BLURPLE, label="Get roles...", custom_id=customId)


class RoleList(interactions.StringSelectMenu):

    # This list is tailored for each user so that the previously selected role(s) are already pre-selected (done in the RoleButton callback)

    # In our callback (see RoleSelection:handleInteraction), we check the selected values against what isn't selected, and update the user's roles
    # accordingly.
    
    def __init__(self, options:list[interactions.StringSelectOption], customId:str, pageNumber:int, totalPages:int) -> None:

        # Items in options list must be interactions.StringSelectOption instances.

        super().__init__(options, placeholder=f"Select a role (Page {pageNumber} of {totalPages})", min_values=0, max_values=1, custom_id=customId)


class RoleSelection(interactions.Extension):


    log = Utils.Log("RoleSelection") # Initialising our Log instance, just to make the console more readable.


    def __init__(self, client:interactions.Client) -> None:

        # Create our dict, all of our guildIds are the keys, then the values are their respective database in dict format.
        self.guildId2Db = self.loadDatabaseItems()

        self.log.print("Ready!")


    def drop(self) -> None:
        # This is called when the Extension is being dropped (unloaded).
        # If we need to do anything before unloading, we can do it here.

        # There's nothing we need to do for now, so we'll just log that we're unloading.
        self.log.print("Unloading.")
        super().drop()


    def loadDatabaseItems(self) -> dict:
        # Here, we load our database items, whether that be from our mongo database or YAML database.
        # This is a separate function from __init__() as we may need to call this again later.

        self.log.print("Loading database items.")


        guildId2Db = {}
        if config.useMongoDb:
            self.mongoClient = pymongo.MongoClient(config.mongoServerString)
            for guild in self.client.guilds:
                # Load the mongo database for every guild that we're in.
                guildRawDb = self.mongoClient[str(guild.id)]
                guildDbCollectionNames = guildRawDb.list_collection_names()
                guildId2Db[guild.id] = {}
                
                for collectionName in guildDbCollectionNames:
                    guildCollection = guildRawDb[collectionName]
                    # Mongo makes this a little more complicated, we need to generate dicts for every document within every collection to generate our
                    # dict for our guildId2Db dict. We do this so that our mongo and yaml db have parity.
                    guildCollectionDocuments = list(guildCollection.find())
                    guildId2Db[guild.id][collectionName] = {str(document["_id"]): {k: v for k, v in document.items() if k != "_id"} for document in guildCollectionDocuments}


        else:
            for guild in self.client.guilds:
                guildId2Db[guild.id] = {}
                # This is fine, if the file doesn't exist, it'll be replaced by the default values later in this function anyway.
                if os.path.exists(f"./databases/{guild.id}.yaml"):
                    with open(f"./databases/{guild.id}.yaml", "r") as guildDb:
                        # YAML is simpler, just load the DB file for each guild we're in, or set to an empty dict if it can't be loaded.
                        guildId2Db[guild.id] = yaml.safe_load(guildDb) or {}


        # Checking for missing keys and putting default values in their place
        # If other DB values are added in the future, this'll need to be modified.
        channels = guildId2Db[guild.id].get("Channels", {})
        rolesChannel = channels.get("RolesChannel", {})
        if "ChannelID" not in rolesChannel:
            rolesChannel["ChannelID"] = "0"
        channels["RolesChannel"] = rolesChannel
        guildId2Db[guild.id]["Channels"] = channels
        roles = guildId2Db[guild.id].get("Roles", {})
        roleSelectionList = roles.get("RoleSelectionList", {})
        if "PublicList" not in roleSelectionList:
            roleSelectionList["PublicList"] = []
        roles["RoleSelectionList"] = roleSelectionList
        guildId2Db[guild.id]["Roles"] = roles

        
        return guildId2Db
    
    
    def getUniqueId(self, guildId:int, number:int) -> str:

        # This is utilised so that every button and selection list can have a unique identifier.

        return f"roleSelection-{guildId}-{number}"
    

    def refreshRoleSelectionDatabase(self, guildId:int) -> None:
        # We need to do this a lot, so updating the role selection list in the database has its own function here.
        # We just take a guildId argument in order to update the correct database with our current dict.

        if config.useMongoDb:
            # We must represent any Discord snowflakes as a string for compatability with a YAML database where needed.
            roles = self.mongoClient[str(guildId)]["Roles"]
            roles.update_one({"_id": "RoleSelectionList"}, {"$set": {"PublicList": self.guildId2Db[guildId]["Roles"]["RoleSelectionList"]["PublicList"]}}, upsert=True)
        else:
            if not os.path.exists("./databases"):
                os.makedirs("./databases")
            with open(f"./databases/{guildId}.yaml", "w") as guildDb:
                yaml.safe_dump(self.guildId2Db[guildId], guildDb)

    

    @interactions.listen(interactions.api.events.Component)
    async def handleInteraction(self, event: interactions.api.events.Component) -> None:

        # Here, we have our callback for our buttons and selection lists.

        # First, we check if it's an interaction for roleSelection, otherwise we ignore it.
        # Since this function would pick up every interaction otherwise.
        if event.ctx.custom_id.startswith("roleSelection"):

            if event.ctx.component_type == interactions.ComponentType.BUTTON:
                # It's a button, so we generate custom selection list(s) for the user to select roles and reply with them.

                roleObjects = []
                index = 0
                # First, check all of the roles still exist, if not, remove them from both our list and the database.
                for roleId in self.guildId2Db[event.ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"]:
                    role = event.ctx.guild.get_role(roleId)
                    if role:
                        # It exists, so add it to our array of Role objects.
                        roleObjects.append(role)
                    else:
                        # It doesn't exist, so remove it from our dict and database.
                        self.guildId2Db[event.ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"].pop(index)
                        self.refreshRoleSelectionDatabase(event.ctx.guild.id)
                    index += 1

                if len(roleObjects) < 1:
                    # Either no roles have been added yet, or they were deleted, we'll tell the user that and return.
                    await event.ctx.send("There are currently no roles available.", ephemeral=True)
                    return
                

                selectionLists = []
                options = [[]]# A list of lists of StringSelectOptions for each selection list.
                index = 0
                listNumber = 0
                for role in roleObjects:
                    # The label arg is what the user sees (we make this the role name),
                    # the value arg is what's sent back to us when they select it (we make this the role ID).
                    # The default arg is a bool as to whether it's pre-selected or not.
                    # We pre-select any roles the user has already obtained to make it tailored to them.
                    # Otherwise, selection lists may be a little confusing for users to use.
                    options[listNumber].append(interactions.StringSelectOption(label=role.name, value=str(role.id), default=event.ctx.member.has_role(role)))
                    index += 1
                    if index % 25 == 0:
                        # We have to split the roles into multiple selection lists if there's too many, as Discord has a limit per list.
                        listNumber += 1
                        options.append([])
                
                index = 1 # This is intentional. Our button is 0!
                for optionList in options:
                    # Now to create all of our RoleList instances and add them to the selectionLists list.
                    # We have each of these in their own ActionRow instance to allow for multiple RoleLists in our response.
                    if len(optionList) > 0:
                        selectionLists.append(interactions.ActionRow(RoleList(optionList, self.getUniqueId(event.ctx.guild.id, index), index, len(options))))
                        index += 1

                # And finally, send them all to the user!
                await event.ctx.send(components=selectionLists, ephemeral=True)

            elif event.ctx.component_type == interactions.ComponentType.STRING_SELECT:
                 # It's a string selection list, so we check what's selected/unselected vs the user's current roles and update them accordingly.

                roleObjects = []
                
                for option in event.ctx.component.options:
                    role = event.ctx.guild.get_role(int(option.value))
                    if role:
                        roleObjects.append(role)
                    else:
                        await event.ctx.send("The list of available roles has changed. Please press \"Get roles...\" again for the updated list.", ephemeral=True)
                        return
                    

                # Now, we give the user the roles, and generate a user friendly response listing what roles were added or removed.
                responseText = ""
                addedRoleNames = ""
                removedRoleNames = ""
                # I've (mostly) done this in a way so that, if it ever was needed for multiple roles to be selected in the future, it can be handled fine
                for role in roleObjects:
                    if str(role.id) not in event.ctx.values:
                        if event.ctx.member.has_role(role):
                            # If they have the role, get rid of it.
                            await event.ctx.member.remove_role(role)
                            self.log.print(
                                f"Removed user \"{event.ctx.user.global_name}\" (User ID: {event.ctx.user.id}) from the \"{role.name}\" role (Role ID: {role.id}) in guild \"{event.ctx.guild.name}\" (Guild ID: {event.ctx.guild.id})"
                                )
                            removedRoleNames += f"    • {role.name}\n" # Add to our user-friendly list of removed roles.
                    else:
                        if not event.ctx.member.has_role(role):
                            # If they don't have the role, add it.
                            await event.ctx.member.add_role(role)
                            self.log.print(
                                f"Gave user \"{event.ctx.user.global_name}\" (User ID: {event.ctx.user.id}) the \"{role.name}\" role (Role ID: {role.id}) in guild \"{event.ctx.guild.name}\" (Guild ID: {event.ctx.guild.id})"
                                )
                            addedRoleNames += f"    • {role.name}\n" # Add to our user-friendly list of added roles.

                            # Change this part if you want multiple roles to be selected (and change the max selection on the RoleList class)
                            # This checks EVERY role that the user can select, even from other selection lists, to ensure they can only have
                            # one at a time, as outlined in the brief.
                            for roleId in self.guildId2Db[event.ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"]:
                                otherRole = event.ctx.guild.get_role(int(roleId))
                                if otherRole != role:
                                    if event.ctx.member.has_role(otherRole):
                                        # If they have the role, get rid of it.
                                        await event.ctx.member.remove_role(otherRole)
                                        self.log.print(
                                            f"Removed user \"{event.ctx.user.global_name}\" (User ID: {event.ctx.user.id}) from the \"{role.name}\" role (Role ID: {role.id}) in guild \"{event.ctx.guild.name}\" (Guild ID: {event.ctx.guild.id})"
                                            )
                                        removedRoleNames += f"    • {otherRole.name}\n" # Add to our user-friendly list of removed roles.

                if len(removedRoleNames) == 0 and len(addedRoleNames) == 0:
                    # No changes to the user's roles.
                    responseText = "No role changes have been made."
                else:
                    if len(removedRoleNames) > 0:
                        # One or more roles were removed from the user as part of this interaction.
                        responseText += "**Removed the following roles:**\n"
                        responseText += removedRoleNames
                    if len(addedRoleNames) > 0:
                        # One or more roles were added to the user as part of this interaction.
                        responseText += "\n\n**Added the following roles:**\n"
                        responseText += addedRoleNames

                # And finally, send our user friendly response text!
                await event.ctx.send(responseText, ephemeral=True)
                

            else:
                self.log.print(f"Ignoring interaction from invalid roleSelection component: {event.ctx.custom_id}")


    @interactions.slash_command(name="setroleschannel", description="Specify a roles selection channel.", 
                                options=[{"name": "channel",
                                          "description": "The channel to send the role selection list to.",
                                          "type": interactions.OptionType.CHANNEL,
                                          "required": True},],
                                default_member_permissions=interactions.Permissions.MANAGE_WEBHOOKS)
    async def setRolesChannel(self, ctx: interactions.SlashContext, channel:interactions.models.discord.channel.GuildChannel) -> None:
        # This is for server staff members to set the channel in which the "Get roles..." button will be sent to.
        await ctx.send(embed=interactions.Embed(title="Please wait", description="Saving your changes...", color=Utils.EmbedColours.neutral), ephemeral=True)

        # We must represent any Discord snowflakes as a string for compatability with a YAML database where needed.
        self.guildId2Db[ctx.guild.id]["Channels"]["RolesChannel"]["ChannelID"] = str(channel.id)
        try:
            # Updating our mongo or yaml DB with our updated dict.
            # This is the only place that does this, so I haven't made updating this part of the database a separate function.
            if config.useMongoDb:
                channels = self.mongoClient[str(ctx.guild.id)]["Channels"]
                channels.update_one({"_id": "RolesChannel"}, {"$set": {"ChannelID": str(channel.id)}}, upsert=True)
            else:
                if not os.path.exists("./databases"):
                    os.makedirs("./databases")
                with open(f"./databases/{ctx.guild.id}.yaml", "w") as guildDb:
                     yaml.safe_dump(self.guildId2Db[ctx.guild.id], guildDb)

            # Everything worked, set the success embed.
            responseEmbed = interactions.Embed(title="Success", description=f"Roles channel set to <#{channel.id}> successfully.", color=Utils.EmbedColours.positive)
            self.log.print(f"Roles channel in guild \"{ctx.guild.name}\" (ID: {ctx.guild.id}) successfully set to #{channel.name}")
        except:
            # There was an exception, tell the user in a friendly embed, then output our exception to console.
            responseEmbed = interactions.Embed(title="Error", description="The roles channel could not be set due to an internal error.", color=Utils.EmbedColours.error)
            self.log.print(f"Could not set roles channel in guild \"{ctx.guild.name}\" (ID: {ctx.guild.id}) to #{channel.name}\n")
            print(traceback.format_exc() + "\n")

        # Send our response embed.
        await ctx.edit(embed=responseEmbed)


    @interactions.slash_command(name="sendrolebutton", description="Resend role selection button in your saved roles channel.", default_member_permissions=interactions.Permissions.MANAGE_WEBHOOKS)
    async def sendRoleButton(self, ctx: interactions.SlashContext) -> None:
        # This is for server staff members to send a fresh copy of the "Get roles..." button in their set roles button. Fails if the channel is not set.
        await ctx.send(embed=interactions.Embed(title="Please wait", description="Sending role button...", color=Utils.EmbedColours.neutral), ephemeral=True)

        try:
            success = True
            if ctx.guild.id in list(self.guildId2Db.keys()):
                if self.guildId2Db[ctx.guild.id]["Channels"]["RolesChannel"]["ChannelID"] != "0":
                    # Channel ID exists in the database
                    rolesChannel = ctx.guild.get_channel(int(self.guildId2Db[ctx.guild.id]["Channels"]["RolesChannel"]["ChannelID"]))
                    if rolesChannel:
                        # The channel exists, send the RoleButton.
                        await rolesChannel.send(components=RoleButton(self.getUniqueId(ctx.guild.id, 0)))
                    else:
                        # The set channel no longer exists.
                        success = False
                else:
                    # If the channel ID is 0, that's our default value and therefore the server hasn't set a roles channel yet.
                    success = False

            else: # The guild isn't in the database, this can happen if we disconnect, join a guild while disconnected, and reconnect on the same instance.
                self.guildId2Db = self.loadDatabaseItems() # Reload our database, then try again.
                if ctx.guild.id in list(self.guildId2Db.keys()):
                    if self.guildId2Db[ctx.guild.id]["Channels"]["RolesChannel"]["ChannelID"] != "0":
                        rolesChannel = ctx.guild.get_channel(int(self.guildId2Db[ctx.guild.id]["Channels"]["RolesChannel"]["ChannelID"]))
                        await rolesChannel.send(components=RoleButton(self.getUniqueId(ctx.guild.id, 0)))
                    else:
                        success = False
                else:
                    success = False

            if success:
                # Everything was successful, send the success embed.
                responseEmbed = interactions.Embed(title="Success", description=f"Role selection button resent in <#{rolesChannel.id}> successfully.", color=Utils.EmbedColours.positive)
            else:
                # The channel isn't set or no longer exists, send the error embed.
                responseEmbed = interactions.Embed(title="Error", description="You have not set a roles selection channel, or the one you have set it to no longer exists. Please use `/setroleschannel` to set one.", color=Utils.EmbedColours.error)
        except:
            # There was an exception, send the error embed then output the traceback to our console.
            responseEmbed = interactions.Embed(title="Error", description="The role button could not be sent due to an internal error.", color=Utils.EmbedColours.error)
            print(traceback.format_exc() + "\n")

        await ctx.edit(embed=responseEmbed)


    @interactions.slash_command(name="addroletolist", description="Adds a role to the role channel selection list.", 
                                options=[{"name": "role",
                                          "description": "The role to add to the role channel selection list.",
                                          "type": interactions.OptionType.ROLE,
                                          "required": True},],
                                default_member_permissions=interactions.Permissions.MANAGE_WEBHOOKS)
    async def addRoleToLIst(self, ctx: interactions.SlashContext, role:interactions.models.discord.Role) -> None:
        # This is for server staff members to add a role for users to select on the RoleList.
        await ctx.send(embed=interactions.Embed(title="Please wait", description="Saving your changes...", color=Utils.EmbedColours.neutral), ephemeral=True)


        if role.is_assignable and not role.default and str(role.id) not in self.guildId2Db[ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"]:
            # Checking our role validity, this ensures that it's not above us, it's not the @everyone role, and that it's not already in our list.

            # Add to our dict
            # We must represent any Discord snowflakes as a string for compatability with a YAML database where needed.
            self.guildId2Db[ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"].append(str(role.id))

            try:
                self.refreshRoleSelectionDatabase(ctx.guild.id)

                # All was successful, let them know.
                responseEmbed = interactions.Embed(title="Success", description=f"Added the <@&{role.id}> role to the selection list successfully.", color=Utils.EmbedColours.positive)
                self.log.print(f"Added role \"{role.name}\" (ID: {role.id}) to the selection list in guild \"{ctx.guild.name}\" (ID {ctx.guild.id}) successfully.")
            except:
                # We encountered an exception, let them know then output the traceback to our console.
                responseEmbed = interactions.Embed(title="Error", description=f"Could not add the <@&{role.id}> role to the selection list due to an internal error.", color=Utils.EmbedColours.error)
                self.log.print(f"Failed to add role \"{role.name}\" (ID: {role.id}) to the selection list in guild \"{ctx.guild.name}\" (ID {ctx.guild.id}).")
                print(traceback.format_exc() + "\n")
        else:
            # The role is invalid, it is either above the bot, it's the @everyone role, or it's already on the list for users to select.
            responseEmbed = interactions.Embed(title="Error", description="The role you have specified can't be assigned by this bot or is already in the list.", color=Utils.EmbedColours.error)

        # And finally, send our response.
        await ctx.edit(embed=responseEmbed)


    @interactions.slash_command(name="removerolefromlist", description="Removes a role from the role channel selection list.", 
                                options=[{"name": "role",
                                          "description": "The role to remove from the role channel selection list.",
                                          "type": interactions.OptionType.ROLE,
                                          "required": True},],
                                default_member_permissions=interactions.Permissions.MANAGE_WEBHOOKS)
    async def removeRoleFromLIst(self, ctx: interactions.SlashContext, role:interactions.models.discord.Role) -> None:
        # This is for server staff members to remove a role so that users can no longer select it on the RoleList.
        await ctx.send(embed=interactions.Embed(title="Please wait", description="Saving your changes...", color=Utils.EmbedColours.neutral), ephemeral=True)


        if str(role.id) in self.guildId2Db[ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"]:

            # Remove from our dict
            self.guildId2Db[ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"].pop(
                self.guildId2Db[ctx.guild.id]["Roles"]["RoleSelectionList"]["PublicList"].index(str(role.id)))

            try:
                self.refreshRoleSelectionDatabase(ctx.guild.id)

                # All was successful, let them know.
                responseEmbed = interactions.Embed(title="Success", description=f"Removed the <@&{role.id}> role from the selection list successfully.", color=Utils.EmbedColours.positive)
                self.log.print(f"Removed role \"{role.name}\" (ID: {role.id}) from the selection list in guild \"{ctx.guild.name}\" (ID {ctx.guild.id}) successfully.")
            except:
                # We encountered an exception, let them know then output the traceback to our console.
                responseEmbed = interactions.Embed(title="Error", description=f"Could not remove the <@&{role.id}> role from the selection list due to an internal error.", color=Utils.EmbedColours.error)
                self.log.print(f"Failed to remove role \"{role.name}\" (ID: {role.id}) from the selection list in guild \"{ctx.guild.name}\" (ID {ctx.guild.id}).")
                print(traceback.format_exc() + "\n")
        else:
            # The role isn't in the selection list for us to remove.
            responseEmbed = interactions.Embed(title="Error", description="The role you have specified isn't in the role selection list.", color=Utils.EmbedColours.error)

        # And finally, send our response.
        await ctx.edit(embed=responseEmbed)