#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import glob
import os

import telegram.ext
from telegram.ext import Updater, CommandHandler

from datetime import datetime, time, tzinfo, timedelta

import imaplib
import email

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

chat_ids_folder = os.environ['CHATS_FOLDER']
botToken = os.environ['BOT_TOKEN']
mailServer = os.environ['MAIL_SERVER']
mailLogin = os.environ['MAIL_LOGIN']
mailPassword = os.environ['MAIL_PASSWORD']
mailSearch = os.environ['MAIL_SEARCH']

previousStatus = "unknown"

def get_max_email_date():
    mail = imaplib.IMAP4_SSL(mailServer)
    try:
        username = mailLogin
        mail.login(username, mailPassword)
        logger.info("Logged into IMAP as {}".format(username))
        mail.select("INBOX")
        typ, data = mail.search(None, mailSearch)
        maxDate = None
        latestMessageId = None
        messageIds = data[0].split()
        for num in messageIds:
            typ, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            date_tuple = email.utils.parsedate_tz(msg['Date'])
            local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            if (maxDate == None or local_date > maxDate):
                maxDate = local_date
                latestMessageId = num
            logger.info("Received email on {}".format( local_date.strftime("%a, %d %b %Y %H:%M:%S UTC")))

        logger.info("Latest message with id {} received on {}".format(latestMessageId, maxDate.strftime("%a, %d %b %Y %H:%M:%S UTC")))

        if (latestMessageId != None):
            oldMessageIds = b" ".join(filter(lambda messageId: messageId != latestMessageId, messageIds))
            if (oldMessageIds != b''):
                logger.info("About to delete old messages with ids {}".format(oldMessageIds))
                mail.store(oldMessageIds, '+FLAGS', r'(\Deleted)')
                typ, response = mail.expunge()
                logger.info("Expunged old mails {}".format(response))

        return maxDate

    finally:
        mail.close()
        mail.logout()

def callback_minute(context: telegram.ext.CallbackContext):
    global previousStatus
    maxEmailDate = get_max_email_date().replace(microsecond=0)
    diff = datetime.now().replace(microsecond=0) - maxEmailDate
    lag = diff.total_seconds()
    if (lag <= 12*60):
        newStatus = "green"
    elif (lag > 24*60):
        newStatus = "red"
    else:
        newStatus = "amber"

    if (previousStatus == newStatus):
        return

    list_of_files = glob.glob("{}*".format(chat_ids_folder))
    for file in list_of_files:
        chat_id = os.path.basename(file)
        logger.info("Sending status to {}".format(chat_id))
        try:
            context.bot.send_message(chat_id=chat_id, text="Latest email alert received {} ago at {}".format(diff, maxEmailDate.strftime("%a, %d %b %Y %H:%M:%S UTC")))
            context.bot.send_message(chat_id=chat_id, text="Status changed from {} to {}".format(previousStatus, newStatus))
        except:
            logger.info("Cannot send message to chat id {}".format(chat_id))

    previousStatus = newStatus

def callback_weekend(context: telegram.ext.CallbackContext):

    maxEmailDate = get_max_email_date().replace(microsecond=0)
    diff = datetime.now().replace(microsecond=0) - maxEmailDate
    lag = diff.total_seconds()
    if (lag <= 6*60):
        newStatus = "green"
    elif (lag > 16*60):
        newStatus = "red"
    else:
        newStatus = "amber"

    list_of_files = glob.glob("{}*".format(chat_ids_folder))
    for file in list_of_files:
        chat_id = os.path.basename(file)
        logger.info("Sending status to {}".format(chat_id))
        try:
            context.bot.send_message(chat_id=chat_id, text="Latest email alert received {} ago at {}".format(diff, maxEmailDate.strftime("%a, %d %b %Y %H:%M:%S UTC")))
            context.bot.send_message(chat_id=chat_id, text="Status is {}".format(newStatus))
        except:
            logger.info("Cannot send message to chat id {}".format(chat_id))

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    update.message.reply_text('Hi! You have subscribed to alerts email delivery status notifications. Use /status to get current status of service; use /stop to unsubscribe')
    logger.info("Added {} chat".format(update.message.chat_id))
    f = open("{}{}".format(chat_ids_folder, update.message.chat_id), "a")
    f.write("{}".format(update.message.chat_id))
    f.close()
    status(update, context)

def stop(update, context):
    logger.info("Removed {} chat".format(update.message.chat_id))
    os.remove("{}{}".format(chat_ids_folder, update.message.chat_id))

def status(update, context):
    maxEmailDate = get_max_email_date().replace(microsecond=0)
    diff = datetime.now().replace(microsecond=0) - maxEmailDate
    lag = diff.total_seconds()
    if (lag <= 6*60):
        newStatus = "green"
    elif (lag > 16*60):
        newStatus = "red"
    else:
        newStatus = "amber"
    update.message.reply_text("Latest email alert received {} ago at {}".format(diff, maxEmailDate.strftime("%a, %d %b %Y %H:%M:%S UTC")))
    update.message.reply_text("Status is {}".format(newStatus))

def main():
    get_max_email_date()

    """Run bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(botToken, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("stop", stop))

    j = updater.job_queue
    job_minute = j.run_repeating(callback_minute, interval=60, first=0)
    # time is assumed in UTC here
    job_weekend = j.run_daily(callback_weekend, time(hour=17, minute=0), days=(5,6))
    # job_once = j.run_once(callback_weekend, 10)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
