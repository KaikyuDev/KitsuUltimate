import random
import threading
import time
import re

from random import choice

from core.lowlevel import mongo_interface
from logger import log
from telegram import methods

string_dummies = {
    "[_]": "\n"
}

dummies = {
    "$base": {
        "{user.name}": "infos.user.name",
        "{user.id}": "infos.user.uid",
        "{user.last_name}": "infos.user.surname",
        "{user.username}": "infos.user.username",
        "{bot.id}": "infos.bot.bot_id",
        "{bot.name}": "infos.bot.name",
        "{bot.username}": "infos.bot.username",
        "{bot.groups}": "infos.db.get_groups_count()",
        "{bot.users}": "infos.db.get_users_count()",
        "{bot.started_users}": "infos.db.get_started_users_count()",
        "{chat.name}": "infos.chat.name",
        "{chat.id}": "infos.chat.cid",
        "{bots_count}": "manager.get_bots_count()",
        "{exec_time}": "ping(infos)",
        "{triggers.count}": "'unimplemented'",
        "{dialogs.count}": "'unimplemented'",
        "{equals.count}": "'unimplemented'",
        "{contents.count}": "'unimplemented'",
        "{interactions.count}": "'unimplemented'",
        "{eteractions.count}": "'unimplemented'"
    },

    "$on_reply": {
        "{to_name}": "infos.to_user.name",
        "{to_uid}": "infos.to_user.uid",
        "{to_surname}": "infos.to_user.surname",
        "{to_username}": "infos.to_user.username",
        "{is_bot}": "infos.to_user.is_bot"
    }
}


def ping(infos):
    return int((time.time() - infos.time) * 1000)


def parse_dummies(reply: str, infos) -> str:
    for dummy_t in dummies:
        if dummy_t == "$on_reply":
            if not infos.is_reply:
                continue

        for dummy in dummies[dummy_t]:
            if dummy in reply:  # eval is dangerous but here is totally controlled
                reply = reply.replace(dummy, str(eval(dummies[dummy_t][dummy])))

    return reply


def parse_str_dummies(reply: str, infos) -> str:
    for dummy in string_dummies:
        if dummy not in reply:
            continue

        reply = reply.replace(dummy, string_dummies[dummy])

    return reply


def parse_sections(reply: str, infos) -> str:
    for section in re.findall(r"\${(.*?)}", reply):
        log.d(f"Section '{section}' found")
        dialogs = mongo_interface.get_dialogs_of_section(infos.bot.bot_id, section)

        if not dialogs:
            sub = "-"
            log.d(f"No dialogs found for section '{section}'")
        else:
            sub = choice(dialogs).reply

        reply = re.sub(r"\${(.*?)}", sub, reply, count=1)
        log.d(f"Substitution of section '{section}' done")

    return reply


def elaborate_multx(reply: str, infos):
    for action, var in re.findall(r"(send|action|wait):(?:(.+?)(?: then|]))", reply):
        # TODO this can cause loops
        log.d(f"Action: {action}, var: {var}")
        if action == "send":
            dialogs = mongo_interface.get_dialogs_of_section(infos.bot.bot_id, var)
            if not dialogs:
                log.d(f"No dialogs for section {var}")
                continue
            dialog = choice(dialogs)
            log.d(f"Choosed reply {dialog.reply}")
            infos.reply(dialog.reply, parse_mode=None)
        elif action == "action":
            actions = {"type": "typing"}
            if var not in actions:
                log.d(f"Unknown action: {var}")
                continue
            methods.send_chat_action(infos.bot.token, infos.chat.cid, actions[var])
        elif action == "wait":
            try:
                var = int(var)
            except ValueError:
                log.w(f"Invalid value: {var}")
                continue
            time.sleep(var)


def execute(reply: str, infos, markup=None):
    if re.search(r"^\[.+]$", reply):
        # (send|action|wait):(?:(.+?)(?:then|]))
        threading.Thread(target=elaborate_multx, args=(reply, infos)).start()
        return

    match = re.search(r"{media:(\w{3}),(.+?)(,(.+))?}", reply)
    if match:
        log.d("Matched media regex")
        media_type = match.group(1)
        media_id = match.group(2)
        caption = match.group(4)
        if media_type == "stk":
            methods.send_sticker(infos.bot.token, infos.chat.cid, media_id, reply_markup=markup)
        elif media_type == "pht":
            methods.send_photo(infos.bot.token, infos.chat.cid, media_id, caption, reply_markup=markup)
        elif media_type == "aud":
            methods.send_audio(infos.bot.token, infos.chat.cid, media_id, reply_markup=markup)
        elif media_type == "voe":
            methods.send_voice(infos.bot.token, infos.chat.cid, media_id, reply_markup=markup)
        elif media_type == "doc":
            methods.send_doc(infos.bot.token, infos.chat.cid, media_id, reply_markup=markup)
        return

    log.d("Parsing reply string")
    reply = parse_sections(reply, infos)
    reply = parse_dummies(reply, infos)
    reply = parse_str_dummies(reply, infos)

    reg = r"rnd\[(\d+),\s*?(\d+)]"
    for min, max in re.findall(reg, reply):
        reply = re.sub(reg, str(random.randint(int(min), int(max))), reply, count=1)

    quote = "[quote]" in reply
    reply = reply.replace("[quote]", "")

    log.d("Sending message")
    methods.send_message(infos.bot.token, infos.chat.cid, reply,
                         parse_mode="markdown", reply_markup=markup)


def parse(reply: str, infos) -> (str, bool):
    reply = parse_sections(reply, infos)
    reply = parse_dummies(reply, infos)
    reply = parse_str_dummies(reply, infos)

    quote = "[quote]" in reply
    reply = reply.replace("[quote]", "")

    return reply, quote
