from product_extractor import extract_product_details


test_transcript = (
    "i'm checking a pack of panador extra. "
    "i can see a nerve duct number that says e4-1409."
)

details = extract_product_details(test_transcript)

print(details)