import discord
import sys
import os
import asyncio
from typing import Any, Union, List, Dict

from discord import Component
from discord.ext import commands
from discord.commands import option
from discord.ui import Button, View
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import faster_whisper

from zeta_bot import (
    errors,
    language,
    utils,
    setting,
    log,
    member,
    guild,
)

version = "0.0.1"
author = "炤铭Zeta (31Zeta)"
python_path = sys.executable
pycord_version = discord.__version__
update_time = "2024.10.15"

logo = (
    "________  _______  _________  ________               ________  ________  _________   \n"
    "|\\_____  \\|\\  ___ \\|\\___   ___\\\\   __  \\             |\\   __  \\|\\   __  \\|\\___   ___\\ \n"
    " \\|___/  /\\ \\   __/\\|___ \\  \\_\\ \\  \\|\\  \\  __________\\ \\  \\|\\ /\\ \\  \\|\\  \\|___ \\  \\_| \n"
    "     /  / /\\ \\  \\_|/__  \\ \\  \\ \\ \\   __  \\|\\__________\\ \\   __  \\ \\  \\\\\\  \\   \\ \\  \\  \n"
    "    /  /_/__\\ \\  \\_|\\ \\  \\ \\  \\ \\ \\  \\ \\  \\|__________|\\ \\  \\|\\  \\ \\  \\\\\\  \\   \\ \\  \\ \n"
    "   |\\________\\ \\_______\\  \\ \\__\\ \\ \\__\\ \\__\\            \\ \\_______\\ \\_______\\   \\ \\__\\\n"
    "    \\|_______|\\|_______|   \\|__|  \\|__|\\|__|             \\|_______|\\|_______|    \\|__|"
)

version_header = (f"Zeta-DTB Version：{version}\n"
                  f"Pycord Version：{pycord_version}\n")

# 多语言模块
lang = language.Lang()
_ = lang.get_string
printl = lang.printl

# 初始化机器人设置
intents = discord.Intents.all()
bot = discord.Bot(help_command=None, case_insensitive=True, intents=intents)
startup_time = utils.time()

# 设置配置文件
utils.create_folder("./configs")
lang_setting = setting.Setting("./configs/language_config.json", setting.language_setting_configs)
lang.set_system_language(lang_setting.value("language"))
setting = setting.Setting("./configs/system_config.json", setting.bot_setting_configs, lang_setting.value("language"))
bot_name = setting.value("bot_name")

# 设置日志记录器
utils.create_folder("./logs")
log_name_time = startup_time.replace(":", "_")
error_log_path = f"./logs/{log_name_time}_errors.log"
log_path = f"./logs/{log_name_time}.log"
logger = log.Log(error_log_path, log_path, setting.value("log"), version_header)

# 设置用户和Discord服务器管理
utils.create_folder("./data")
member_lib = member.MemberLibrary()
guild_lib = guild.GuildLibrary()

# 设置录制功能
connections = {}

logger.rp("初始化完成", "[系统]")


def start(mode: str) -> None:
    """
    根据模式启动程序
    """
    if mode == "normal" or mode == "":
        run_bot()
    elif mode == "setting":
        setting.modify_mode()
        run_bot()
    elif mode == "reset":
        setting.reset_setting()
        run_bot()
    else:
        raise errors.BootModeNotFound


if __name__ == "__main__":
    start("normal")


def run_bot() -> None:
    """启动机器人"""
    try:
        bot.run(setting.value("token"))
    except errors.LoginFailure:
        print("登录失败，请检查Discord机器人令牌是否正确，在启动指令后添加\" --mode=setting\"来修改设置")


@bot.event
async def on_error(exception):
    logger.on_error(exception)


@bot.event
async def on_application_command_error(ctx, exception):
    logger.on_application_command_error(ctx, exception)

    # 向用户回复发生错误
    await ctx.respond("发生错误")


