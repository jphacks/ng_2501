'use client'

import { useState } from 'react'

interface SearchBarProps {
    onSearch: (query: string) => void
    isGenerating: boolean
}

export function SearchBar({ onSearch, isGenerating }: SearchBarProps) {
    const [query, setQuery] = useState('')

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        onSearch(query)
    }

    return (
        <form onSubmit={handleSearch} className="flex items-center gap-2 p-4">
            <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search for videos by ID..."
                className="w-full px-3 py-2 text-sm border border-[#0A3B7E]/20 rounded focus:ring-2 focus:ring-[#0A3B7E] focus:border-transparent"
                disabled={isGenerating}
            />
            <button
                type="submit"
                disabled={!query.trim() || isGenerating}
                className="px-4 py-2 text-sm font-medium text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90 disabled:bg-[#030405]/30 disabled:cursor-not-allowed transition-colors"
            >
                Search
            </button>
        </form>
    )
}
