#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import requests
import re

import telegram.ext
from telegram.ext import Updater, CommandHandler
import logging


ORDERS = dict()
PERSISTENCEFILENAME = "dmOrderStatusBot.dat"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Welcome to the inoffical telegram bot to keep up to date with your orders '
                              'at DM-Fotoworld\n Here are the commands:\n'
                              '/addorder $OrderNumber $StoreNumber\n'
                              '/removeorder $OrderNumber $StoreNumber\n'
                              '/listorder\n'
                              '/getupdate\n')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')
    #TODO


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def check_args(context):
    if len(context.args) != 2:
        print("THERE WERE NO OR NOT ENOUGH ARGS PASSED")
        return False
    print("CHECKING ARGS: " + context.args[0] + " " + context.args[1])
    return re.fullmatch("[0-9]{6}", context.args[0]) and re.fullmatch("[0-9]{3,5}", context.args[1])


def check_in_orders(order_number, store_number, user_id, delete):
    # This not only checks if the combination of order number and store number is on the given user watchlist, but also
    # can delete the order if delete is true
    print("CHECKING IF TUPLE " + order_number + " " + store_number + " IS ON WATCHLIST FROM USER: " + str(user_id))
    print("DELETE IS SET: " + str(delete))
    current_orders = ORDERS.get(user_id)
    for order in current_orders:
        if order[0] == order_number and order[1] == store_number:
            print("TUPLE FOUND: " + order[0] + " " + order[1])
            if delete:
                print("TUPLE DELETED")
                current_orders.remove(order)
                persistence_update()
            return True
    print("TUPLE NOT FOUND")
    return False


def add_order(update, context):
    print("EXECUTING ADD ORDER COMMAND")
    if not check_args(context):
        print("ARGS NOT OK")
        update.message.reply_text(
            "The command: " + update.message.text + " does not match the format: /addorder $order-number $store-number")

    else:
        print("ARGS OK")
        chat_id = update.effective_chat.id
        order_number = context.args[0]
        store_number = context.args[1]

        print("ORDER NUMBER: " + order_number)
        print("STORE NUMBER: " + store_number)
        print("CHAT ID: " + str(chat_id))

        if chat_id not in ORDERS:
            # If the user is new, a empty watchlist is added, avoids further checks if the user exists
            print("CHAT ID NOT IN ORDERS DICT, ADDING")
            ORDERS[chat_id] = []

        current_orders = ORDERS.get(chat_id)

        if check_in_orders(order_number, store_number, chat_id, False):
            print("ORDER NUMBER & STORE NUMBER TUPLE ALREADY ON WATCHLIST")
            update.message.reply_text(
                "Your order number: " + order_number + " and store number: " + store_number + " is already on "
                                                                                              "your watchlist")
        else:
            status = get_status(store_number, order_number).json().get("summaryStateCode")
            print("ORDER STATUS IS: "+status)
            if status == "ERROR":
                update.message.reply_text(
                    "Your order number: " + order_number + " and store number: " + store_number + " could not be found,"
                                                                                                  " maybe it is not "
                                                                                                  "registered in the "
                                                                                                  "system yet\nstill it"
                                                                                                  " was added to your "
                                                                                                  "wachlist")

            else:
                update.message.reply_text(
                    "Your order number: " + order_number + " and store number: " + store_number + " has been added to "
                                                                                                  "your watchlist\nYour"
                                                                                                  " Order is currently:"
                                                                                                  " " + status)
            current_orders.append([order_number, store_number, status])
            persistence_update()
    print("ADD ORDER COMMAND FINISHED")
    print("-----")


def remove_order(update, context):
    print("EXECUTING REMOVE ORDER COMMAND")
    if not check_args(context):
        print("ARGS NOT OK")
        update.message.reply_text(
            "The command: " + update.message.text + " does not match the format: "
                                                    "/removeorder $order-number $store-number")
    else:
        print("ARGS OK")
        order_number = context.args[0]
        store_number = context.args[1]
        chat_id = update.effective_chat.id
        print("ORDER NUMBER: " + order_number)
        print("STORE NUMBER: " + store_number)
        print("CHAT ID: " + str(chat_id))
        if check_in_orders(order_number, store_number, chat_id, True):
            print("ORDER WAS ON WATCHLIST")
            update.message.reply_text(
                "Your order number: " + order_number + " and store number: " + store_number + " has been removed "
                                                                                              "from your watchlist")
        else:
            print("ORDER NOT ON WATCHLIST")
            update.message.reply_text(
                "Your order number: " + order_number + " and store number: " + store_number + "is not on "
                                                                                              "your watchlist")
    print("REMOVE ORDER COMMAND FINISHED")
    print("-----")


def get_update(update, context):
    print("EXECUTE GET UPDATE COMMAND")
    chat_id = update.effective_chat.id
    print("CHAT ID: " + str(chat_id))
    status_message = ""
    if chat_id in ORDERS:
        for order in ORDERS.get(chat_id):
            store_number = order[1]
            order_number = order[0]
            print("GETTING UPDATE FOR ORDER NR: " + order_number + " STORE NUMBER: "+store_number)
            response = get_status(store_number, order_number)
            current_message = "Order Nr: " + order_number + "\nFrom store Nr: " + store_number + "\nStatus:\n" \
                              + response.json().get("summaryStateText")
            status_message = status_message + "\n \n" + current_message
    if status_message == "":
        status_message = "You are currently not watching any orders."
    update.message.reply_text(status_message)
    print("FINISHED GET UPDATE COMMAND")
    print("-----")


