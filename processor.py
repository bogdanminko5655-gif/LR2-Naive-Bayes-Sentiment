"""Єдині правила препроцесингу для навчання та експорту вебмоделі."""
from pathlib import Path
import re
import string
from nltk.tokenize import TweetTokenizer
from nltk.stem import PorterStemmer

BASE_DIR = Path(__file__).resolve().parent
STOPWORDS = set((BASE_DIR / 'data' / 'stopwords_en.txt').read_text(encoding='utf-8').splitlines())
# Негативні частки не прибираємо: 'not good' має відрізнятись від 'good'.
STOPWORDS -= {'no', 'nor', 'not', "don't", "isn't", "wasn't", "won't", "can't"}
STEMMER = PorterStemmer()
TOKENIZER = TweetTokenizer(preserve_case=False, strip_handles=True, reduce_len=True)


def raw_tokens(tweet: str) -> list[str]:
    """Очистити URL, ретвіти, тікери та #; залишити значущі токени."""
    tweet = re.sub(r'^RT\s+', '', str(tweet), flags=re.I)
    tweet = re.sub(r'https?://\S+|www\.\S+', ' ', tweet, flags=re.I)
    tweet = re.sub(r'\$\w+', ' ', tweet)
    tweet = re.sub(r'#', '', tweet)
    tokens = TOKENIZER.tokenize(tweet)
    return [t for t in tokens if t not in STOPWORDS and
            t not in string.punctuation and t.strip() and
            not t.startswith('@')]


def process_tweet(tweet: str) -> list[str]:
    return [STEMMER.stem(token) for token in raw_tokens(tweet)]
