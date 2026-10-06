/**
 * Friction channel hooks - one query over the read route.
 *
 * The response arrives ALREADY GROUPED by layer and in canonical order, and a layer with
 * no reports is absent from it; this hook passes both facts through untouched. It does not
 * sort, re-group or fill the gaps, because those are display rulings and they live where
 * they are visible, in the page.
 *
 * @module hooks/useFeedback
 * @version 1.0.0
 */

import { useQuery } from '@tanstack/react-query';
import { feedbackApi } from '../services/feedbackApi';
import type { FeedbackLayerGroup } from '../types/feedback';

export const feedbackKeys = {
  /** The whole list; one key so a later realtime handler can invalidate the view with one call. */
  all: ['seatFeedback'] as const,
};

interface FeedbackView {
  /** The groups exactly as the API sent them: canonical order, absent when a layer is empty. */
  groups: FeedbackLayerGroup[];
  /** Rows counted across all groups, as the API counts them. */
  total: number;
}

async function fetchFeedback(): Promise<FeedbackView> {
  const response = await feedbackApi.listFeedback();
  return { groups: response.layers ?? [], total: response.total ?? 0 };
}

/** Every friction report the caller may see, grouped as the API groups them. */
export function useFeedback(): FeedbackView & {
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const query = useQuery({
    queryKey: feedbackKeys.all,
    queryFn: fetchFeedback,
  });

  return {
    groups: query.data?.groups ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
