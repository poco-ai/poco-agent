export interface UserInputQuestionOption {
  label: string;
  value?: string;
  description: string;
}

export interface UserInputQuestion {
  id?: string;
  question: string;
  header: string;
  options: UserInputQuestionOption[];
  multiSelect: boolean;
}

export interface UserInputRequest {
  id: string;
  session_id: string;
  tool_name: string;
  tool_input: {
    questions?: UserInputQuestion[];
    answers?: Record<string, string> | null;
    plan?: string;
    [key: string]: unknown;
  };
  status: string;
  answers?: Record<string, string> | null;
  expires_at: string;
  answered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserInputAnswerRequest {
  answers: Record<string, string>;
}
