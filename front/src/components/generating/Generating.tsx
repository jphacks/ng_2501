'use client'

import { Header } from '../common/Header'

/**
 * Presentation層: 動画生成中の表示コンポーネント
 */
export function Generating() {
    return (
        <div className="space-y-4">
            <Header statusText="生成中" />
            <div className="relative overflow-hidden bg-white/90 backdrop-blur-sm border border-gray-200/50 rounded-lg p-8 text-center shadow-lg">
                {/* 粒子的なグラデーション背景 */}
                <div className="absolute inset-0 opacity-50">
                    {/* 大きい粒子（PCで目立つ） */}
                    <div className="absolute top-[-20%] left-[-10%] w-64 md:w-96 h-64 md:h-96 rounded-full blur-3xl animate-float-1 bg-[#7ab7a4]/60" />
                    <div className="absolute bottom-[-20%] right-[-10%] w-72 md:w-[28rem] h-72 md:h-[28rem] rounded-full blur-3xl animate-float-2 bg-[#ea8b63]/60" />
                    <div className="absolute top-[5%] right-[-10%] w-56 md:w-80 h-56 md:h-80 rounded-full blur-3xl animate-float-3 bg-[#324ea0]/60" />
                    <div className="absolute bottom-[10%] left-[-10%] w-48 md:w-72 h-48 md:h-72 rounded-full blur-3xl animate-float-4 bg-[#7ab7a4]/50" />
                    <div className="absolute top-[35%] left-[25%] w-40 md:w-64 h-40 md:h-64 rounded-full blur-3xl animate-float-5 bg-[#ea8b63]/50" />
                    
                    {/* 追加の小さい粒子（密度を上げる） */}
                    <div className="absolute top-[60%] right-[15%] w-32 md:w-56 h-32 md:h-56 rounded-full blur-2xl animate-float-6 bg-[#324ea0]/45" />
                    <div className="absolute top-[25%] left-[5%] w-36 md:w-60 h-36 md:h-60 rounded-full blur-2xl animate-float-7 bg-[#7ab7a4]/45" />
                    <div className="absolute bottom-[35%] right-[5%] w-40 md:w-64 h-40 md:h-64 rounded-full blur-2xl animate-float-8 bg-[#ea8b63]/45" />
                </div>
                
                {/* コンテンツ */}
                <div className="relative z-10">
                    <div className="flex justify-center mb-4">
                        <img 
                            src="/sudo-generating.gif" 
                            alt="生成中" 
                            className="w-48 h-48 object-contain drop-shadow-lg"
                        />
                    </div>
                    <h3 className="text-lg font-semibold text-[#030405] mb-2">動画を生成中...</h3>
                    <p className="text-sm text-[#030405]/70">
                        数式動画を生成中です（約2~5分）。しばらくお待ちください。
                    </p>
                </div>
                
                <style jsx>{`
                    @keyframes float-1 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        25% { transform: translate(15px, -25px) scale(1.1); }
                        50% { transform: translate(-10px, -40px) scale(0.9); }
                        75% { transform: translate(-20px, -15px) scale(1.05); }
                    }
                    
                    @keyframes float-2 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        25% { transform: translate(-20px, 30px) scale(0.95); }
                        50% { transform: translate(10px, 45px) scale(1.1); }
                        75% { transform: translate(25px, 20px) scale(1); }
                    }
                    
                    @keyframes float-3 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        33% { transform: translate(-30px, 15px) scale(1.12); }
                        66% { transform: translate(25px, -10px) scale(0.92); }
                    }
                    
                    @keyframes float-4 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        30% { transform: translate(25px, -20px) scale(0.95); }
                        60% { transform: translate(-15px, 25px) scale(1.08); }
                    }
                    
                    @keyframes float-5 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        40% { transform: translate(-18px, 22px) scale(1.05); }
                        80% { transform: translate(20px, -18px) scale(0.95); }
                    }
                    
                    .animate-float-1 {
                        animation: float-1 18s ease-in-out infinite;
                    }
                    
                    .animate-float-2 {
                        animation: float-2 16s ease-in-out infinite;
                    }
                    
                    .animate-float-3 {
                        animation: float-3 14s ease-in-out infinite;
                    }
                    
                    .animate-float-4 {
                        animation: float-4 20s ease-in-out infinite;
                    }
                    
                    .animate-float-5 {
                        animation: float-5 22s ease-in-out infinite;
                    }
                    
                    @keyframes float-6 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        35% { transform: translate(22px, -28px) scale(1.08); }
                        70% { transform: translate(-20px, 15px) scale(0.94); }
                    }
                    
                    @keyframes float-7 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        25% { transform: translate(-25px, 30px) scale(0.92); }
                        50% { transform: translate(18px, -22px) scale(1.1); }
                        75% { transform: translate(28px, 12px) scale(1.02); }
                    }
                    
                    @keyframes float-8 {
                        0%, 100% { transform: translate(0, 0) scale(1); }
                        45% { transform: translate(-15px, -25px) scale(1.06); }
                        90% { transform: translate(25px, 20px) scale(0.96); }
                    }
                    
                    .animate-float-6 {
                        animation: float-6 19s ease-in-out infinite;
                    }
                    
                    .animate-float-7 {
                        animation: float-7 17s ease-in-out infinite;
                    }
                    
                    .animate-float-8 {
                        animation: float-8 21s ease-in-out infinite;
                    }
                `}</style>
            </div>
        </div>
    )
}
