# Release Checklist

Status: skeleton. No release is allowed yet.

## Universal Release Requirements

```text
TASK_BOARD has no unreviewed critical tasks.
HANDOFFS is current.
BLOCKERS has no unresolved P0/P1 blocker.
TEST_MATRIX required checks passed.
DECISIONS contains all architecture changes.
PROJECT_STATE reflects the current phase and gate.
```

## Live Release Requirements

Live release is forbidden until later gates explicitly permit it.

Minimum future requirements:

```text
ledger idempotent
recovery boot tested
safe mode working
book health gate working
risk gate working
paper trading approved
hard stop deterministic
kill switch working
no order without prior persistence
external dead man switch before serious production
```

