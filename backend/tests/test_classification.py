from backend.services.classification import classify_from_answers


def test_classifies_false_when_all_answers_are_none_option():
    answers = [["해당 없음"], ["해당 없음"]]
    assert classify_from_answers(answers) is False


def test_classifies_false_when_answers_are_empty():
    assert classify_from_answers([]) is False


def test_classifies_true_when_any_answer_has_real_option():
    answers = [["해당 없음"], ["설계 자료"]]
    assert classify_from_answers(answers) is True


def test_classifies_true_when_answer_mixes_none_and_real_option():
    answers = [["해당 없음"], ["해당 없음", "공정 조건"]]
    assert classify_from_answers(answers) is True
