"""
Optional email alerts on new trade signals. Configure via menu option 8
(reuses the same API key setup flow — email is just another provider there).

Every email spells out not just the numbers but WHY the signal fired and
what closes it out, since a bare entry/stop/target doesn't tell you the
exit logic behind the strategy that generated it.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

STRATEGY_EXPLANATIONS = {
    "trend_following": (
        "STRATEGY: Trend-following\n"
        "Triggered by the 9-period EMA crossing the 21-period EMA, confirmed by "
        "price being on the same side of the 50-period SMA. The bet is that the "
        "existing trend continues in this direction.\n\n"
        "SELL / EXIT CONDITIONS:\n"
        "  - Hit the STOP -> close the position. The trend read was wrong; get out.\n"
        "  - Hit the TARGET -> close the position. Take the profit.\n"
        "  - These are fixed levels calculated from ATR at the moment the signal "
        "fired. There is no automatic trailing stop — if you want to lock in "
        "more profit as price moves in your favor, that's a manual decision."
    ),
    "mean_reversion": (
        "STRATEGY: Mean-reversion\n"
        "Triggered by RSI reaching an extreme (oversold or overbought) while "
        "price touches the outer Bollinger Band. The bet is a bounce back "
        "toward the average — NOT a new sustained trend.\n\n"
        "SELL / EXIT CONDITIONS:\n"
        "  - Hit the TARGET -> close the position. This is typically back near "
        "the average/mid-band — the reversion played out, take the profit.\n"
        "  - Hit the STOP -> close the position. The move kept extending "
        "against you instead of reverting; the mean-reversion read was wrong.\n"
        "  - Mean-reversion trades tend to resolve faster than trend trades — "
        "don't expect this one to run for days."
    ),
}


def _build_subject(signals: list) -> str:
    parts = ", ".join(f"{r['side']} {r['symbol']}" for r in signals)
    return f"Signal Engine: {len(signals)} new signal(s) — {parts}"


def _build_body(signals: list) -> str:
    lines = [
        f"Signal Engine found {len(signals)} new trade idea(s).",
        "Nothing was placed — Fidelity has no trading API, so this is a suggestion",
        "for you to place manually and then log (menu option 5) once filled.",
        "=" * 72,
    ]
    for r in signals:
        lines.append("")
        lines.append(f"{r['side']} {r['suggested_qty']} shares of {r['symbol']}")
        lines.append(f"  Entry:   ~${r['entry']}")
        lines.append(f"  Stop:     ${r['stop']}")
        lines.append(f"  Target:   ${r['target']}")
        lines.append(f"  Regime:   {r['regime']}  (ADX {r['adx']}, Bollinger width {r['bb_width_pct']}%)")
        lines.append(f"  Sizing:   {r['risk_reason']}")
        lines.append("")
        lines.append(STRATEGY_EXPLANATIONS.get(r["strategy"], "No strategy explanation available."))
        lines.append("")
        lines.append("-" * 72)
    lines.append("")
    lines.append("Reminder: log the fill in the menu (option 5) as soon as you place it —")
    lines.append("the risk engine's PDT count and sizing depend on that being current.")
    return "\n".join(lines)


def _send(subject: str, body: str) -> bool:
    if not config.EMAIL_ENABLED:
        return False
    msg = MIMEMultipart()
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = config.EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_TO, msg.as_string())
        return True
    except Exception as e:
        print(f"[notifier] Failed to send email: {e}")
        return False


def maybe_send(new_actionable: list):
    """Called from main.run_once() with only the genuinely NEW (not-yet-alerted)
    signals for this scan — silently does nothing if email isn't configured."""
    if not new_actionable or not config.EMAIL_ENABLED:
        return
    if _send(_build_subject(new_actionable), _build_body(new_actionable)):
        print(f"[notifier] Email sent to {config.EMAIL_TO}")


def send_test_email() -> bool:
    body = (
        "This is a test email from your Signal Engine setup.\n\n"
        "If you're reading this, email alerts are configured correctly and "
        "you'll get a message like this (with real trade details) whenever "
        "a new signal is found."
    )
    return _send("Signal Engine: test email", body)
