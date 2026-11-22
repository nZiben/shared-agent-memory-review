import copy
import json
from pathlib import Path
import tempfile
import unittest
from review_forge.cli import topics
from review_forge.editorial import load_editorial
from review_forge.publishing import build_site, load_bibliography
from review_forge.util import ReviewError

ROOT=Path(__file__).resolve().parents[1]

class FocusedPublication(unittest.TestCase):
    def setUp(self):
        self.topic=topics()[0]['id']
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for source in (ROOT/'reviews').rglob('*.json'):
            dest=self.root/source.relative_to(ROOT)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(source.read_bytes())
        self.path=self.root/'reviews'/f'{self.topic}.json'

    def test_site_contains_only_its_own_review_and_preserves_history(self):
        site=build_site(self.root/'library',self.root/'public')
        library=json.loads((site/'data/library.json').read_text())
        self.assertEqual([t['id'] for t in library['topics']],[self.topic])
        data=json.loads((site/f'data/topics/{self.topic}.json').read_text())
        self.assertEqual(len(data['review']['papers']),100)
        self.assertEqual(len(data['versions']),3)
        self.assertEqual(len(list((site/'data/topics').glob('*.json'))),1)
        for version in data['versions']:
            self.assertTrue((site/f"exports/{self.topic}/{version['id']}/index.html").exists())

    def test_bad_revision_keeps_the_last_valid_site(self):
        site=build_site(self.root/'library',self.root/'public')
        before=(site/'site-manifest.json').read_bytes()
        data=json.loads(self.path.read_text())
        data['cards'][0]['claims'][0]['evidence'][0]['url']='javascript:alert(1)'
        self.path.write_text(json.dumps(data))
        with self.assertRaises(ReviewError):
            build_site(self.root/'library',site)
        self.assertEqual((site/'site-manifest.json').read_bytes(),before)

    def test_discovery_is_restricted_to_this_topic(self):
        plan=json.loads((ROOT/'bibliography/search-plan.json').read_text())
        bibliography=load_bibliography(ROOT/'bibliography/papers.json')
        self.assertEqual(set(plan['topics']),{self.topic})
        self.assertEqual(set(bibliography['topics']),{self.topic})
        self.assertTrue(plan['topics'][self.topic]['main'])

    def test_evidence_versions_and_claim_references_validate(self):
        data=load_editorial(ROOT/f'reviews/{self.topic}.json')
        self.assertEqual(len({p['arxiv_id'].split('v')[0] for p in data['papers']}),100)
        self.assertEqual(len(data['comparison']),100)
        self.assertTrue(all(row['theme'] and row['study_type'] for row in data['comparison']))

if __name__=='__main__':
    unittest.main()
