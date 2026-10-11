QUESTION_FLOW = [
    (
        "product_name",
        "What is the name of the product?"
    ),
    (
        "nafdac_number",
        "Can you see a NAFDAC registration number? "
        "Please read it exactly as printed."
    ),
    (
        "manufacturer",
        "Can you see the manufacturer's or applicant's name on the pack? "
        "If yes, please read it aloud."
    ),
    (
        "batch_number",
        "Can you see a batch or lot number? "
        "If yes, please read it aloud."
    ),
    (
        "expiry_date",
        "Can you see an expiry date? "
        "If yes, please read it aloud."
    ),
]


def get_next_question(product_state, skipped_fields=None):
    """
    Decide what Before Use should ask next.

    Inputs:
        product_state:
            Dictionary containing the product information
            collected so far.

        skipped_fields:
            Fields the user said they cannot find.

    Output:
        Dictionary containing:
            - field
            - question

        Returns None when there are no more questions.
    """

    if skipped_fields is None:
        skipped_fields = set()

    for field, question in QUESTION_FLOW:

        value = product_state.get(field)

        if not value and field not in skipped_fields:

            return {
                "field": field,
                "question": question,
            }

    return None