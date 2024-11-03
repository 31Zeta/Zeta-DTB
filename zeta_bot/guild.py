import discord
import os
from typing import Union

from zeta_bot import (
    errors,
    language,
    decorators,
    utils,
    log,
    member,
)


class Guild:
    def __init__(self, guild: discord.guild, lib_root: str):
        self._guild = guild
        self._id = self._guild.id
        self._name = self._guild.name
        self._lib_root = lib_root
        self._root = f"{self._lib_root}/{self._guild.id}"
        self._path = f"{self._root}/{self._guild.id}.json"
        self._logger = log.Log()
        self._active_views = {}

        if not os.path.exists(self._root):
            utils.create_folder(self._root)

        try:
            self.load()
        except FileNotFoundError:
            self.save()
        except KeyError:
            self.save()
        except errors.JSONFileError:
            self.save()

        self.voice_volume = 100.0

        self._logger.rp(f"服务器相关信息初始化完成：{self._name}", self._name)

    def __str__(self):
        return self._name

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_voice_volume(self) -> float:
        return self.voice_volume

    def get_active_views(self) -> dict:
        return self._active_views

    def set_voice_volume(self, volume: Union[int, float]) -> None:
        self.voice_volume = float(volume)

    async def refresh_list_view(self) -> None:
        if "playlist_menu_view" in self._active_views and self._active_views["playlist_menu_view"] is not None:
            await self._active_views["playlist_menu_view"].refresh_menu()

    def save(self) -> None:
        utils.json_save(self._path, self)

    def load(self) -> None:
        loaded_dict = utils.json_load(self._path)

    def encode(self) -> dict:
        return {
            "id": self._id,
            "name": self._name,
        }


@decorators.Singleton
class GuildLibrary:
    def __init__(self):
        self._root = "./data/guilds"
        utils.create_folder(self._root)
        self._guild_dict = {}
        self._hashtag_file_path = f"{self._root}/#Guilds.json"
        self._logger = log.Log()

        # 检查#Guilds文件
        if not os.path.exists(self._hashtag_file_path):
            utils.json_save(self._hashtag_file_path, {})
        try:
            self.hashtag_file = {}
            self.load_hashtag_file()
        except errors.JSONFileError:
            raise errors.JSONFileError

    def save_hashtag_file(self):
        utils.json_save(self._hashtag_file_path, self.hashtag_file)

    def load_hashtag_file(self):
        loaded_dict = utils.json_load(self._hashtag_file_path)
        # 将键值重建为int格式
        for key in loaded_dict:
            try:
                new_key = int(key)
            except ValueError:
                new_key = key
            self.hashtag_file[new_key] = loaded_dict[key]

    def check(self, ctx: Union[discord.ApplicationContext, discord.AutocompleteContext]) -> None:
        if isinstance(ctx, discord.ApplicationContext):
            guild_id = ctx.guild.id
            guild_name = ctx.guild.name
        else:
            guild_id = ctx.interaction.guild.id
            guild_name = ctx.interaction.guild.name

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self._guild_dict:
            if isinstance(ctx, discord.ApplicationContext):
                self._guild_dict[guild_id] = Guild(ctx.guild, self._root)
            else:
                self._guild_dict[guild_id] = Guild(ctx.interaction.guild, self._root)

        # 更新#Guilds文件
        self.load_hashtag_file()
        if guild_id not in self.hashtag_file or guild_name != self.hashtag_file[guild_id]:
            self.hashtag_file[guild_id] = guild_name
            self.save_hashtag_file()

    def check_by_guild_obj(self, guild: discord.Guild) -> None:
        guild_id = guild.id
        guild_name = guild.name

        # 如果guild_dict中不存在本Discord服务器
        if guild_id not in self._guild_dict:
            self._guild_dict[guild_id] = Guild(guild, self._root)

        # 更新#Guilds文件
        self.load_hashtag_file()
        if guild_id not in self.hashtag_file or guild_name != self.hashtag_file[guild_id]:
            self.hashtag_file[guild_id] = guild_name
            self.save_hashtag_file()

    def get_guild(self, ctx: Union[discord.ApplicationContext, discord.AutocompleteContext]) -> Union[Guild, None]:
        if isinstance(ctx, discord.ApplicationContext):
            guild_id = ctx.guild.id
        else:
            # isinstance ctx → discord.AutocompleteContext
            guild_id = ctx.interaction.guild.id

        if guild_id in self._guild_dict:
            return self._guild_dict[guild_id]
        else:
            return None

    def save_all(self) -> None:
        self._logger.rp("开始保存各Discord服务器数据", "[Discord服务器库]")
        for key in self._guild_dict:
            self._guild_dict[key].save()
        self._logger.rp("各Discord服务器数据保存完毕", "[Discord服务器库]")
