export type LearningConcept = {
  id: string;
  name: string;
  type: string;
  importance: number;
  status: "unseen" | "learning" | "understood" | "mastered";
  mastery: number;
};

export type LearningPath = {
  id: string;
  workspace_id: string;
  title: string;
  goal: string;
  status: string;
  created_at: string;
  items: Array<{
    id: string;
    position: number;
    status: string;
    concept: LearningConcept;
  }>;
};

export type NextConcept = {
  concept: LearningConcept | null;
  gaps: Array<{
    concept: LearningConcept;
    blocked_concept: LearningConcept;
    message: string;
  }>;
};

export type QuizQuestion = {
  id: string;
  concept_id: string;
  question: string;
  type: "multiple_choice" | "short_answer";
  choices: string[] | null;
  explanation: string | null;
  difficulty: number;
  source_chunk_ids: string[];
};

export type QuizResult = {
  correct: boolean;
  score: number;
  correct_answer: string;
  explanation: string;
  mastery_before: number;
  mastery_after: number;
  knowledge_status: string;
};

