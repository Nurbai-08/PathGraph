export type Citation = {
  index: number;
  source_id: string;
  source_title: string;
  chunk_id: string;
  heading_path: string;
  excerpt: string;
};

export type GroundedAnswer = {
  source_backed_answer: string;
  additional_explanation: string;
  citations: Citation[];
};

export type WhyAnswer = GroundedAnswer & {
  why_it_matters: string;
  path: string[];
};

export type CompareAnswer = {
  concept_a: string;
  concept_b: string;
  similarities: string[];
  differences: string[];
  when_to_use_a: string[];
  when_to_use_b: string[];
  examples: string[];
  citations: Citation[];
};

