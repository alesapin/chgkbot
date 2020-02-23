# -*- coding: utf-8 -*-
import logging
import argparse
import random
import string

import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from answers_comporator import AnswersComporator, ComparisonResult
from question import format_answer, format_question, Question, QuestionDifficulty
from question import format_correct_answer, format_incorrect_answer
from querist import Querist

COMPARATOR = AnswersComporator()

DBPATH = 'chgkdb'

def start(update, context):
    context.bot.send_sticker(update.effective_chat.id, sticker='CAADAgADOQADz4EnAAH4KDhcwQVw8RYE')


def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


def ask_question(update, context):
    logging.info("Asking question")
    query = update.callback_query
    if query:
        trusted = query.data == 'trusted'
    else:
        trusted = False
    querist = Querist(DBPATH)
    try:
        question = querist.get_question_for(update.effective_chat.id, trusted)
        question_text = format_question(question)
    except Exception as ex:
        logging.info("Exception looking for question: %s", str(ex))
        question = None
        question_text = "Кажется такие вопросы закончились :("


    if question:
        buttons = [InlineKeyboardButton("Ответ", callback_data='giveup'),]
    else:
        buttons = []

    buttons += [
        InlineKeyboardButton("Проверенный", callback_data='trusted'),
        InlineKeyboardButton("Следующий", callback_data='next')
    ]

    reply_markup = InlineKeyboardMarkup([buttons])

    message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=question_text,
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=reply_markup)

    if question:
        context.chat_data[message.message_id] = question.qid


def show_question(update, context):
    logging.info("Showing question")
    if not context.chat_data:
        update.message.reply_text('Я не задавал вопросов, используйте /question, чтобы я задал новый вопрос.')

    querist = Querist(DBPATH)
    message_id = max(context.chat_data.keys())
    qid = context.chat_data[message_id]
    buttons = [[
        InlineKeyboardButton("Ответ", callback_data='giveup'),
        InlineKeyboardButton("Проверенный", callback_data='trusted'),
        InlineKeyboardButton("Следующий", callback_data='next')]]
    reply_markup = InlineKeyboardMarkup(buttons)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=format_question(querist.get_question(qid)),
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=reply_markup)


