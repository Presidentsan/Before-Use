def capture_prompt():
    return (
        "Tell me what you can see on the product. "
        "You can say the product name, NAFDAC number, "
        "manufacturer, batch number, and expiry date in any order."
    )


def confirmation_prompt(details):
    details = details or {}

    product_name = details.get("product_name")

    if product_name:
        return (
            f"I've organised what I heard about {product_name}. "
            "Please compare every detail with the product in your hand "
            "and correct anything that is not right."
        )

    return (
        "I've organised what I heard. "
        "Please compare every detail with the product in your hand "
        "and correct anything that is not right."
    )


def missing_detail_prompt(question):
    if not question:
        return "There is one more detail I need."

    return (
        f"One more thing. {question} "
        "If you cannot find it on the pack, you can skip it."
    )


def ready_to_check_prompt():
    return (
        "I have the product details you were able to provide. "
        "The next step is to check them against available official evidence."
    )


def checking_prompt():
    return (
        "I'm ready to compare your confirmed information with "
        "available official product records and relevant safety alerts."
    )


def development_result_prompt():
    return (
        "Your product details are ready. "
        "The official evidence engine has not been connected yet, "
        "so I am not making a verification claim."
    )
