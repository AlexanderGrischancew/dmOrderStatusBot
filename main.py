#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import telegram.ext
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import logging


ORDERS = dict()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')
    #TODO


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')
    #TODO

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def checkArgs(context):
    print("CHECKING ARGS: " + context.args[0] + " " + context.args[1])
    return re.match("[0-9]{6}",context.args[0]) and re.match("[0-9]{3,5}",context.args[1])

def checkIfInOrders(orderNumber, storeNumber, userID, delete):
    print("CHECKING IF TUPLE "+orderNumber+ " "+ storeNumber+ " IS ON WATCHLIST FROM USER: "+str(userID))
    print("DELETE IS SET: " + str(delete))
    currentOrders = ORDERS.get(userID)
    for order in currentOrders:
        if order[0] == orderNumber and order[1] == storeNumber:
            print("TUPLE FOUND: "+ order[0] + " " + order[1])
            if delete:
                print("TUPLE DELETED")
                currentOrders.remove(order)
            return True
    print("TUPLE NOT FOUND")
    return False

def addOrder(update, context):
    print("EXECUTING ADD ORDER COMMAND")
    if not checkArgs(context):
        print("ARGS NOT OK")
        update.message.reply_text(
            'The command: ' + update.message.text + " does not match the format: /addorder $order-number $store-number")

    else:
        print("ARGS OK")
        global ORDERS
        chat_id = update.effective_chat.id
        orderNumber = context.args[0]
        storeNumber = context.args[1]

        print("ORDER NUMBER: "+ orderNumber)
        print("STORE NUMBER: "+ storeNumber)
        print("CHAT ID: " + str(chat_id))

        if chat_id not in ORDERS:
            print("CHAT ID NOT IN ORDERS DICT, ADDING")
            ORDERS[chat_id] = []

        currentOrders = ORDERS.get(chat_id)

        if checkIfInOrders(orderNumber,storeNumber,chat_id,False):
            print("ORDER NUMBER & STORE NUMBER TUPLE ALREADY ON WATCHLIST")
            update.message.reply_text(
                'Your order number: ' + orderNumber + ' and store number: ' + storeNumber + ' is already on your watchlist')
        else:
            status = getStatus(storeNumber,orderNumber).json().get("summaryStateCode")
            print("ORDER STATUS IS: "+status)
            if status == "ERROR":
                update.message.reply_text(
                    'Your order number: ' + orderNumber + ' and store number: ' + storeNumber + ' could not be found, maybe it is not registered in the system yet\nstill it was added to your wachlist')

            else:
                update.message.reply_text(
                    'Your order number: ' + orderNumber + ' and store number: ' + storeNumber + ' has been added to your watchlist\nYour Order is currently: '+status)
            currentOrders.append((orderNumber, storeNumber, status))
        print("ADD ORDER COMMAND FINISHED")
        print("-----")

def removeOrder(update, context):
    print("EXECUTING REMOVE ORDER COMMAND")
    if not checkArgs(context):
        print("ARGS NOT OK")
        update.message.reply_text(
            'The command: ' + update.message.text + " does not match the format: /addorder $order-number $store-number")
    else:
        print("ARGS OK")
        orderNumber = context.args[0]
        storeNumber = context.args[1]
        chat_id = update.effective_chat.id
        print("ORDER NUMBER: "+ orderNumber)
        print("STORE NUMBER: "+ storeNumber)
        print("CHAT ID: " + str(chat_id))
        if checkIfInOrders(orderNumber,storeNumber,chat_id,True):
            print("ORDER WAS ON WATCHLIST")
            update.message.reply_text(
                'Your order number: ' + orderNumber + ' and store number: ' + storeNumber + ' has been removed from your watchlist')
        else:
            print("ORDER NOT ON WATCHLIST")
            update.message.reply_text(
                'Your order number: ' + orderNumber + ' and store number: ' + storeNumber + 'is not on your watchlist')
    print("REMOVE ORDER COMMAND FINISHED")
    print("-----")

