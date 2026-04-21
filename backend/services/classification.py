NONE_OPTION = "해당 없음"


def classify_from_answers(answers: list[list[str]]) -> bool:
    for selected_options in answers:
        for option in selected_options:
            if option != NONE_OPTION:
                return True
    return False
