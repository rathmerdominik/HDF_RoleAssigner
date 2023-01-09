import os
import toml
import logging

import discord
from discord import Embed, File
from discord.ext import commands

from typing import Dict, Union, List

from .types.config import Entry, Message

from .utils.helper import load_config, write_config


logger = logging.getLogger(__name__)


class RoleAssigner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

        self.config = load_config()

    async def get_file_from_str(self, url: str) -> File:
        file_loc = os.path.dirname(__file__)
        return File(f"{file_loc}/assets/{url}", url)

    async def gen_entries(self, embed: Embed, entries: Dict[str, Entry]) -> Embed:

        for entry in entries.keys():
            embed.add_field(name=entries[entry].title, value=entries[entry].description, inline=False)

        return embed

    async def assemble_message(
        self,
        title: str = None,
        title_url: str = None,
        description: str = None,
        thumbnail: Union[File, str] = None,
        color: str = None,
        author_name: str = None,
        author_icon: str = None,
        author_link: str = None,
        footer_text: str = None,
        footer_icon: str = None,
        entries: Dict[str, Entry] = None,
    ) -> Embed:

        embed = Embed(
            title=title,
            description=description,
            color=int(color, 16),
            url=title_url,
        )
        
        if thumbnail:
            if isinstance(thumbnail, discord.file.File):
                embed.set_thumbnail(url=f"attachment://{thumbnail.filename}")
            else:
                embed.set_thumbnail(url=thumbnail)

        if author_name:
            if isinstance(author_icon, discord.file.File):
                author_icon = await self.get_file_from_str(author_icon)
                embed.set_author(
                    name=author_name,
                    url=author_link,
                    icon_url=f"attachment://{author_icon.filename}",
                )
            else:
                embed.set_author(
                    name=author_name,
                    url=author_link,
                    icon_url=author_icon,
                )

        if footer_text:
            if isinstance(footer_icon, discord.file.File):
                footer_icon = await self.get_file_from_str(footer_icon)
                embed.set_footer(
                    text=footer_text, icon_url=f"attachment://{footer_icon.filename}"
                )
            else:
                embed.set_footer(text=footer_text, icon_url=footer_icon)

        if entries:
            embed = await self.gen_entries(embed, entries)

        return embed

    async def apply_reactions(
        self,
        message: discord.Message,
        entries: List[Dict[str, Entry]],
        guild: discord.Guild,
    ):
        applied_reactions = message.reactions

        for entry in entries:
            emoji = entries[entry].emoji_id

            if emoji in applied_reactions:
                continue

            if not isinstance(emoji, str):
                emoji = await guild.fetch_emoji(entries[entry].emoji_id)

            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        messages: Message = self.config.messages
        guild = self.bot.get_guild(payload.guild_id)

        for message in messages.keys():
            if not messages[message].message_id == payload.message_id:
                continue

            entries: List[Dict[str, Entry]] = messages[message].entries
            for entry in entries:

                if entries[entry].emoji_id == payload.emoji.id:
                    role = guild.get_role(entries[entry].role_id)

                    if role not in payload.member.roles:
                        await payload.member.add_roles(
                            role, reason="Added by RoleAssigner"
                        )

                    elif self.config.remove_role_when_owned:
                        await payload.member.remove_roles(
                            role, reason="Removed by RoleAssigner"
                        )

        channel = await guild.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_ready(self):

        guild = self.bot.get_guild(self.config.guild_id)

        for message in self.config.messages.keys():
            try:
                channel = guild.get_channel(self.config.messages[message].channel_id)

                if not channel:
                    logger.error(
                        f"Channel ID for {message} is non existent! Please correct"
                    )
                    return

                thumbnail = self.config.messages[message].thumbnail

                # TODO this entire block may have to be optimized. I haven't found a better way yet. But this cant be it... Problem lies with discord sending files
                logger.debug(thumbnail)
                if thumbnail and not thumbnail.startswith(("http://", "https://")):

                    file_loc = os.path.dirname(__file__)
                    file = File(f"{file_loc}/assets/{thumbnail}", thumbnail)

                    logger.debug(file)
                    embed = await self.assemble_message(
                        title=self.config.messages[message].title,
                        title_url=self.config.messages[message].title_url,
                        description=self.config.messages[message].description,
                        thumbnail=file,
                        color=self.config.messages[message].color,
                        author_name=self.config.messages[message].author.name,
                        author_icon=self.config.messages[message].author.icon,
                        author_link=self.config.messages[message].author.url,
                        footer_text=self.config.messages[message].footer.text,
                        footer_icon=self.config.messages[message].footer.icon_url,
                        entries=self.config.messages[message].entries,
                    )
                    # TODO this just cant be the correct solution. Find a better way than this

                    try:
                        created_message = await channel.fetch_message(
                            self.config.messages[message].message_id
                        )
                        await created_message.edit(embed=embed, attachments=[file])

                    except discord.errors.NotFound:
                        logger.info(f"No message found. Creating one for {message}")
                        self.config.messages[message].message_id = 0
                        created_message = await channel.send(embed=embed, file=file)
                else:
                    embed = await self.assemble_message(
                        title=self.config.messages[message].title,
                        title_url=self.config.messages[message].title_url,
                        description=self.config.messages[message].description,
                        thumbnail=thumbnail,
                        color=self.config.messages[message].color,
                        author_name=self.config.messages[message].author.name,
                        author_icon=self.config.messages[message].author.icon,
                        author_link=self.config.messages[message].author.url,
                        footer_text=self.config.messages[message].footer.text,
                        footer_icon=self.config.messages[message].footer.icon_url,
                        entries=self.config.messages[message].entries,
                    )

                    # TODO this just cant be the correct solution. Find a better way than this

                    try:
                        created_message = await channel.fetch_message(
                            self.config.messages[message].message_id
                        )
                        await created_message.edit(embed=embed, attachments=[])

                    except discord.errors.NotFound:
                        logger.info(f"No message found. Creating one for {message}")
                        self.config.messages[message].message_id = 0

                        created_message = await channel.send(embed=embed)

                if not self.config.messages[message].message_id:
                    self.config.messages[message].message_id = created_message.id
                    write_config(self.config)

                if self.config.messages[message].entries:
                    await self.apply_reactions(
                        created_message, self.config.messages[message].entries, guild
                    )

            except discord.errors.HTTPException as e:
                logger.error(
                    f'There is an invalid URL in your "{message}" block. Please fix potentially wrong URLs. Remember links have to start with http or https. Exact error message: {str(e)}'
                )
                continue
            except ValueError as e:
                if "invalid literal for int()" in str(e):
                    logger.error(
                        f'Color attribute has been set wrongly for the "{message}" message block. Only use Hex values e.g FFFFFF or 000000. Exact error message: {str(e)}'
                    )
                continue

            except Exception as e:
                logger.exception(
                    f'Unhandeled Error occured. Please report with this message: "{e}"'
                )
                continue


async def setup(bot: commands.Bot):
    logger.info("Role Assigner Module locked and loaded!")
    await bot.add_cog(RoleAssigner(bot))


async def teardown(bot: commands.Bot):
    logger.info("Role Assigner Module unloaded!")
