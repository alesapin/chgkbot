# -*- encoding: utf-8 -*-

import pymorphy2
from enum import Enum
import re
import string
from Levenshtein import distance

GROUPING_SPACE_REGEX = re.compile('([^\w_-]|[+])', re.U)

class ComparisonResult(Enum):
    EQUAL = 1
    ALMOST_EQUAL = 2
    NON_EQUAL = 3

class AnswersComporator(object):
    def __init__(self, norm_dist=2, lemma_dist=2):
        self.norm_dist = norm_dist
        self.lemma_dist = lemma_dist
        self.morph = pymorphy2.MorphAnalyzer()

    def _tokenize(self, text):
        return [t for t in GROUPING_SPACE_REGEX.split(text) if t and not t.isspace() and t not in string.punctuation]

    def is_similar(self, correct_answer, proposed_answer):
        if len(correct_answer) <= 3:
            if correct_answer == proposed_answer:
                return ComparisonResult.EQUAL
            else:
                return ComparisonResult.NON_EQUAL

        if distance(correct_answer, proposed_answer) <= 1:
            return ComparisonResult.ALMOST_EQUAL

        correct_tokenized = self._tokenize(correct_answer)
        proposed_tokenized = self._tokenize(proposed_answer)

        if len(correct_tokenized) != len(proposed_tokenized):
            return ComparisonResult.NON_EQUAL

        if correct_tokenized == proposed_tokenized:
            return ComparisonResult.EQUAL

        total_diff = 0
        for i in range(len(correct_tokenized)):
            total_diff += distance(correct_tokenized[i], proposed_tokenized[i])

        if total_diff <= 2:
            return ComparisonResult.ALMOST_EQUAL

        correct_lemmatized = [self.morph.parse(x)[0].normal_form for x in correct_tokenized]
        proposed_lemmatized = [self.morph.parse(x)[0].normal_form for x in proposed_tokenized]

        if correct_lemmatized == proposed_lemmatized:
            return ComparisonResult.ALMOST_EQUAL

        return ComparisonResult.NON_EQUAL