def getUpdate(update, context):
    print("EXECUTE GET UPDATE COMMAND")
    global ORDERS
    chat_id = update.effective_chat.id
    print("CHAT ID: " + str(chat_id))
    statusMessage = ""
    if chat_id in ORDERS:
        for order in ORDERS.get(chat_id):
            shopNumber = order[1]
            orderNumber = order[0]
            print("GETTING UPDATE FOR ORDER NR: "+ orderNumber + " STORE NUMBER: "+shopNumber)
            r = getStatus(shopNumber,orderNumber)
            currentMessage = "Order Nr: " + orderNumber + "\nFrom store Nr: " + shopNumber + "\nStatus:\n" + r.json().get("summaryStateText")
            statusMessage = statusMessage + "\n \n" + currentMessage
    if statusMessage == "":
        statusMessage = "You are currently not watching any orders."
    update.message.reply_text(statusMessage)
    print("FINISHED GET UPDATE COMMAND")
    print("-----")

def listOrders(update, context):
    print("EXECUTING LIST ORDERS COMMAND")
    chat_id = update.effective_chat.id
    print("CHAT ID: "+ str(chat_id))
    message = "Your are currently watching:\n"
    if chat_id in ORDERS:
        for order in ORDERS.get(chat_id):
            shopNumber = order[1]
            orderNumber = order[0]
            print("ORDER NR: "+orderNumber + " STORE NUMBER: "+ shopNumber +" FOUND ON WATCHLIST")
            message = message + "Order: " + orderNumber + " store: "+shopNumber + "\n"

    if message == "Your are currently watching:\n":
        print("NO ORDERS ON WATCHLIST")
        message = "You are currently not watching any orders."

    update.message.reply_text(message)
    print("FINISHED GET UPDATE COMMAND")
    print("-----")

def check_status(context: telegram.ext.CallbackContext):
    print("EXECUTING SHEDULED CHECK STATUS COMMAND")
    global ORDERS
    for user in ORDERS:
        print("CHECKING FOR USER: " + str(user))
        statusMessage = ""
        for order in ORDERS.get(user):
            currentMessage=""
            shopNumber = order[1]
            orderNumber = order[0]
            orderCurrentStatus = order [2]
            print("CHECKING ORDER NUMBER: " + orderNumber + " STORE NUMBER: " + shopNumber)
            print("CURRENT STATUS IS: " + orderCurrentStatus)
            r = getStatus(shopNumber,orderNumber)
            status = r.json().get("summaryStateCode")
            print("RETRIEVED STATUS IS: " +status)
            if status != orderCurrentStatus:
                currentMessage = "Order Nr: " + orderNumber + " from store Nr: " + shopNumber + " has changed to:\n" + r.json().get("summaryStateText")

            statusMessage = statusMessage + currentMessage
        if statusMessage != "":
            context.bot.send_message(chat_id=user, text=statusMessage)
    print("FINISHED SHEDULED CHECK STATUS COMMAND")
    print("-----")

def getStatus(storeNumber, orderNumber):
    print("GETTING STATUS FOR ORDER NUMBER: " +orderNumber+" AND STORE NUMBER: " + storeNumber)
    request_url = "https://spot.photoprintit.com/spotapi/orderInfo/forShop"
    url_parameter = {'config': '1320',
                     'shop': storeNumber,
                     'order': orderNumber,
                     'language': 'en'}
    print(requests.get(request_url, params=url_parameter).text)
    return requests.get(request_url, params=url_parameter)


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(BOTTOKEN, use_context=True)

    jq = updater.job_queue
    jq.run_repeating(check_status, 21600, first=30)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("addorder", addOrder, pass_args=True))
    dp.add_handler(CommandHandler("getupdate", getUpdate))
    dp.add_handler(CommandHandler("listorders", listOrders))
    dp.add_handler(CommandHandler("removeorder", removeOrder, pass_args=True))
    # on noncommand i.e message - echo the message on Telegram
    #dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    print("BOT STARTED")

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()