async def command_check(ctx: discord.ApplicationContext) -> bool:
    """
    对指令触发进行日志记录，检测用户是否记录在案，检测用户是否有权限使用该条指令
    """
    member_lib.check(ctx)
    user_group = member_lib.get_group(ctx.user.id)
    operation = str(ctx.command)
    # 如果用户是机器人所有者
    if str(ctx.user.id) == setting.value("owner"):
        logger.rp(f"用户 {ctx.user} [用户组: 机器人所有者] 发送指令：<{operation}>", ctx.guild)
        return True
    elif member_lib.allow(ctx.user.id, operation):
        logger.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>", ctx.guild)
        return True
    else:
        logger.rp(f"用户 {ctx.user} [用户组: {user_group}] 发送指令：<{operation}>，权限不足，操作已被拒绝", ctx.guild)
        await ctx.respond("权限不足")
        return False


# 启动就绪时
@bot.event
async def on_ready():
    """
    当机器人启动完成时自动调用
    """

    current_time = utils.time()
    logger.rp(f"登录完成：以{bot.user}的身份登录，登录时间：{current_time}", "[系统]")

    # 启动定时任务框架
    scheduler_ar_1 = AsyncIOScheduler()
    scheduler_ar_2 = AsyncIOScheduler()

    if setting.value("auto_reboot"):
        # 设置自动重启
        ar_timezone = "Asia/Shanghai"
        ar_time = utils.time_split(setting.value("ar_time"))
        scheduler_ar_1.add_job(
            auto_reboot, CronTrigger(
                timezone=ar_timezone, hour=ar_time[0],
                minute=ar_time[1], second=ar_time[2]
            )
        )

        if setting.value("ar_reminder"):
            # 设置自动重启提醒
            ar_r_time = utils.time_split(setting.value("ar_reminder_time"))
            scheduler_ar_2.add_job(
                auto_reboot_reminder, CronTrigger(
                    timezone=ar_timezone, hour=ar_r_time[0],
                    minute=ar_r_time[1], second=ar_r_time[2]
                )
            )

        scheduler_ar_1.start()
        scheduler_ar_2.start()

        logger.rp(
            f"设置自动重启时间为 {ar_time[0]}时{ar_time[1]}分{ar_time[2]}秒", "[系统]"
        )

    # 设置机器人状态
    bot_activity_type = discord.ActivityType.playing
    await bot.change_presence(
        activity=discord.Activity(type=bot_activity_type, name=setting.value("default_activity")))

    logger.rp(f"启动完成", "[系统]")


# 文字频道中收到信息时
@bot.event
async def on_message(message):
    """
    当检测到消息时调用

    :param message:频道中的消息
    :return:
    """
    if message.author == bot.user:
        return

    if message.content.startswith(bot_name):
        await message.channel.send("我在")

    if message.content.startswith("test"):
        await message.channel.send(_("custom.reply_1"))


async def auto_reboot():
    """
    用于执行定时重启，如果<auto_reboot_announcement>为True则广播重启消息
    """
    current_time = utils.time()
    logger.rp(f"执行自动定时重启", "[系统]")
    guild_lib.save_all()
    # user_library.save()
    if setting.value("ar_announcement"):
        for current_guild in bot.guilds:
            voice_client = current_guild.voice_client
            if voice_client is not None:
                await current_guild.text_channels[0].send(f"{current_time} 开始执行自动定时重启")
    os.execl(python_path, python_path, * sys.argv)


async def auto_reboot_reminder():
    """
    向机器人仍在语音频道中的所有服务器的第一个文字频道发送即将重启通知
    """
    ar_time = setting.value("ar_time")
    logger.rp(f"发送自动重启通知", "[系统]")
    for current_guild in bot.guilds:
        voice_client = current_guild.voice_client
        if voice_client is not None:
            await current_guild.text_channels[0].send(f"注意：将在{ar_time}时自动重启")


