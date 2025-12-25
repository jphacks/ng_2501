
import { useCallback } from 'react';
import type { VideoData } from '@/app/datas/Video';

const stripWrappingQuotes = (value: string) => value.replace(/^['"]|['"]$/g, '');
const resolveBackendBaseUrl = () => {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? '';
  return stripWrappingQuotes(raw).trim().replace(/\/$/, '');
};
const buildAnimationUrl = (videoId: string) => {
  if (!videoId) {
    return '';
  }
  const backendBase = resolveBackendBaseUrl();
  if (!backendBase) {
    return `/api/animation/${videoId}`;
  }
  return `${backendBase}/api/animation/${videoId}`;
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
  video_path?: string;
  prompt_path?: string;
  manim_code_path?: string;
  video_id?: string; // Changed to string to match backend UUID
}
type SendResponse = {
    ok: boolean;
    message?: string;
}


const API_BASE_URL = `${resolveBackendBaseUrl()}/api`;

/**
 * Custom hook for interacting with the database and animation generation APIs.
 */
export const useDB = () => {
  const handleError = (error: unknown) => {
    console.error("API call failed:", error);
    // In a real app, you might want to set an error state here
    throw error;
  };

  /**
   * Creates a new animation plan and gets a generation_id.
   */
  const planAnimation = useCallback(async (input: ConceptInput): Promise<PlanResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/plan_animation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      return await response.json();
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);

  /**
   * Generates a video from a prompt.
   */
  const generateAnimation = useCallback(async (prompt: GeneratingPlan): Promise<SuccessResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/animation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(prompt),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      return await response.json();
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);

  /**
   * Edits an existing animation.
   */
  const editAnimation = useCallback(async (editData: EditPrompt): Promise<SuccessResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/concept_to_animation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editData),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      return await response.json();
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);

  const sendVideoId = useCallback(async (videoId: string): Promise<SendResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/register_rag/${videoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = (await response.json()) as SendResponse

      if (!response.ok) {
        throw new Error(data?.message ?? '動画ID送信リクエストに失敗しました')
      }
      if (!data?.ok) {
        throw new Error(data?.message ?? '動画ID送信に失敗しました')
      }
      return data
    } catch (error) {
      handleError(error)
      throw error
    }
  }, []);

  const getVideoInfo = useCallback(async (videoId: string): Promise<any> => {
    try {
      const response = await fetch(`${API_BASE_URL}/animation/get_info/${videoId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
      });
      if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      return await response.json();
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);

  const searchVideo = useCallback(async (content: string): Promise<VideoData[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/search_animation`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content }),
      });
      if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.detail}`);
      }
      const data = await response.json() as {
        results?: Array<{ video_id?: string; content?: string }>;
      };
      const results = data.results ?? [];
      return results
        .filter((item): item is { video_id: string; content?: string } => !!item.video_id)
        .map((item) => {
          const videoPath = buildAnimationUrl(item.video_id);
          return {
            videoId: item.video_id,
            videoPath,
            content: item.content ?? '',
          };
        });
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, []);

  return {
    planAnimation,
    generateAnimation,
    editAnimation,
    sendVideoId,
    getVideoInfo,
    searchVideo,
  };
};
