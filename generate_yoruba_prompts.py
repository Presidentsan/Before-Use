from pathlib import Path

from tts_service import generate_yoruba_speech


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_prompts"
)


PROMPTS = {

    # =====================================================
    # PRODUCT CHECK
    # =====================================================

    "capture_prompt": (
        "Sọ ohun tí o rí lórí ọjà náà fún mi. "
        "O lè sọ orúkọ ọjà, nọ́mbà ìforúkọsílẹ̀, "
        "ilé-iṣẹ́ tó ṣe é, nọ́mbà ìṣelọpọ àti "
        "ọjọ́ tí yóò parí. "
        "Má ṣe yọ ara rẹ lẹ́nu bí o kò bá rí gbogbo wọn. "
        "A ó jẹ́ kí o ṣàyẹ̀wò àwọn àlàyé pàtàkì "
        "kí ètò yìí tó ṣàyẹ̀wò ẹ̀rí."
    ),

    "evidence_passport_result": (
        "Àbájáde ìṣàyẹ̀wò ti ṣetán. "
        "Jọ̀wọ́ wo àbájáde àti ẹ̀rí tó hàn lójú ìbòjú. "
        "Rántí pé ìbámu pẹ̀lú àkọsílẹ̀ ìforúkọsílẹ̀ "
        "kì í ṣe ẹ̀rí pé àpò ọjà tó wà lọ́wọ́ rẹ "
        "jẹ́ ojúlówó."
    ),


    # =====================================================
    # PHARMACY
    # =====================================================

    "pharmacy_search_prompt": (
        "Sọ àgbègbè tí o fẹ́ kí n wá ilé elegbogi sí fún mi. "
        "O tún lè sọ bí o ṣe fẹ́ kí ìjìnnà náà tó. "
        "Fún àpẹẹrẹ, o lè sọ pé kí n wá ilé elegbogi "
        "ní agbègbè Ìkẹ́jà."
    ),

    "pharmacy_result_summary": (
        "Àwọn àbájáde ìwádìí ilé elegbogi ti ṣetán. "
        "Jọ̀wọ́ wo àwọn ibi tí a rí lójú ìbòjú. "
        "Ṣàyẹ̀wò àlàyé ilé elegbogi náà dáadáa "
        "kí o tó pinnu ibi tí o máa lọ."
    ),
}


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Generating fixed Yorùbá prompts..."
    )

    print()

    for message_id, text in PROMPTS.items():

        output_file = (
            OUTPUT_DIR
            / f"{message_id}.wav"
        )

        print(
            "Generating:",
            message_id,
        )

        audio_bytes = (
            generate_yoruba_speech(
                text
            )
        )

        output_file.write_bytes(
            audio_bytes
        )

        print(
            "Saved:",
            output_file
        )

        print(
            "Size:",
            len(audio_bytes),
            "bytes",
        )

        print()

    print(
        "Finished."
    )

    print()

    print(
        "Generated files:"
    )

    for message_id in PROMPTS:

        print(
            " -",
            (
                OUTPUT_DIR
                / f"{message_id}.wav"
            )
        )


if __name__ == "__main__":
    main()