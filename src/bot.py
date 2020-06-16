import json
import logging
import re

import twitter
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.utils.request import Request
from twitter import TwitterError


class LinkFixBot:
    TWITTER_LINK_REGEX = re.compile(r"(?:https?://)?twitter.com/[^/]+/status/([0-9]+)")

    def __init__(self, conf_file):
        with open(conf_file, 'r') as f:
            self.config = json.load(f)
        self.bot_key = self.config["telegram"]["bot_key"]
        self.api = twitter.Api(
            consumer_key=self.config["twitter"]["consumer_key"],
            consumer_secret=self.config["twitter"]["consumer_secret"],
            access_token_key=self.config["twitter"]["access_token_key"],
            access_token_secret=self.config["twitter"]["access_token_secret"]
        )
        self.bot = None
        self.alive = False

    def start(self):
        request = Request(con_pool_size=8)
        self.bot = Bot(token=self.bot_key, request=request)
        updater = Updater(bot=self.bot, use_context=True)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        dispatcher.add_handler(CommandHandler("start", self.func_start))
        dispatcher.add_handler(MessageHandler(Filters.all, self.func_twitter_link))

        updater.start_polling()

    def func_start(self, update: Update, context: CallbackContext):
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="Welcome. This is a very simple bot. "
                 "You forward twitter retweet links here, and it replies with teh actual twitter status link."
        )

    def func_twitter_link(self, update: Update, context: CallbackContext):
        text = update.message.text
        for status_id in self.TWITTER_LINK_REGEX.findall(text):
            context.bot.send_message(chat_id=update.message.chat_id, text=self.handle_twitter_link(status_id))

    def handle_twitter_link(self, status_id: str):
        try:
            status = self.api.GetStatus(status_id)
        except twitter.error.TwitterError as e:
            return f"Twitter error: {e}"
        if status is None:
            return "This doesn't seem to be a valid tweet."
        retweeted_status = status.retweeted_status
        if retweeted_status is None:
            return "This doesn't seem to be a retweet link."
        return f"https://twitter.com/{retweeted_status.user.screen_name}/status/{retweeted_status.id}"
