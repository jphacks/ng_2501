import { VideoGenerationFlow } from '@/components/VideoGenerationFlow'

export default function Home() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 p-4 md:p-8">
            <div className="max-w-4xl mx-auto">
                {/* ヘッダー */}
                <div className="text-center mb-8 md:mb-12">
                    <h1 className="text-3xl md:text-5xl font-bold text-gray-800 mb-4">
                        Tips Maker
                    </h1>
                </div>

                {/* メインコンテンツ */}
                <div className="bg-white rounded-xl shadow-xl p-6 md:p-8">
                    <VideoGenerationFlow />
                </div>
            </div>
        </main>
    )
}