async def eos(ctx: discord.ApplicationContext, response, content: str, view=None, debug=False)\
        -> Union[discord.InteractionMessage, discord.Message]:
    """
    [Edit Or Send]
    如果<response>可以被编辑，则将<response>编辑为<content>
    否则使用<ctx>发送<content>
    """
    if debug:
        print(f"[DEBUG] eos参数response类型为：{type(response)}\n")

    if isinstance(response, discord.Interaction):
        return await response.edit_original_response(content=content, view=view)
    elif isinstance(response, discord.InteractionMessage):
        return await response.edit(content=content, view=view)
    elif isinstance(response, discord.Message):
        return await response.edit(content=content, view=view)
    else:
        return await ctx.send(content=content, view=view)


async def ec(target, content: str, view=None) -> Union[None, discord.Message]:
    """
    [Edit Cumulatively]
    如果修改次数大于一次，请确保传入本方法第一次返回的Message对象，因为Interaction只能获取最初的信息
    """
    if isinstance(target, discord.Message):
        original_message = target.content
    elif isinstance(target, discord.Interaction):
        target_original_response = await target.original_response()
        original_message = target_original_response.content
    elif isinstance(target, discord.InteractionMessage):
        original_message = target.content
    else:
        return None
    new_content = original_message + '\n' + content
    return await target.edit(content=new_content, view=view)


def get_voice_client_status(voice_client: discord.VoiceProtocol) -> int:
    """
    获取voice_client的播放状态
        0 - 待机中
        1 - 正在播放
        2 - 暂停
        3 - 不在语音频道中
    """
    if not voice_client:
        voice_client_status = 3
    elif voice_client.is_playing():
        voice_client_status = 1
    elif voice_client.is_paused():
        voice_client_status = 2
    else:
        voice_client_status = 0
    return voice_client_status


def get_voice_client_status_str(status_code: int) -> str:
    """
    将voice_client播放状态代码转换为文本
        0 - 待机中
        1 - 正在播放
        2 - 暂停
        3 - 不在语音频道中
    """
    if status_code == 3:
        voice_client_status = "不在语音频道中"
    elif status_code == 1:
        voice_client_status = "正在播放"
    elif status_code == 2:
        voice_client_status = "暂停"
    elif status_code == 0:
        voice_client_status = "待机中"
    else:
        voice_client_status = "未知"
    return voice_client_status


@bot.slash_command(description="[管理员] 测试指令1")
async def debug1(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)
    current_guild = guild_lib.get_guild(ctx)
    await current_guild.refresh_list_view()

    await ctx.respond("列表已刷新")


@bot.slash_command(description="[管理员] 测试指令2")
async def debug2(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    guild_lib.check(ctx)
    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)

    # 检测机器人是否已经加入语音频道
    if ctx.guild.voice_client is None:
        logger.rp("机器人未在任何语音频道中，尝试加入语音频道", ctx.guild)
        join_result = await join_callback(ctx, command_call=False)
        if join_result:
            # 更新加入频道后的voice_client
            voice_client = ctx.guild.voice_client
        else:
            return

    connections.update({ctx.guild.id: voice_client})  # Updating the cache with the guild and channel.

    voice_client.start_recording(
        discord.sinks.WaveSink(),  # The sink type to use.
        once_done,  # What to do once done.
        ctx.channel  # The channel to disconnect from.
    )

    # await ctx.respond("开始录制")
    #
    # await ctx.respond("测试结果已打印")


