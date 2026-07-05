import { apiFetch } from './api';

export type Severity = "Minimal" | "Mild" | "Moderate" | "Moderately Severe" | "Severe";

export interface Phq9Submission {
  assessment_id: number;
  timestamp: string;
  score: number;
  severity: Severity;
  q9_flag: boolean;
  disclaimer: string;
}

export interface Phq9HistoryEntry {
  id: number;
  timestamp: string;
  score: number;
  severity: Severity;
  q9_flag: boolean;
}

export async function submitPhq9(responses: number[]): Promise<Phq9Submission> {
  return apiFetch<Phq9Submission>('/api/phq9', {
    method: 'POST',
    body: { responses },
  });
}

export async function getPhq9History(limit = 20): Promise<Phq9HistoryEntry[]> {
  const data = await apiFetch<{ assessments: Phq9HistoryEntry[] }>(`/api/phq9/history?limit=${limit}`);
  return data.assessments || [];
}