def list_orders(update, context):
    print("EXECUTING LIST ORDERS COMMAND")
    chat_id = update.effective_chat.id
    print("CHAT ID: " + str(chat_id))
    message = "Your are currently watching:\n"
    print(str(ORDERS))
    if chat_id in ORDERS:
        for order in ORDERS.get(chat_id):
            shop_number = order[1]
            order_number = order[0]
            print("ORDER NR: " + order_number + " STORE NUMBER: " + shop_number + " FOUND ON WATCHLIST")
            message = message + "Order: " + order_number + " store: " + shop_number + "\n"

    if message == "Your are currently watching:\n":
        print("NO ORDERS ON WATCHLIST")
        message = "You are currently not watching any orders."

    update.message.reply_text(message)
    print("FINISHED GET UPDATE COMMAND")
    print("-----")


def check_status(context: telegram.ext.CallbackContext):
    print("EXECUTING SCHEDULED CHECK STATUS COMMAND")
    persistence_update_needed = False  # if no order have changed there is no need to update the persistence file
    for user in ORDERS:
        print("CHECKING FOR USER: " + str(user))
        status_message = ""
        for order in ORDERS.get(user):
            print(str(ORDERS.get(user)))
            current_message = ""
            store_number = order[1]
            order_number = order[0]
            order_current_status = order[2]
            print("CHECKING ORDER NUMBER: " + order_number + " STORE NUMBER: " + store_number)
            print("CURRENT STATUS IS: " + order_current_status)
            r = get_status(store_number, order_number)
            status = r.json().get("summaryStateCode")
            print("RETRIEVED STATUS IS: " + status)
            if status != order_current_status:
                persistence_update_needed = True
                current_message = "Order Nr: " + order_number + " from store Nr: " + store_number + \
                                  " has changed form " + order_current_status + " to:\n" + \
                                  r.json().get("summaryStateText") + "\n\n"
                order[2] = status
                print("UPDATED STATUS FOR ORDER NR: " + order_number+" FROM STORE NUMBER: " + store_number +
                      "\nFROM STATUS: " + order_current_status + " --> " + status)

            status_message = status_message + current_message
        if status_message != "":
            print("SEND MESSAGE TO: " + str(user) + " Message:\n" + status_message)
            context.bot.send_message(chat_id=user, text=status_message)

    if persistence_update_needed:
        persistence_update()
    print("FINISHED SCHEDULED CHECK STATUS COMMAND")
    print("-----")


def get_status(store_number, order_number):
    print("GETTING STATUS FOR ORDER NUMBER: " + order_number + " AND STORE NUMBER: " + store_number)
    request_url = "https://spot.photoprintit.com/spotapi/orderInfo/forShop"
    url_parameter = {'config': '1320',
                     'shop': store_number,
                     'order': order_number,
                     'language': 'en'}
    print(requests.get(request_url, params=url_parameter).text)
    return requests.get(request_url, params=url_parameter)


def persistence_update():
    print("PERSISTENCE UPDATE TRIGGERED")
    persistence_file = open(PERSISTENCEFILENAME, "w+")
    for user in ORDERS:
        for order in ORDERS.get(user):
            column = str(user)
            for data in order:
                column += " " + data
            column += "\n"
            persistence_file.write(column)
    persistence_file.close()
    print("PERSISTENCE UPDATE FINISHED")


def persistence_load():
    print("PERSISTENCE LOAD TRIGGERED")
    if os.path.isfile(PERSISTENCEFILENAME):
        persistence_file = open(PERSISTENCEFILENAME, "r")
        persistence_content = persistence_file.read()
        print("PERSISTENCE DATA FOUND")
        persistence_content_newline_split = persistence_content.split("\n")
        for line in persistence_content_newline_split:
            if line != "":
                line_split = line.split(" ")
                print(str(line_split))
                # it is important that the user id contained in line_split[0] is cast to int else the will be data loss
                if int(line_split[0]) not in ORDERS:
                    ORDERS[int(line_split[0])] = []
                current_user = ORDERS.get(int(line_split[0]))
                order_list = [line_split[1], line_split[2], line_split[3]]
                current_user.append(order_list)
                print(str(ORDERS))

        persistence_file.close()
    print("PERSISTENCE LOAD FINISHED")
    print("-----")


def main():
    """Start the bot."""
    # Create the EventHandler and pass it bot's token.
    persistence_load()
    updater = Updater(TOKEN, use_context=True)

    jq = updater.job_queue
    now = 0
    three_hours = 21600
    jq.run_repeating(check_status, three_hours, first=now)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("addorder", add_order, pass_args=True))
    dp.add_handler(CommandHandler("getupdate", get_update))
    dp.add_handler(CommandHandler("listorders", list_orders))
    dp.add_handler(CommandHandler("removeorder", remove_order, pass_args=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    print("BOT STARTED")
    print("-----")

    updater.idle()


if __name__ == '__main__':
    main()