@bot.slash_command(description="[管理员] 测试指令3")
async def debug3(ctx):
    """
    测试用指令
    """
    if not await command_check(ctx):
        return

    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.respond("当前没在录制")  # Respond with this if we aren't recording.

    await ctx.respond("测试结果已打印")


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):  # Our voice client already passes these in.
    recorded_users = [  # A list of recorded users
        f"<@{user_id}>"
        for user_id, audio in sink.audio_data.items()
    ]
    await sink.vc.disconnect()  # Disconnect from the voice channel.
    files = [discord.File(audio.file, f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]  # List down the files.
    await channel.send(f"finished recording audio for: {', '.join(recorded_users)}.", files=files)  # Send a message with the accumulated files.


@bot.slash_command(name_localizations=lang.get_command_name("info"), description="关于Zeta-Discord机器人")
async def info(ctx: discord.ApplicationContext) -> None:
    if not await command_check(ctx):
        return
    await info_callback(ctx)


@bot.slash_command(name_localizations=lang.get_command_name("join"), description=f"让{bot_name}加入当前所在或者指定语音频道")
@option(
    "channel", discord.VoiceChannel,
    description=f"要让{bot_name}加入的频道，如果不选择则加入指令发送者所在的频道",
    required=False
)
async def join(ctx: discord.ApplicationContext, channel: Union[discord.VoiceChannel, None]) -> bool:
    if not await command_check(ctx):
        return False
    return await join_callback(ctx, channel, command_call=True)


@bot.slash_command(name_localizations=lang.get_command_name("leave"), description=f"让{bot_name}离开当前所在语音频道")
async def leave(ctx: discord.ApplicationContext) -> None:
    if not await command_check(ctx):
        return
    await leave_callback(ctx)


async def info_callback(ctx: discord.ApplicationContext) -> None:
    """
    显示关于信息

    :param ctx: 指令原句
    :return:
    """
    await ctx.respond(f"**Zeta-DTB [版本 v{version}]**\n"
                      f"   基于 Pycord v{pycord_version} 运行\n"
                      f"   版本更新日期：{update_time}\n"
                      f"   作者：炤铭Zeta (31Zeta)")


async def join_callback(
        ctx: discord.ApplicationContext, channel: discord.VoiceChannel = None, command_call: bool = False) -> bool:
    """
    让机器人加入指令发送者所在的语音频道并发送提示\n
    如果机器人已经加入一个频道则转移到新频道并发送提示
    如发送者未加入任何语音频道发送提示

    :param ctx: 指令原句
    :param channel: 要加入的频道
    :param command_call: 该指令是否是由用户指令调用
    :return: 布尔值，是否成功加入频道
    """
    guild_lib.check(ctx)
    current_guild = guild_lib.get_guild(ctx)

    # 未输入参数的情况
    if channel is None:
        # 指令发送者未加入频道的情况
        if not ctx.user.voice:
            logger.rp(f"频道加入失败，用户 {ctx.user} 发送指令时未加入任何语音频道", ctx.guild)
            await ctx.respond("您未加入任何语音频道")
            return False

        # 目标频道设定为指令发送者所在的频道
        else:
            channel = ctx.user.voice.channel

    voice_client = ctx.guild.voice_client

    # 机器人未在任何语音频道的情况
    if voice_client is None:
        await channel.connect()
        if command_call:
            await ctx.respond(f"加入语音频道：->  ***{channel.name}***")

    # 机器人已经在一个频道的情况
    else:
        previous_channel = voice_client.channel
        await voice_client.move_to(channel)
        if command_call:
            await ctx.respond(f"转移语音频道：***{previous_channel}***  ->  ***{channel.name}***")

    logger.rp(f"加入语音频道：{channel.name}", ctx.guild)
    await current_guild.refresh_list_view()
    return True


async def leave_callback(ctx: discord.ApplicationContext) -> None:
    """
    让机器人离开语音频道并发送提示

    :param ctx: 指令原句
    :return:
    """
    guild_lib.check(ctx)

    voice_client = ctx.guild.voice_client
    current_guild = guild_lib.get_guild(ctx)

    if voice_client is not None:
        last_channel = voice_client.channel
        await voice_client.disconnect(force=False)

        logger.rp(f"离开语音频道：{last_channel}", ctx.guild)

        await ctx.respond(f"离开语音频道：<- ***{last_channel}***")

    else:
        await ctx.respond(f"{bot_name} 没有连接到任何语音频道")

    await current_guild.refresh_list_view()

