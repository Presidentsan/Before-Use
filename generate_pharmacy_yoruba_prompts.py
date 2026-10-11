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

        print()

    print(
        "Pharmacy Yorùbá audio complete."
    )


if __name__ == "__main__":
    main()