import sqlite3
from question import Question, difficulty_to_string
import datetime
import time


class SQLiteAPI(object):
    def __init__(self, dbname):
        self.conn = sqlite3.connect(dbname)
        self.create_tables_if_not_exists()

    def create_tables_if_not_exists(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS questions(
            qid integer PRIMARY KEY,
            body text,
            answer text,
            comment text,
            tournament_title text,
            difficulty text,
            rating real,
            trusted integer)
        ''')

        c.execute('''CREATE TABLE IF NOT EXISTS answers(
            chat_id integer,
            qid integer,
            person text DEFAULT '',
            tries integer DEFAULT 0,
            answered integer DEFAULT 0,
            giveup integer DEFAULT 0,
            start_time integer DEFAULT 0,
            user_text text DEFAULT '',
            finish_time integer DEFAULT 0,
            PRIMARY KEY (chat_id, qid)
        )''')

        self.conn.commit()

    def store_new_question(self, question, chat_id, trusted=0):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO questions VALUES({question.qid}, '{question.text}', '{question.answer}', '{question.comment}', '{question.tournament_title}', '{difficulty_to_string(question.difficulty)}', {question.rating}, {trusted})")

        c.execute(f"INSERT INTO answers (chat_id, qid) VALUES ({chat_id}, {question.qid})")
        self.conn.commit()

    def get_question(self, qid):
        c = self.conn.cursor()
        c.execute("SELECT * FROM questions WHERE qid=?", (qid, ))
        row = c.fetchone()
        return Question(row[0], row[1], row[2], row[3], row[4], row[5], row[6])

    def start_question(self, qid, chat_id):
        c = self.conn.cursor()
        start = int(time.time())
        c.execute(f"UPDATE answers SET start_time = {start} WHERE qid = ? and chat_id = ?", (qid, chat_id))
        self.conn.commit()

    def wrong_answer_question(self, qid, chat_id):
        c = self.conn.cursor()
        c.execute("UPDATE answers SET tries = tries + 1 WHERE qid = ? and chat_id = ?", (qid, chat_id))

        self.conn.commit()

    def correct_answer_question(self, qid, chat_id, person):
        finish = int(time.time())
        c = self.conn.cursor()
        c.execute("UPDATE answers SET tries = tries + 1, person = ?, answered = 1, finish_time = ? WHERE qid = ? and chat_id = ?", (person, finish, qid, chat_id))
        self.conn.commit()

    def giveup_question(self, qid, chat_id):
        finish = int(time.time())
        c = self.conn.cursor()
        c.execute("UPDATE answers SET tries = tries + 1, giveup = 1, answered = 1, finish_time = ? WHERE qid = ? and chat_id = ?", (finish, qid, chat_id))
        self.conn.commit()

    def is_question_answered(self, qid, chat_id):
        c = self.conn.cursor()
        c.execute("SELECT answered FROM answers WHERE qid = ? and chat_id = ?", (qid, chat_id))
        row = c.fetchone()
        if not row:
            return False
        return row[0] != 0

    def get_trusted_question(self, chat_id, trusted):
        c = self.conn.cursor()
        c.execute("SELECT qid, body, answer, comment, tournament_title, difficulty, rating FROM questions INNER JOIN answers USING (qid) WHERE chat_id = ? AND answered = 0 and trusted = ?", (chat_id, int(trusted)))
        row = c.fetchone()
        if not row:
            raise Exception("Cannot find any not already answered question")
        return Question(row[0], row[1], row[2], row[3], row[4], row[5], row[6])

    def get_answer_stats(self, qid, chat_id):
        c = self.conn.cursor()
        c.execute("SELECT tries, start_time, finish_time FROM answers WHERE qid = ? and chat_id = ?", (qid, chat_id))
        row = c.fetchone()
        if not row:
            return (0, 0, 0)

        tries = row[0]
        start_time = row[1]
        end_time = row[2]
        return tries, datetime.timedelta(seconds=end_time - start_time)



