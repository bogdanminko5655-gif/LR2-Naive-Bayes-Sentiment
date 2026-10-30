"""Лабораторна №2: Naive Bayes sentiment classification, NLTK twitter_samples.
Запуск: python main.py  (після pip install -r requirements.txt).
Дані: NLTK twitter_samples або два локальні JSON-файли у data/.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
import json
import math
from pathlib import Path
import random
import sys
from typing import Iterable

from processor import BASE_DIR, STOPWORDS, raw_tokens, process_tweet, STEMMER

RESULTS = BASE_DIR / 'results'
DOCS = BASE_DIR / 'docs'
DATA = BASE_DIR / 'data'


def load_jsonl_tweets(path: Path) -> list[str]:
    """twitter_samples files: json per line, occasionally strings/objects."""
    items = []
    with path.open('r', encoding='utf-8') as file:
        for line in file:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, str):
                items.append(value)
            elif isinstance(value, dict) and 'text' in value:
                items.append(value['text'])
            else:
                raise ValueError(f'Непідтримуваний запис у {path.name}')
    return items


def load_dataset():
    """Use local JSON first, then NLTK corpus, then attempt official download."""
    for folder in (DATA, DATA / 'twitter_samples'):
        pos = folder / 'positive_tweets.json'
        neg = folder / 'negative_tweets.json'
        if pos.exists() and neg.exists():
            print(f'Локальні дані: {folder}')
            return load_jsonl_tweets(pos), load_jsonl_tweets(neg)
    from nltk.corpus import twitter_samples
    try:
        return twitter_samples.strings('positive_tweets.json'), twitter_samples.strings('negative_tweets.json')
    except LookupError:
        pass
    import nltk
    print('Завантаження корпусу twitter_samples (NLTK)...')
    ok = False
    try:
        ok = nltk.download('twitter_samples', quiet=True, raise_on_error=False)
    except Exception as exc:
        print('Попередження завантаження:', exc)
    if ok:
        try:
            return twitter_samples.strings('positive_tweets.json'), twitter_samples.strings('negative_tweets.json')
        except Exception:
            pass
    raise RuntimeError(
        'Не вдалось завантажити twitter_samples. Завантажте вручну:\n'
        'https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/twitter_samples.zip\n'
        'Розпакуйте та покладіть positive_tweets.json і negative_tweets.json у data/\n'
        'Не вимикайте SSL-перевірку. Деталі: README.md'
    )


def split_balanced(positive: list[str], negative: list[str], seed: int = 42):
    """Рівні частки за класами: 80% train, 20% test."""
    rng = random.Random(seed)
    pos, neg = list(positive), list(negative)
    rng.shuffle(pos)
    rng.shuffle(neg)
    npos = int(len(pos) * .8)
    nneg = int(len(neg) * .8)
    train = [(x, 1) for x in pos[:npos]] + [(x, 0) for x in neg[:nneg]]
    test = [(x, 1) for x in pos[npos:]] + [(x, 0) for x in neg[nneg:]]
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def count_tweets(tweets: Iterable[tuple[str, int]]) -> Counter:
    """Словник частот: (stem, class) -> число вживань."""
    freqs = Counter()
    for tweet, label in tweets:
        for word in process_tweet(tweet):
            freqs[(word, label)] += 1
    return freqs


def train_naive_bayes(freqs: Counter, train_set: list[tuple[str, int]]):
    """Multinomial NB у формі log odds із згладжуванням Лапласа (+1)."""
    vocab = {word for word, _ in freqs}
    V = len(vocab)
    if not V:
        raise ValueError('Порожній словник')
    D_pos = sum(label == 1 for _, label in train_set)
    D_neg = len(train_set) - D_pos
    if D_pos == 0 or D_neg == 0:
        raise ValueError('У навчанні потрібні обидва класи')
    N_pos = sum(freq for (_, cls), freq in freqs.items() if cls == 1)
    N_neg = sum(freq for (_, cls), freq in freqs.items() if cls == 0)
    logprior = math.log(D_pos / D_neg)
    loglikelihood = {}
    for word in vocab:
        p_pos = (freqs.get((word, 1), 0) + 1) / (N_pos + V)
        p_neg = (freqs.get((word, 0), 0) + 1) / (N_neg + V)
        loglikelihood[word] = math.log(p_pos / p_neg)
    return logprior, loglikelihood


def naive_bayes_predict(tweet: str, logprior: float, loglikelihood: dict) -> float:
    return logprior + sum(loglikelihood.get(w, 0.0) for w in process_tweet(tweet))


def test_naive_bayes(test_set, logprior, loglikelihood):
    predictions = []
    for i, (tweet, truth) in enumerate(test_set):
        score = naive_bayes_predict(tweet, logprior, loglikelihood)
        predicted = int(score > 0)
        predictions.append({'index': i, 'truth': truth, 'predicted': predicted,
                            'score': round(score, 6), 'correct': int(truth == predicted),
                            'tokens': ' '.join(process_tweet(tweet)[:16])})
    accuracy = sum(row['correct'] for row in predictions) / len(predictions)
    return accuracy, predictions


def get_ratio(freqs, word):
    pos = freqs.get((word, 1), 0)
    neg = freqs.get((word, 0), 0)
    return {'positive': pos, 'negative': neg, 'ratio': (pos + 1)/(neg + 1)}


def get_words_by_threshold(freqs, label, threshold, min_total=3):
    result = {}
    for word in {w for w, _ in freqs}:
        r = get_ratio(freqs, word)
        if r['positive'] + r['negative'] < min_total:
            continue
        if (label == 1 and r['ratio'] >= threshold) or (label == 0 and r['ratio'] <= threshold):
            result[word] = r
    return result


def save_csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def export_model(logprior: float, loglikelihood: dict, train: list[tuple[str, int]],
                 accuracy: float, docs: Path = DOCS):
    """Maps raw tokens -> Porter stems for browser; no third-party JS dependencies."""
    stem_map = {}
    for tweet, _ in train:
        for raw in raw_tokens(tweet):
            stem_map[raw] = STEMMER.stem(raw)
    payload = {'trained': True, 'dataset': 'NLTK twitter_samples',
               'logprior': logprior, 'loglikelihood': loglikelihood,
               'stem_map': stem_map, 'stopwords': sorted(STOPWORDS),
               'accuracy': round(accuracy, 5), 'train_count': len(train),
               'preprocessing': 'TweetTokenizer + PorterStemmer; browser uses exported known-token map'}
    docs.mkdir(parents=True, exist_ok=True)
    (docs / 'model.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
                                    encoding='utf-8')
    return payload


def make_graphs(metrics, words):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10})
    c = metrics['confusion_matrix']
    fig, ax = plt.subplots(figsize=(5.7, 4.6))
    img = ax.imshow(c, cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(c[i][j]), ha='center', va='center', fontsize=18,
                    color='white' if c[i][j] > max(map(max, c))*.55 else '#17324a')
    ax.set(xticks=[0,1], yticks=[0,1], xticklabels=['Negative','Positive'],
           yticklabels=['Negative','Positive'], xlabel='Predicted', ylabel='True',
           title='Confusion matrix - Naive Bayes')
    fig.tight_layout()
    fig.savefig(RESULTS/'confusion_matrix.png', dpi=175)
    plt.close(fig)
    top_pos = sorted(words, key=lambda r:r['loglikelihood'], reverse=True)[:10]
    top_neg = sorted(words, key=lambda r:r['loglikelihood'])[:10]
    chosen = top_neg[::-1] + top_pos
    fig, ax = plt.subplots(figsize=(9.5,6))
    names = [row['word'] for row in chosen]
    values = [row['loglikelihood'] for row in chosen]
    colors = ['#d75d68' if v < 0 else '#208c84' for v in values]
    ax.barh(range(len(values)), values, color=colors)
    ax.set_yticks(range(len(names)), names)
    ax.axvline(0, color='#666', linewidth=.8)
    ax.set_xlabel('Log likelihood ratio (positive / negative)')
    ax.set_title('Top indicative words (training data)')
    fig.tight_layout()
    fig.savefig(RESULTS/'top_words.png', dpi=165)
    plt.close(fig)


def execute(positive, negative):
    RESULTS.mkdir(exist_ok=True)
    train, test = split_balanced(positive, negative)
    print(f'Дані: позитивних {len(positive)}, негативних {len(negative)}')
    print(f'Навчальна вибірка: {len(train)}, тестова: {len(test)}')
    freqs = count_tweets(train)
    logprior, likelihood = train_naive_bayes(freqs, train)
    accuracy, predictions = test_naive_bayes(test, logprior, likelihood)
    tn = sum(r['truth']==0 and r['predicted']==0 for r in predictions)
    fp = sum(r['truth']==0 and r['predicted']==1 for r in predictions)
    fn = sum(r['truth']==1 and r['predicted']==0 for r in predictions)
    tp = sum(r['truth']==1 and r['predicted']==1 for r in predictions)
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0
    vocab = {w for w,_ in freqs}
    word_rows = [dict(word=w, positive=freqs.get((w,1), 0),
                      negative=freqs.get((w,0), 0),
                      ratio=round(get_ratio(freqs,w)['ratio'],6),
                      loglikelihood=round(likelihood[w],6)) for w in vocab]
    word_rows.sort(key=lambda d: (d['positive']+d['negative'],d['word']), reverse=True)
    save_csv(RESULTS/'word_frequencies.csv', ['word','positive','negative','ratio','loglikelihood'],word_rows)
    save_csv(RESULTS/'test_predictions.csv', list(predictions[0]), predictions)
    mistakes = [r for r in predictions if r['correct']==0]
    save_csv(RESULTS/'classification_errors.csv', list(predictions[0]), mistakes)
    examples = [
       'I am happy because I am learning :)',
       'Today is wonderful and I feel great!',
       'I hate this awful day :(',
       'This movie is not good at all.'
    ]
    example_rows = []
    for text in examples:
        score = naive_bayes_predict(text, logprior, likelihood)
        example_rows.append({'tweet':text,'log_score':round(score,6),
                             'predicted':'positive' if score > 0 else 'negative',
                             'tokens':' '.join(process_tweet(text))})
    save_csv(RESULTS/'own_tweets.csv', ['tweet','log_score','predicted','tokens'], example_rows)
    metrics = {
      'dataset':'NLTK twitter_samples','positive_count':len(positive),'negative_count':len(negative),
      'train_count':len(train),'test_count':len(test),'vocab_size':len(vocab),
      'logprior':round(logprior,9), 'accuracy':round(accuracy,6),'precision':round(precision,6),
      'recall':round(recall,6),'f1':round(f1,6),
      'confusion_matrix':[[tn,fp],[fn,tp]], 'errors':len(mistakes), 'seed':42,
      'class_ratio_train':{'positive':sum(y==1 for _,y in train), 'negative':sum(y==0 for _,y in train)}
    }
    (RESULTS/'metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
    make_graphs(metrics,word_rows)
    export_model(logprior,likelihood,train,accuracy)
    (RESULTS/'summary.md').write_text(
      f'# Результати ЛР2\n\nКорпус: NLTK twitter_samples.\n\n'
      f'- Навчальних: {len(train)}; тестових: {len(test)}\n'
      f'- Словник: {len(vocab)} основ\n'
      f'- Точність: **{accuracy:.2%}**\n'
      f'- Precision: {precision:.4f}; recall: {recall:.4f}; F1: {f1:.4f}\n'
      f'- Матриця помилок: {metrics["confusion_matrix"]}\n'
      f'- Помилок класифікації: {len(mistakes)}\n\n'
      'Деталі: metrics.json, classification_errors.csv, word_frequencies.csv і графіки.\n',
      encoding='utf-8')
    print(f'Словник: {len(vocab)} основ; log prior: {logprior:.5f}')
    print(f'Точність: {accuracy:.2%}; Precision: {precision:.4f}; Recall: {recall:.4f}; F1: {f1:.4f}')
    print('Матриця помилок (рядки: 0/1, колонки: 0/1):', metrics['confusion_matrix'])
    print(f'Неправильних прогнозів: {len(mistakes)}')
    print('Власні приклади:')
    for r in example_rows:
        print(' ',r['predicted'],f'(score={r["log_score"]:.4f})', r['tweet'])
    return metrics


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-report', action='store_true')
    args=parser.parse_args()
    positive,negative=load_dataset()
    if len(positive)<5 or len(negative)<5:
        raise ValueError('Замало даних для навчання і тестування')
    metrics=execute(positive,negative)
    if not args.no_report:
        from make_report import build_report
        build_report(metrics)
        print('Звіт: Lab2_Report.docx')
    print('Модель для GitHub Pages: docs/model.json')
    print('Результати: results/')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError,LookupError) as e:
        print('ПОМИЛКА:',e,file=sys.stderr)
        sys.exit(1)
