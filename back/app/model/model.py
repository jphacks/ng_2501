import os
import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, ForeignKey, func, event, Engine,UUID
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# --- データベース設定 (DB非依存) ---

# 環境変数 'DATABASE_URL' から接続文字列を取得
# 例 (PostgreSQL): "postgresql://postgres:postgres@db:5432/devdb"
# 例 (SQLite): "sqlite:///./video_data.db"
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_SQLITE = False

if not DATABASE_URL:
    # 環境変数が設定されていない場合、元のSQLiteパスをデフォルトとして使用
    DB_FILE_PATH = '/workspaces/ai_agent/back/app/tools/video_data/video_data.db'
    DB_DIR = os.path.dirname(DB_FILE_PATH)
    
    # データベースディレクトリが存在しない場合は作成 (SQLiteの場合のみ)
    if not os.path.exists(DB_DIR):
        print(f"Creating directory: {DB_DIR}")
        os.makedirs(DB_DIR, exist_ok=True)
    
    DATABASE_URL = f'sqlite:///{DB_FILE_PATH}'
    IS_SQLITE = True
    print(f"WARNING: DATABASE_URL not set. Using default SQLite database: {DATABASE_URL}")
else:
    IS_SQLITE = "sqlite" in DATABASE_URL.lower()
    print(f"Using DATABASE_URL from environment.")


# SQLAlchemyのベースクラス
Base = declarative_base()

# --- SQLAlchemy モデル定義 ---

class Prompt(Base):
    """
    `prompt` テーブルに対応するモデル。
    """
    __tablename__ = 'prompt'
    prompt_id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_path = Column(String)
    
    # Videoへのリレーション (カスケード削除を有効化)
    videos = relationship("Video", back_populates="prompt", cascade="all, delete")

class ManimCode(Base):
    """
    `manim_code` テーブルに対応するモデル。
    """
    __tablename__ = 'manim_code'
    manim_code_id = Column(Integer, primary_key=True, autoincrement=True)
    manim_code_path = Column(String)
    
    # Videoへのリレーション (カスケード削除を有効化)
    videos = relationship("Video", back_populates="manim_code", cascade="all, delete")

class Generation(Base):
    """
    `generation` テーブルに対応するモデル。
    """
    __tablename__ = 'generation'
    generate_id = Column(Integer, primary_key=True, autoincrement=True)
    generate_time = Column(TIMESTAMP)
    
    # Videoへのリレーション
    videos = relationship("Video", back_populates="generation")


class Video(Base):
    """
    `video` テーブルに対応するモデル。
    """
    __tablename__ = 'video'
    
    # 元のDDL `video_id INTEGER PRIMARY KEY` に対応。
    # SQLiteでは、これにより自動インクリメントと手動ID挿入の両方が可能になる。
    video_id = Column(UUID, primary_key=True)  # UUID文字列として扱うためStringに変更
    
    generate_id = Column(Integer, ForeignKey('generation.generate_id'))
    video_path = Column(String)
    
    # `ondelete='CASCADE'` を指定して、元のDDLの挙動を再現
    prompt_id = Column(Integer, ForeignKey('prompt.prompt_id', ondelete='CASCADE'))
    manim_code_id = Column(Integer, ForeignKey('manim_code.manim_code_id', ondelete='CASCADE'))
    
    generate_time = Column(TIMESTAMP)
    edit_time = Column(TIMESTAMP, nullable=True) # 元のDDLには存在するが、コードでは使われていない
    edit_count = Column(Integer, default=1)

    # 親テーブルへのリレーション
    prompt = relationship("Prompt", back_populates="videos")
    manim_code = relationship("ManimCode", back_populates="videos")
    generation = relationship("Generation", back_populates="videos")

# --- SQLAlchemy エンジンとセッションの設定 ---

