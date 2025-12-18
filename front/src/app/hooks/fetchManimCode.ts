
import { useCallback } from 'react';
import type { VideoData, VideoInfo } from '@/app/datas/Video';

const stripWrappingQuotes = (value: string) => value.replace(/^['"]|['"]$/g, '');
const resolveBackendBaseUrl = () => {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? '';
  return stripWrappingQuotes(raw).trim().replace(/\/$/, '');
};

// Type definitions based on the backend Pydantic models
interface ConceptInput {
  text: string;
  additional_instructions?: string;
}

interface PlanResponse {
  plan: string;
  generation_id: number | null;
}

interface GeneratingPlan {
  generation_id: number;
  planning: string;
}

interface EditPrompt {
  db_id: string;
  prior_inner_video_id: string;
  enhance_prompt: string;
}

interface SuccessResponse {
  ok: boolean;
  message?: string;

}
type SendResponse = {
    ok: boolean;
    message?: string;
}


const API_BASE_URL = `${resolveBackendBaseUrl()}/api`;

/**
 * Custom hook for interacting with the database and animation generation APIs.
 */
export const fetchManimCode = () => {
  const handleError = (error: unknown) => {
    console.error("API call failed:", error);
    // In a real app, you might want to set an error state here
    throw error;
  };

  const fetchManimCode = useCallback(async (manim_code_id: number): Promise<SuccessResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/get_manim_code/${manim_code_id}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      const data = await response.json();
      return {
        ok: true,
        message: data.content,
      };
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);


  return {
    fetchManimCode,
  };
};
