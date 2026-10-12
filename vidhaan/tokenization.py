"""Versioned, deterministic lexical tokenization shared by indexing and ranking."""
import hashlib
import json
import re

STOP = set('a an the is are was were be been being to for of in on at as and or it its this that what which how does do can i my me please under about tell explain source document act section'.split())
TOKENIZER = 'vidhaan-lexical-v1-' + hashlib.sha256(json.dumps(sorted(STOP)).encode()).hexdigest()[:12]


def normalize(question):
    return ' '.join(question.strip().split())[:2000]


def tokenize(text):
    return [t for t in re.findall(r'[a-z0-9]+(?:\.[a-z0-9]+)*', text.casefold()) if t not in STOP]
