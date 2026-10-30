import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from sys import path
path.insert(0, str(Path(__file__).resolve().parents[1]))
from processor import process_tweet, raw_tokens
from main import count_tweets, train_naive_bayes, naive_bayes_predict, split_balanced, get_ratio, export_model

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.train=[('I love great sunny days :)',1), ('Wonderful and beautiful movie',1),
                    ('I am very happy today',1), ('Horrible boring day',0),
                    ('I hate this terrible movie :(',0), ('Bad awful experience',0)]
        self.freq=count_tweets(self.train)
        self.prior, self.ll=train_naive_bayes(self.freq,self.train)

    def test_preprocessing(self):
        p=process_tweet('RT @user I love #wonderful days :) https://example.org')
        self.assertIn('wonder',p)
        self.assertNotIn('https',p)
        self.assertIn(':)',p)

    def test_prior_balanced(self):
        self.assertAlmostEqual(self.prior,0.0)

    def test_direction(self):
        self.assertGreater(naive_bayes_predict('wonderful love',self.prior,self.ll),0)
        self.assertLess(naive_bayes_predict('horrible awful',self.prior,self.ll),0)

    def test_ratio(self):
        self.assertGreater(get_ratio(self.freq,'wonder')['ratio'],1)

    def test_split(self):
        t,v=split_balanced(['good']*10,['bad']*10)
        self.assertEqual(len(t),16)
        self.assertEqual(len(v),4)
        self.assertEqual(sum(y for _,y in t),8)

    def test_exported_model(self):
        with tempfile.TemporaryDirectory() as d:
            result=export_model(self.prior,self.ll,self.train,.75,Path(d))
            output=json.loads((Path(d)/'model.json').read_text(encoding='utf-8'))
            self.assertTrue(output['trained'])
            self.assertIn('wonderful',result['stem_map'])
            self.assertIn(result['stem_map']['wonderful'],result['loglikelihood'])

if __name__=='__main__':unittest.main()
