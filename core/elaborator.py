from typing import List

from core.functions import maker_functions, functions
from core.lowlevel import mongo_interface
from core.functions.maker_master_functions import stop
from entities.dialog import Dialog
from entities.infos import Infos
from random import choice

from entities.trigger import Trigger
from logger import log
from utils import regex_utils

_commands = {
    "bid": functions.bid,
    "start": functions.start,
    "uid": functions.uid
}

_owner_commands = {
    "menu": functions.menu,
}

_maker_commands = {
    "newbot": maker_functions.newbot,
    "myid": maker_functions.myid
}

_maker_master_commands = {
    "stop": stop
}


def complete_dialog(infos: Infos, dialog_section: str):
    log.d(f"Elaborating reply of section {dialog_section}")
    dialogs: List[Dialog] = mongo_interface.get_dialogs_of_section(
        infos.bot.bot_id, dialog_section)

    if not dialogs:
        log.d(f"No dialogs set for section {dialog_section}")
        return

    dialog = choice(dialogs)
    infos.reply(dialog.reply, parse_mode=None)
    log.d("Replied")
    return True


def elaborate_equal(infos: Infos, equal: Trigger):
    if regex_utils.is_equal(infos.message.text, equal.trigger):
        return complete_dialog(infos, equal.section)


def elaborate_content(infos: Infos, content: Trigger):
    if regex_utils.is_content(infos.message.text, content.trigger):
        return complete_dialog(infos, content.section)


def elaborate_interaction(infos: Infos, interaction: Trigger):
    is_bot_quote = infos.is_reply and infos.to_user.is_bot
    is_bot_chat = infos.chat.is_private
    is_inter = regex_utils.is_interaction(infos.message.text,
                                          infos.bot.regexed_name)

    if any([is_inter, is_bot_quote, is_bot_chat]):
        if regex_utils.is_in_message(infos.message.text, interaction.trigger):
            return complete_dialog(infos, interaction.section)


def elaborate_eteraction(infos: Infos, eteraction: Trigger):
    is_inter = regex_utils.is_interaction(infos.message.text,
                                          infos.bot.regexed_name)
    if is_inter and infos.is_reply:
        log.d("Message is a reply and starts/ends with bot's name")
        log.d(f"Checking trigger {eteraction.trigger}")
        if regex_utils.is_in_message(infos.message.text, eteraction.trigger):
            log.d("Trigger is present in text")
            return complete_dialog(infos, eteraction.section)


t_type_elaborators = {
    "equal": elaborate_equal,
    "content": elaborate_content,
    "interaction": elaborate_interaction,
    "eteraction": elaborate_eteraction
}


def elaborate(infos: Infos):
    if not infos.message.is_text:
        return

    for t_type_elaborator in t_type_elaborators:
        triggers = mongo_interface.get_triggers_of_type(infos.bot.bot_id,
                                                        t_type_elaborator)
        for trigger in triggers:
            if t_type_elaborators[t_type_elaborator](infos, trigger):
                return


def command(infos: Infos):
    if infos.message.command in _commands:
        log.d(f"User issued command {infos.message.command}")
        _commands[infos.message.command](infos)
        return True

    return False


def owner_command(infos: Infos):
    if not infos.user.is_bot_owner:
        return False

    if infos.message.command in _owner_commands:
        log.d(f"Owner issued command {infos.message.command}")
        _owner_commands[infos.message.command](infos)
        return True

    return False


def maker_command(infos: Infos):
    if not infos.bot.is_maker:
        return

    if infos.message.command in _maker_commands:
        log.d(f"{infos.user.uid} issued maker "
              f"command {infos.message.command}")
        _maker_commands[infos.message.command](infos)
        return True

    return False


def maker_master_command(infos: Infos):
    if not infos.user.is_maker_owner:
        return

    if infos.message.command in _maker_master_commands:
        log.d(f"Maker owner issued command {infos.message.command}")
        _maker_master_commands[infos.message.command](infos)
        return True
    return False
