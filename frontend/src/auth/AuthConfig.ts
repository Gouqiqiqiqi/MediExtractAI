/**
 * Demo-mode auth stub.
 *
 * The original deployment used Azure AD (MSAL) — see git history. In demo
 * mode the backend requires no authentication, so the frontend simply skips
 * token acquisition. Re-introduce MSAL here if deploying with real OIDC.
 */

export const DEMO_MODE = true;

export async function acquireToken(): Promise<string | null> {
  return null;
}
