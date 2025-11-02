import unittest
import sqlite3 as sql
import os
from back.app.tools.video_data.video_db import VideoDatabase

class TestVideoDatabase(unittest.TestCase):
    def get_connection(self):
        return sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')

    def setUp(self):
        self.video_db = VideoDatabase()

    def tearDown(self):
        os.remove('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')

    def test_first_generate_video(self):
        # テスト用の動画、プロンプト、manimコードのid
        expected_video_id = 1  # 期待されるvideo_id（初回挿入時）
        expected_generate_id = 1 # 期待されるgenerate_id（初回挿入時）
        expected_prompt_id = 1   # 期待されるprompt_id（初回挿入時）
        expected_manim_code_id = 1  # 期待されるmanim_code_id（初回挿入時）

        expected_video_data = {
            'video_id': expected_video_id,
            'generate_id': expected_generate_id,
            'video_path': 'test_data/video.mp4',
            'prompt_id': expected_prompt_id,
            'manim_code_id': expected_manim_code_id,
            'generate_time': None,  # 動的に生成されるためNoneで比較対象から除外
            'edit_time': None,      # 動的に生成されるためNoneで比較対象から除外
            'edit_count': 1
        }

        # プロンプト確認画面への遷移時の動作
        self.video_db.generate_prompt()

        # 動画生成処理のテスト
        video_id = self.video_db.generate_video('test_data/video.mp4', 'test_data/prompt.json', 'test_data/manim_code.json')

        # DBに正しく保存されたか確認
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM video WHERE video_id = ?', (video_id,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "動画がDBに保存されていません。")
        for key, expected_value in expected_video_data.items():
            if expected_value is not None:
                self.assertEqual(row[list(expected_video_data.keys()).index(key)], expected_value, f"{key}が期待値と異なります。")

        
    def test_second_generate_video(self):
        # テスト用の動画、プロンプト、manimコードのid
        expected_video_id = 2  # 期待されるvideo_id
        expected_generate_id = 2 # 期待されるgenerate_id
        expected_prompt_id = 2  # 期待されるprompt_id
        expected_manim_code_id = 2  # 期待されるmanim_code_id

        expected_video_data = {
            'video_id': expected_video_id,
            'generate_id': expected_generate_id,
            'video_path': 'test_data/video.mp4',
            'prompt_id': expected_prompt_id,
            'manim_code_id': expected_manim_code_id,
            'generate_time': None,  # 動的に生成されるためNoneで比較対象から除外
            'edit_time': None,      # 動的に生成されるためNoneで比較対象から除外
            'edit_count': 1
        }
        self.video_db.generate_prompt()
        self.video_db.generate_video('test_data/video.mp4', 'test_data/prompt.json', 'test_data/manim_code.json')

        # プロンプト確認画面への遷移時の動作
        generate_id = self.video_db.generate_prompt()

        # 動画生成処理のテスト
        video_id = self.video_db.generate_video('test_data/video.mp4', 'test_data/prompt.json', 'test_data/manim_code.json')

        # DBに正しく保存されたか確認
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM video WHERE video_id = ?', (video_id,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "動画がDBに保存されていません。")
        for key, expected_value in expected_video_data.items():
            if expected_value is not None:
                self.assertEqual(row[list(expected_video_data.keys()).index(key)], expected_value, f"{key}が期待値と異なります。")

        self.assertEqual(generate_id, expected_generate_id, "generate_idが期待値と異なります。")

    def test_edit_video(self):
        # 既存の動画IDと新しい動画パス
        prior_video_id = 1  # 事前に存在する動画ID
        new_video_path = 'test_data/edited_video.mp4'
        expected_video_id = 2  # 期待される新しいvideo_id
        expected_data = {
            'video_id': expected_video_id,
            'generate_id': 1,
            'video_path': new_video_path,
            'prompt_id': 1,
            'manim_code_id': 1,
            'generate_time': None,  # 動的に生成されるためNoneで比較対象から除外
            'edit_time': None,      # 動的に生成されるためNoneで比較対象から除外
            'edit_count': 2
        }
        self.video_db.generate_prompt()
        self.video_db.generate_video('test_data/video.mp4', 'test_data/prompt.json', 'test_data/manim_code.json')

        # 動画編集処理のテスト
        new_video_id = self.video_db.edit_video(prior_video_id, new_video_path)

        # DBに正しく保存されたか確認
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM video WHERE video_id = ?', (new_video_id,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "編集された動画がDBに保存されていません。")
        for key, expected_value in expected_data.items():
            if expected_value is not None:
                self.assertEqual(row[list(expected_data.keys()).index(key)], expected_value, f"{key}が期待値と異なります。")

    def test_delete_video(self):
        # 削除する動画ID
        video_id_to_delete = 2  # 事前に存在する動画ID

        # 動画削除処理のテスト
        self.video_db.delete_video(video_id_to_delete)

        # DBから正しく削除されたか確認
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM video WHERE video_id = ?', (video_id_to_delete,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNone(row, "動画がDBから削除されていません。")

if __name__ == '__main__':
    unittest.main()
