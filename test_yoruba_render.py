from voice_reply import (
    _render_reply_text,
)


TESTS = [
    (
        "Tell me what you can see on the product. "
        "You can give several details in one recording."
    ),

    (
        "I found Panadol Extra, NAFDAC number 04-0005. "
        "Please compare these details with the product "
        "in your hand."
    ),

    (
        "The registration record matches the details "
        "you supplied. This does not prove that this "
        "individual physical pack is genuine."
    ),
]


for number, text in enumerate(
    TESTS,
    start=1,
):

    print()
    print("=" * 60)

    print(
        f"TEST {number}"
    )

    print()

    print(
        "ENGLISH:"
    )

    print(
        text
    )

    print()

    print(
        "YORUBA:"
    )

    print(
        _render_reply_text(
            text,
            "yo",
        )
    )