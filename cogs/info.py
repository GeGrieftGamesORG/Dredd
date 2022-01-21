"""
Dredd, discord bot
Copyright (C) 2022 Moksej
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
import typing
import os
import codecs
import pathlib
import inspect
import pygit2
import itertools
import psutil

from discord.ext import commands
from discord.utils import escape_markdown, snowflake_time
from collections import Counter
from datetime import datetime, timezone, timedelta
from io import BytesIO

from db.cache import CacheManager as CM
from utils import btime, default, rtfm
from utils.paginator import Pages
from utils.i18n import locale_doc


# noinspection PyUnboundLocalVariable
class Info(commands.Cog, name='Information'):
    def __init__(self, bot):
        self.bot = bot
        self.help_icon = "<:tag:686251889586864145>"
        self.big_icon = "https://cdn.discordapp.com/emojis/686251889586864145.png?v=1"

    @staticmethod
    def format_commit(commit):
        short, _, _ = commit.message.partition('\n')
        short_sha2 = commit.hex[0:6]
        commit_tz = timezone(timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)

        # [`hash`](url) message (offset)
        offset = btime.human_timedelta(commit_time.astimezone(timezone.utc), accuracy=1)
        return f'• [`{short_sha2}`](https://github.com/TheMoksej/Dredd/commit/{commit.hex}) {short} ({offset})'

    def get_last_commits(self, count=3):
        repo = pygit2.Repository('.git')
        commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count))
        return '\n'.join(self.format_commit(c) for c in commits)

    @commands.command(brief=_("See the bot's latency to discord"))
    @locale_doc
    async def ping(self, ctx):
        _(""" See the bot's latency to discord """)

        discord_start = time.monotonic()
        async with self.bot.session.get("https://discord.com/") as resp:
            if resp.status == 200:
                discord_end = time.monotonic()
                discord_ms = f"{round((discord_end - discord_start) * 1000)}ms"
            else:
                discord_ms = "fucking dead"
        await ctx.send(f"\U0001f3d3 Pong   |   {discord_ms}")

    @commands.command(brief=_("A detailed information of the bot"), aliases=['botinfo', 'info', 'bi'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def about(self, ctx):
        _(""" A detailed information of the bot """)

        version = self.bot.version
        channel_types = Counter(type(c) for c in self.bot.get_all_channels())
        voice = channel_types[discord.channel.VoiceChannel]
        text = channel_types[discord.channel.TextChannel]

        te = len([c for c in set(self.bot.walk_commands()) if c.cog_name == "Owner"])
        se = len([c for c in set(self.bot.walk_commands()) if c.cog_name == "Staff"])
        xd = len([c for c in set(self.bot.walk_commands())])
        if await ctx.bot.is_owner(ctx.author):
            ts = 0
        elif await ctx.bot.is_admin(ctx.author):
            ts = te
        elif not await ctx.bot.is_admin(ctx.author):
            ts = te + se
        totcmd = xd - ts

        mems = sum(x.member_count for x in self.bot.guilds)
        website = 'https://dreddbot.xyz/'
        Moksej = self.bot.get_user(345457928972533773)

        embed = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        embed.set_author(name=_("About {0}").format(self.bot.user), icon_url=self.bot.user.avatar.url)
        embed.description = _("""
Dredd is a bot that will help your server with moderation, provide fun to your members, and much more! The bot is currently running on **V{0}** and is currently maintained.

**Developer:** [{1}](https://discord.com/users/345457928972533773)
**Library & version:** {2} [enhanced discord.py {3}]({18})
**Last boot:** {4}
**Created:** {5} ({6})

**Links:**
• [Support server]({7})
• [Bot invite]({8})
• [Website]({17})

**Latest Changes:**
{9}

**Total:**
• Commands: **{10}**
• Members: **{11}**
• Servers: **{12}**
• Channels: {13} **{14}** | {15} **{16}**\n
""").format(version, escape_markdown(str(Moksej)), self.bot.settings['emojis']['misc']['python'], discord.__version__, btime.discord_time_format(self.bot.uptime, source='R'),
            btime.discord_time_format(self.bot.user.created_at), btime.discord_time_format(self.bot.user.created_at, source='R'), self.bot.support, self.bot.invite,
            self.get_last_commits(), f'{totcmd:,}', f'{mems:,}', f'{len(self.bot.guilds):,}', self.bot.settings['emojis']['logs']['unlock'], f'{text:,}',
            self.bot.settings['emojis']['logs']['vcunlock'], f'{voice:,}', website, "https://github.com/iDevision/discord.py")
        embed.set_image(
            url=self.bot.settings['banners']['default'])

        await ctx.send(embed=embed)

    @commands.command(name='system', aliases=['sys'])
    @commands.cooldown(1, 3, commands.BucketType.member)
    @locale_doc
    async def system(self, ctx):
        _(""" A detailed information of the server the bot is hosted on. """)

        embed = discord.Embed(colour=self.bot.settings['colors']['embed_color'])
        embed.description = _("**System CPU:**\n- Frequency: {0} Mhz\n- Cores: {1}\n- Usage: {2}%\n\n"
                              "**System Memory:**\n- Available: {3} MB\n- Total: {4} MB\n- Used: {5} MB\n\n"
                              "**System Disk:**\n- Total: {6} GB\n- Used: {7} GB\n- Free: {8} GB\n\n"
                              "**Process Info:**\n- Memory Usage: {9} MB\n- CPU Usage: {10}%\n- Threads: {11}").format(round(psutil.cpu_freq().current, 2),
                                                                                                                       psutil.cpu_count(), psutil.cpu_percent(),
                                                                                                                       round(psutil.virtual_memory().available / 1048576),
                                                                                                                       round(psutil.virtual_memory().total / 1048576),
                                                                                                                       round(psutil.virtual_memory().used / 1048576),
                                                                                                                       round(psutil.disk_usage("/").total / 1073741824, 2),
                                                                                                                       round(psutil.disk_usage("/").used / 1073741824, 2),
                                                                                                                       round(psutil.disk_usage("/").free / 1073741824, 2),
                                                                                                                       round(self.bot.process.memory_full_info().rss / 1048576, 2),
                                                                                                                       self.bot.process.cpu_percent(), self.bot.process.num_threads())

        return await ctx.send(embed=embed)

    @commands.command(brief=_("Get detailed information about the user"), aliases=['user', 'ui'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @locale_doc
    async def userinfo(self, ctx, *, user: typing.Union[discord.User, str] = None):  # sourcery no-metrics
        _(""" A defailed information of the user. Fetches the user if they do not share any guilds with the bot. """)

        embcolor = self.bot.settings['colors']['embed_color']
        user = await default.find_user(ctx, user)

        if not user:
            return await ctx.send(_("{0} | That user could not be found.").format(ctx.bot.settings['emojis']['misc']['warn']))

        if not self.bot.get_user(user.id):
            embcolor = ctx.bot.settings['colors']['fetch_color']

        discord_badges = await default.public_flags(ctx, user)
        if user.bot and not discord_badges:
            discord_badges = f"{self.bot.settings['emojis']['badges']['bot']}"
        e = discord.Embed(color=embcolor)
        e.set_author(name=_("{0}'s Information").format(user), icon_url=user.avatar.url if user.avatar else user.display_avatar.url)

        member = ctx.guild.get_member(user.id)
        if member:
            nick = member.nick or 'N/A'
            nicks = ''
            uroles = [role.mention for role in member.roles if not role.is_default()]
            uroles.reverse()
            if len(uroles) > 15:
                uroles = [f"{', '.join(uroles[:10])} (+{len(member.roles) - 11})"]
            if not member.bot and CM.get(self.bot, 'nicks_op', member.id) is None:
                nicks += _('\n**Latest nicknames:**  ')
                nicknames = await self.bot.db.fetch("SELECT * FROM nicknames WHERE user_id = $1 AND guild_id = $2 ORDER BY time DESC LIMIT 5", user.id, ctx.guild.id)
                if nicknames:
                    for nickk in nicknames:
                        nicks += f"{escape_markdown(nickk['nickname'])}, "
                if not nicknames:
                    nicks += 'N/A  '
            user_roles = _(' **({0} Total)**').format(len(member.roles) - 1) if uroles != [] else _('No roles')
            e.add_field(name=_("General Information:"), value=_("""
{0} {1}

**User ID:** {2}
**Account created:** {3} ({4})""").format(user, discord_badges,
                                          user.id, btime.discord_time_format(user.created_at),
                                          btime.discord_time_format(user.created_at, source='R')), inline=False)
            e.add_field(name=_("Server Information:"), value=_("""
**Nickname:** {0}{1}
**Joined at:** {2} ({3})
**Roles:** {4}""").format(nick, nicks[:-2],
                          btime.discord_time_format(member.joined_at),
                          btime.discord_time_format(member.joined_at, source='R'),
                          ', '.join(uroles) + user_roles))
        else:

            # guilds = [x for x in self.bot.guilds if x.get_member(user.id)]
            # try:
            #     member = guilds[0].get_member(user.id)
            #     status = default.member_status(ctx, member)
            #     act = default.member_activity(ctx, member)
            # except Exception:
            #     status = ''
            #     act = ''
            e.add_field(name=_("General Information:"), value=_("""
{0} {1}

**User ID:** {2}
**Account created:** {3} ({4})""").format(user, discord_badges,
                                          user.id, btime.discord_time_format(user.created_at),
                                          btime.discord_time_format(user.created_at, source='R')), inline=False)

        if await self.bot.is_booster(user):
            media = await default.medias(ctx, user)
            if media:
                e.add_field(name=_('Social media:'), value=media, inline=False)

        avatar = user.avatar or user.display_avatar
        if not avatar.is_animated():
            e.set_thumbnail(url=avatar.with_format('png').url)
        elif avatar.is_animated():
            e.set_thumbnail(url=avatar.with_format('gif').url)
        else:
            e.set_thumbnail(url=user.avatar.url if user.avatar else user.display_avatar.url)

        await ctx.send(embed=e)

    @commands.command(name='serverinfo', aliases=['server', 'si'],
                      brief=_("Get current server's detailed information"))
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def serverinfo(self, ctx):
        _(""" A detailed information of the current server """)

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        acks = default.server_badges(ctx, ctx.guild)
        ack = _("\n**Acknowledgements:**\n{0}").format(acks) if acks else ''
        humann = sum(not member.bot for member in ctx.guild.members)
        botts = sum(member.bot for member in ctx.guild.members)
        num = sum(1 for user in ctx.guild.members if (ctx.channel.permissions_for(user).kick_members or ctx.channel.permissions_for(user).ban_members) and not user.bot)

        bans = ''
        if ctx.channel.permissions_for(ctx.guild.me).ban_members:
            bans += _("\n**Banned:** {0}").format(f'{len(await ctx.guild.bans()):,}')
        nitromsg = _("This server has **{0}** boosts").format(ctx.guild.premium_subscription_count)
        nitromsg += f"\n{default.next_level(ctx)}"

        e = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        e.set_author(name=_("{0} Information").format(ctx.guild.name), icon_url=ctx.guild.icon.url if ctx.guild.icon else self.bot.user.display_avatar.url)
        if ctx.guild.description:
            e.description = ctx.guild.description
        e.add_field(name=_('General Information:'), value=_("""
**Name:** {0}
**ID:** {1}
**Guild created:** {2} ({3})
**Verification level:** {4}

**Owner:** {5}
**Owner ID:** {6}{7}

**Nitro status:**
{8}
""").format(ctx.guild.name, ctx.guild.id, btime.discord_time_format(ctx.guild.created_at),
            btime.discord_time_format(ctx.guild.created_at, source='R'),
            str(ctx.guild.verification_level).capitalize(),
            ctx.guild.owner or 'Unknown', ctx.guild.owner_id, ack, nitromsg))

        e.add_field(name=_('Other Information:'), value=_("""**Members:** (Total: {0})
**Bots:** {2} | **Humans:** {3}
**Staff:** {4}{5}
**Channels:** {6} {7} | {8} {9}
""").format(f'{ctx.guild.member_count:,}', '', f'{botts:,}', f'{humann:,}', f'{num:,}', bans,
            self.bot.settings['emojis']['logs']['unlock'], f'{len(ctx.guild.text_channels):,}',
            self.bot.settings['emojis']['logs']['vcunlock'], f'{len(ctx.guild.voice_channels):,}'))
        features = set(ctx.guild.features)
        all_features = {
            'ANIMATED_ICON': _('Animated Icon'),
            'BANNER': _('Banner'),
            'COMMERCE': _('Commerce'),
            'COMMUNITY': _('Community server'),
            'DISCOVERABLE': _('Server Discovery'),
            'FEATURABLE': _('Featurable'),
            'INVITE_SPLASH': _('Invite Splash'),
            'MEMBER_VERIFICATION_GATE_ENABLED': _('Member Verification Gate Enabled'),
            'NEWS': _('News Channels'),
            'PARTNERED': _('Partnered'),
            'PREVIEW_ENABLED': _('Prieview Enabled'),
            'VANITY_URL': _('Vanity Invite'),
            'VERIFIED': _('Verified'),
            'VIP_REGIONS': _('VIP Voice Servers'),
            'WELCOME_SCREEN_ENABLED': _('Welcome screen'),
            'TICKETED_EVENTS_ENABLED': _('Ticketed events enabled'),
            'MONETIZATION_ENABLED': _('Monetization enabled'),
            'MORE_STICKERS': _('More stickers')
        }
        info = [label for feature, label in all_features.items() if feature in features]

        if info:
            e.add_field(name=_("Features"), value=', '.join(info), inline=False)

        if ctx.guild.icon and not ctx.guild.icon.is_animated():
            e.set_thumbnail(url=ctx.guild.icon.with_format("png").url)
        elif ctx.guild.icon and ctx.guild.icon.is_animated():
            e.set_thumbnail(url=ctx.guild.icon.with_format("gif").url)
        if ctx.guild.banner:
            e.set_image(url=ctx.guild.banner.with_format("png").url)
        await ctx.send(embed=e)

    @commands.command(aliases=['lc'],
                      brief=_("Lines of python code used making the bot"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def linecount(self, ctx):
        _(""" Lines of python code used making the bot """)

        pylines = 0
        pyfiles = 0
        for path, subdirs, files in os.walk('.'):
            for name in files:
                if name.endswith('.py'):
                    pyfiles += 1
                    with codecs.open('./' + str(pathlib.PurePath(path, name)), 'r', 'utf-8') as f:
                        for i, l in enumerate(f):
                            if not l.strip().startswith('#') and len(l.strip()) == 0:  # skip commented lines.
                                pylines += 1

        await ctx.send(_("{0} I am made up of **{1}** files and **{2}** lines of code.\n"
                       "You can look at my source here: https://github.com/TheMoksej/Dredd").format(self.bot.settings['emojis']['misc']['python'], f'{pyfiles:,}', f'{pylines:,}'))

    @commands.command(aliases=['source', 'src', 'github'], brief=_("Source code of the bot"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def sourcecode(self, ctx, *, command: str = None):
        _(""" Source code of the bot """)

        source_url = 'https://github.com/dredd-bot/Dredd'
        if command is None:
            return await ctx.send(_("{0} You can see my source code here: <{1}>").format(self.bot.settings['emojis']['misc']['python'], source_url))

        cmd = self.bot.get_command(command)
        if cmd is None:
            return await ctx.send(_("{0} You can see my source code here: <{1}>").format(self.bot.settings['emojis']['misc']['python'], source_url))

        source = inspect.getsource(cmd.callback)
        obj = self.bot.get_command(command.replace('.', ' '))
        module = obj.callback.__module__
        location = module.replace('.', '/') + '.py'
        src = obj.callback.__code__
        lines, firstlineno = inspect.getsourcelines(src)
        branch = 'master'
        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'

        if len(source) + 8 < 2000 - len(f"{self.bot.settings['emojis']['social']['github']} {final_url}"):
            await ctx.send(f"{self.bot.settings['emojis']['social']['github']} {final_url}```py\n{source}```")
        elif len(source) < 50000 - len(f"{self.bot.settings['emojis']['social']['github']} {final_url}"):
            await ctx.send(content=f"{self.bot.settings['emojis']['social']['github']} {final_url}", file=discord.File(filename=location, fp=BytesIO(source.encode('utf-8'))))
        else:
            await ctx.send(_("The source code for this command is too long, you can view it here:\n{0}").format(final_url))

    @commands.command(aliases=['pfp', 'av'], brief=_("Get user's profile picture"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def avatar(self, ctx, *, user: discord.User = None):
        _(""" Get user's profile picture. Fetches the user if they do not share any guilds with the bot """)

        user = user or ctx.author
        Zenpa = self.bot.get_user(373863656607318018)
        embed = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        embed.set_author(name=_("{0}'s Profile Picture!").format(user), icon_url=user.avatar.url if user.avatar else user.display_avatar.url)
        png = user.avatar.with_format('png').url if user.avatar else user.display_avatar.with_format('png').url
        jpg = user.avatar.with_format('jpg').url if user.avatar else user.display_avatar.with_format('jpg').url
        webp = user.avatar.with_format('webp').url if user.avatar else user.display_avatar.with_format('webp').url
        gif = user.avatar.with_format('gif').url if user.avatar and user.avatar.is_animated() else user.display_avatar.with_format('gif').url if user.display_avatar.is_animated() else None
        display = user.display_avatar.with_format('gif').url if user.display_avatar.is_animated() else user.display_avatar.with_format('png').url
        embed.description = _("[png]({0}) | [jpg]({1}) | [webp]({2}){3}").format(png, jpg, webp, _(' | [gif]({0})').format(gif) if gif else '')

        if user.id in [self.bot.user.id, 667117267405766696, 576476937988472853]:
            embed.set_image(url=display)
            embed.set_footer(text=_('Huge thanks to {0} for this avatar').format(Zenpa))
        else:
            embed.set_image(url=display)
        await ctx.send(embed=embed)

    @commands.command(brief=_("Displays user's banner if they have one."))
    @commands.cooldown(1, 10, commands.BucketType.user)
    @locale_doc
    async def banner(self, ctx, user: discord.User = None):
        _(""" Get user's banner if they have one. """)
        user = user or ctx.author
        banner = user.banner or (await self.bot.fetch_user(user.id)).banner

        if not banner:
            return await ctx.send(_("{0} {1} doesn't have a banner!").format(self.bot.settings['emojis']['misc']['warn'], user))

        embed = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        embed.set_author(name=_("{0}'s Banner!").format(user), icon_url=user.avatar.url if user.avatar else user.display_avatar.url)
        png = banner.with_format('png').url
        jpg = banner.with_format('jpg').url
        webp = banner.with_format('webp').url
        embed.description = _("[png]({0}) | [jpg]({1}) | [webp]({2})").format(png, jpg, webp)
        embed.set_image(url=banner.url if banner.is_animated() else banner.with_format('png').url)
        await ctx.send(embed=embed)

    @commands.command(name='support', brief=_("Get a link to bot's support server"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def support(self, ctx, embed: bool = True):
        _(""" A link to bot's support server. You can pass in boolean to get the non-embedded version of the invite """)

        if embed:
            e = discord.Embed(color=self.bot.settings['colors']['embed_color'],
                              description=_("{0} Need help? Feel free to [join the support server!]({1})").format(self.bot.settings['emojis']['avatars']['main'],
                                                                                                                  self.bot.support))
            await ctx.send(embed=e)
        else:
            await ctx.send(_("{0} Need help? Feel free to join the the support server here: {1}").format(self.bot.settings['emojis']['avatars']['main'],
                                                                                                         self.bot.support))

    @commands.command(name='invite', brief=_("Get the bot's invite"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def invite(self, ctx, embed: bool = True):
        _(""" The bot's invite link. You can pass in boolean to get the non-embedded version of the invite """)

        if embed:
            e = discord.Embed(color=self.bot.settings['colors']['embed_color'],
                              description=_("{0} Want me in your server? What are you waiting for then? [Invite now!]({1})").format(self.bot.settings['emojis']['avatars']['main'],
                                                                                                                                    self.bot.invite))
            await ctx.send(embed=e)
        else:
            await ctx.send(_("{0} Want me in your server? What are you waiting for then? Invite now:\n\n{1}").format(self.bot.settings['emojis']['avatars']['main'],
                                                                                                                     self.bot.invite))

    @commands.command(brief=_('Vote for me, please'))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def vote(self, ctx):
        _(""" Links of bot lists where you can vote for the bot """)

        botlist = self.bot.bot_lists
        e = discord.Embed(color=self.bot.settings['colors']['embed_color'], title=_("Voting Locations"))
        e.description = (_("You can vote for me in any of those lists:\n{0}\n\n*Voting will unlock some commands for you to use and will help me grow faster!*").format(
            "\n".join(f"`[{num}]` {bot_list}" for num, bot_list in enumerate(self.bot.bot_lists.values(), start=1))
        ))
        await ctx.send(embed=e)

    @commands.command(brief=_("The bot's Privacy Policy and Terms of Use"))
    @commands.cooldown(1, 5, commands.BucketType.member)
    @locale_doc
    async def privacy(self, ctx):
        _(""" The bot's Privacy Policy and Terms of Use """)

        await ctx.send(_("{0} You can see my privacy policy here: {1}").format(self.bot.settings['emojis']['social']['privacy'], self.bot.privacy))

    @commands.command(brief=_("A thank you to bot contributors"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def credits(self, ctx):
        _(""" A thank you to people who have helped find bugs, work on, and design art for the bot! """)

        designers = [f"• {x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(679646141926604827).members if x.id != 373863656607318018]
        beta_hunters = [f"{x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(764813311329566770).members]
        hunters = [f"{x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(679643117510459432).members if f"{x.name}#{x.discriminator}" not in beta_hunters]
        contribs = [f"• {x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(760499932582510602).members]
        sponsors = [f"{x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(779299456125763584).members]
        translators = [f"{x.name}#{x.discriminator}" for x in self.bot.get_guild(671078170874740756).get_role(803762986996072468).members]
        dutchy = await self.bot.fetch_user(171539705043615744)
        zenpa = await self.bot.fetch_user(373863656607318018)
        contribs.append(f"• {dutchy.name}#{dutchy.discriminator}")
        designers.append(f"• **{zenpa}**\n╠ {ctx.bot.settings['emojis']['social']['discord']} [Discord Server](https://discord.gg/A6p9tep)\n"
                         f"╚ {ctx.bot.settings['emojis']['social']['instagram']} [Instagram](https://www.instagram.com/donatas.an/)")

        e = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        e.set_author(name=_("The Dredd team says thanks to these people!"), icon_url=self.bot.user.avatar.url)
        e.description = _("""
**Sponsor(s):** {0}
**Beta bug hunter(s):** {1}
**Bug hunter(s):** {2}
**Translator(s):** {3}""").format(escape_markdown(', '.join(sponsors)),
                                  escape_markdown(', '.join(beta_hunters)),
                                  escape_markdown(', '.join(hunters)),
                                  escape_markdown(', '.join(translators)))
        e.add_field(name=_('**Graphic Designer(s):**'), value='\n'.join(designers))
        e.add_field(name=_('**Contributor(s):**'), value=escape_markdown('\n'.join(contribs)))
        await ctx.send(embed=e)

    @commands.command(brief=_("List of roles in the server"))
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def roles(self, ctx, *, role: discord.Role = None):
        _(""" List of all the server roles. Providing the role mention will display all the members in that role """)

        allroles = []
        if not role:
            for num, roles in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
                if roles.is_default():
                    continue
                allroles.append(f"`[{str(num).zfill(2)}]` {roles.mention} | {roles.id} | **[ Users : {len(roles.members)} ]**\n")
        else:
            for num, member in enumerate(role.members, start=1):
                allroles.append(f"`[{str(num).zfill(2)}]` {member.mention} | {member.id} | **[ Total Roles : {len(member.roles)} ]**\n")

        if not allroles:
            return await ctx.send(_("{0} Server has no roles").format(self.bot.settings['emojis']['misc']['warn']))

        # data = BytesIO(allroles.encode('utf-8'))
        paginator = Pages(ctx,
                          title=_("Roles in {0}").format(ctx.guild.name) if not role else _("Members in {0}").format(role.name),
                          entries=allroles,
                          per_page=15,
                          embed_color=self.bot.settings['colors']['embed_color'],
                          author=ctx.author)
        await paginator.paginate()

    @commands.command(brief=_("Get information of the role"), aliases=['rinfo', 'ri'])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def roleinfo(self, ctx, *, role: discord.Role):
        _(""" Get information of the role """)

        embed = discord.Embed(color=role.color, title=_("{0} Information").format(role.name))
        embed.add_field(name=_("__**Basic Information**__"),
                        value=_("**Role name:** {0}\n**Role mention:** {1}\n**Role ID:** {2}").format(
                            role.name, role.mention, role.id
                        ))
        rolemembers = [f"{member.name}#{member.discriminator}" for member in role.members]
        role_members = f"{', '.join(rolemembers[:10])} **(+{len(rolemembers) - 10})**" if len(rolemembers) > 10 else ', '.join(rolemembers)
        embed.add_field(name=_("__**Permissions:**__"),
                        value=', '.join(x.replace('_', ' ').title() for x, v in role.permissions if v and x.lower() != 'admin'),
                        inline=False)
        embed.add_field(name=_("__**Other Information:**__"),
                        value=_("**Is Integration:** {0}\n**Hoisted:** {1}\n**Position:** {2}\n"
                                "**Color:** {3}\n**Created:** {4}\n\n**Members:** {5}").format(
                                    role.managed, role.hoist, len(ctx.guild.roles) - role.position,
                                    role.color, btime.discord_time_format(role.created_at, source='R'), role_members
                                ),
                        inline=False)

        await ctx.send(embed=embed)

    @commands.group(name='nicknames', aliases=['nicks'],
                    brief=_('Get a list of recent nicknames member had'), invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def nicknames(self, ctx, member: discord.Member = None):
        _(""" Get a list of 10 nicknames member had in the past 90 days """)

        member = member or ctx.author

        if CM.get(self.bot, 'nicks_op', f'{ctx.author.id} - {ctx.guild.id}'):  # type: ignore
            return await ctx.send(_("{0} | **{1}** has opted out of nickname logging.").format(
                self.bot.settings['emojis']['misc']['warn'],
                member
            ))

        nicks = await self.bot.db.fetch("SELECT * FROM nicknames WHERE user_id = $1 AND guild_id = $2 ORDER BY time DESC LIMIT 10", member.id, ctx.guild.id)
        names = [str(n['nickname']) for n in nicks]
        if not names:
            return await ctx.send(_("{0} | **{1}** has had no past nicknames since I joined.").format(
                self.bot.settings['emojis']['misc']['warn'],
                member
            ))

        recent = _("**{0}'s past nicknames:**").format(member)
        for num, res in enumerate(names, start=1):
            recent += f"\n`[{num}]` {escape_markdown(res)}"

        await ctx.send(recent, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(brief=_("See permissions member has in the server"), aliases=['perms'])
    @commands.guild_only()
    @locale_doc
    async def permissions(self, ctx, member: discord.Member = None):
        _(""" See permissions member has in the server """)

        member = member or ctx.author

        sperms = dict(member.guild_permissions)

        perm = []
        for p, value in sperms.items():
            if value is True and not member.guild_permissions.administrator:
                perm.append(f"{self.bot.settings['emojis']['misc']['enabled']} {p.replace('_', ' ').title()}\n")
            if value is False and not member.guild_permissions.administrator:
                perm.append(f"{self.bot.settings['emojis']['misc']['disabled']} {p.replace('_', ' ').title()}\n")

        if member.guild_permissions.administrator:
            perm = [f"{self.bot.settings['emojis']['misc']['enabled']} Administrator"]

        paginator = Pages(ctx,
                          title=_("{0}'s Server Permissions").format(member.name),
                          entries=perm,
                          per_page=20,
                          embed_color=ctx.bot.settings['colors']['embed_color'],
                          show_entry_count=False,
                          author=ctx.author)
        await paginator.paginate()

    @commands.command(brief=_("A list of disabled commands"), aliases=['disabledcmds'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @locale_doc
    async def disabledcommands(self, ctx):
        _(""" A list of disabled commands globally and in the server """)

        cmd, cmds, cogs = [], [], []
        for res in await self.bot.db.fetch("SELECT * FROM discmds"):
            cmd.append(f"\n• **{res['command']}** - {res['reason']}")
        for res in await self.bot.db.fetch("SELECT * FROM guild_disabled WHERE guild_id = $1", ctx.guild.id):
            cmds.append(res['command'])
        for res in await self.bot.db.fetch('SELECT * FROM cog_disabled WHERE guild_id = $1', ctx.guild.id):
            cogs.append(res['cog'])

        if not cmd and not cmds and not cogs:
            return await ctx.send(_("{0} | No commands are disabled!").format(self.bot.settings['emojis']['misc']['warn']))

        e = discord.Embed(color=self.bot.settings['colors']['embed_color'], title=_("List of all disabled commands"))
        e.description = _("The following commands can only be run by bot staff")
        if cmd:
            e.add_field(name=_('**Globally disabled commands:**'), value=f"{''.join(cmd)}", inline=False)
        if cmds:
            e.add_field(name=_("**Disabled commands in this server:**"), value="- {0}".format(
                ', '.join(cmds)[:30]
            ))
        if cogs:
            e.add_field(name=_("**Disabled categories in this server:**"), value="• {0}".format('\n• '.join(cogs)), inline=False)
        await ctx.send(embed=e)

    @commands.command(brief=_("Get a list of all the server emotes"), aliases=['se', 'emotes'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @locale_doc
    async def serveremotes(self, ctx):
        _(""" Get a list of all the server emotes """)

        _all = [f"`[{num}]` {e} **{e.name}** | {e.id}\n" for num, e in enumerate(ctx.guild.emojis, start=1)]

        if not _all:
            return await ctx.send(_("{0} | This server has no emotes!").format(self.bot.settings['emojis']['misc']['warn']))

        paginator = Pages(ctx,
                          title=_("{0} emotes list").format(ctx.guild.name),
                          entries=_all,
                          per_page=15,
                          embed_color=self.bot.settings['colors']['embed_color'],
                          author=ctx.author)
        await paginator.paginate()

    @commands.command(brief=_("A list of bot's partners"), aliases=['partners', 'plist'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def partnerslist(self, ctx):  # sourcery no-metrics
        _(""" A list of bot's partners """)

        partners = await self.bot.db.fetch("SELECT * FROM partners ORDER BY time ASC")

        partner = []
        for res in partners:
            if res['type'] == 0:
                partnered = f"{self.bot.get_user(res['_id'])} ({res['_id']})"
                ptype = f"Bot: [{self.bot.get_user(res['bot_id'])}](https://discord.com/users/{res['bot_id']})"
                if partnered is None:
                    partnered = f"({res['_id']})"
            elif res['type'] == 1:
                guild = self.bot.get_guild(res['_id'])
                if guild is not None:
                    try:
                        guildinv = await guild.invites()
                        for inv in guildinv[:1]:
                            partnered = f"[{guild}]({inv}) ({res['_id']}) | Owner: {guild.owner} ({guild.owner.id})"
                    except Exception:
                        partnered = f"{guild} ({res['_id']}) | Owner: {guild.owner} ({guild.owner.id})"
                    ptype = _('Server')
                elif not guild and res['valid']:
                    partnered = f"[{res['name']}]({res['invite']})"
                    ptype = _('Server')
                else:
                    partnered = f"({res['_id']})"
                    ptype = 'Invalid type, unpartner.'
            partner.append(_("**Partner:** {0}\n"
                             "**Partnered for:** {1}\n"
                             "**Partner type:** {2}\n"
                             "**Partnered message:**\n>>> {3}").format(
                                 partnered,
                                 btime.human_timedelta(res['time'], source=datetime.utcnow(), suffix=None),
                                 ptype,
                                 res['message']
                             ))

        msg = await self.bot.get_channel(self.bot.settings['channels']['partners']).fetch_message(741690217379135569)
        partner.append(_("Interested in partnering? Here's the official message:\n\n{0}"
                         " or [join the support server]({1})").format(
                             msg.content,
                             self.bot.support
                         ))

        paginator = Pages(ctx,
                          title=_("Partnered people with Dredd"),
                          entries=partner,
                          per_page=1,
                          embed_color=self.bot.settings['colors']['embed_color'])
        await paginator.paginate()

    @commands.command(aliases=['showbadges'], brief=_("A list of user's bot acknowledgements"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def badges(self, ctx, *, user: typing.Union[discord.User, str] = None):
        _(""" A list of user's bot acknowledgements """)

        embcolor = self.bot.settings['colors']['embed_color']
        member = await default.find_user(ctx, user)
        if not member:
            return await ctx.send(_("{0} | That user could not be found.").format(ctx.bot.settings['emojis']['misc']['warn']))

        if not self.bot.get_user(member.id):
            embcolor = ctx.bot.settings['colors']['fetch_color']

        badges = default.bot_acknowledgements(ctx, member)

        if not badges:
            return await ctx.send(_("{0} | **{1}** has no bot acknowledgements").format(self.bot.settings['emojis']['misc']['warn'],
                                                                                        member))
        e = discord.Embed(color=embcolor)
        e.set_author(name=_("{0}'s Bot Acknowledgements").format(member), icon_url=member.avatar.url if member.avatar else member.display_avatar.url)
        e.description = badges
        await ctx.send(embed=e)

    @commands.command(brief=_("Top 10 most used commands"), aliases=['topcmds'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def topcommands(self, ctx, option: str = None):  # sourcery no-metrics
        _(""" A list of 10 most used commands. You may also include: `me` and `guild` to see a list of your or guild's most used commands """)
        opts = ['me', 'guild']
        if await self.bot.is_owner(ctx.author):
            opts.append(option)
        if not option or option not in opts:
            cmd = await self.bot.db.fetch("select command, sum(usage) from command_logs where user_id != $1 group by command order by sum(usage) desc LIMIT 10", 345457928972533773)
            index = _('**Top 10 most used commands:**')
            query1 = 'select sum(usage) from command_logs where user_id != $1'
            total = await self.bot.db.fetchval(query1, 345457928972533773)
            if not total:
                return await ctx.send(_("{0} Looks like you haven't used any commands :/").format(self.bot.settings['emojis']['misc']['warn']))
            index2 = _('In total users have used {0} commands!').format(total)
        elif option == 'me':
            query = 'select command, sum(usage) from command_logs where user_id = $1 group by command order by sum(usage) desc limit 10'
            cmd = await self.bot.db.fetch(query, ctx.author.id)
            index = _('**Your top 10 most used commands**')
            total = await self.bot.db.fetchval('select sum(usage) from command_logs where user_id = $1', ctx.author.id)
            if not total:
                return await ctx.send(_("{0} Looks like you haven't used any commands :/").format(self.bot.settings['emojis']['misc']['warn']))
            index2 = _("In total you have used {0:,} commands!").format(total)
        elif option == 'guild':
            if not ctx.guild:
                return await ctx.send(_("{0} This command must be ran in any server, not dms").format(self.bot.settings['emojis']['misc']['warn']))
            query = 'select command, sum(usage) from command_logs where guild_id = $1 and user_id != $2 group by command order by sum(usage) desc limit 10'
            cmd = await self.bot.db.fetch(query, ctx.guild.id, 345457928972533773)
            index = _('**Top 10 most used commands in this server:**')
            total = await self.bot.db.fetchval('select sum(usage) from command_logs where guild_id = $1 and user_id != $2', ctx.guild.id, 345457928972533773)
            if not total:
                return await ctx.send(_("{0} Looks like you haven't used any commands :/").format(self.bot.settings['emojis']['misc']['warn']))
            index2 = _("In total this guild has used {0:,} commands!").format(total)
        else:
            query = 'select command, sum(usage) from command_logs where user_id = $1 group by command order by sum(usage) desc limit 10'
            cmd = await self.bot.db.fetch(query, int(option))
            index = f'**Top 10 most used commands by {self.bot.get_user(int(option))}:**'
            total = await self.bot.db.fetchval('select sum(usage) from command_logs where user_id = $1', int(option))
            if not total:
                return await ctx.send("{0} Looks like they haven't used any commands :/".format(self.bot.settings['emojis']['misc']['warn']))
            index2 = f"In total {self.bot.get_user(int(option))} has used {total:,} commands!"

        countmsg = "```ml\n"
        command = _('Command')
        used = _('Used')
        countmsg += f"{command}                   | {used}\n"
        countmsg += "——————————————————————————————————"
        for res in cmd:
            countmsg += f"\n{res['command']}{' '*int(26 - len(str(res['command'])))}| {int(res['sum']):,}"
        countmsg += '\n```'
        countmsg += index2

        await ctx.send(f"{index}{countmsg}")

    @commands.command(brief=_("A list of newest members in the server"))
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def newusers(self, ctx, *, count: int):
        _(""" A list of newest members in the server """)

        if len(ctx.guild.members) < count:
            return await ctx.send(_("This server has {0} members").format(len(ctx.guild.members)))
        counts = max(min(count, 10), 1)

        if not ctx.guild.chunked:
            await self.bot.request_offline_members(ctx.guild)
        members = sorted(ctx.guild.members, key=lambda m: m.joined_at, reverse=True)[:counts]
        e = discord.Embed(title=_('Newest member(s) in this server:'), colour=self.bot.settings['colors']['embed_color'])
        for num, member in enumerate(members, start=1):
            data = _('**Joined Server at** {0}\n**Account created at** {1}').format(btime.discord_time_format(member.joined_at, source='R'),
                                                                                    btime.discord_time_format(member.created_at, source='R'))
            e.add_field(name=f'`[{num}]` **{member}** ({member.id})', value=data, inline=False)
            if count > 10:
                e.set_footer(text=_("The limit is set to 10"))

        await ctx.send(embed=e)

    @commands.command(brief="A list of members with specific character(s) in their name", aliases=['members'])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @locale_doc
    async def listmembers(self, ctx, *, name: str):
        _(""" A list of members with specific character(s) in their name """)

        if len(name) > 32:
            return await ctx.send(_("{0} Names can't be longer than 32 characters! "
                                    "You're {1} characters over.").format(self.bot.settings['emojis']['misc']['warn'],
                                                                          len(name) - 32))

        members = await ctx.guild.query_members(name, limit=7)

        if not members:
            return await ctx.send(_("{0} Couldn't find anyone with a given regex.").format(self.bot.settings['emojis']['misc']['warn']))

        all_members = [f"`[{num}]` **{member}** - {member.id}\n" for num, member in enumerate(members, start=1)]

        e = discord.Embed(color=self.bot.settings['colors']['embed_color'])
        e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        e.title = _('Users with regex {0} in their name').format(name)
        e.description = f"{''.join(all_members)}"
        await ctx.send(embed=e)

    # Credits for this go to https://github.com/Rapptz/RoboDanny.
    @commands.group(aliases=['rtfd'], invoke_without_command=True,
                    brief=_("Documentation of enhanced discord.py"))
    @locale_doc
    async def rtfm(self, ctx, *, obj: str = None):
        _(""" Documentation of enhanced discord.py """)
        await rtfm.do_rtfm(self, ctx, 'latest', obj)

    @rtfm.command(name='python', aliases=['py'],
                  brief=_("Documentation of python"))
    @locale_doc
    async def rtfm_python(self, ctx, *, obj: str = None):
        _(""" Documentation of python """)
        await rtfm.do_rtfm(self, ctx, 'python', obj)

    @commands.command(brief=_("Shows a snowflake information"))
    @locale_doc
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def snowflake(self, ctx, *, snowflake: int):
        _(""" Shows the information of a Discord snowflake """)

        timestamp = snowflake_time(snowflake)
        worker_id = (snowflake & 0x3E0000) >> 17
        process_id = (snowflake & 0x1F000) >> 12
        increment = snowflake & 0xFFF

        e = discord.Embed(color=self.bot.settings['colors']['embed_color'], title=_("Snowflake information"), url="https://discord.com/developers/docs/reference#snowflakes")
        e.description = _("**Created at:** {0} ({1})\n**Worker ID:** {2}\n**Process ID:** {3}\n**Increment:** {4}".format(
            btime.discord_time_format(timestamp), btime.discord_time_format(timestamp, "R"), worker_id, process_id, increment
        ))
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Info(bot))
