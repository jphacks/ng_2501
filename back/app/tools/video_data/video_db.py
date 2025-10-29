import sqlite3 as sql
import os
import datetime

class VideoDatabase:
    def __init__(self):
        print("Initializing Video Database...")
        if not os.path.exists('/workspaces/ai_agent/back/app/tools/video_data/video_data.db'):
            open('/workspaces/ai_agent/back/app/tools/video_data/video_data.db', 'a').close()
            conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE prompt (
                    prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_path TEXT
                )
            ''')
            
            cur.execute('''
                CREATE TABLE manim_code (
                    manim_code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manim_code_path TEXT
                )
            ''')
            
            cur.execute('''
                CREATE TABLE video (
                    video_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generate_id INTEGER,
                    video_path TEXT,
                    prompt_id INTEGER,
                    manim_code_id INTEGER,
                    generate_time TIMESTAMP,
                    edit_time TIMESTAMP,
                    edit_count INTEGER DEFAULT 1,
                    FOREIGN KEY (prompt_id) REFERENCES prompt(prompt_id) ON DELETE CASCADE,
                    FOREIGN KEY (manim_code_id) REFERENCES manim_code(manim_code_id) ON DELETE CASCADE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE generation (
                    generate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generate_time TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
        else:
            print("Database already exists.")
    
    def generate_prompt(self):
        '''生成IDを新規作成する処理
        
        最初の画面からプロンプト確認画面へと遷移する際に呼び出し、生成IDを新規作成する。

        Example:
            video_db = VideoDatabase()
            video_db.generate_prompt()
        '''

        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO generation (generate_time) VALUES (CURRENT_TIMESTAMP)')
        generate_id = cur.lastrowid
        conn.commit()
        conn.close()

        return generate_id

    def generate_video(self, video_path, prompt_path, manim_code_path):
        '''生成された動画とそれに紐づくプロンプト、manimコードをDBに保存する処理

        生成された動画ファイルのパス、プロンプトファイルのパス、manimコードファイルのパスを受け取り、DBに保存する。
        プロンプト、Manimコードは制約条件を課しているため、commitを同時に行う。

        Example:
            video_db = VideoDatabase()
            video_db.generate_video('path/to/video.mp4', 'path/to/prompt.json', 'path/to/manim_code.json')
        '''

        create_time = datetime.datetime.now()
        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        generate_id = cur.execute('SELECT MAX(generate_id) FROM generation').fetchone()[0]

        cur.execute('INSERT INTO prompt (prompt_path) VALUES (?)', (prompt_path,))
        prompt_id = cur.lastrowid
        cur.execute('INSERT INTO manim_code (manim_code_path) VALUES (?)', (manim_code_path,))
        manim_code_id = cur.lastrowid
        cur.execute('INSERT INTO video (generate_id, video_path, prompt_id, manim_code_id, generate_time) VALUES (?,?,?,?,?)', (generate_id, video_path, prompt_id, manim_code_id, create_time))
        video_id = cur.lastrowid
        conn.commit()
        conn.close()

        return video_id

    def edit_video(self, prior_video_id, new_video_path):
        '''編集された動画を新たにDBに保存する処理
        
        既存の動画IDをもとに、新たに生成された動画ファイルのパスを受け取り、DBに保存する。
        Example:
            video_db = VideoDatabase()
            video_db.edit_video(edit_video_id, 'path/to/edited_video.mp4')
        '''

        create_time = datetime.datetime.now()
        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('SELECT generate_id, prompt_id, manim_code_id, edit_count FROM video WHERE video_id = ?', (prior_video_id,))
        row = cur.fetchone()
        if row:
            generate_id, prompt_id, manim_code_id, edit_count = row
        else:
            conn.close()
            return

        new_edit_count = edit_count + 1
        cur.execute('INSERT INTO video (generate_id, video_path, prompt_id, manim_code_id, generate_time, edit_count) VALUES (?,?,?,?,?,?)', (generate_id, new_video_path, prompt_id, manim_code_id, create_time, new_edit_count))
        new_video_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        return new_video_id

    def delete_video(self, video_id):
        '''指定された動画IDの動画をDBから削除する処理
        
        Example:
            video_db = VideoDatabase()
            video_db.delete_video(video_id)
        '''

        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM video WHERE video_id = ?', (video_id,))
        conn.commit()
        conn.close()

    def delete_prompt(self, prompt_id):
        '''指定されたプロンプトIDのプロンプトをDBから削除する処理
        
        Example:
            video_db = VideoDatabase()
            video_db.delete_prompt(prompt_id)
        '''

        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM prompt WHERE prompt_id = ?', (prompt_id,))
        conn.commit()
        conn.close()
        
    def delete_manim_code(self, manim_code_id):
        '''指定されたmanimコードIDのmanimコードをDBから削除する処理
        
        Example:
            video_db = VideoDatabase()
            video_db.delete_manim_code(manim_code_id)
        '''

        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM manim_code WHERE manim_code_id = ?', (manim_code_id,))
        conn.commit()
        conn.close()

    def reset_database(self):
        '''DB内の全データを削除する処理
        
        Example:
            video_db = VideoDatabase()
            video_db.reset_database()
        '''

        conn = sql.connect('/workspaces/ai_agent/back/app/tools/video_data/video_data.db')
        cur = conn.cursor()
        cur.execute('DELETE FROM video')
        cur.execute('DELETE FROM prompt')
        cur.execute('DELETE FROM manim_code')
        cur.execute('DELETE FROM generation')
        conn.commit()
        conn.close()
