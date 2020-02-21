from question import Question, QuestionDifficulty
import requests
import logging
import xml.etree.ElementTree as ET

DB_URL = 'https://db.chgk.info/xml'
MAX_ANSWER_LENGTH_LETTERS = 15
MAX_ANSWER_LENGTH_WORDS = 4
MIN_RATING = 0.07
RETRY_COUNT = 5


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


class ChgkDBAPI(object):
    def __init__(self, db_uri=DB_URL):
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


