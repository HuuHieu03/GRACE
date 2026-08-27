from transformers import AutoTokenizer, RobertaTokenizer, AutoModel

print("1. Testing with extra_special_tokens=[]:")
try:
    tok = AutoTokenizer.from_pretrained("Salesforce/codet5-base", extra_special_tokens=[])
    print("Success 1!")
except Exception as e:
    print("Error 1:", e)

print("2. Testing with RobertaTokenizerFast:")
try:
    from transformers import RobertaTokenizerFast
    tok = RobertaTokenizerFast.from_pretrained("Salesforce/codet5-base")
    print("Success 2!")
except Exception as e:
    print("Error 2:", e)

print("3. Testing AutoTokenizer with revision or trust_remote_code:")
try:
    tok = AutoTokenizer.from_pretrained("Salesforce/codet5-base", trust_remote_code=True)
    print("Success 3!")
except Exception as e:
    print("Error 3:", e)

print("4. Testing T5Tokenizer:")
try:
    from transformers import T5Tokenizer
    tok = T5Tokenizer.from_pretrained("Salesforce/codet5-base")
    print("Success 4!")
except Exception as e:
    print("Error 4:", e)

print("5. Testing RobertaTokenizer with vocab_file, merges_file:")
try:
    from huggingface_hub import hf_hub_download
    vocab = hf_hub_download("Salesforce/codet5-base", "vocab.json")
    merges = hf_hub_download("Salesforce/codet5-base", "merges.txt")
    tok = RobertaTokenizer(vocab_file=vocab, merges_file=merges)
    print("Success 5 - RobertaTokenizer with manual vocab/merges!")
except Exception as e:
    print("Error 5:", e)
