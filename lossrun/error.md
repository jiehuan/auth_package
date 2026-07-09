Now we have the full message, and it's unambiguous:

```
tenant=451fd7f5-4b59-4f2f-9b45-16ab9c30036f
client=20a16d7d-b418-4eab-a185-ec5569c22ff0

AADSTS700016: Application with identifier '20a16d7d-b418-4eab-a185-ec5569c22ff0'
was not found in the directory 'XLC'.
```

And Entra's own explanation, verbatim:

> *This can happen if the application has not been installed by the administrator of the tenant or consented to by any user in the tenant. You may have sent your authentication request to the wrong tenant.*

So: **the app registration `20a16d7d...` does not exist in tenant `451fd7f5...` (directory "XLC").**

Your credentials aren't wrong in the sense of being typos. The client ID and secret are real — they just belong to a *different tenant* than the one you're authenticating against. This is the "wrong tenant" branch of 700016.

Two possibilities:

**A. The client ID is right, the tenant ID is wrong.** The app lives in some other AXA directory, and preprod's `ADLS_TENANT_ID` was set to XLC's tenant. Fix: point `ADLS_TENANT_ID` at the tenant that owns the app registration.

**B. The tenant ID is right, but no service principal exists in XLC.** A multi-tenant app registration can be *defined* in tenant A while needing an explicit service principal (enterprise application) provisioned in tenant B before it can authenticate there. Fix: an XLC admin has to consent/install the app.

Which one it is, you can determine in about a minute:

```bash
az login --tenant 451fd7f5-4b59-4f2f-9b45-16ab9c30036f
az ad sp show --id 20a16d7d-b418-4eab-a185-ec5569c22ff0
```

- Errors with "not found" → confirms the SP is absent from XLC. Either it's the wrong tenant (A) or it needs provisioning (B).
- Returns an object → the SP exists and the problem is elsewhere (unlikely given the error).

Then check where the app actually lives:

```bash
az ad app show --id 20a16d7d-b418-4eab-a185-ec5569c22ff0
```

Also worth noting from the log: the account is `zxlc0159adlsppue2dls01.dfs.core.windows.net`, container `z-xlc-0328-axio-pp-ue2-dlc04-axiomaisubmissionprioriti`. That storage account is in the XLC subscription, so the SPN almost certainly *should* be in the XLC tenant — which points at **A**: dev and preprod are using the same client ID, but preprod's storage lives in a tenant where that SPN was never registered. Whoever provisioned dev's SPN needs to do the same for preprod, or you need preprod's own client ID.

The 19–22 second gaps I flagged earlier are just `ClientSecretCredential`'s internal retry backoff, not a NetworkPolicy problem — TLS to `login.microsoftonline.com` is clearly working since Entra is returning structured errors. That earlier hypothesis is dead.

One code note: `_verify_connectivity()` is doing its job — `ADLS client initialization failed; cleaning up` appears in the log, followed by the teardown. That's the new code catching what the old `health_check()` silently swallowed.
