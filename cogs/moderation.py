"""
Dredd.
Copyright (C) 2020 Moksej
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import discord
import time
import datetime
import json
import asyncio
import random # Warnings
from discord.ext import commands, tasks
from datetime import datetime
from utils import default, btime
from collections import Counter
from utils.paginator import Pages
from db import emotes
from utils.default import responsible
from io import BytesIO


class moderation(commands.Cog, name="Moderation"):

    def __init__(self, bot):
        self.bot = bot
        self.big_icon = "https://cdn.discordapp.com/emojis/695710706296815626.png?v=1"
        self.help_icon = "<:bann:695710706296815626>"
        self.bot.embed_color = 0x0058D6

# ! Commands

#########################################################################################################

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None):
        if limit > 2000:
            return await ctx.send("You can purge maximum amount of 2000 messages!")

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send("No permissions")
        except discord.HTTPException as e:
            return await ctx.send(f"Looks like you got an error: {e}")

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        if deleted == 1:
            messages = "<:msgdelete:686980262923337728> Deleted **1** message"
        else:
            messages = f"<:msgdelete:686980262923337728> Deleted **{deleted}** messages"
        if deleted:
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)

        to_send = '\n'.join(messages)
        
        if len(to_send) > 2000:
            text = f"<:msgdelete:686980262923337728> Removed `{deleted}` messages"
            await ctx.send(text, delete_after=10)
        else:
            e = discord.Embed(color=self.bot.embed_color)
            e.description = f"{messages}"
            await ctx.send(embed=e, delete_after=10)

    async def log_delete(self, ctx, data):
        check = await self.bot.db.fetchval("SELECT * FROM moderation WHERE guild_id = $1", ctx.guild.id)

        if check is None:
            return
        elif check is not None:
            channel = await self.bot.db.fetchval("SELECT channel_id FROM moderation WHERE guild_id = $1", ctx.guild.id)
            chan = self.bot.get_channel(channel)
            
            #e = discord.Embed(color=self.bot.logging_color, description=f"{messages} messages were deleted by **{ctx.author}**. [View File]({data})")
            text = f"Messages were deleted by **{ctx.author}**."
            file=data
            await chan.send(text, file=file)


#########################################################################################################

    @commands.command(brief="Change someones nickname", description="Change or remove anyones nickname", aliases=["nick"])
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def setnick(self, ctx, member: discord.Member, *, name: str = None):
        """ Change someone's nickname """
        
        
        try:
            if member.top_role.position > ctx.author.top_role.position:
                return await ctx.send("You can't change nickname of the member that is above you")
            if member.top_role.position >= ctx.guild.me.top_role.position:
                return await ctx.send(f"I was unable to change {member.name}'s nickname")
            if name and len(name) > 32:
                return await ctx.send(f"{emotes.red_mark} Nickname is too long! You can't have nicknames longer than 32 characters")
            await member.edit(nick=name)
            if name is not None:
                emb = discord.Embed(color=self.bot.embed_color, description=f"{emotes.white_mark} Changed **{member.name}'s** nickname to **{name}**.")
                return await ctx.send(embed=emb)
            if name is None:
                emb = discord.Embed(color=self.bot.embed_color, description=f"{emotes.white_mark} Removed **{member.name}'s** nickname")
                return await ctx.send(embed=emb)
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to change **{member}**'s nickname.")

    @commands.command(brief="Kick members", description="Kick someone from the server")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True, manage_messages=True)
    async def kick(self, ctx, members: commands.Greedy[discord.Member], *, reason: str = None):
        """
        Kicks member from server.
        You can also provide multiple members to kick.
        """
        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide member(s) to kick.")
            
            
            failed = 0
            for member in members:
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.guild.kick(member, reason=responsible(ctx.author, reason))
                except discord.HTTPException:
                    failed += 1

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully kicked **{total}** members.")
            else:
                await ctx.send(f"Successfully kicked **{total - failed}/{total}** members.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to kick members.")

    @commands.command(brief="Ban members", description="Ban someone from the server")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, manage_messages=True)
    async def ban(self, ctx, members: commands.Greedy[discord.Member], *, reason: str = None):
        """
        Ban member from the server.
        You can also provide multiple members to ban.
        """

        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide members to ban.")
            

            failed = 0
            for member in members:
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.guild.ban(member, reason=responsible(ctx.author, reason))
                except discord.HTTPException:
                    failed += 1

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully banned **{total}** members.")
            else:
                await ctx.send(f"Successfully banned **{total - failed}/{total}** members.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to ban members.")

    @commands.command(brief="Unban members", description="Unban someone from the server")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, manage_messages=True)
    async def unban(self, ctx, user: discord.User, *, reason: str=None):
        """
        Unbans user from server
        """

        await ctx.message.delete()

        await ctx.guild.unban(discord.Object(id=user.id), reason=responsible(ctx.author, reason))
        await ctx.send(f"{emotes.white_mark} **{user}** was unbanned successfully, with a reason: ``{reason}``", delete_after=15)
    
    @commands.command(brief="Unban all members", description="Unban everyone from the server.")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, use_external_emojis=True, manage_messages=True)
    async def unbanall(self, ctx, *, reason: str=None):
        """ Unban all users from the server """
        bans = len(await ctx.guild.bans())

        try:
            unbanned = 0
            
            if bans == 0:
                return await ctx.send("This guild has no bans.")
            
            def check(r, u):
                return u.id == ctx.author.id and r.message.id == checkmsg.id
                
            checkmsg = await ctx.send(f"Are you sure you want to unban **{bans}** members from this guild?")
            await checkmsg.add_reaction(f'{emotes.white_mark}')
            await checkmsg.add_reaction(f'{emotes.red_mark}')
            await checkmsg.add_reaction('🔍')
            react, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)

            # ? They want to unban everyone

            if str(react) == f"{emotes.white_mark}": 
                unb = await ctx.send(f"Unbanning **{bans}** members from this guild.")    
                await checkmsg.delete()
                for user in await ctx.guild.bans():
                    await ctx.guild.unban(user.user, reason=responsible(ctx.author, reason))
                    await unb.edit(content=f"{emotes.loading1} Processing unbans...")
                await unb.edit(content=f"Unbanned **{bans}** members from this guild.", delete_after=15)

            # ? They don't want to unban anyone

            if str(react) == f"{emotes.red_mark}":      
                await checkmsg.delete()
                await ctx.send("Alright. Not unbanning anyone..")

            # ? They want to see ban list

            if str(react) == "🔍":
                await checkmsg.clear_reactions()
                ban = []
                for banz in await ctx.guild.bans():
                    ben = f"• {banz.user}\n"
                    ban.append(ben)
                    e = discord.Embed(color=self.bot.embed_color, title=f"Bans for {ctx.guild}", description="".join(ban))
                    e.set_footer(text="Are you sure you want to unban them all?")
                    await checkmsg.edit(content='', embed=e)
                await checkmsg.add_reaction(f'{emotes.white_mark}')
                await checkmsg.add_reaction(f'{emotes.red_mark}')
                react, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)

                # ? They want to unban everyone
                

                if str(react) == f"{emotes.white_mark}": 
                    unb = await ctx.send(f"Unbanning **{bans}** members from this guild.")    
                    await checkmsg.delete()
                    for user in await ctx.guild.bans():
                        await ctx.guild.unban(user.user, reason=responsible(ctx.author, reason))
                        await unb.edit(content=f"{emotes.loading1} Processing unbans...")
                    await unb.edit(content=f"Unbanned **{bans}** members from this guild.", delete_after=15)

                # ? They don't want to unban anyone

                if str(react) == f"{emotes.red_mark}":      
                    await checkmsg.delete()
                    await ctx.send("Alright. Not unbanning anyone..")

        except Exception as e:
            return

                

    @commands.command(brief="Softban members", description="Softbans member from the server")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True, manage_messages=True)
    async def softban(self, ctx, user: discord.Member, reason: str = None):
        """ Softbans member from the server """


        try:
            member = user
            if user == ctx.author:
                return await ctx.send("Are you seriously trying to ban yourself? That's stupid")
            elif user.top_role.position >= ctx.author.top_role.position:
                return await ctx.send("You can't ban user who's above or equal to you!")
            elif member.top_role.position >= ctx.guild.me.top_role.position:
                return await ctx.send(f"I was unable to soft-ban {user.name}")
            obj = discord.Object(id=user.id)
            await ctx.guild.ban(obj, reason=responsible(ctx.author, reason))
            await ctx.guild.unban(obj, reason=responsible(ctx.author, reason))
            await ctx.send(f"{emotes.white_mark} **{user}** was soft-banned successfully, with a reason: ``{reason}``", delete_after=15)
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to soft-ban **{user}**.")
    
    @commands.command(brief="Mute someone")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, members: commands.Greedy[discord.Member], *, reason: str = None):
        """ Mute someone in your server. 
        Make sure you have muted role in your server and properly configured."""
        message = []

        muterole = discord.utils.find(lambda r: r.name.lower() == "muted", ctx.guild.roles)

        if muterole is None:
            embed = discord.Embed(color=self.bot.embed_color, description=f"{emotes.red_mark} I can't find a role named `Muted` Are you sure you've made one?")
            return await ctx.send(embed=embed, delete_after=10)


        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide members to mute.")

            if total > 5:
                return await ctx.send("You can mute only 5 members at once!")                    
            

            failed = 0
            failed_list = ""
            for member in members:
                if muterole in member.roles:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.add_roles(muterole, reason=responsible(ctx.author, reason))
                except discord.HTTPException as e:
                    failed += 1
                    failed_list += f"{member.mention} - {e}"
                except discord.Forbidden as e:
                    failed += 1
                    failed_list += f"{member.mention} - {e}"

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully muted **{total}** members for: `{reason}`.")
            else:
                await ctx.send(f"Successfully muted **{total - failed}/{total}** members for: `{reason}`.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to mute members.")
        

    @commands.command(brief="Unmute someone", description="Unmute someone from this server")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, members: commands.Greedy[discord.Member], *, reason: str = None):
        """ Unmute someone in the server. 
        Make sure bot has permissions to deassign the `Muted` role."""
        
        muterole = discord.utils.find(lambda r: r.name.lower() == "muted", ctx.guild.roles)

        if muterole is None:
            embed = discord.Embed(color=self.bot.embed_color, description=f"{emotes.red_mark} I can't find a role named `Muted` Are you sure you've made one?")
            return await ctx.send(embed=embed, delete_after=10)

        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide members to mute.")            

            failed = 0
            failed_list = ""
            for member in members:
                if muterole not in member.roles:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.remove_roles(muterole, reason=responsible(ctx.author, reason))
                except discord.HTTPException as e:
                    failed += 1
                    failed_list += f"{member.mention} - {e}"
                except discord.Forbidden as e:
                    failed += 1
                    failed_list += f"{member.mention} - {e}"

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully unmuted **{total}** members for: `{reason}`.")
            else:
                await ctx.send(f"Successfully unmuted **{total - failed}/{total}** members for: `{reason}`.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to unmute members.")
            
    @commands.command(brief="Dehoist members", description="Dehoist all members to specific nickname")
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def dehoist(self, ctx, *, nick: str):
        """ Dehoist members with non alphabetic letters """        
        nickname_only = False

        try:           
            hoisters = []
            for member in ctx.guild.members:
                if nickname_only:
                    if not member.nick: return
                    name = member.nick
                else:
                    name = member.display_name
                if not name[0].isalnum():
                    await member.edit(nick=nick)
                    hoisters.append(f" {member} --> {member.mention} ({member.id})\n")
            if not hoisters:
                return await ctx.send("I was unable to find any hosters")
            text = '**Removed these hoisters:**'
            for num, hoister in enumerate(hoisters, start=0):
                text += f"`[{num + 1}]` {hoister}"
            await ctx.send(text)
        except Exception as e:
            await ctx.send(f"```diff\n- {e}```")
    
    @commands.command(brief="Clone text channel", description="Clone text channel in this server")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def clone(self, ctx, channel: discord.TextChannel, *, reason: str = None):
        """ Clone text channel in the server"""
        server = ctx.message.guild
        if reason is None:
            reason = 'No reason'
        try:
            await ctx.message.delete()
        except:
            pass
        for c in ctx.guild.channels:
            if c.name == f'{channel.name}-clone':
                return await ctx.send(f"{emotes.red_mark} {channel.name} clone already exists!")     
        await channel.clone(name=f'{channel.name}-clone', reason=responsible(ctx.author, reason))
        await ctx.send(f"{emotes.white_mark} Successfully cloned {channel.name}")

    @commands.group(aliases=['clear', 'delete', 'prune'], brief="Clear messages", description="Clear messages from the chat", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx):
        """ Purge messages in the chat. Default amount is set to **100**"""
        await ctx.send_help(ctx.command)   
    @purge.command(brief="Every message", description="Clear all messages in chat")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def all(self, ctx, search=100):
        """ Removes all messages
        Might take longer if you're purging messages that are older than 2 weeks """
        await ctx.message.delete()
        msgs = ""
        for message in await ctx.channel.history(limit=search).flatten():
            msgs += f"[{message.created_at}] {message.author} - {message.content}\n"

        data = BytesIO(msgs.encode('utf-8'))
        await self.do_removal(ctx, search, lambda e: True)
        await self.log_delete(ctx, data=discord.File(data, filename=f"{default.timetext('Messages')}"))
    
    @purge.command(brief="User messages", description="Clear messages sent from an user")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def user(self, ctx, member: discord.Member, search=100):
        """ Removes user messages """
        await ctx.message.delete()
        msgs = ""
        for message in await ctx.channel.history(limit=search).flatten():
            if message.author == member:
                msgs += f"[{message.created_at}] {message.author} - {message.content}\n"
        data = BytesIO(msgs.encode('utf-8'))
        await self.do_removal(ctx, search, lambda e: e.author == member)
        await self.log_delete(ctx, data=discord.File(data, filename=f"{default.timetext(f'{member}_messages')}"))
    
    @purge.command(brief="Bot's messages", description="Clear messages sent from an user")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def bot(self, ctx, bot: discord.Member, search=100):
        """ Removes bot's messages """
        if not bot.bot:
            return await ctx.send(f'{emotes.red_mark} Please define a valid bot.')
        await ctx.message.delete()
        await self.do_removal(ctx, search, lambda e: e.author == bot)
    
    @commands.command(brief="Voice mute member", description="Voice mute any member in the server", aliases=["vmute"])
    @commands.guild_only()
    @commands.has_guild_permissions(mute_members=True)
    @commands.bot_has_guild_permissions(mute_members=True)
    async def voicemute(self, ctx, members: commands.Greedy[discord.Member], reason: str=None):
        """ Voice mute member in the server """

        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide members to voice mute.")

            if total > 5:
                return await ctx.send("You can voicemute only 5 members at once.")            

            failed = 0
            for member in members:
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.edit(mute=True, reason=responsible(ctx.author, reason))
                except discord.HTTPException as e:
                    failed += 1
                except discord.Forbidden:
                    failed += 1

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully voice muted **{total}** members.")
            else:
                await ctx.send(f"Successfully voice muted **{total - failed}/{total}** members.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to voice mute members.")


    @commands.command(brief="Voice unmute member", description="Voice unmute any member in the server", aliases=["vunmute"])
    @commands.guild_only()
    @commands.has_guild_permissions(mute_members=True)
    @commands.bot_has_guild_permissions(mute_members=True)
    async def voiceunmute(self, ctx, members: commands.Greedy[discord.Member], reason: str=None):
        """ Voice unmute member in the server """

        try:
            total = len(members)

            if total == 0:
                return await ctx.send("Please provide members to voice unmute.")

            if total > 5:
                return await ctx.send("You can voice unmute only 5 members at once.")            

            failed = 0
            for member in members:
                if member.top_role.position >= ctx.author.top_role.position:
                    failed += 1
                    continue
                if member.top_role.position >= ctx.guild.me.top_role.position:
                    failed += 1
                    continue
                if member == ctx.author:
                    failed += 1
                    continue
                try:
                    await member.edit(mute=False, reason=responsible(ctx.author, reason))
                except discord.HTTPException:
                    failed += 1

            if failed == 0:
                await ctx.send(f"{emotes.white_mark} Succesfully voice unmuted **{total}** members.")
            else:
                await ctx.send(f"Successfully voice unmuted **{total - failed}/{total}** members.")
        except Exception as e:
            print(e)
            await ctx.send(f"Something failed while trying to voice unmute members.")
    
    @commands.command(brief="New users", hidden=True)
    @commands.guild_only()
    async def newusers(self, ctx, *, count: int):
        """
        See the newest members in the server.
        Limit is set to `10`
        """
        if len(ctx.guild.members) < count:
            return await ctx.send(f"This server has only {len(ctx.guild.members)} members")
        counts = max(min(count, 10), 1)

        if not ctx.guild.chunked:
            await self.bot.request_offline_members(ctx.guild)
        members = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)[:counts]
        e = discord.Embed(title='Newest member(s) in this server', colour=self.bot.embed_color)
        for member in members:
            data = f'**Joined Server at** {btime.human_timedelta(member.joined_at)}\n**Account created at** {btime.human_timedelta(member.created_at)}'
            e.add_field(name=f'**{member}** ({member.id})', value=data, inline=False)
            if count > 10:
                e.set_footer(text="Limit is set to 10")

        await ctx.send(embed=e)

    @commands.command(brief="Hoist a role", aliases=['ar'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def announcerole(self, ctx, *, role: discord.Role):
        """ Make a role mentionable you want to mention in announcements.
        
        The role will become unmentionable after you mention it or you don't mention it for 30seconds. """
        if role == ctx.guild.default_role:
            return await ctx.send("To prevent abuse, I won't allow mentionable role for everyone/here role.")

        if ctx.author.top_role.position <= role.position:
            return await ctx.send("It seems like the role you attempt to mention is over your permissions, therefor I won't allow you.")

        if ctx.me.top_role.position <= role.position:
            return await ctx.send("This role is above my permissions, I can't make it mentionable ;-;")

        await role.edit(mentionable=True, reason=f"announcerole command")
        msg = await ctx.send(f"**{role.name}** is now mentionable, if you don't mention it within 30 seconds, I will revert the changes.")

        while True:
            def role_checker(m):
                if (role.mention in m.content):
                    return True
                return False

            try:
                checker = await self.bot.wait_for('message', timeout=30.0, check=role_checker)
                if checker.author.id == ctx.author.id:
                    await role.edit(mentionable=False, reason=f"announcerole command")
                    return await msg.edit(content=f"**{role.name}** mentioned by **{ctx.author}** in {checker.channel.mention}")
                    break
                else:
                    await checker.delete()
            except asyncio.TimeoutError:
                await role.edit(mentionable=False, reason=f"announcerole command")
                return await msg.edit(content=f"**{role.name}** was never mentioned by **{ctx.author}**...")
                break
    
    @commands.command(brief="Member warnings", aliases=['warns'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member = None):
        """ Check all guild warns or all member warnings """

        if member is None:
            warns_check = await self.bot.db.fetchval("SELECT * FROM warnings WHERE guild_id = $1", ctx.guild.id)
            
            if warns_check is None:
                return await ctx.send(f"There are no warnings in this guild.")
                
            if warns_check is not None:
                user = []
                for user_id, reason, id, time in await self.bot.db.fetch("SELECT user_id, reason, id, time FROM warnings WHERE guild_id = $1", ctx.guild.id):
                    user.append(f'**User:** {ctx.guild.get_member(user_id)}\n' + '**ID:** ' + str(id) + "\n" + '**Reason:** ' + reason + "\n**Warned:** " + str(default.date(time)) + "\n**────────────────────────**")
                
                members = []
                for reason in user:
                    members.append(f"{reason}\n")
                    
                paginator = Pages(ctx,
                          title=f"Guild warnings",
                          entries=members,
                          thumbnail=None,
                          per_page = 5,
                          embed_color=ctx.bot.embed_color,
                          show_entry_count=True,
                          author=ctx.author)
                await paginator.paginate()
        

        if member is not None:
            warns_check = await self.bot.db.fetchval("SELECT * FROM warnings WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
            
            if warns_check is None:
                return await ctx.send(f"**{member}** has no warnings.")
                
            if warns_check is not None:
                user = []
                for reason, id, time in await self.bot.db.fetch("SELECT reason, id, time FROM warnings WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
                    user.append('**ID:** ' + str(id) + "\n" + '**Reason:** ' + reason + "\n**Warned:** " + str(default.date(time)) + "\n**────────────────────────**")
                
                members = []
                for reason in user:
                    members.append(f"{reason}\n")
                    
                paginator = Pages(ctx,
                          title=f"{member}'s warnings",
                          entries=members,
                          thumbnail=None,
                          per_page = 5,
                          embed_color=ctx.bot.embed_color,
                          show_entry_count=True,
                          author=ctx.author)
                await paginator.paginate()

    @commands.command(brief="Warn a member")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """ Warn a member for something """

        if reason is None:
            reason = "No reason."
        else:
            reason = reason
        
        if member == ctx.author:
            return await ctx.send("Ok you're warned, dummy...")
        if member.top_role.position >= ctx.author.top_role.position and ctx.author != ctx.guild.owner:
            return await ctx.send("You can't warn someone who's higher or equal to you!")
        if member.top_role.position > ctx.guild.me.top_role.position:
            return await ctx.send(f"I'm lower than {member.name}. I can't warn him.")

        random_id = random.randint(1111, 99999)
        
        await self.bot.db.execute("INSERT INTO warnings(user_id, guild_id, id, reason, time) VALUES ($1, $2, $3, $4, $5)", member.id, ctx.guild.id, random_id, reason, datetime.utcnow())

        e = discord.Embed(color=self.bot.embed_color, description=f"Successfully warned **{member}** for: **{reason}** with ID: **{random_id}**", delete_after=15)

        await ctx.send(embed=e)

    @commands.command(brief="Remove warn from member", aliases=['unwarn'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def removewarn(self, ctx, member: discord.Member, warnid):
        """ Remove warn from member's history """

        if member is ctx.author:
            return await ctx.send("Ok your warn was removed, dummy...")
        if member.top_role.position >= ctx.author.top_role.position and ctx.author != ctx.guild.owner:
            return await ctx.send("You can't remove warns from someone who's higher or equal to you!")
        if member.top_role.position > ctx.guild.me.top_role.position:
            return await ctx.send(f"I'm lower than {member.name}. I can't remove warns from him.")

        check_id = await self.bot.db.fetchval('SELECT * FROM warnings WHERE guild_id = $1 AND id = $2', ctx.guild.id, int(warnid))

        if check_id is None:
            await ctx.send(f"Warn with ID: **{warnid}** was not found.")

        if check_id is not None:
            warnings = await self.bot.db.fetchval('SELECT * FROM warnings WHERE user_id = $1 AND id = $2', member.id, int(warnid))
            if warnings is not None:
                await self.bot.db.execute("DELETE FROM warnings WHERE id = $1 AND user_id = $2", int(warnid), member.id)
                await ctx.send(f"Removed warn from **{member}** with id: **{int(warnid)}**")
            if warnings is None:
                return await ctx.send(f"Warn with ID: **{int(warnid)}** was not found.")
    
    @commands.command(brief="Remove all warns from member", aliases=['unwarnall'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(use_external_emojis=True)
    async def removewarns(self, ctx, member: discord.Member):
        """ Remove all member's warns """

        try:
            if member is ctx.author:
                return await ctx.send("Ok your warns were removed, dummy...")
            if member.top_role.position >= ctx.author.top_role.position and ctx.author != ctx.guild.owner:
                return await ctx.send("You can't remove warns from someone who's higher or equal to you!")
            if member.top_role.position > ctx.guild.me.top_role.position:
                return await ctx.send(f"I'm lower than {member.name}. I can't remove warns from him.")

            def check(r, u):
                return u.id == ctx.author.id and r.message.id == checkmsg.id
            sel = await self.bot.db.fetch("SELECT * FROM warnings WHERE user_id = $1 AND guild_id = $2", member.id, ctx.guild.id)

            if len(sel) == 0:
                return await ctx.send(f"**{member}** has no warnings.")
            checkmsg = await ctx.send(f"Are you sure you want to remove all **{len(sel)}** warns from the **{member}**?")
            await checkmsg.add_reaction(f'{emotes.white_mark}')
            await checkmsg.add_reaction(f'{emotes.red_mark}')
            react, user = await self.bot.wait_for('reaction_add', check=check, timeout=30)

            if str(react) == f"{emotes.white_mark}":
                await checkmsg.delete()
                await self.bot.db.execute("DELETE FROM warnings WHERE user_id = $1 AND guild_id = $2", member.id, ctx.guild.id)
                await ctx.send(f"Removed **{len(sel)}** warnings from: **{member}**", delete_after=15)
            
            if str(react) == f"{emotes.red_mark}":
                await checkmsg.delete()
                return await ctx.send("Not removing any warns.", delete_after=15)

        except asyncio.TimeoutError:
            await checkmsg.clear_reactions()
            return await checkmsg.edit(content=f"Timing out...", delete_after=15)
        except Exception as e:
            print(e)
            await ctx.send("Looks like something wrong happened.")

    @commands.command(brief='Lock a text channel')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def lockchannel(self, ctx, channel: discord.TextChannel, *, reason: str = None):
        """ Lock any text channels from everyone being able to chat """
        
        if reason is None:
            reason = "No reason"

        if channel.overwrites_for(ctx.guild.default_role).send_messages == False:
            return await ctx.send(f"{emotes.red_mark} {channel.mention} is already locked!", delete_after=20)
        else:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=responsible(ctx.author, reason))
            await channel.send(f"{emotes.locked} This channel was locked for: `{reason}`")
            await ctx.send(f"{emotes.white_mark} {channel.mention} was locked!", delete_after=20)
    
    @commands.command(brief='Unlock a text channel')
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def unlockchannel(self, ctx, channel: discord.TextChannel, *, reason: str = None):
        """ Unlock text channel to everyone 
        This will sync permissions with category """

        if reason is None:
            reason = "No reason"

        if channel.overwrites_for(ctx.guild.default_role).send_messages is None:
            return await ctx.send(f"{emotes.red_mark} {channel.mention} is not locked!", delete_after=20)
        elif channel.overwrites_for(ctx.guild.default_role).send_messages == False:
            await channel.set_permissions(ctx.guild.default_role, overwrite=None, reason=responsible(ctx.author, reason))
            await channel.send(f"{emotes.unlocked} This channel was unlocked for: `{reason}`")
            await ctx.send(f"{emotes.white_mark} {channel.mention} was unlocked!", delete_after=20)

    @commands.command(brief='Turn on/off server raid mode')
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(kick_members=True)
    async def raidmode(self, ctx):
        """ Raid is happening in your server? Turn on anti-raider! It'll kick every new member that joins. 
        It'll also inform them in DMs that server is currently in anti-raid mode and doesn't allow new members! """

        raid_check = await self.bot.db.fetchval("SELECT raidmode FROM guilds WHERE guild_id = $1", ctx.guild.id)

        if raid_check == False:
            await self.bot.db.execute("UPDATE guilds SET raidmode = $1 WHERE guild_id = $2", True, ctx.guild.id)
            await ctx.send(f"{emotes.white_mark} Raid mode was activated! New members will get kicked with a message in their DMs")
        elif raid_check == True:
            await self.bot.db.execute("UPDATE guilds SET raidmode = $1 WHERE guild_id = $2", False, ctx.guild.id)
            await ctx.send(f"{emotes.white_mark} Raid mode was deactivated! New members won't be kicked anymore.")
        
            
    
def setup(bot):
    bot.add_cog(moderation(bot))