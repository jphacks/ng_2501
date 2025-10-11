const stripWrappingQuotes = (value: string) => value.replace(/^['"]|['"]$/g, '')

const resolveBackendUrl = () => {
    const raw = process.env.NEXT_PUBLIC_API_URL ?? ''
    return stripWrappingQuotes(raw).trim().replace(/\/$/, '')
}

const fetchVideo = async (videoId: string): Promise<string | null> => { 
    const baseUrl = resolveBackendUrl()
    if (!baseUrl) {
        console.error('Error fetching video: バックエンドのURLが設定されていません')
        return null
    }

    try {
        const path = `${baseUrl}/animation/${videoId}`
        const response = await fetch(
            path,
            {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            },
        )

        if (!response.ok) {
            throw new Error('動画の取得に失敗しました')
        }

        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        return url
    } catch (err) {
        console.error('Error fetching video:', err)
        return null
    }
}

export default fetchVideo
