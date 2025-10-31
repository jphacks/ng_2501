/**
 * ⚠️ テスト用コンポーネント ⚠️
 * 
 * このファイルは動画ダウンロード機能のレビュー・動作確認のための一時的なものです。
 * レビュー完了後、このファイルごと削除してください。
 * 
 * 目的：
 * - 既存の動画を読み込んでダウンロード機能をテストする
 * - バックエンドで新規に動画を生成せずに動作確認できるようにする
 * 
 * 削除時の影響：
 * - このファイルを削除しても本番コードには影響しません
 * - VideoGenerationFlow.tsx から import を削除するだけでOK
 */

'use client'

interface TestVideoLoaderProps {
    onLoadVideo: (videoId: string, promptText: string) => Promise<void>
    isLoading: boolean
}

/**
 * テスト用：既存動画読み込みボタン
 */
export function TestVideoLoader({ onLoadVideo, isLoading }: TestVideoLoaderProps) {
    // ⚠️ テスト用の動画ID（自分の環境の動画IDに変更してください）
    const TEST_VIDEO_ID = '0ad1f000-abcd-468c-bd20-2c3190102d5e'
    const TEST_PROMPT = '単位円と三角関数のデモンストレーション'

    const handleClick = async () => {
        await onLoadVideo(TEST_VIDEO_ID, TEST_PROMPT)
    }

    return (
        <div className="mb-3 p-3 bg-yellow-50 border-2 border-yellow-300 rounded">
            <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">⚠️</span>
                <p className="text-xs font-semibold text-yellow-800">テスト用機能</p>
            </div>
            <p className="text-xs text-gray-600 mb-2">
                既存の動画を読み込んでダウンロード機能をテストします
            </p>
            <p className="text-xs text-gray-500 mb-2">
                動画ID: <code className="bg-gray-100 px-1 rounded">{TEST_VIDEO_ID}</code>
            </p>
            <button
                type="button"
                onClick={handleClick}
                disabled={isLoading}
                className="px-4 py-2 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
                {isLoading ? '読み込み中...' : '動画を読み込む'}
            </button>
        </div>
    )
}