# SQLiteで外部キー制約を有効にするためのイベントリスナー
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    *SQLite接続時のみ* PRAGMA foreign_keys=ONを実行し、
    外部キー制約(ON DELETE CASCADEなど)を有効にする。
    """
    if IS_SQLITE:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

class VideoDatabase:
    """
    SQLAlchemyを使用してビデオデータベースを管理するクラス。
    元の`sqlite3`ベースのクラスと同じインターフェースを提供します。
    """
    
    def __init__(self):
        print("Initializing Video Database (SQLAlchemy)...")
        
        try:
            self.engine = create_engine(DATABASE_URL)
            # スレッドローカルなセッションファクトリを作成
            self.Session = scoped_session(sessionmaker(bind=self.engine, autoflush=True, autocommit=False))

            # `create_all` は、テーブルが存在しない場合のみ作成する (DB非依存)
            Base.metadata.create_all(self.engine)
            print("Database tables checked/created successfully.")
        
        except Exception as e:
            print(f"FATAL: Error connecting to database or creating tables: {e}")
            print(f"Database URL used: {DATABASE_URL}")
            print("Please ensure the database server is running, accessible, and credentials are correct.")
            raise

    def _get_session(self):
        """
        新しいセッションを取得するヘルパーメソッド。
        """
        return self.Session()

    def generate_prompt(self) -> int:
        '''生成IDを新規作成する処理
        
        最初の画面からプロンプト確認画面へと遷移する際に呼び出し、生成IDを新規作成する。
        '''
        session = self._get_session()
        try:
            new_generation = Generation(generate_time=datetime.datetime.now())
            session.add(new_generation)
            session.commit()
            return new_generation.generate_id
        except Exception as e:
            session.rollback()
            print(f"Error in generate_prompt: {e}")
            raise
        finally:
            session.close()


    def generate_video(self, generate_id:int, video_id: str, video_path: str, prompt_path: str, manim_code_path: str) -> int:
        '''生成された動画とそれに紐づくプロンプト、manimコードをDBに保存する処理

        生成された動画id、動画ファイルのパス、プロンプトファイルのパス、manimコードファイルのパスを受け取り、DBに保存する。
        '''
        session = self._get_session()
        try:
            create_time = datetime.datetime.now()
            
            # 新しいPromptとManimCodeを作成
            new_prompt = Prompt(prompt_path=prompt_path)
            new_manim_code = ManimCode(manim_code_path=manim_code_path)
            session.add_all([new_prompt, new_manim_code])
            
            # flushして、DBにINSERTを実行し、IDを取得する (コミットはまだしない)
            session.flush()
            
            # 新しいVideoを作成 (video_idを手動で設定)
            new_video = Video(
                video_id=video_id,
                generate_id=generate_id,
                video_path=video_path,
                prompt_id=new_prompt.prompt_id,
                manim_code_id=new_manim_code.manim_code_id,
                generate_time=create_time
                # edit_countはモデルのdefault=1が適用される
            )
            session.add(new_video)
            
            # すべての変更をコミット
            session.commit()
            
            return new_video.video_id
        except Exception as e:
            session.rollback()
            print(f"Error in generate_video: {e}")
            raise
        finally:
            session.close()

    def edit_video(self, prior_video_id: int,  new_video_path: str,new_video_id:str ) -> Optional[int]:
        '''編集された動画を新たにDBに保存する処理
        
        既存の動画IDをもとに、新たに生成された動画ファイルのパスを受け取り、DBに保存する。
        '''
        session = self._get_session()
        try:
            create_time = datetime.datetime.now()
            
            # 編集元の動画情報を取得
            prior_video = session.query(Video).get(prior_video_id)
            
            if not prior_video:
                print(f"Video with id {prior_video_id} not found.")
                return None
            
            new_edit_count = prior_video.edit_count + 1
            
            
            new_video = Video(
                generate_id=prior_video.generate_id,
                video_id=new_video_id,
                video_path=new_video_path,
                prompt_id=prior_video.prompt_id,
                manim_code_id=prior_video.manim_code_id,
                generate_time=create_time,
                edit_count=new_edit_count
            )
            
            session.add(new_video)
            session.commit()
            
            return new_video.video_id
        except Exception as e:
            session.rollback()
            print(f"Error in edit_video: {e}")
            raise
        finally:
            session.close()

    # --- ここから追加 ---

    def get_video(self, video_id: int) -> Optional[Video]:
        '''指定されたvideo_IDのVideoオブジェクトを取得する処理'''
        session = self._get_session()
        try:
            video = session.query(Video).get(video_id)
            return video
        except Exception as e:
            print(f"Error in get_video: {e}")
            return None
        finally:
            session.close()

    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        '''指定されたprompt_IDのPromptオブジェクトを取得する処理'''
        session = self._get_session()
        try:
            prompt = session.query(Prompt).get(prompt_id)
            return prompt
        except Exception as e:
            print(f"Error in get_prompt: {e}")
            return None
        finally:
            session.close()

    def get_manim_code(self, manim_code_id: int) -> Optional[ManimCode]:
        '''指定されたmanim_code_IDのManimCodeオブジェクトを取得する処理'''
        session = self._get_session()
        try:
            manim_code = session.query(ManimCode).get(manim_code_id)
            return manim_code
        except Exception as e:
            print(f"Error in get_manim_code: {e}")
            return None
        finally:
            session.close()

    def get_all_videos(self) -> list[Video]:
        '''すべてのVideoオブジェクトのリストを取得する処理'''
        session = self._get_session()
        try:
            videos = session.query(Video).all()
            return videos
        except Exception as e:
            print(f"Error in get_all_videos: {e}")
            return []
        finally:
            session.close()

    def get_videos_by_generation(self, generate_id: int) -> list[Video]:
        '''指定されたgenerate_idに関連するVideoオブジェクトのリストを取得する処理'''
        session = self._get_session()
        try:
            videos = session.query(Video).filter(Video.generate_id == generate_id).all()
            return videos
        except Exception as e:
            print(f"Error in get_videos_by_generation: {e}")
            return []
        finally:
            session.close()

    # --- ここまで追加 ---

    def _drop_and_recreate_tables(self):
        '''
        【危険】すべてのテーブルを削除し、再作成する。
        スキーマの変更を反映させるために使用する。
        '''
        try:
            print("Dropping all tables...")
            # Base.metadata.drop_allは外部キーの依存関係を考慮してくれる
            Base.metadata.drop_all(self.engine)
            print("All tables dropped.")
            
            print("Recreating all tables...")
            Base.metadata.create_all(self.engine)
            print("All tables recreated successfully.")
            
        except Exception as e:
            print(f"Error in _drop_and_recreate_tables: {e}")
            raise

    def delete_video(self, video_id: int):
        '''指定された動画IDの動画をDBから削除する処理'''
        session = self._get_session()
        try:
            video_to_delete = session.query(Video).get(video_id)
            if video_to_delete:
                session.delete(video_to_delete)
                session.commit()
            else:
                print(f"Video with id {video_id} not found for deletion.")
        except Exception as e:
            session.rollback()
            print(f"Error in delete_video: {e}")
            raise
        finally:
            session.close()

    def delete_prompt(self, prompt_id: int):
        '''指定されたプロンプトIDのプロンプトをDBから削除する処理
        
        関連するVideoもカスケード削除されます。
        '''
        session = self._get_session()
        try:
            prompt_to_delete = session.query(Prompt).get(prompt_id)
            if prompt_to_delete:
                session.delete(prompt_to_delete)
                session.commit()
            else:
                print(f"Prompt with id {prompt_id} not found for deletion.")
        except Exception as e:
            session.rollback()
            print(f"Error in delete_prompt: {e}")
            raise
        finally:
            session.close()
        
    def delete_manim_code(self, manim_code_id: int):
        '''指定されたmanimコードIDのmanimコードをDBから削除する処理
        
        関連するVideoもカスケード削除されます。
        '''
        session = self._get_session()
        try:
            code_to_delete = session.query(ManimCode).get(manim_code_id)
            if code_to_delete:
                session.delete(code_to_delete)
                session.commit()
            else:
                print(f"ManimCode with id {manim_code_id} not found for deletion.")
        except Exception as e:
            session.rollback()
            print(f"Error in delete_manim_code: {e}")
            raise
        finally:
            session.close()

    def reset_database(self):
        '''DB内の指定されたテーブルの全データを削除する処理
        
        元のコードの挙動を再現し、`video`, `prompt`, `manim_code`, `generation`
        の各テーブルから全データを削除します。
        (`video_seq` は元のコードでは削除対象外だったため、ここでも対象外とします)
        '''
        session = self._get_session()
        try:
            # 外部キー制約を考慮し、依存される側(Video)から削除
            session.query(Video).delete()
            session.query(Prompt).delete()
            session.query(ManimCode).delete()
            session.query(Generation).delete()
            
            session.commit()
            print("Database tables (Video, Prompt, ManimCode, Generation) have been reset.")
        except Exception as e:
            session.rollback()
            print(f"Error in reset_database: {e}")
            raise
        finally:
            session.close()

# --- FastAPI 依存性注入のための設定 ---
# (元のコードから変更なし)

_video_db_instance: Optional[VideoDatabase] = None

def get_video_db() -> VideoDatabase:
    """
    VideoDatabaseのシングルトンインスタンスを取得する依存関係関数。
    """
    global _video_db_instance
    if _video_db_instance is None:
        _video_db_instance = VideoDatabase()
    return _video_db_instance