def button_for_question(update, context):
    try:
        query = update.callback_query
        if query.data == 'giveup':
            message_id = update.callback_query.message.message_id
            qid = context.chat_data[message_id]
            querist = Querist(DBPATH)
            querist.giveup(qid, update.effective_chat.id)
            keyboard = [[
                InlineKeyboardButton("Следующий", callback_data='next'),
                InlineKeyboardButton("Проверенный", callback_data='trusted')
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=format_answer(querist.get_question(qid)),
                parse_mode=telegram.ParseMode.MARKDOWN,
                reply_markup=reply_markup)
        elif query.data.startswith('next') or query.data.startswith('trusted'):
            logging.info("Calling from event")
            ask_question(update, context)
    except Exception as ex:
        print(ex)
        update.message.reply_text('Я не задавал вопросов, используйте /question, чтобы я задал новый вопрос.')


def answer_helper(update, context, text_orig, message_id=None):
    text = text_orig.lower().replace('\n', ' ').replace('  ', ' ').replace('ё', 'е')
    if text.endswith(tuple(string.punctuation)):
        text = text[:-1]
    try:
        querist = Querist(DBPATH)
        chat_id = update.effective_chat.id
        if message_id:
            if message_id not in context.chat_data:
                return

            qid = context.chat_data[message_id]
        else:
            message_id = max(context.chat_data.keys())
            qid = context.chat_data[message_id]
        username = update.message.from_user.first_name
        question = querist.get_question(qid)
        logging.info("Correct answer %s", question.get_simplified_answer())
        logging.info("User answer %s", text)
        compared = COMPARATOR.is_similar(question.get_simplified_answer(), text)
        correct = False
        if compared in (ComparisonResult.ALMOST_EQUAL, ComparisonResult.EQUAL):
            tries, timediff = querist.answer_correct(qid, chat_id, username)
            response = format_correct_answer(question, username, text_orig, timediff, tries)
            del context.chat_data[message_id]
            keyboard = [[
                InlineKeyboardButton("Ответ", callback_data='giveup'),
                InlineKeyboardButton("Следующий", callback_data='next'),
                InlineKeyboardButton("Проверенный", callback_data='trusted'),
            ]]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if random.random() > 0.95:
                context.bot.send_sticker(update.effective_chat.id, sticker='CAADAgADRQADz4EnAAGobmc11WxLvBYE')
        else:
            querist.answer_incorrect(qid, chat_id)
            response = format_incorrect_answer(question, username, text_orig)
            reply_markup = InlineKeyboardMarkup([])
            if random.random() > 0.95:
                sticker = random.choice(['CAADAgADTAADz4EnAAFtb7QFn4Pk3BYE', 'CAADAgADQwADz4EnAAFPeWXff4oazBYE'])
                context.bot.send_sticker(update.effective_chat.id, sticker=sticker)

        update.message.reply_text(
            response,
            quote=True,
            parse_mode=telegram.ParseMode.MARKDOWN,
            reply_markup=reply_markup)
    except Exception as ex:
        logging.info("Exception %s", ex)
        update.message.reply_text('Я не задавал вопросов, используйте /question, чтобы я задал новый вопрос.')


def answer_reply_question(update, context):
    answer_helper(update, context, update.message.text, update.message.reply_to_message.message_id)


def answer_command_question(update, context):
    answer_helper(update, context, ' '.join(context.args))


def add_question(update, context):
    chat_data = context.chat_data
    if 'question_started' in chat_data and chat_data['question_started']:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Вы уже вводите вопрос")
    text = "Введите текст вопроса."
    context.chat_data['question_started'] = True
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def read_data_from_messages(update, context):
    chat_data = context.chat_data
    if 'question_started' in chat_data and chat_data['question_started']:
        chat_data['question_started'] = False
        chat_data['question_text'] = update.message.text
        chat_data['answer_started'] = True
        context.bot.send_message(chat_id=update.effective_chat.id, text="А теперь введите ответ.")
    elif 'answer_started' in chat_data and chat_data['answer_started']:
        chat_data['question_started'] = False
        chat_data['answer_started'] = False
        new_qid = random.randint(0, 4294967296)
        username = update.message.from_user.first_name
        q = Question(new_qid, chat_data['question_text'], update.message.text, '', username, QuestionDifficulty.MEDIUM, 0)
        querist = Querist(DBPATH)
        querist.add_trusted_question(q)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Готово, id вопроса {}".format(new_qid))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Chgk Bot")
    parser.add_argument("-t", "--token", required=True, help="Telegram token")
    parser.add_argument("-d", "--db-path", help="Path to database")
    parser.add_argument("-l", "--log-path", help="Path to logs file")

    args = parser.parse_args()

    if args.db_path:
        DBPATH = args.db_path

    log_config = {
        "level": logging.DEBUG,
        "format": '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }

    if args.log_path:
        log_config['filename'] = args.log_path

    logging.basicConfig(**log_config)

    updater = Updater(token=args.token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    question_handler = CommandHandler('question', ask_question)
    show_handler = CommandHandler('show', show_question)
    add_question_handler = CommandHandler('add', add_question)
    answer_message_handler = MessageHandler(Filters.reply, answer_reply_question)
    read_data_from_messages_handler = MessageHandler(Filters.all, read_data_from_messages)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(question_handler)
    dispatcher.add_handler(add_question_handler)
    dispatcher.add_handler(show_handler)
    dispatcher.add_handler(CallbackQueryHandler(button_for_question))
    dispatcher.add_handler(answer_message_handler)
    dispatcher.add_handler(read_data_from_messages_handler)

    updater.start_polling()
