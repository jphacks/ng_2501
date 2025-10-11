import { VideoGenerationFlow } from '@/components/VideoGenerationFlow'

export default function Home() {
    return (
        <main className="min-h-screen bg-gray-50 p-3">
            <div className="max-w-[1600px] mx-auto">
                <div className="bg-white rounded-lg shadow-sm p-4">
                    <VideoGenerationFlow />
                </div>
            </div>
        </main>
    )
}
