# FixPilot Safety & Compliance Governance v1.0

Status: planned policy with the first runtime guardrails now implemented.

## Product rule

FixPilot helps the user decide the next safe diagnostic step. It does not replace qualified repair work, override a device manual, or remotely direct a dangerous procedure.

Priority order:

1. Personal and equipment safety.
2. Data protection and recoverability.
3. Accurate, appropriately uncertain diagnosis.
4. Speed, personality, and response brevity.

Technical level only changes explanation depth. It never relaxes a safety requirement.

## Risk model

| Level | Examples | Required behavior | UI |
| --- | --- | --- | --- |
| R0 low | Read-only checks, restart, viewing settings | Give one clear step. | No risk block. |
| R1 medium | Driver rollback/removal, disabling a device, system restore | State the impact and the recovery path; one reversible step at a time. | Yellow triangle: medium risk. |
| R2 high | Registry changes, reinstallation, partitions, BitLocker/TPM, writing to a failing disk | Confirm the target and backup/recovery condition first. Stop if either is unknown. | Yellow triangle: high risk. |
| R3 no remote detail | BIOS/firmware flash, voltage/overclocking, powered disassembly, PSU internals, liquid/smoke/high voltage | Do not give execution detail. Ask the user to power off, stop, and seek qualified help where needed. | Yellow triangle: high risk + stop guidance. |

### Explicitly prohibited remote instructions

- ATX 24-pin PSU jumper / paperclip test: no pin positions, no metal-tool instructions, and never call it simple or safe.
- Formatting, partition rebuilding, initialization, or recovery-software installation on a potentially failing disk.
- Detailed instructions for powered disassembly, exposed high voltage, swollen batteries, smoke, burning smell, or liquid damage.
- Humour or roast-mode output in any risk, data-loss, emergency, or anxiety scenario.

## Response protocol and rendering

When an answer asks the user to execute an R1 action, the model must begin with `[RISK:medium]`. For R2 or R3 it must begin with `[RISK:high]`. R0, questions, and explanations get no marker.

The server strips the marker and emits trusted structured metadata. The client renders a fixed yellow-triangle warning at the top of the same assistant answer, so a model cannot dilute or invent inconsistent safety language.

Fixed copy:

- Medium: This step changes system, driver, or device state. Check the target and recovery path first.
- High: This step may affect data, bootability, or hardware. Back up and confirm the target; stop if unsure.

The composer permanently shows a low-emphasis disclaimer: `FixPilot 可能出错，请核对重要信息。`

## Privacy and data handling

- API keys remain browser-local and diagnostics never record complete keys.
- Images are handled as OCR text only; FixPilot must not claim to see unrecognized visual details or access the user's machine.
- Private conversations remain scoped to the logged-in owner. Sharing is an explicit user action.
- Conversation deletion must remove the corresponding persisted messages.

## Acceptance checklist

- [ ] R0 has no warning block.
- [ ] R1 displays the medium-risk yellow triangle and includes a reversible path.
- [ ] R2/R3 display the high-risk yellow triangle and confirm backup/target before action.
- [ ] Beginner and advanced profiles receive the same safety boundary.
- [ ] No raw `[RISK:*]` marker appears in UI or stored conversation history.
- [ ] Risk answers never trigger memes, `6`, or roast content.
- [ ] Failed model replies save no messages and consume no invite quota.

## Next iteration

1. Add server-side audit events when high-risk terms appear but no risk marker was produced.
2. Add a Settings “Safety & data protection” page showing R0–R3 in user-facing Chinese.
3. Establish a red-team suite covering PSU jumpers, BIOS flash, BitLocker, wrong-disk format, data recovery, powered disassembly, and smoke/liquid damage.
