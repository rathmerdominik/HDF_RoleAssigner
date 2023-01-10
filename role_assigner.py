import os
import toml
import logging

import discord
from discord import Embed, File
from discord.ui import View, Button
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

    async def gen_file_if_needed(self, url_str: str) -> Union[File, str]:
        if url_str and not url_str.startswith(("http://", "https://")):
            return await self.get_file_from_str(url_str)
        return url_str

    async def gen_entries(self, embed: Embed, entries: Dict[str, Entry]) -> Embed:

        for entry in entries.keys():
            emoji = entries[entry].emoji_id
            if isinstance(entries[entry].emoji_id, int):
                guild = self.bot.get_guild(self.config.guild_id)
                emoji = await guild.fetch_emoji(entries[entry].emoji_id)

            embed.add_field(
                name=entries[entry].title,
                value=entries[entry].description,
                inline=False,
            )

        return embed

    async def assemble_message(
        self,
        title: str = None,
        title_url: str = None,
        description: str = None,
        thumbnail: Union[File, str] = None,
        color: str = None,
        author_name: str = None,
        author_icon: Union[File, str] = None,
        author_link: str = None,
        footer_text: str = None,
        footer_icon: Union[File, str] = None,
        entries: Dict[str, Entry] = None,
    ) -> Embed:

        embed = Embed(
            title=title,
            description=description,
            color=int(color, 16),
            url=title_url,
        )

        if thumbnail:
            if isinstance(thumbnail, File):
                embed.set_thumbnail(url=f"attachment://{thumbnail.filename}")
            else:
                embed.set_thumbnail(url=thumbnail)

        if author_name:
            if isinstance(author_icon, discord.file.File):
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
            if isinstance(footer_icon, File):
                embed.set_footer(
                    text=footer_text, icon_url=f"attachment://{footer_icon.filename}"
                )
            else:
                embed.set_footer(text=footer_text, icon_url=footer_icon)

        if entries:
            embed = await self.gen_entries(embed, entries)

        return embed

    async def generate_buttons(
        self,
        entries: List[Dict[str, Entry]],
        guild: discord.Guild,
    ) -> View:

        view = View()

        for entry in entries:
            emoji = entries[entry].emoji_id
            if not emoji:
                continue

            if not isinstance(emoji, str):
                emoji = await guild.fetch_emoji(entries[entry].emoji_id)

            view.add_item(
                Button(
                    label=entries[entry].title,
                    emoji=emoji,
                    custom_id=f"{entries[entry].role_id}",
                )
            )

        return view

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        guild = interaction.guild
        role_id = int(interaction.data["custom_id"])
        role = guild.get_role(role_id)

        if role not in interaction.user.roles:
            await interaction.user.add_roles(role, reason="Added by RoleAssigner")
            await interaction.response.send_message(
                f'Successfully added you to "{role.name}" group!', ephemeral=True
            )

        elif self.config.remove_role_when_owned:
            await interaction.user.remove_roles(role, reason="Removed by RoleAssigner")
            await interaction.response.send_message(
                f'Successfully removed you from the "{role.name}" group!',
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_ready(self):

        guild = self.bot.get_guild(self.config.guild_id)

        for message in self.config.messages.keys():
            try:
                try:
                    channel = guild.get_channel(
                        self.config.messages[message].channel_id
                    )
                except AttributeError:
                    logger.error(
                        "You forgot to set a guild ID. Please set it in the config.toml file"
                    )
                    return

                if not channel:
                    logger.error(
                        f"Channel ID for {message} is non existent! Please correct"
                    )
                    return

                thumbnail = await self.gen_file_if_needed(
                    self.config.messages[message].thumbnail
                )
                author_icon = await self.gen_file_if_needed(
                    self.config.messages[message].author.icon
                )
                footer_icon = await self.gen_file_if_needed(
                    self.config.messages[message].footer.icon_url
                )

                files = []
                if isinstance(thumbnail, File):
                    files.append(thumbnail)
                if isinstance(author_icon, File):
                    files.append(author_icon)
                if isinstance(footer_icon, File):
                    files.append(footer_icon)

                embed = await self.assemble_message(
                    title=self.config.messages[message].title,
                    title_url=self.config.messages[message].title_url,
                    description=self.config.messages[message].description,
                    thumbnail=thumbnail,
                    color=self.config.messages[message].color,
                    author_name=self.config.messages[message].author.name,
                    author_icon=author_icon,
                    author_link=self.config.messages[message].author.url,
                    footer_text=self.config.messages[message].footer.text,
                    footer_icon=footer_icon,
                    entries=self.config.messages[message].entries,
                )

                if self.config.messages[message].entries:
                    buttons: View = await self.generate_buttons(
                        self.config.messages[message].entries, guild
                    )

                try:
                    created_message = await channel.fetch_message(
                        self.config.messages[message].message_id
                    )
                    await created_message.edit(
                        embed=embed, attachments=files, view=buttons
                    )

                except discord.errors.NotFound:
                    logger.info(f"No message found. Creating one for {message}")
                    self.config.messages[message].message_id = 0
                    created_message = await channel.send(
                        embed=embed, files=files, view=buttons
                    )

                if not self.config.messages[message].message_id:
                    self.config.messages[message].message_id = created_message.id
                    write_config(self.config)

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
