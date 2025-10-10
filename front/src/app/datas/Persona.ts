// Domain層: ペルソナ（学習者プロファイル）のデータ形式

/**
 * ペルソナのデータ形式
 * ユーザーの学習プロファイル
 */
export interface Persona {
    specializedField: string // 専門（興味のある）分野
    learningLevel: string // 学習到達度（例：どの単元まで学習済みか）
}

/**
 * テキスト分析結果
 * ペルソナ分析・翻訳機能の出力
 */
export interface TextAnalysisResult {
    translatedText: string // 翻訳されたテキストデータ
    persona: Persona // 分析されたペルソナ
}
