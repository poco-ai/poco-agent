import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { InputFile } from "@/features/chat/types";

export async function uploadAttachment(file: File): Promise<InputFile> {
  const formData = new FormData();
  formData.append("file", file);

  return apiClient.post<InputFile>(API_ENDPOINTS.attachmentsUpload, formData);
}
