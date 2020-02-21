from sqliteapi import SQLiteAPI
from chgkdbapi import ChgkDBAPI

class Querist(object):
    def __init__(self):
        self.chgkdb = ChgkDBAPI()
        self.sqlite = SQLiteAPI('chgkdb')

    def get_question_for(self, chat_id, trusted):
        if trusted:
            question = self.sqlite.get_trusted_question(chat_id, trusted)
        else:
            question = self.chgkdb.get_better_question()
            while self.sqlite.is_question_answered(question.qid, chat_id):
                question = self.chgkdb.get_better_question()
            self.sqlite.store_new_question(question, chat_id, 0)

        self.sqlite.start_question(question.qid, chat_id)

        return question

    def get_question(self, qid):
        return self.sqlite.get_question(qid)

    def answer_incorrect(self, qid, chat_id):
        self.sqlite.wrong_answer_question(qid, chat_id)

    def answer_correct(self, qid, chat_id, person):
        self.sqlite.correct_answer_question(qid, chat_id, person)
        return self.sqlite.get_answer_stats(qid, chat_id)

    def giveup(self, qid, chat_id):
        self.sqlite.giveup_question(qid, chat_id)
