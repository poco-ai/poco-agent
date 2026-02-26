import { userService } from "@/features/user/api/user-api";

export async function getUserProfileAction() {
  return userService.getProfile();
}

export async function getUserCreditsAction() {
  return userService.getCredits();
}
