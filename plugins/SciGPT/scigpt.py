import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins import *
from .summary import Summary
from bridge import bridge
from common.expired_dict import ExpiredDict
from common import const
import os
from .utils import Util
from config import plugin_config


@plugins.register(
    name="SciGPT",
    desc="A plugin that supports knowledge base.",
    version="0.1.0",
    author="luohao",
    desire_priority=99
)
class SciGPT(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.config = super().load_config()
        if not self.config:
            # 未加载到配置，使用模板中的配置
            self.config = self._load_config_template()

        print(f"[SciGPT] inited, config={self.config}")

    def on_handle_context(self, e_context: EventContext):
        """
        消息处理逻辑
        :param e_context: 消息上下文
        """

        context = e_context['context']
        if context.type not in [ContextType.TEXT, ContextType.IMAGE, ContextType.IMAGE_CREATE, ContextType.FILE,
                                ContextType.SHARING]:
            return
        
        if context.type == ContextType.TEXT and context.content == '退出对话':
            _delete_file_id(context)
            print('delete file')

        if context.type in [ContextType.FILE]:
            user_id = _find_user_id(context)
            # 文件处理
            context.get("msg").prepare()
            file_path = context.content
            print('context', context)
            if not Summary().check_file(file_path):
                return

            docId = Summary().summary(file_path, sender_id=user_id)
            print('docId', docId)
            if not docId:
                _set_reply_text("因为神秘力量无法获取内容，请稍后再试吧", e_context, level=ReplyType.TEXT)
                return
            USER_FILE_MAP[_find_user_id(context) + "-file_id"] = docId

            os.remove(file_path)
            return

        if context.type == ContextType.SHARING or \
                (context.type == ContextType.TEXT and Summary().check_url(context.content)):
            if not Summary().check_url(context.content):
                return
            user_id = _find_user_id(context)
            docId = Summary().summary_url(url=context.content, sender_id=user_id)
            if not docId:
                _set_reply_text("因为神秘力量无法获取文章内容，请稍后再试吧~", e_context, level=ReplyType.TEXT)
                return

            USER_FILE_MAP[_find_user_id(context) + "-file_id"] = docId
            return

        if context.type == ContextType.TEXT and _find_file_id(context):
            bot = bridge.Bridge().find_chat_bot(const.SciGPT)
            context.kwargs["file_id"] = [_find_file_id(context)]
            reply = bot.reply(context.content, context)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

    def get_help_text(self, verbose=False, **kwargs):
        trigger_prefix = _get_trigger_prefix()
        help_text = "用于集成 SciGPT 提供的知识库、文档总结、联网搜索等能力。\n\n"
        if not verbose:
            return help_text

        return help_text

    def _load_config_template(self):
        logger.debug("No SciGPT plugin config.json, use plugins/scigpt/config.json.template")
        try:
            plugin_config_path = os.path.join(self.path, "config.json.template")
            if os.path.exists(plugin_config_path):
                with open(plugin_config_path, "r", encoding="utf-8") as f:
                    plugin_conf = json.load(f)
                    plugin_config["scigpt"] = plugin_conf
                    return plugin_conf
        except Exception as e:
            logger.exception(e)

    def reload(self):
        self.config = super().load_config()


def _find_user_id(context):
    if context["isgroup"]:
        return context.kwargs.get("msg").actual_user_id
    else:
        return context["receiver"]


def _set_reply_text(content: str, e_context: EventContext, level: ReplyType = ReplyType.ERROR):
    reply = Reply(level, content)
    e_context["reply"] = reply
    e_context.action = EventAction.BREAK_PASS


def _get_trigger_prefix():
    return conf().get("plugin_trigger_prefix", "$")


def _delete_file_id(context):
    user_id = _find_user_id(context)
    if user_id:
        USER_FILE_MAP.pop(user_id + "-file_id")

def _find_file_id(context):
    user_id = _find_user_id(context)
    if user_id:
        return USER_FILE_MAP.get(user_id + "-file_id")


USER_FILE_MAP = ExpiredDict(conf().get("expires_in_seconds") or 60 * 30)
