import sqlite3
import tempfile
import unittest
from pathlib import Path

from data_pipeline.catalog_builder import Record, write_db


class CatalogBuilderSchemaTests(unittest.TestCase):
    def test_write_db_produces_runtime_schema(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'catalog.sqlite3'
            rows=[
                Record(
                    content_id='demo:1', title='测试恋爱片', content_type='movie',
                    release_year=2025, runtime_minutes=100, countries=['中国大陆'],
                    language='Chinese', genres=['Romance','Comedy'],
                    overview='一段轻松的关系故事，用于离线验证结构化标签和检索字段。',
                    poster_url='https://example.test/poster.jpg', source='unit',
                    source_id='1', source_url='https://example.test/1',
                    rating_score=8.1, popularity=12,
                ),
                Record(
                    content_id='demo:2', title='测试悬疑剧', content_type='series',
                    release_year=2024, episode_runtime_minutes=45, countries=['中国大陆'],
                    language='Chinese', genres=['Thriller'],
                    overview='围绕谜题展开的剧集。', source='unit',
                    source_id='2', source_url='https://example.test/2',
                ),
            ]
            write_db(str(db),rows)
            con=sqlite3.connect(db)
            self.assertEqual(2,con.execute('select count(*) from content').fetchone()[0])
            self.assertEqual('2.1',con.execute("select value from catalog_meta where key='schema_version'").fetchone()[0])
            movie=con.execute("select relationship_tags_json,emotion_tags_json from content where content_id='demo:1'").fetchone()
            self.assertIn('romantic',movie[0])
            self.assertIn('funny',movie[1])
            try:
                fts=con.execute("select count(*) from content_fts").fetchone()[0]
                self.assertEqual(2,fts)
            except sqlite3.OperationalError:
                pass
            con.close()


if __name__=='__main__':
    unittest.main()
