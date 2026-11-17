import tempfile
import unittest
from pathlib import Path
from database import Store, breakdown, dollars

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Store(Path(self.tmp.name)/'spay.db')
        self.poster = self.db.register('poster1','poster')
        self.supporter = self.db.register('supporter1','billionaire')
    def tearDown(self):
        self.tmp.cleanup()
    def test_breakdown(self):
        self.assertEqual(breakdown('100.00'),(10000,200,10200))
        self.assertEqual(breakdown('0.01'),(1,0,1))
        self.assertEqual(breakdown('0.25'),(25,1,26))
        self.assertEqual(dollars(10200),'$102.00')
    def test_invalid_amounts(self):
        for amount in ['nan','Infinity','-1','0','1.001','1000001','hello']:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                breakdown(amount)
    def test_funding_atomic_and_once(self):
        bill = self.db.create_bill(self.poster,'Utility bill','Electricity','100.00')
        self.assertEqual(self.db.demo_fund(self.supporter,bill),(10000,200))
        self.assertEqual(self.db.summary(),{'n':1,'base':10000,'fees':200})
        with self.assertRaises(ValueError):
            self.db.demo_fund(self.supporter,bill)
        self.assertEqual(self.db.summary()['n'],1)
        self.assertEqual(self.db.bills(poster_id=self.poster)[0]['status'],'demo_funded')
    def test_role_enforcement(self):
        with self.assertRaises(ValueError):
            self.db.create_bill(self.supporter,'Utility bill','','10')
        bill=self.db.create_bill(self.poster,'Utility bill','','10')
        with self.assertRaises(ValueError):
            self.db.demo_fund(self.poster,bill)
    def test_persistence(self):
        self.db.create_bill(self.poster,'Utility bill','','25')
        reopened=Store(Path(self.tmp.name)/'spay.db')
        self.assertEqual(len(reopened.bills(poster_id=self.poster)),1)

if __name__=='__main__':
    unittest.main()
