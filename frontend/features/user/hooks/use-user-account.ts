import { useUserAccountContext } from "@/features/user/model/user-account-provider";

export function useUserAccount() {
  return useUserAccountContext();
}
