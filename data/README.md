# Dataset for lab 2

The **twitter_samples** corpus is provided by NLTK and is not redistributed here.
The corpus's licensing conditions are subject to the Twitter Developer Agreement.

`main.py` tries to download `twitter_samples` automatically.
If it fails (e.g. an SSL certificate error), download the official package:

https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/twitter_samples.zip

Unzip and copy **only** `positive_tweets.json` and `negative_tweets.json`
to the `data/` folder next to this README. `main.py` will use them locally.

`stopwords_en.txt` is included so no separate stopwords download is needed.
Do not push the downloaded tweets to GitHub without reviewing the corpus license.
