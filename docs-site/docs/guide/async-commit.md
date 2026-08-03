# Async Commit

Some Maximo commits take longer than an MCP client is willing to wait.

The clearest case is creating a persistent object through `DMMAXOBJECTCFG`: one nested
payload carries `maxobjectcfg` + `maxtablecfg` + every `maxattributecfg` + `maxsysindexes`,
and Maximo routinely spends **2–4 minutes** on it. MCP clients abort the RPC at around 60
seconds with `-32001 Request timed out` — while Maximo carries on working.

That left agents in the worst possible state: no idea whether the change landed, a Working
Set still locked by the commit that was quietly still running, and a retry that failed.

`ws_commit` solves this by *starting a job and answering immediately* for object structures
known to be slow.

## The contract

The same two steps apply to every Object Structure that uses this path:

```
ws_commit         →  { async: true, asyncId, workingSetId, osName, status: "running" }
ws_commit_status  →  running | succeeded | failed  (+ the full commit result)
```

### 1. Start

```json
{ "id": "ws-acctmpl" }
```

```json
{
  "op_success": true,
  "result": {
    "async": true,
    "asyncId": "cmt_9f2c…",
    "workingSetId": "ws-acctmpl",
    "osName": "DMMAXOBJECTCFG",
    "status": "running",
    "startedAt": "2026-08-02T06:44:00.000Z",
    "staged": { "created": 1, "updated": 0, "deleted": 0 },
    "poll": { "tool": "ws_commit_status", "args": { "asyncId": "cmt_9f2c…" } }
  }
}
```

Nothing is final at this point. The RPC returned; Maximo is still working.

### 2. Poll

```json
{ "asyncId": "cmt_9f2c…" }
```

While running you get `status: "running"` and a live `durationMs`. On a terminal state you
get the complete commit result — hrefs and HTTP status on success, or the Maximo error
(`BMXAA…`) on failure:

```json
{
  "op_success": true,
  "result": {
    "asyncId": "cmt_9f2c…",
    "status": "succeeded",
    "durationMs": 194502,
    "commitResult": { "op_success": true, "result": { "results": [ … ] } }
  }
}
```

Poll roughly every 30 seconds. Object-config commits of 2–4 minutes are normal.

::: tip Lost the asyncId?
Call `ws_commit_status` with the Working Set id instead — it returns that set's most recent
commit job. Results stay pollable for 30 minutes after they finish (`MCP_ASYNC_COMMIT_RETENTION_MS`).
:::

## Locking

The Working Set stays locked for the life of the job, so a second `ws_commit` cannot
double-submit. The refusal now tells you what is going on rather than just saying no:

```json
{
  "op_success": false,
  "error": {
    "reason": "locked",
    "detail": { "workingSetId": "ws-acctmpl", "lockHeldMs": 61204, "asyncId": "cmt_9f2c…", "commitStatus": "running" },
    "action": "poll_ws_commit_status"
  }
}
```

**After a timeout, poll — do not re-commit.** The lock clears automatically when the job
reaches a terminal state, and a Working Set with a commit in flight is never evicted for
inactivity.

Removing the Working Set (`ws_remove`) does **not** cancel a running commit — Maximo is
already working on it. The response returns the `asyncId` so the outcome is still pollable
after the set is gone.

## Which object structures are async

Only `DMMAXOBJECTCFG` by default. Everything else — domains, scripts, applications,
business records — stays synchronous, because async costs an extra round-trip and only
earns its place when a commit genuinely blows the client timeout.

Adding another slow Object Structure is configuration, not a code change:

```bash
MCP_ASYNC_COMMIT_OS=DMMAXOBJECTCFG,DMMAXAPPS
```

Set `MCP_ASYNC_COMMIT_OS=""` to disable async commits entirely.

### Per-call overrides

| Parameter | Effect |
| --- | --- |
| `forceAsync: true` | Run in the background even for an Object Structure that is not on the list |
| `forceSync: true` | Run inline even for one that is — the call may exceed the client timeout |

## Confirmation gate

`requireConfirmation` used to be accepted and then ignored, which left callers waiting on a
prompt that never arrived. It now fails fast: the commit does not run, and the response
carries the staged changes for you to show the user.

```json
{
  "op_success": false,
  "error": {
    "reason": "needs_confirmation",
    "detail": { "staged": { "created": 1, "updated": 0, "deleted": 0 }, "changes": { … } },
    "action": "Present these changes to the user, then call ws_commit again with confirmed:true. Nothing has been sent to Maximo."
  }
}
```

Re-call with `confirmed: true` to proceed.

## When the request never reaches an answer

Async commit solves the *client* timeout. The server's own HTTP call is a separate ceiling —
see [HTTP transport and timeouts](/guide/configuration#http-transport-and-timeouts). Commit
writes run on a pool with no per-phase cap, bounded by `MAXIMO_COMMIT_TIMEOUT_MS`.

If a commit dies without an HTTP response, the result says so rather than guessing:

```json
{
  "op_success": false,
  "error": {
    "reason": "commit_failed",
    "outcome": "unknown",
    "transport_failures": [
      { "code": "UND_ERR_HEADERS_TIMEOUT", "elapsedMs": 304074, "interpretation": "..." }
    ],
    "action": "DO NOT blindly retry. No HTTP response was received, so Maximo's actual outcome is unknown..."
  }
}
```

`outcome: "unknown"` is not a formality. Maximo does not stop working because our socket
closed — a configuration write may well have been applied. **Verify with `os_query_builder`
before committing again**, or you risk a duplicate or a collision.

## Limits

Commit jobs live in the server process. A restart loses them — the same is already true of
Working Sets, so this adds no new failure mode, but after a restart the way to establish
what happened is `os_query_builder` against Maximo, not `ws_commit_status`.

Jobs are also **per process**. Under `http` transport with more than one replica, a poll can
land on an instance that does not own the job and get `commit_job_not_found`; the same applies
to the working-set lock, which is per-process and not a cluster-wide mutex. Run one instance
per client (the stdio default), or use sticky sessions, until these move to a shared store.
