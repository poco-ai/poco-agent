fix(executor-manager): require tokens for manager APIs

- Protect EM control-plane routes with X-Internal-Token and executor proxy routes with callback tokens
- Send internal headers from Backend EM clients and callback Bearer tokens from executor clients
- Add auth regression coverage for EM routes, Backend callers, and executor manager clients
- Record the token boundary decision and completed hardening plan
