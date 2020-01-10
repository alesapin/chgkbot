# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import requests
import hashlib
from enum import IntEnum
import logging
import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import CallbackQueryHandler
import string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from answers_comporator import AnswersComporator, ComparisonResult
import datetime
import random
import argparse

class QuestionDifficulty(IntEnum):
    UNKNOWN = 0
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    DIFFICULT = 4
    COFFIN = 5

def difficulty_to_string(value):
    if value == QuestionDifficulty.TRIVIAL:
        return "Изи"
    elif value == QuestionDifficulty.EASY:
        return "Простой"
    elif value == QuestionDifficulty.MEDIUM:
        return "Средний"
    elif value == QuestionDifficulty.DIFFICULT:
        return "Сложный"
    elif value == QuestionDifficulty.COFFIN:
        return "Гроб"
    return "Не указана"

DB_URL = 'https://db.chgk.info/xml'
MAX_ANSWER_LENGTH_LETTERS = 15
MAX_ANSWER_LENGTH_WORDS = 4
MIN_RATING = 0.07
RETRY_COUNT = 5

class Question(object):
    def __init__(self, qid, text, answer, comment, tournament_title, difficulty, rating):
        self.qid = qid
        self.text = text.replace('\n', ' ').replace('  ', ' ')
        self.answer = answer.replace('\n', ' ').replace('  ', ' ')
        self.comment = None
        if comment:
            self.comment = comment.replace('\n', ' ').replace('  ', ' ')
        self.tournament_title = None
        if tournament_title:
            self.tournament_title = tournament_title
        m = hashlib.md5()
        m.update(self.text.encode('utf-8'))
        self.hsh = m.hexdigest()
        self.difficulty = difficulty
        self.rating = rating

    def get_simplified_answer(self):
        result = self.answer.lower().replace('ё', 'е')
        if result.endswith(tuple(string.punctuation)):
            return result[:-1]
        return result

    def __str__(self):
        return f"Qid: {self.qid}\n" + \
               f"Question: {self.text}\n" + \
               f"Answer: {self.answer}\n" + \
               f"Comment: {self.comment}\n" + \
               f"Tournament: {self.tournament_title}"

def parse_questions(dom_tree_root):
    result = []
    for questions in dom_tree_root:
        comment = None
        tournament = None
        difficulty = QuestionDifficulty.UNKNOWN
        rating = 0.0
        for question_tree in questions:
            if question_tree.tag == 'QuestionId':
                qid = int(question_tree.text)
            elif question_tree.tag == 'Question':
                text = question_tree.text
            elif question_tree.tag == 'Answer':
                answer = question_tree.text
            elif question_tree.tag == 'Comments':
                comment = question_tree.text
            elif question_tree.tag == 'tournamentTitle':
                tournament = question_tree.text
            elif question_tree.tag == 'Complexity':
                if question_tree.text:
                    difficulty = QuestionDifficulty(int(question_tree.text))
            elif question_tree.tag == 'Rating':
                if question_tree.text:
                    correct, all_tries = question_tree.text.split('/')
                    rating = float(correct) / float(all_tries)

        result.append(Question(qid, text, answer, comment, tournament, difficulty, rating))
    return result

def format_answer(q):
    return f"Правильный ответ: *{q.answer}*\nКомментарий: {q.comment}\nТурнир: {q.tournament_title}"

def format_question(q):
    return f"❓*Внимание вопрос* \[Сложность: {difficulty_to_string(q.difficulty)}]:\n{q.text}"

def format_correct_answer(q, username, text, comparison_result, timedt, tries):
    s = timedt.seconds
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    timediff = ""
    if hours:
        timediff = "{:02}ч ".format(hours)
    if minutes:
        timediff += "{:02}м ".format(minutes)
    timediff += "{:02}с".format(seconds)

    result = f"⭐️️Правильно, *{username}*!\n*Ваш ответ:* {text}.\n*Верный ответ:* {q.answer}"
    result += f"\n\n*Затрачено времени:* {timediff}\n*Всего попыток:* {tries}"
    if q.comment:
        result += f'\n\n*Комментарий:*\n{q.comment}'
    return result


def format_incorrect_answer(q, username, text):
    return f"'*{text}*' - это неверный ответ. :("


class ChgkDBAPI(object):
    def __init__(self, db_uri):
        self.db_uri = db_uri

    def get_random_questions(self, limit, difficulty=None):
        logging.info("DIfficulty %s", difficulty)
        if not difficulty or difficulty == QuestionDifficulty.UNKNOWN:
            complexity_arg = ''
        else:
            complexity_arg = '/complexity' + str(int(difficulty))

        uri = self.db_uri + '/random/answers/types13{}/limit{}'.format(complexity_arg, limit)
        logging.info("URI: %s", uri)
        retry = 0
        while retry < RETRY_COUNT:
            try:
                response = requests.get(uri)
            except:
                retry += 1
                continue
            break
        root = ET.fromstring(response.content)
        return parse_questions(root)

    def get_better_question(self, difficulty=None):
        return self.get_better_questions(1, difficulty)[0]

    def get_better_questions(self, limit, difficulty=None):
        result = []
        while len(result) < limit:
            rand_questions = self.get_random_questions(limit - len(result) + 2, difficulty)
            for rand_question in rand_questions:
                answer = rand_question.answer
                if (len(answer) < MAX_ANSWER_LENGTH_LETTERS
                    and len(answer.split(' ')) < MAX_ANSWER_LENGTH_WORDS
                    and not '(pic:' in rand_question.text
                    and (rand_question.rating >= MIN_RATING or rand_question.rating == 0.0)):
                    result.append(rand_question)
        return result


