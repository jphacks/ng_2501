import { VideoGenerationFlow } from '@/components/VideoGenerationFlow'

export default function Home() {
    return (
        <main className="h-screen bg-gray-50 p-3 flex flex-col">
            <div className="max-w-[1600px] mx-auto flex-1 flex flex-col min-h-0">
                <div className="bg-white rounded-lg shadow-sm p-4 flex-1 flex flex-col min-h-0">
                    <VideoGenerationFlow />
                </div>
            </div>
        </main>
    )
}
