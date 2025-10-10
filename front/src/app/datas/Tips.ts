// Domain層: TIPS（学習コンテンツ）のデータ形式

import type { Persona } from './Persona'

/**
 * TIPSのデータ形式
 * READMEの「検索機能」の出力パラメータに準拠
 */
export interface Tips {
    theme: string // TIPSタイトル
    tipContent: string // TIPS内容
    keywords: string[] // TIPSキーワード
}

/**
 * READMEの「○○ To Text入力機能」の入力仕様に準拠
 */
export interface TextAnalysisRequest {
    text: string // テキストデータ
}

/**
 * READMEの「テキストペルソナ分析・翻訳機能」の出力仕様に準拠
 */
export interface TextAnalysisResult {
    translatedText: string // 翻訳されたテキストデータ
    persona: Persona // ペルソナ適応辞書
}
