"""Resume generating Before Use English recordings at the rate-limit-safe pace.

Usage (from project root):
    python generate_english_prompts_resume.py --start-from pharmacy_search_prompt

Previously generated WAV files are left untouched. The --start-from option is
inclusive. With no --start-from, this processes all messages.
"""
import argparse
import time
from pathlib import Path
from tts_service import generate_english_speech

MESSAGES = {
    'welcome_home': 'Welcome to Before Use, your voice-powered product checking assistant. To get started, tap Check a Product, then speak or type the details on the label. We will help you compare those details with available official registration records and safety alerts. Let us get started.',
    'capture_prompt': 'Tell me what you can read on the product label. You may mention the product name, NAFDAC number, manufacturer, batch number, and expiry date. You can also type the details. After recording, review everything carefully before checking.',
    'confirmation_prompt': 'Review the details we captured, and correct anything that does not match the product label.',
    'ready_to_check': 'Your product details are ready. Continue to check the available evidence.',
    'checking_prompt': 'Before Use is checking the available official evidence. A registration match alone does not prove that the physical product is genuine.',
    'pharmacy_search_prompt': 'Tell me the area where you want to find a pharmacy. You can also give a distance. For example, find me a pharmacy around Ikeja within five kilometres.',
    'evidence_passport_result': 'Your evidence check is complete. Review the findings and safety alerts on the screen. A registration match does not prove the physical pack is genuine. Listen to or read the specific result before deciding what to do.',
    'pharmacy_result_summary': 'Your pharmacy search results are ready. Review the listed locations and check registration on the official Pharmacists Council of Nigeria website.',
}

parser = argparse.ArgumentParser()
parser.add_argument('--start-from', choices=list(MESSAGES), default='welcome_home', help='First message to regenerate (inclusive)')
parser.add_argument('--pause', type=int, default=30, help='Seconds between API calls; default 30')
args = parser.parse_args()

output = Path(__file__).resolve().parent / 'voice_assets' / 'english_prompts'
output.mkdir(parents=True, exist_ok=True)
started = False
pending = []
for name, script in MESSAGES.items():
    if name == args.start_from:
        started = True
    if started:
        pending.append((name, script))

for index, (name, script) in enumerate(pending):
    if index:
        print(f'Waiting {args.pause} seconds to respect the Gemini quota...', flush=True)
        time.sleep(args.pause)
    print('Generating:', name, flush=True)
    try:
        audio = generate_english_speech(script)
        if not audio.startswith(b'RIFF'):
            raise ValueError('Expected WAV data; not writing invalid audio')
        (output / (name + '.wav')).write_bytes(audio)
        print('Saved:', name, flush=True)
    except Exception as exc:
        print(f'Generation stopped at {name}: {type(exc).__name__}: {exc}', flush=True)
        print('Resume later with: python generate_english_prompts_resume.py --start-from ' + name, flush=True)
        raise SystemExit(1)
print('All selected English recordings saved.')
