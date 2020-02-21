import hashlib
import string
from enum import IntEnum

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


class Question(object):
    def __init__(self, qid, text, answer, comment, tournament_title, difficulty, rating):
        self.qid = qid
        self.text = text.replace('\n', ' ').replace('  ', ' ')
        self.answer = answer.replace('\n', ' ').replace('  ', ' ')
        self.comment = None
        if comment:
            self.comment = comment.replace('\n', ' ').replace('  ', ' ')
        else:
            self.comment = ''
        self.tournament_title = None
        if tournament_title:
            self.tournament_title = tournament_title
        else:
            self.tournament_title = ''
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

def format_answer(q):
    return f"Правильный ответ: *{q.answer}*\nКомментарий: {q.comment}\nТурнир: {q.tournament_title}"


def format_question(q):
    return f"❓*Внимание вопрос*:\n{q.text}"


def format_correct_answer(q, username, text, timedt, tries):
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