def start(update, context):
    context.bot.send_sticker(update.effective_chat.id, sticker='CAADAgADOQADz4EnAAH4KDhcwQVw8RYE')

def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

def ask_question(update, context):
    logging.info("Asking question")
    query = update.callback_query
    complexity_value = QuestionDifficulty.UNKNOWN
    if not query:
        try:
            args = ' '.join(context.args)
            complexity_value = int(args)
        except:
            pass
    else:
        complexity_value = QuestionDifficulty(int(query.data[1:]))

    api = ChgkDBAPI(DB_URL)
    question = api.get_better_question(complexity_value)
    buttons = [[
        InlineKeyboardButton("Ответ", callback_data='giveup'),
        InlineKeyboardButton("Любой", callback_data='q' + str(int(QuestionDifficulty.UNKNOWN))),
    ]] + [[InlineKeyboardButton(difficulty_to_string(d), callback_data='q' + str(int(d))) for d in QuestionDifficulty if d != QuestionDifficulty.UNKNOWN]]

    reply_markup = InlineKeyboardMarkup(buttons)

    message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=format_question(question),
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=reply_markup)

    context.chat_data[message.message_id] = [question, datetime.datetime.now(), 1]

def show_question(update, context):
    logging.info("Showing question")
    if not context.chat_data:
        update.message.reply_text('Я не задавал вопросов, используйте /question, чтобы я задал новый вопрос.')

    message_id = max(context.chat_data.keys())
    question, start, tries = context.chat_data[message_id]
    buttons = [[
        InlineKeyboardButton("Ответ", callback_data='giveup'),
        InlineKeyboardButton("Любой", callback_data='q' + str(int(QuestionDifficulty.UNKNOWN))),
    ]] + [[InlineKeyboardButton(difficulty_to_string(d), callback_data='q' + str(int(d))) for d in QuestionDifficulty if d != QuestionDifficulty.UNKNOWN]]

    reply_markup = InlineKeyboardMarkup(buttons)

    message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=format_question(question),
        parse_mode=telegram.ParseMode.MARKDOWN,
        reply_markup=reply_markup)
    context.chat_data[message.message_id] = [question, start, tries]

def button_for_question(update, context):
    try:
        query = update.callback_query
        if query.data == 'giveup':
            message_id = update.callback_query.message.message_id
            question, start, tries = context.chat_data[message_id]
            keyboard = [[InlineKeyboardButton(difficulty_to_string(d), callback_data='q' + str(int(d))) for d in QuestionDifficulty if d != QuestionDifficulty.UNKNOWN]] + [[InlineKeyboardButton("Любой", callback_data='q' + str(int(QuestionDifficulty.UNKNOWN)))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=format_answer(question),
                parse_mode=telegram.ParseMode.MARKDOWN,
                reply_markup=reply_markup)
        elif query.data.startswith('q'):
            logging.info("Calling from event")
            ask_question(update, context)
    except Exception as ex:
        print(ex)
        update.message.reply_text('Я не задавал вопросов, используйте /question, чтобы я задал новый вопрос.')

COMPARATOR = AnswersComporator()

def answer_helper(update, context, text_orig, message_id=None):
    text = text_orig.lower().replace('\n', ' ').replace('  ', ' ').replace('ё', 'е')
    if text.endswith(tuple(string.punctuation)):
        text = text[:-1]
    try:
        if message_id:
            if message_id not in context.chat_data:
                return
            question, start, tries = context.chat_data[message_id]
        else:
            message_id = max(context.chat_data.keys())
            question, start, tries = context.chat_data[message_id]
        username = update.message.from_user.first_name
        logging.info("Correct answer %s", question.get_simplified_answer())
        logging.info("User answer %s", text)
        compared = COMPARATOR.is_similar(question.get_simplified_answer(), text)
        correct = False
        if compared in (ComparisonResult.ALMOST_EQUAL, ComparisonResult.EQUAL):
            timediff = datetime.datetime.now() - start
            response = format_correct_answer(question, username, text_orig, compared, timediff, tries)
            del context.chat_data[message_id]
            keyboard = [[InlineKeyboardButton(difficulty_to_string(d), callback_data='q' + str(int(d))) for d in QuestionDifficulty if d != QuestionDifficulty.UNKNOWN]] +\
                [[InlineKeyboardButton("Любой", callback_data='q' + str(int(QuestionDifficulty.UNKNOWN)))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if random.random() > 0.95:
                context.bot.send_sticker(update.effective_chat.id, sticker='CAADAgADRQADz4EnAAGobmc11WxLvBYE')
        else:
            response = format_incorrect_answer(question, username, text_orig)
            context.chat_data[message_id][2] += 1
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Chgk Bot")
    parser.add_argument("-t", "--token", required=True, help="Telegram token")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    updater = Updater(token=args.token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    question_handler = CommandHandler('question', ask_question)
    show_handler = CommandHandler('show', show_question)
    answer_message_handler = MessageHandler(Filters.reply, answer_reply_question)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(question_handler)
    dispatcher.add_handler(answer_message_handler)
    dispatcher.add_handler(show_handler)
    dispatcher.add_handler(CallbackQueryHandler(button_for_question))

    updater.start_polling()
