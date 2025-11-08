const stripWrappingQuotes = (value: string) => value.replace(/^['"]|['"]$/g, '')

const resolveBackendUrl = () => {
    const raw = process.env.NEXT_PUBLIC_API_URL ?? ''
    const sanitized = stripWrappingQuotes(raw).trim().replace(/\/$/, '')
    if (sanitized) {
        return sanitized
    }
    if (typeof window !== 'undefined') {
        return window.location.origin
    }
    return ''
}

const buildAnimationUrl = (videoId: string) => {
    if (!videoId) {
        return ''
    }
    const baseUrl = resolveBackendUrl()
    if (!baseUrl) {
        return `/api/animation/${videoId}`
    }
    return `${baseUrl}/api/animation/${videoId}`
}

const fetchVideo = async (videoId: string): Promise<string | null> => { 
    const path = buildAnimationUrl(videoId)
    if (!path) {
        console.error('Error fetching video: videoId が無効です')
        return null
    }
    return path
}

export default fetchVideo
